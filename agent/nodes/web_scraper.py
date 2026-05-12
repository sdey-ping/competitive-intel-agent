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


def web_scraper_node(state: AgentState) -> AgentState:
    vendors        = state["vendors"]
    research_query = state.get("research_query", "")
    raw_data       = state.get("raw_data", [])
    errors         = state.get("errors", [])
    existing       = {d["vendor_name"]: d for d in raw_data}

    for vendor_name in vendors:
        competitor = get_competitor_by_name(vendor_name)
        if not competitor:
            errors.append(f"Vendor '{vendor_name}' not found in database.")
            continue

        marketing_urls = _split_urls([
            competitor.get("website_url", ""),
            competitor.get("blog_url", ""),
        ])

        technical_urls = _split_urls([
            competitor.get("docs_url", ""),
            competitor.get("changelog_url", ""),
        ])

        # Query-aware scrape: Serper finds relevant deep pages, then we crawl them
        result = scrape_for_vendor(
            vendor_name=vendor_name,
            research_query=research_query,
            marketing_urls=marketing_urls,
            technical_urls=technical_urls,
        )

        if vendor_name in existing:
            existing[vendor_name]["web_content"]  = result["web_content"]
            existing[vendor_name]["docs_content"] = result["docs_content"]
            existing[vendor_name]["source_urls"]  = result["source_urls"]
        else:
            existing[vendor_name] = {
                "vendor_name":       vendor_name,
                "web_content":       result["web_content"],
                "docs_content":      result["docs_content"],
                "youtube_content":   "",
                "scrapbook_content": "",
                "scrapbook_images":  [],
                "source_urls":       result["source_urls"],
            }

    return {
        **state,
        "raw_data":     list(existing.values()),
        "errors":       errors,
        "current_step": "web_scraping_complete",
    }
