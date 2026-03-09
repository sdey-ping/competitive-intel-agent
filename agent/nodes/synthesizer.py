from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState, CompetitorSynthesis
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)

# ── Shared system prompt ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior competitive intelligence analyst for a B2B SaaS product team.
Your job is to produce a deep, technically detailed competitive analysis — not surface-level summaries.

Rules:
- Be specific. Name actual features, protocols, UI patterns, and use cases found in the content.
- Never make generic statements like "they have a strong product" without backing it with specifics.
- If something is not mentioned in the source content, say "Not found in available sources."
- When images are provided, extract every visible detail — button labels, menu items, field names,
  workflow steps, error states, data formats, pricing tiers.
- CRITICAL: The research question is the PRIMARY lens. Every section must directly answer or connect
  back to what was asked. Do not produce generic boilerplate — answer the actual question.
- Prioritize content from the last 90 days over older content when dates are available."""


# ── MODE 1: Feature Deep Dive ──────────────────────────────────────────────────
# Used when user asks about a specific named feature or capability.

FEATURE_DEEP_DIVE_PROMPT = """
Competitor: {vendor_name}
Research Question: {research_query}
Feature in Focus: {target_feature}

=== WEBSITE & BLOG CONTENT ===
{web_content}

=== PRODUCT DOCUMENTATION & CHANGELOG ===
{docs_content}

=== YOUTUBE VIDEO TRANSCRIPTS ===
{youtube_content}

=== PERSONAL SCRAPBOOK NOTES & IMAGES ===
{scrapbook_content}

{image_note}
---

The user wants a DEEP DIVE on a specific feature. Do NOT produce a generic company overview.
Focus entirely on the feature "{target_feature}" and answer the research question: "{research_query}"

## Direct Answer
2-4 sentences directly answering the research question based only on what is in the source content.
Be specific and blunt.

## What This Feature Does
- Exact step-by-step workflow: what does the user do, what does the system do?
- What specific problem does it solve? Be concrete — not "improves efficiency" but exactly what task
  becomes faster/easier/possible that wasn't before.
- What data formats, inputs, or outputs are involved?
- Are there configuration options, limits, or prerequisites mentioned?

## Who It's Built For
- Which persona or role does this feature target? (e.g. IT admin, end user, developer, ops team)
- Which company size or industry is explicitly mentioned or implied?
- What workflow or job-to-be-done does this slot into?

## How It Fits Into Their Product Strategy
- Where does this feature sit in their broader product? (core product, add-on, workflow layer?)
- What does shipping this feature signal about their direction?
- Does this close a gap, expand a market, or defend existing turf?

## How It Compares to Our Product
- Does our product have an equivalent capability? If yes, how does it differ?
- If we don't have this, what is the impact — which customers could use this against us?
- What is our best counter-narrative or differentiation point?

## Watch Points
2-3 specific follow-up questions this feature raises that are worth monitoring next quarter.
"""


# ── MODE 2: Landscape Scan ─────────────────────────────────────────────────────
# Used when user wants a digest of recent launches and feature activity.

LANDSCAPE_SCAN_PROMPT = """
Competitor: {vendor_name}
Research Question: {research_query}

=== WEBSITE & BLOG CONTENT ===
{web_content}

=== PRODUCT DOCUMENTATION & CHANGELOG ===
{docs_content}

=== YOUTUBE VIDEO TRANSCRIPTS ===
{youtube_content}

=== PERSONAL SCRAPBOOK NOTES & IMAGES ===
{scrapbook_content}

{image_note}
---

The user wants a STRUCTURED DIGEST of recent feature activity. Do not write long prose.
Produce a scannable list of everything that has shipped or been announced.

## Direct Answer
1-2 sentences summarizing the most significant recent activity, filtered through: "{research_query}"

## Recent Launches (Last 90 Days Priority)
For each feature or update found, list:
- **Feature Name** — One sentence description. Target segment. Date if available.

Group into sub-sections if there are natural clusters (e.g. Security, Integrations, UI, Platform).
If a date is not available, list it without one. Do not fabricate dates.

## Signals & Themes
What patterns emerge from the launch activity? What problem area are they investing in most heavily?
Keep to 3-5 bullet points, each with a one-line rationale.

## Gaps Visible in the Scan
What areas seem notably absent from recent activity? What are they NOT shipping in?
"""


# ── MODE 3: Strategic Analysis ─────────────────────────────────────────────────
# Full 8-section analysis, but genuinely filtered through the research question.

STRATEGIC_PROMPT = """
Competitor: {vendor_name}
Research Focus: {research_query}

=== WEBSITE & BLOG CONTENT ===
{web_content}

=== PRODUCT DOCUMENTATION & CHANGELOG ===
{docs_content}

=== YOUTUBE VIDEO TRANSCRIPTS ===
{youtube_content}

=== PERSONAL SCRAPBOOK NOTES & IMAGES ===
{scrapbook_content}

{image_note}
---

Produce a DEEP strategic competitive analysis. Every section must be filtered through the lens of
the research question: "{research_query}"

If a section is not relevant to the question, say "Not directly relevant to this research focus"
rather than padding with generic content.

## Direct Answer
2-4 sentences directly answering the research question based only on source content.

## Recent Feature Launches & Updates
Only launches relevant to the research question. For each:
- Feature name, what it does, launch date if available, target segment, technical details.

## Use Cases & Target Segments
- Specific problems this vendor solves, for whom, in context of the research question.
- Concrete use cases with details. Industries and company sizes explicitly targeted.

## Technical Architecture & Protocol Support
- APIs, protocols, standards relevant to the research question.
- Integration capabilities, infrastructure/deployment options.
- Known constraints, deprecations, data formats.

## User Interface & User Experience
- UI paradigm and specific patterns relevant to the research question.
- Onboarding, notable UX patterns, mobile/accessibility support.

## Pricing & Packaging
- Specific tier names, prices, inclusions. Usage limits and metering dimensions.
- Freemium/PLG motion. Enterprise vs self-serve split. Recent pricing changes.

## Strategic Direction & Roadmap Signals
- Where they appear headed in next 6-12 months, in context of the research question.
- Dominant themes in blog/releases/talks. Acquisitions, partnerships, platform bets.

## Gaps vs Your Product
- Where this vendor appears ahead — be specific.
- Where they appear weaker or missing functionality.
- Your best differentiation opportunity based on the research question.

## Key Watch Points
Top 3-5 things to monitor next quarter, directly tied to the research question, with reasoning.
For each: should we build something here? What specifically?
"""


# ── MODE 4: Battle Card ────────────────────────────────────────────────────────
# Tight, sales-ready one-pager per competitor.

BATTLE_CARD_PROMPT = """
Competitor: {vendor_name}
Research Question: {research_query}

=== WEBSITE & BLOG CONTENT ===
{web_content}

=== PRODUCT DOCUMENTATION & CHANGELOG ===
{docs_content}

=== YOUTUBE VIDEO TRANSCRIPTS ===
{youtube_content}

=== PERSONAL SCRAPBOOK NOTES & IMAGES ===
{scrapbook_content}

{image_note}
---

Produce a BATTLE CARD — a tight, sales-ready competitive summary. Be blunt and specific.
This will be used by sales reps and executives who need fast, confident answers.

## Direct Answer
1-2 sentences directly answering: "{research_query}"

## Their Top 3 Strengths
The 3 things {vendor_name} genuinely does well that come up most often in their content.
Each as a single bold claim followed by one sentence of evidence from the sources.

## Their Top 3 Weaknesses
The 3 most notable gaps, limitations, or complaints visible in the content.
Each as a single bold claim followed by one sentence of evidence or rationale.

## Our Differentiation (Where We Win)
3-5 specific points where your product likely has an advantage, inferred from their gaps.
Be concrete — not "better UX" but "no-code flow builder vs their code-required approach."

## Common Objections & Responses
If a prospect says "{vendor_name} has X" — how should we respond?
List 3 likely objections with a one-sentence counter for each.

## Pricing Summary
Their known tiers and limits. What the enterprise motion looks like. Any PLG or freemium.

## One-Line Positioning
A single sentence that defines exactly how we should position against {vendor_name} in a sales call.
"""


# ── Prompt router ──────────────────────────────────────────────────────────────

PROMPT_TEMPLATES = {
    "feature_deep_dive": FEATURE_DEEP_DIVE_PROMPT,
    "landscape_scan":    LANDSCAPE_SCAN_PROMPT,
    "strategic":         STRATEGIC_PROMPT,
    "battle_card":       BATTLE_CARD_PROMPT,
}

# Which sections to extract per mode
SECTIONS_BY_MODE = {
    "feature_deep_dive": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "What This Feature Does"),
        ("use_cases",            "Who It's Built For"),
        ("strategic_direction",  "How It Fits Into Their Product Strategy"),
        ("gap_vs_your_product",  "How It Compares to Our Product"),
        ("watch_points",         "Watch Points"),
    ],
    "landscape_scan": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "Recent Launches"),
        ("strategic_direction",  "Signals & Themes"),
        ("gap_vs_your_product",  "Gaps Visible in the Scan"),
    ],
    "strategic": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "Recent Feature Launches"),
        ("use_cases",            "Use Cases"),
        ("technical_details",    "Technical Architecture"),
        ("ui_ux",                "User Interface"),
        ("pricing_signals",      "Pricing & Packaging"),
        ("strategic_direction",  "Strategic Direction"),
        ("gap_vs_your_product",  "Gaps vs Your Product"),
        ("watch_points",         "Key Watch Points"),
    ],
    "battle_card": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "Their Top 3 Strengths"),
        ("gap_vs_your_product",  "Their Top 3 Weaknesses"),
        ("strategic_direction",  "Our Differentiation"),
        ("use_cases",            "Common Objections"),
        ("pricing_signals",      "Pricing Summary"),
        ("watch_points",         "One-Line Positioning"),
    ],
}


def _build_multimodal_message(prompt_text: str, images_base64: list) -> HumanMessage:
    if not images_base64:
        return HumanMessage(content=prompt_text)
    content_blocks = [{"type": "text", "text": prompt_text}]
    for b64 in images_base64:
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
        })
    return HumanMessage(content=content_blocks)


def synthesizer_node(state: AgentState) -> AgentState:
    raw_data = state.get("raw_data", [])
    research_query = state.get("research_query", "General competitive overview")
    analysis_mode = state.get("analysis_mode", "strategic")
    target_feature = state.get("target_feature", "")
    syntheses: list = []
    errors = state.get("errors", [])

    prompt_template = PROMPT_TEMPLATES.get(analysis_mode, STRATEGIC_PROMPT)
    sections_to_extract = SECTIONS_BY_MODE.get(analysis_mode, SECTIONS_BY_MODE["strategic"])

    for item in raw_data:
        vendor_name = item["vendor_name"]
        scrapbook_images = item.get("scrapbook_images", [])

        total_content = (
            item.get("web_content", "") +
            item.get("docs_content", "") +
            item.get("youtube_content", "") +
            item.get("scrapbook_content", "")
        )
        has_images = len(scrapbook_images) > 0

        if not total_content.strip() and not has_images:
            errors.append(f"No content retrieved for {vendor_name} — skipping synthesis.")
            continue

        try:
            image_note = (
                f"\n=== SCRAPBOOK IMAGES ===\n"
                f"{len(scrapbook_images)} image(s) attached below. Analyze every visible detail.\n"
                if has_images else ""
            )

            prompt = prompt_template.format(
                vendor_name=vendor_name,
                research_query=research_query,
                target_feature=target_feature or research_query,
                web_content=item.get("web_content", "Not available")[:4000],
                docs_content=item.get("docs_content", "Not available")[:4000],
                youtube_content=item.get("youtube_content", "Not available")[:3000],
                scrapbook_content=item.get("scrapbook_content", "Not available")[:2000],
                image_note=image_note,
            )

            human_msg = _build_multimodal_message(prompt, scrapbook_images)
            response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), human_msg])
            raw_synthesis = response.content

            # Build synthesis dict — extract only the sections relevant to this mode
            synthesis: dict = {
                "vendor_name": vendor_name,
                "analysis_mode": analysis_mode,
                "raw_synthesis": raw_synthesis,
                # Defaults for all possible keys
                "direct_answer": "",
                "recent_launches": "",
                "use_cases": "",
                "technical_details": "",
                "ui_ux": "",
                "pricing_signals": "",
                "strategic_direction": "",
                "gap_vs_your_product": "",
                "watch_points": "",
            }

            for state_key, section_heading in sections_to_extract:
                synthesis[state_key] = _extract_section(raw_synthesis, section_heading)

            syntheses.append(synthesis)

            if has_images:
                errors.append(f"✅ {vendor_name}: synthesized with {len(scrapbook_images)} scrapbook image(s)")

        except Exception as e:
            errors.append(f"Synthesis failed for {vendor_name}: {str(e)}")

    return {
        **state,
        "syntheses": syntheses,
        "errors": errors,
        "current_step": "synthesis_complete",
    }


def _extract_section(text: str, section_title: str) -> str:
    lines = text.split("\n")
    capturing = False
    result = []
    for line in lines:
        if section_title.lower() in line.lower() and line.startswith("##"):
            capturing = True
            continue
        if capturing:
            if line.startswith("##"):
                break
            result.append(line)
    return "\n".join(result).strip()
