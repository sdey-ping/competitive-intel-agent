from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState, DiffResult
from db.database import get_last_report_for_vendor
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

llm = ChatAnthropic(model=CLAUDE_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.1)

DIFF_SYSTEM = """You are a competitive intelligence analyst. Your job is to compare 
two intelligence snapshots for the same competitor and identify only what is genuinely 
new, changed, or removed — specifically as it relates to the research question asked.
Be concise and specific. Ignore changes unrelated to the research focus."""

DIFF_PROMPT = """
Competitor: {vendor_name}
Research Question This Run: {research_query}

PREVIOUS SNAPSHOT (from {prev_date}):
{previous}

NEW SNAPSHOT (today):
{current}

Identify ONLY meaningful changes that are relevant to the research question above.
Format your response as:

🆕 NEW: [Features, announcements, or capabilities that didn't exist before — relevant to the research question]
🔄 CHANGED: [Things that shifted — pricing, positioning, messaging, strategy — relevant to the research question]
🚫 DROPPED: [Topics or initiatives that seem to have been deprioritized or removed]

If nothing meaningful changed relevant to the research question, respond with:
"No significant changes detected since last run for this research focus."

Keep it under 200 words. Be specific, not generic.
"""


def _diff_one(synthesis: dict, research_query: str) -> tuple:
    """Diff a single vendor synthesis against its last snapshot. Returns (diff_dict, error_str|None)."""
    vendor_name       = synthesis["vendor_name"]
    current_synthesis = synthesis["raw_synthesis"]
    last              = get_last_report_for_vendor(vendor_name)

    if not last:
        return {"vendor_name": vendor_name,
                "delta_summary": "📋 First run for this vendor — no previous snapshot to compare against.",
                "is_first_run": True}, None

    try:
        prompt = DIFF_PROMPT.format(
            vendor_name=vendor_name,
            research_query=research_query,
            prev_date=last.get("created_at", "unknown date"),
            previous=last.get("new_snapshot", "")[:8000],
            current=current_synthesis[:8000],
        )
        response = llm.invoke([
            SystemMessage(content=DIFF_SYSTEM),
            HumanMessage(content=prompt),
        ])
        return {"vendor_name": vendor_name,
                "delta_summary": response.content,
                "is_first_run": False}, None

    except Exception as e:
        return {"vendor_name": vendor_name,
                "delta_summary": "[Diff computation failed]",
                "is_first_run": False}, f"Diff failed for {vendor_name}: {str(e)}"


def diff_engine_node(state: AgentState) -> AgentState:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    syntheses      = state.get("syntheses", [])
    research_query = state.get("research_query", "")
    errors         = list(state.get("errors", []))
    results        = {}

    with ThreadPoolExecutor(max_workers=len(syntheses)) as executor:
        futures = {
            executor.submit(_diff_one, s, research_query): s["vendor_name"]
            for s in syntheses
        }
        for future in as_completed(futures):
            vendor_name = futures[future]
            diff, error = future.result()
            if error:
                errors.append(error)
            results[vendor_name] = diff

    # Preserve original vendor order
    diffs = [results[s["vendor_name"]] for s in syntheses if s["vendor_name"] in results]

    return {
        **state,
        "diffs":        diffs,
        "errors":       errors,
        "current_step": "diff_complete",
    }
