from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState, CompetitorSynthesis
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)

SYSTEM_PROMPT = """You are a senior competitive intelligence analyst for a B2B SaaS product team.
Your job is to produce deep, technically detailed, research-specific analysis — never surface-level summaries.

Rules:
- Be specific. Name actual features, protocols, UI patterns, use cases, and data found in the content.
- Never make generic statements without backing them with specifics from the source.
- If something is not mentioned in the source content, say "Not found in available sources." — do NOT invent.
- When images are provided, extract every visible detail: button labels, menu items, field names,
  workflow steps, error states, data formats, pricing tiers.
- CRITICAL: The research question is the PRIMARY lens. Do not produce generic boilerplate.
  If the user asks for a SWOT, produce a full structured SWOT with multiple points per quadrant.
  If the user asks for a comparison, produce a detailed point-by-point comparison.
  Match the depth and structure of your output to what the question is actually asking for.
- Prioritize content from the last 90 days when dates are available.
- The Direct Answer section must fully answer the research question — not just 2 sentences.
  If the question requires a SWOT, the Direct Answer IS the full SWOT. If it requires a comparison,
  the Direct Answer IS the full comparison. Match length to complexity."""


# ── MODE 1: Feature Deep Dive ──────────────────────────────────────────────────

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
Focus entirely on the feature "{target_feature}" and answer: "{research_query}"

## Direct Answer
Directly and fully answer the research question based only on source content. Be specific and blunt.
If it asks how something works, explain it step by step. If it asks for a comparison, compare directly.
Length should match the complexity of the question — do not artificially limit this section.

## What This Feature Does
- Exact step-by-step workflow: what does the user do, what does the system do?
- What specific problem does it solve? Be concrete.
- What data formats, inputs, outputs are involved?
- Configuration options, limits, prerequisites?

## Who It's Built For
- Specific persona/role targeted (IT admin, developer, ops team, etc.)
- Company size or industry explicitly mentioned or implied
- Workflow or job-to-be-done this slots into

## How It Fits Into Their Product Strategy
- Where does this feature sit in their broader product?
- What does shipping this signal about their direction?
- Does this close a gap, expand a market, or defend existing turf?

## How It Compares to Our Product
- Equivalent capability in our product? How does it differ?
- If we lack this — which customers could use it against us?
- Our best counter-narrative or differentiation point?

## Watch Points
2-3 specific follow-up questions worth monitoring next quarter.

## Reference Links
List the specific page URLs from the source content that contained relevant information.
RULES: (1) Use full deep URLs — NOT root domains like https://okta.com.
(2) Format each as: - [Descriptive page title](https://full-url-to-specific-page)
(3) Only include URLs visibly present in the source content above.
(4) If no specific deep-link URLs appear in the source, write "No specific URLs found in source."
"""


# ── MODE 2: Landscape Scan ─────────────────────────────────────────────────────

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

The user wants a STRUCTURED DIGEST of recent feature activity. Produce a scannable list.

## Direct Answer
1-2 sentences summarizing the most significant recent activity relevant to: "{research_query}"

## Recent Launches (Last 90 Days Priority)
For each feature or update found:
- **Feature Name** — One sentence description. Target segment. Date if available.
Group into sub-sections if natural clusters exist (Security, Integrations, UI, Platform).
Do not fabricate dates.

## Signals & Themes
3-5 bullet points on what patterns emerge from the launch activity, each with a one-line rationale.

## Gaps Visible in the Scan
What areas seem notably absent from recent activity?

## Reference Links
List the specific page URLs from the source content that contained relevant information.
RULES: (1) Use full deep URLs — NOT root domains like https://okta.com.
(2) Format each as: - [Descriptive page title](https://full-url-to-specific-page)
(3) Only include URLs visibly present in the source content above.
(4) If no specific deep-link URLs appear in the source, write "No specific URLs found in source."
"""


# ── MODE 3: Strategic Analysis ─────────────────────────────────────────────────

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

Produce a DEEP strategic competitive analysis filtered through: "{research_query}"

IMPORTANT: The "Direct Answer" section must FULLY answer what the user asked.
- If they asked for a SWOT analysis → produce a complete SWOT with 3-5 points per quadrant,
  each with specific evidence from the source content. Do not summarize into 2 sentences.
- If they asked for a comparison → produce a structured point-by-point comparison.
- If they asked a strategic question → provide a thorough, multi-paragraph answer with evidence.
The Direct Answer is the primary deliverable. Make it as long as the question demands.

If a supporting section below is not relevant to the question, write exactly:
"Not directly relevant to this research focus." — do not pad with generic content.

## Direct Answer
[Fully answer "{research_query}" here — match structure and depth to what was asked.
For a SWOT: use ### Strengths, ### Weaknesses, ### Opportunities, ### Threats sub-sections.
For a comparison: use structured sub-sections per dimension being compared.
Each point must cite specific features, behaviors, or data from the source content.]

## Recent Feature Launches & Updates
Only launches directly relevant to the research question. For each:
- Feature name, what it does, launch date if available, target segment, technical details.
If not relevant: "Not directly relevant to this research focus."

## Use Cases & Target Segments
Specific problems this vendor solves, for whom, in context of the research question.
Concrete use cases with details. Industries and company sizes explicitly targeted.
If not relevant: "Not directly relevant to this research focus."

## Technical Architecture & Protocol Support
APIs, protocols, standards, integration capabilities relevant to the research question.
Known constraints, deprecations, data formats.
If not relevant: "Not directly relevant to this research focus."

## Pricing & Packaging
Specific tier names, prices, inclusions, usage limits.
Enterprise vs self-serve split. Recent pricing changes.
If not relevant: "Not directly relevant to this research focus."

## Strategic Direction & Roadmap Signals
Where they appear headed in the next 6-12 months, in context of the research question.
Dominant themes in blog/releases/talks. Acquisitions, partnerships, platform bets.
If not relevant: "Not directly relevant to this research focus."

## Gaps vs Your Product
Where this vendor appears ahead — be specific.
Where they appear weaker or missing functionality.
Best differentiation opportunity based on the research question.
If not relevant: "Not directly relevant to this research focus."

## Key Watch Points
Top 3-5 things to monitor next quarter, tied to the research question.
For each: should we build something here? What specifically?
If not relevant: "Not directly relevant to this research focus."

## Reference Links
List the specific page URLs from the source content that contained relevant information.
RULES: (1) Use full deep URLs — NOT root domains like https://okta.com.
(2) Format each as: - [Descriptive page title](https://full-url-to-specific-page)
(3) Only include URLs visibly present in the source content above.
(4) If no specific deep-link URLs appear in the source, write "No specific URLs found in source."
"""


# ── MODE 4: Battle Card ────────────────────────────────────────────────────────

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

Produce a BATTLE CARD — tight, sales-ready, blunt. Used by sales reps and executives.

## Direct Answer
1-2 sentences directly answering: "{research_query}"

## Their Top 3 Strengths
Each as a bold claim + one sentence of evidence from the sources.

## Their Top 3 Weaknesses
Each as a bold claim + one sentence of evidence or rationale from the sources.

## Our Differentiation (Where We Win)
3-5 specific points of advantage, inferred from their gaps. Be concrete.

## Common Objections & Responses
3 likely objections a prospect might raise, with a one-sentence counter for each.

## Pricing Summary
Known tiers and limits. Enterprise motion. PLG or freemium.

## One-Line Positioning
A single sentence defining how to position against {vendor_name} in a sales call.

## Reference Links
List the specific page URLs from the source content that contained relevant information.
RULES: (1) Use full deep URLs — NOT root domains like https://okta.com.
(2) Format each as: - [Descriptive page title](https://full-url-to-specific-page)
(3) Only include URLs visibly present in the source content above.
(4) If no specific deep-link URLs appear in the source, write "No specific URLs found in source."
"""


PROMPT_TEMPLATES = {
    "feature_deep_dive": FEATURE_DEEP_DIVE_PROMPT,
    "landscape_scan":    LANDSCAPE_SCAN_PROMPT,
    "strategic":         STRATEGIC_PROMPT,
    "battle_card":       BATTLE_CARD_PROMPT,
}

# UI/UX removed from strategic — only appears in feature_deep_dive
SECTIONS_BY_MODE = {
    "feature_deep_dive": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "What This Feature Does"),
        ("use_cases",            "Who It's Built For"),
        ("strategic_direction",  "How It Fits Into Their Product Strategy"),
        ("gap_vs_your_product",  "How It Compares to Our Product"),
        ("watch_points",         "Watch Points"),
        ("source_urls",          "Reference Links"),
    ],
    "landscape_scan": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "Recent Launches"),
        ("strategic_direction",  "Signals & Themes"),
        ("gap_vs_your_product",  "Gaps Visible in the Scan"),
        ("source_urls",          "Reference Links"),
    ],
    "strategic": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "Recent Feature Launches"),
        ("use_cases",            "Use Cases"),
        ("technical_details",    "Technical Architecture"),
        ("pricing_signals",      "Pricing & Packaging"),
        ("strategic_direction",  "Strategic Direction"),
        ("gap_vs_your_product",  "Gaps vs Your Product"),
        ("watch_points",         "Key Watch Points"),
        ("source_urls",          "Reference Links"),
    ],
    "battle_card": [
        ("direct_answer",        "Direct Answer"),
        ("recent_launches",      "Their Top 3 Strengths"),
        ("gap_vs_your_product",  "Their Top 3 Weaknesses"),
        ("strategic_direction",  "Our Differentiation"),
        ("use_cases",            "Common Objections"),
        ("pricing_signals",      "Pricing Summary"),
        ("watch_points",         "One-Line Positioning"),
        ("source_urls",          "Reference Links"),
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
        source_urls = item.get("source_urls", [])

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
                web_content=item.get("web_content", "Not available")[:40000],
                docs_content=item.get("docs_content", "Not available")[:40000],
                youtube_content=item.get("youtube_content", "Not available")[:10000],
                scrapbook_content=item.get("scrapbook_content", "Not available")[:8000],
                image_note=image_note,
            )

            human_msg = _build_multimodal_message(prompt, scrapbook_images)
            response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), human_msg])
            raw_synthesis = response.content

            synthesis: dict = {
                "vendor_name": vendor_name,
                "analysis_mode": analysis_mode,
                "raw_synthesis": raw_synthesis,
                "direct_answer": "",
                "recent_launches": "",
                "use_cases": "",
                "technical_details": "",
                "ui_ux": "",
                "pricing_signals": "",
                "strategic_direction": "",
                "gap_vs_your_product": "",
                "watch_points": "",
                "source_urls": source_urls,
            }

            for state_key, section_heading in sections_to_extract:
                if state_key == "source_urls":
                    # Extract reference links from GPT output + merge with scraped URLs
                    gpt_links = _extract_reference_links(raw_synthesis)
                    all_links = list(dict.fromkeys(gpt_links + source_urls))  # dedupe, preserve order
                    synthesis["source_urls"] = all_links
                else:
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
    """
    Extract content between two top-level (##) headings.
    Critically: does NOT stop on ### or #### sub-headings inside the section —
    only stops when another ## (exactly two hashes, not three+) heading appears.
    """
    lines = text.split("\n")
    capturing = False
    result = []
    for line in lines:
        stripped = line.lstrip()
        # Detect a ## heading (exactly — not ### or ####)
        is_h2 = stripped.startswith("## ") or stripped == "##"
        if is_h2 and section_title.lower() in line.lower():
            capturing = True
            continue
        if capturing:
            if is_h2:  # another top-level section starts — stop
                break
            result.append(line)
    return "\n".join(result).strip()


def _extract_reference_links(text: str) -> list[str]:
    """
    Extract URLs from the Reference Links section of GPT output.
    Only keeps URLs that have a real path (not bare root domains like https://okta.com/).
    Preserves markdown link format [title](url) so UI can render proper labels.
    """
    import re
    section = _extract_section(text, "Reference Links")
    if not section:
        return []

    results = []
    # Prefer markdown links [Title](url) — preserve label
    md_links = re.findall(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)', section)
    seen_urls = set()
    for title, url in md_links:
        # Strip trailing punctuation
        url = url.rstrip(".,;)")
        if url not in seen_urls:
            seen_urls.add(url)
            results.append(f"[{title}]({url})")

    # Fall back to bare URLs if no markdown links found
    if not results:
        bare_urls = re.findall(r'https?://[^\s\)]+', section)
        for url in bare_urls:
            url = url.rstrip(".,;)")
            if url not in seen_urls:
                seen_urls.add(url)
                results.append(url)

    return results
