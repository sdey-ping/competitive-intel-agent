import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState
from config.settings import ANTHROPIC_API_KEY, CLAUDE_HAIKU_MODEL

# Use a fast, cheap model just for classification
llm = ChatAnthropic(model=CLAUDE_HAIKU_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0)

CLASSIFIER_SYSTEM = """You are an intent classifier for a competitive intelligence tool used by product managers.

Your job is to read a research query and return a JSON object that classifies the user's intent 
into one of four analysis modes. Return ONLY valid JSON — no preamble, no explanation.

The four modes are:

1. "feature_deep_dive"
   When the user asks about a specific named feature, changelog item, capability, or integration.
   Signals: feature names, version numbers, specific capability names, "what is X", "how does X work",
   "explain X", "tell me about X feature", pasting in a feature description/changelog entry.
   
2. "landscape_scan"
   When the user wants a list or overview of recent activity — what shipped, what's new, what changed.
   Signals: "what did X ship", "list features", "what's new", "recent updates", "changelog", 
   "what have they launched", "what features do they have".

3. "strategic"
   When the user wants positioning, direction, comparison, or high-level company analysis.
   Signals: "how does X approach Y", "compare X and Y", "where is X headed", "strategy", 
   "pricing model", "how do they compete", "AI safety", "enterprise motion", "roadmap".

4. "battle_card"
   When the user wants a sales-ready or decision-ready comparison focused on differentiation.
   Signals: "how do we compare", "where are we ahead", "where are we behind", "objections",
   "sales", "battle card", "differentiation", "why choose us over X".

Return this exact JSON shape:
{
  "mode": "<one of the four mode strings>",
  "target_feature": "<exact feature name if mode is feature_deep_dive, else empty string>",
  "reasoning": "<one sentence explaining why you chose this mode>"
}"""

CLASSIFIER_PROMPT = """Research query from user:

\"\"\"{query}\"\"\"

Classify this query into one of the four analysis modes and return JSON."""


# Human-readable labels for each mode (used in UI)
MODE_META = {
    "feature_deep_dive": {
        "label": "Feature Deep Dive",
        "icon": "🔬",
        "description": "Focused analysis of a specific feature or capability",
    },
    "landscape_scan": {
        "label": "Landscape Scan",
        "icon": "📋",
        "description": "Overview of recent launches and feature activity",
    },
    "strategic": {
        "label": "Strategic Analysis",
        "icon": "🧭",
        "description": "Positioning, direction, and high-level comparison",
    },
    "battle_card": {
        "label": "Battle Card",
        "icon": "⚔️",
        "description": "Sales-ready differentiation and objection-handling",
    },
}


def intent_classifier_node(state: AgentState) -> AgentState:
    """
    Classify the research query into one of four analysis modes.
    Sets analysis_mode and target_feature in state.
    If mode_confidence == "user_override", skip classification and use existing mode.
    """
    errors = state.get("errors", [])

    # If user explicitly selected a mode in the UI, respect it
    if state.get("mode_confidence") == "user_override":
        return {
            **state,
            "current_step": "intent_classified",
        }

    research_query = state.get("research_query", "")

    # Default fallback
    analysis_mode = "strategic"
    target_feature = ""

    try:
        prompt = CLASSIFIER_PROMPT.format(query=research_query)
        response = llm.invoke([
            SystemMessage(content=CLASSIFIER_SYSTEM),
            HumanMessage(content=prompt),
        ])

        raw = response.content.strip()

        # Strip markdown code fences if model wraps in them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)
        analysis_mode = parsed.get("mode", "strategic")
        target_feature = parsed.get("target_feature", "")

        # Validate mode is one of the four known values
        if analysis_mode not in MODE_META:
            analysis_mode = "strategic"

    except Exception as e:
        errors.append(f"Intent classification failed, defaulting to strategic mode: {str(e)}")
        analysis_mode = "strategic"
        target_feature = ""

    return {
        **state,
        "analysis_mode": analysis_mode,
        "target_feature": target_feature,
        "mode_confidence": "auto",
        "errors": errors,
        "current_step": "intent_classified",
    }
