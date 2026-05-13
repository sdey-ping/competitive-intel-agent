from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.state import AgentState
from agent.tools.scraper_tool import scrape_for_vendor
from db.database import get_competitor_by_name


def _split_urls(raw: list[str]) -> list[str]:
    """Split comma-separated URL strings and return a flat, clean list."""
    urls = []
    for entry in raw:
        for u in entry.split(","):
            u = u.strip()
            if u:
                urls.append(u)
    return urls


def _scrape_one(vendor_name: str, research_query: str, existing: dict) -> tuple:
    """Scrape a single vendor. Returns (vendor_name, result_dict, error_str|None)."""
    competitor = get_competitor_by_name(vendor_name)
    if not competitor:
        return vendor_name, None, f"Vendor '{vendor_name}' not found in database."

    marketing_urls = _split_urls([
        competitor.get("website_url", ""),
        competitor.get("blog_url", ""),
    ])
    technical_urls = _split_urls([
        competitor.get("docs_url", ""),
        competitor.get("changelog_url", ""),
    ])

    result = scrape_for_vendor(
        vendor_name=vendor_name,
        research_query=research_query,
        marketing_urls=marketing_urls,
        technical_urls=technical_urls,
    )

    if vendor_name in existing:
        merged = dict(existing[vendor_name])
        merged["web_content"]  = result["web_content"]
        merged["docs_content"] = result["docs_content"]
        merged["source_urls"]  = result["source_urls"]
    else:
        merged = {
            "vendor_name":       vendor_name,
            "web_content":       result["web_content"],
            "docs_content":      result["docs_content"],
            "youtube_content":   "",
            "scrapbook_content": "",
            "scrapbook_images":  [],
            "source_urls":       result["source_urls"],
        }
    return vendor_name, merged, None


def web_scraper_node(state: AgentState) -> AgentState:
    vendors        = state["vendors"]
    research_query = state.get("research_query", "")
    raw_data       = state.get("raw_data", [])
    errors         = list(state.get("errors", []))
    existing       = {d["vendor_name"]: d for d in raw_data}
    results        = {}

    with ThreadPoolExecutor(max_workers=len(vendors)) as executor:
        futures = {
            executor.submit(_scrape_one, v, research_query, existing): v
            for v in vendors
        }
        for future in as_completed(futures):
            vendor_name, merged, error = future.result()
            if error:
                errors.append(error)
            else:
                results[vendor_name] = merged

    # Preserve original vendor order
    ordered = [results[v] for v in vendors if v in results]

    return {
        **state,
        "raw_data":     ordered,
        "errors":       errors,
        "current_step": "web_scraping_complete",
    }
