from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState, DiffResult
from db.database import get_last_report_for_vendor
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.1)

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


def diff_engine_node(state: AgentState) -> AgentState:
    """
    Compare new syntheses against previous stored snapshots.
    Highlights only what is new/changed since last run, filtered by research query.
    """
    syntheses = state.get("syntheses", [])
    research_query = state.get("research_query", "")
    diffs: list[DiffResult] = []
    errors = state.get("errors", [])

    for synthesis in syntheses:
        vendor_name = synthesis["vendor_name"]
        current_synthesis = synthesis["raw_synthesis"]

        last = get_last_report_for_vendor(vendor_name)

        if not last:
            diffs.append({
                "vendor_name": vendor_name,
                "delta_summary": "📋 First run for this vendor — no previous snapshot to compare against.",
                "is_first_run": True,
            })
            continue

        try:
            prompt = DIFF_PROMPT.format(
                vendor_name=vendor_name,
                research_query=research_query,
                prev_date=last.get("created_at", "unknown date"),
                previous=last.get("new_snapshot", "")[:3000],
                current=current_synthesis[:3000],
            )

            response = llm.invoke([
                SystemMessage(content=DIFF_SYSTEM),
                HumanMessage(content=prompt),
            ])

            diffs.append({
                "vendor_name": vendor_name,
                "delta_summary": response.content,
                "is_first_run": False,
            })

        except Exception as e:
            errors.append(f"Diff failed for {vendor_name}: {str(e)}")
            diffs.append({
                "vendor_name": vendor_name,
                "delta_summary": "[Diff computation failed]",
                "is_first_run": False,
            })

    return {
        **state,
        "diffs": diffs,
        "errors": errors,
        "current_step": "diff_complete",
    }
