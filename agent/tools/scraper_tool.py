"""
scraper_tool.py — Query-aware deep crawler with Serper seeding.

Strategy per vendor domain:
  1. Serper: query "<vendor> <topic> site:<domain>" → seed URLs ranked by relevance
  2. BFS crawl up to MAX_DEPTH=5 levels from each seed, staying on same domain
  3. At each level, score all discovered links by query-word overlap in URL + page title
     and only follow the TOP_K_PER_LEVEL most promising ones (avoids crawl explosion)
  4. Content scoring: pages are kept only if they contain enough query-relevant terms
  5. Fallback: if Serper unavailable, use configured root URLs as BFS seeds directly
  6. Returns: web_content, docs_content, source_urls[]
"""

import time
import requests
from collections import deque
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

try:
    from config.settings import SERPER_API_KEY
except ImportError:
    SERPER_API_KEY = ""

# ── Crawler config ─────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SERPER_ENDPOINT    = "https://google.serper.dev/search"
SERPER_NUM_SEEDS   = 8      # seed URLs per domain from Serper
MAX_DEPTH          = 5      # BFS levels deep from each seed
TOP_K_PER_LEVEL    = 4      # max links to follow per page at each BFS level
MAX_PAGES_TOTAL    = 40     # hard cap on total pages fetched per domain
MAX_CHARS_PER_PAGE = 8000   # truncate each page to keep context manageable
MIN_CONTENT_SCORE  = 2      # min query-word hits required to keep a page
REQUEST_TIMEOUT    = 12     # seconds per HTTP request
CRAWL_DELAY        = 0.25   # seconds between requests
JINA_PREFIX        = "https://r.jina.ai/"
JINA_TIMEOUT       = 30     # Jina renders JS server-side — needs more time
SPA_SHELL_THRESHOLD = 200   # chars below which we treat a page as an unrendered SPA shell

# URL path segments that signal high-value product content — prioritized in BFS
HIGH_VALUE_PATTERNS = [
    "/docs/", "/documentation/", "/changelog/", "/release-notes/",
    "/blog/", "/news/", "/updates/", "/features/", "/product/",
    "/help/", "/support/", "/learn/", "/guide/", "/reference/",
    "/platform/", "/solutions/", "/workflows/", "/integrations/",
    "/use-cases/", "/usecases/", "/case-studies/", "/how-it-works/",
    "/api/", "/sdk/", "/developer/", "/developers/", "/technical/",
    "/security/", "/compliance/", "/enterprise/", "/pricing/",
    "/whitepaper/", "/resources/", "/knowledge-base/", "/kb/",
]

# URL patterns to skip — these never contain useful product content
SKIP_PATTERNS = [
    "/login", "/signup", "/register", "/cart", "/checkout",
    "/cdn-cgi/", "/static/", "/assets/", "/images/", "/img/",
    ".jpg", ".png", ".gif", ".svg", ".ico", ".pdf", ".zip",
    ".css", ".js", "/wp-admin", "/tag/", "/author/", "/page/",
    "javascript:", "mailto:", "tel:", "#",
    "/privacy", "/terms", "/legal", "/cookie",
    "/careers", "/jobs", "/about-us", "/contact",
]


# ── URL utilities ──────────────────────────────────────────────────────────────

def _normalize(url: str) -> str:
    """Strip fragment and trailing slash for dedup purposes."""
    p = urlparse(url)
    clean = p._replace(fragment="").geturl()
    return clean.rstrip("/")


def _should_skip(url: str) -> bool:
    lower = url.lower()
    return any(pat in lower for pat in SKIP_PATTERNS)


def _is_high_value(url: str) -> bool:
    lower = url.lower()
    return any(pat in lower for pat in HIGH_VALUE_PATTERNS)


def _url_score(url: str, query_words: set) -> int:
    """
    Score a URL by relevance to the research query.
    Uses URL path + filename words. High-value path patterns add a bonus.
    """
    path = urlparse(url).path.lower()
    # Convert path separators/hyphens/underscores to spaces for word matching
    path_words = set(path.replace("/", " ").replace("-", " ").replace("_", " ").split())
    score = sum(1 for w in query_words if len(w) > 3 and w in path_words)
    if _is_high_value(url):
        score += 2
    return score


# ── Serper ────────────────────────────────────────────────────────────────────

def _serper_search(vendor_name: str, research_query: str, domain: str) -> list[str]:
    """
    Search Google via Serper restricted to domain.
    Returns ranked list of deep page URLs, or [] on any failure.
    """
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.post(
            SERPER_ENDPOINT,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": f"{vendor_name} {research_query} site:{domain}", "num": SERPER_NUM_SEEDS},
            timeout=10,
        )
        resp.raise_for_status()
        return [
            r["link"] for r in resp.json().get("organic", [])
            if domain in r.get("link", "")
        ]
    except Exception:
        return []


# ── SPA detection & Jina fallback ────────────────────────────────────────────

def _is_spa_shell(text: str) -> bool:
    """True if extracted text is too thin to be real content — likely an unrendered JS app."""
    return len(text.strip()) < SPA_SHELL_THRESHOLD


def _fetch_via_jina(url: str) -> tuple[str, str]:
    """
    Fallback fetch via Jina Reader (r.jina.ai). Renders JS server-side and returns
    clean Markdown text. Does not return internal links — BFS link discovery is lost
    for this page, but Serper seeds cover the most important pages anyway.
    """
    try:
        jina_url = JINA_PREFIX + url
        resp = requests.get(
            jina_url,
            headers={"Accept": "text/plain", "User-Agent": HEADERS["User-Agent"]},
            timeout=JINA_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.text.strip()[:MAX_CHARS_PER_PAGE]
        return url, text
    except Exception as e:
        return url, f"[Jina fetch error: {str(e)}]"


# ── Page fetcher ──────────────────────────────────────────────────────────────

def _fetch_page(url: str) -> tuple[str, str, list[str]]:
    """
    Fetch a page. Returns (title, clean_text, internal_links[]).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                            allow_redirects=True)
        resp.raise_for_status()

        # Skip non-HTML responses
        ct = resp.headers.get("content-type", "")
        if "html" not in ct:
            return "", "", []

        soup = BeautifulSoup(resp.text, "lxml")
        base_domain = urlparse(url).netloc

        # Collect internal links before stripping tags
        raw_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            full = urljoin(url, href)
            p = urlparse(full)
            if p.netloc == base_domain and p.scheme in ("http", "https"):
                normalized = _normalize(full)
                if not _should_skip(normalized):
                    raw_links.append(normalized)

        # Page title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Strip noise
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "iframe", "noscript", "svg",
                          "button", "input", "meta", "link", "picture"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 40]
        clean = "\n".join(lines)[:MAX_CHARS_PER_PAGE]

        if _is_spa_shell(clean):
            _, jina_text = _fetch_via_jina(url)
            return title, jina_text, []

        return title, clean, list(dict.fromkeys(raw_links))

    except Exception as e:
        return "", f"[Fetch error: {str(e)}]", []


# ── Content relevance scorer ──────────────────────────────────────────────────

def _content_score(text: str, query_words: set) -> int:
    """Count how many distinct query words appear in the page text."""
    lower = text.lower()
    return sum(1 for w in query_words if len(w) > 3 and w in lower)


# ── BFS deep crawler ──────────────────────────────────────────────────────────

def _bfs_crawl(
    seed_urls: list[str],
    domain: str,
    research_query: str,
    visited: set,
) -> tuple[str, list[str]]:
    """
    BFS crawl from seed_urls up to MAX_DEPTH levels.

    At each level:
      - Score all discovered child links by query relevance
      - Follow only the TOP_K_PER_LEVEL highest-scoring ones
      - Keep pages whose content scores >= MIN_CONTENT_SCORE

    Returns (combined_text, visited_url_list).
    """
    query_words = set(research_query.lower().split())
    pages_fetched = 0
    content_parts = []
    visited_urls = []

    # BFS queue: (url, depth)
    queue = deque()
    for url in seed_urls:
        n = _normalize(url)
        if n not in visited:
            queue.append((n, 0))
            visited.add(n)

    while queue and pages_fetched < MAX_PAGES_TOTAL:
        url, depth = queue.popleft()

        time.sleep(CRAWL_DELAY)
        title, text, child_links = _fetch_page(url)
        pages_fetched += 1

        # Score and keep page content if relevant
        if text and not text.startswith("[Fetch error"):
            score = _content_score(text, query_words)
            if score >= MIN_CONTENT_SCORE or depth == 0:
                # depth==0 seeds always kept (they came from Serper/config)
                header = f"--- [{title or url}] {url} ---"
                content_parts.append(f"{header}\n{text}")
                visited_urls.append(url)

        # Enqueue children if not at max depth
        if depth < MAX_DEPTH:
            # Score and rank child links
            scored = sorted(
                [(l, _url_score(l, query_words)) for l in child_links if l not in visited],
                key=lambda x: x[1],
                reverse=True,
            )
            added = 0
            for child_url, _ in scored:
                if added >= TOP_K_PER_LEVEL:
                    break
                if child_url not in visited:
                    visited.add(child_url)
                    queue.append((child_url, depth + 1))
                    added += 1

    return "\n\n".join(content_parts), visited_urls


# ── Main public API ───────────────────────────────────────────────────────────

def scrape_url(url: str) -> str:
    """Simple single-URL scrape. Backward-compatible."""
    _, text, _ = _fetch_page(url)
    return text


def scrape_multiple(urls: list[str]) -> str:
    """Simple multi-URL scrape without Serper/crawl. Backward-compatible."""
    parts = []
    for url in urls:
        if url:
            _, text, _ = _fetch_page(url)
            if text:
                parts.append(f"--- Source: {url} ---\n{text}")
    return "\n\n".join(parts)


def scrape_for_vendor(
    vendor_name: str,
    research_query: str,
    marketing_urls: list[str],
    technical_urls: list[str],
) -> dict:
    """
    Query-aware deep crawl for a single vendor.

    Per domain in marketing_urls and technical_urls:
      1. Serper finds the top relevant deep-link seeds for the research query
      2. BFS crawl up to 5 levels deep, following the most query-relevant links
      3. Pages with insufficient query-word density are discarded
      4. Falls back to direct BFS from configured URL if Serper unavailable

    Returns:
        {
            "web_content":  str,        # content from marketing URL domains
            "docs_content": str,        # content from technical URL domains
            "source_urls":  list[str],  # every URL visited (for reference links)
        }
    """
    visited: set      = set()
    web_parts: list   = []
    docs_parts: list  = []
    all_visited: list = []

    def _process_bucket(seed_urls: list[str], bucket: list):
        for seed_url in seed_urls:
            if not seed_url:
                continue
            domain = urlparse(seed_url).netloc
            if not domain:
                continue

            # Get query-relevant seed URLs via Serper
            serper_seeds = _serper_search(vendor_name, research_query, domain)

            # Always include the configured URL as a seed too
            all_seeds = list(dict.fromkeys(
                serper_seeds + [_normalize(seed_url)]
            ))

            # BFS deep crawl from all seeds
            content, urls = _bfs_crawl(all_seeds, domain, research_query, visited)
            if content:
                bucket.append(content)
            all_visited.extend(urls)

    _process_bucket(marketing_urls, web_parts)
    _process_bucket(technical_urls, docs_parts)

    return {
        "web_content":  "\n\n".join(web_parts),
        "docs_content": "\n\n".join(docs_parts),
        "source_urls":  list(dict.fromkeys(all_visited)),
    }
