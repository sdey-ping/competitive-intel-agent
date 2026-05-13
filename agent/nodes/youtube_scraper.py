from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.state import AgentState
from agent.tools.youtube_tool import fetch_channel_transcripts
from db.database import get_competitor_by_name


def _fetch_one(vendor_name: str, raw_data: dict) -> tuple:
    """Fetch YouTube transcripts for a single vendor. Returns (vendor_name, updated_entry)."""
    competitor = get_competitor_by_name(vendor_name)
    if not competitor:
        return vendor_name, None

    channel = competitor.get("youtube_channel", "")
    youtube_content = fetch_channel_transcripts(channel, max_videos=5) if channel else ""

    if vendor_name in raw_data:
        merged = dict(raw_data[vendor_name])
        merged["youtube_content"] = youtube_content
    else:
        merged = {
            "vendor_name":     vendor_name,
            "web_content":     "",
            "youtube_content": youtube_content,
            "scrapbook_content": "",
        }
    return vendor_name, merged


def youtube_scraper_node(state: AgentState) -> AgentState:
    vendors  = state["vendors"]
    raw_data = {d["vendor_name"]: d for d in state.get("raw_data", [])}
    errors   = list(state.get("errors", []))
    results  = {}

    with ThreadPoolExecutor(max_workers=len(vendors)) as executor:
        futures = {
            executor.submit(_fetch_one, v, raw_data): v
            for v in vendors
        }
        for future in as_completed(futures):
            vendor_name, merged = future.result()
            if merged is not None:
                results[vendor_name] = merged

    # Preserve original vendor order
    ordered = [results[v] for v in vendors if v in results]

    return {
        **state,
        "raw_data": ordered,
        "errors":   errors,
        "current_step": "youtube_scraping_complete",
    }
