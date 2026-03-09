from agent.state import AgentState
from agent.tools.scraper_tool import scrape_multiple
from db.database import get_competitor_by_name


def web_scraper_node(state: AgentState) -> AgentState:
    vendors = state["vendors"]
    raw_data = state.get("raw_data", [])
    errors = state.get("errors", [])
    existing = {d["vendor_name"]: d for d in raw_data}

    for vendor_name in vendors:
        competitor = get_competitor_by_name(vendor_name)
        if not competitor:
            errors.append(f"Vendor '{vendor_name}' not found in database.")
            continue

        marketing_urls = [u for u in [
            competitor.get("website_url", ""),
            competitor.get("blog_url", ""),
        ] if u]

        technical_urls = [u for u in [
            competitor.get("docs_url", ""),
            competitor.get("changelog_url", ""),
        ] if u]

        web_content = scrape_multiple(marketing_urls) if marketing_urls else ""
        docs_content = scrape_multiple(technical_urls) if technical_urls else ""

        # Track all URLs actually scraped — surfaced in UI as reference links
        all_urls = [u for u in marketing_urls + technical_urls if u]

        if vendor_name in existing:
            existing[vendor_name]["web_content"] = web_content
            existing[vendor_name]["docs_content"] = docs_content
            existing[vendor_name]["source_urls"] = all_urls
        else:
            existing[vendor_name] = {
                "vendor_name": vendor_name,
                "web_content": web_content,
                "docs_content": docs_content,
                "youtube_content": "",
                "scrapbook_content": "",
                "scrapbook_images": [],
                "source_urls": all_urls,
            }

    return {
        **state,
        "raw_data": list(existing.values()),
        "errors": errors,
        "current_step": "web_scraping_complete",
    }
