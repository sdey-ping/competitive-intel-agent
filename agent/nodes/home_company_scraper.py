import json
import os
from agent.state import AgentState
from agent.tools.scraper_tool import scrape_for_vendor
from db.database import get_home_company_context, save_home_company_context

YOUR_COMPANY_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "your_company.json"
)


def _load_your_company() -> dict:
    path = os.path.abspath(YOUR_COMPANY_FILE)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def home_company_scraper_node(state: AgentState) -> AgentState:
    """
    Scrape your own product's website, blog, docs, and changelog.
    Result is cached for 24 hours — re-scrapes automatically when stale so the
    synthesizer always has up-to-date context for 'our product' comparisons.
    """
    errors = state.get("errors", [])

    cached = get_home_company_context()
    if cached:
        return {
            **state,
            "home_company_content": cached,
            "current_step": "home_company_loaded_from_cache",
        }

    config = _load_your_company()
    if not config:
        errors.append("config/your_company.json not found — 'our product' context unavailable.")
        return {
            **state,
            "home_company_content": "",
            "errors": errors,
            "current_step": "home_company_scrape_skipped",
        }

    company_name = config.get("company_name", "Our Company")
    research_query = state.get("research_query", "product capabilities and recent updates")

    marketing_urls = [u for u in [
        config.get("website_url", ""),
        config.get("blog_url", ""),
    ] if u]

    technical_urls = [u for u in [
        config.get("docs_url", ""),
        config.get("changelog_url", ""),
    ] if u]

    try:
        result = scrape_for_vendor(
            vendor_name=company_name,
            research_query=research_query,
            marketing_urls=marketing_urls,
            technical_urls=technical_urls,
        )
        content = "\n\n".join(filter(None, [
            result.get("web_content", ""),
            result.get("docs_content", ""),
        ]))
        save_home_company_context(content)
    except Exception as e:
        errors.append(f"Home company scrape failed: {str(e)}")
        content = ""

    return {
        **state,
        "home_company_content": content,
        "errors": errors,
        "current_step": "home_company_scrape_complete",
    }
