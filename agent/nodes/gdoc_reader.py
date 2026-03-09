from agent.state import AgentState
from agent.tools.gdrive_tool import get_scrapbook_section


def gdoc_reader_node(state: AgentState) -> AgentState:
    """
    Read personal scrapbook notes from Google Doc for each vendor.
    Only runs if use_scrapbook is True in state (user opt-in toggle in UI).
    """
    # ── Respect user toggle — skip entirely if disabled ───────────────────────
    if not state.get("use_scrapbook", False):
        return {
            **state,
            "current_step": "gdoc_reading_complete",
        }

    vendors = state["vendors"]
    raw_data = {d["vendor_name"]: d for d in state.get("raw_data", [])}
    errors = state.get("errors", [])

    for vendor_name in vendors:
        result = get_scrapbook_section(vendor_name)
        scrapbook_text = result.get("text", "")
        scrapbook_images = result.get("images", [])

        if vendor_name in raw_data:
            raw_data[vendor_name]["scrapbook_content"] = scrapbook_text
            raw_data[vendor_name]["scrapbook_images"] = scrapbook_images
        else:
            raw_data[vendor_name] = {
                "vendor_name": vendor_name,
                "web_content": "",
                "youtube_content": "",
                "scrapbook_content": scrapbook_text,
                "scrapbook_images": scrapbook_images,
                "source_urls": [],
            }

    return {
        **state,
        "raw_data": list(raw_data.values()),
        "errors": errors,
        "current_step": "gdoc_reading_complete",
    }
