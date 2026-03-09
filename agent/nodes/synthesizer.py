from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState, CompetitorSynthesis
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)

SYSTEM_PROMPT = """You are a senior competitive intelligence analyst for a B2B SaaS product team.
Your job is to produce a deep, technically detailed competitive analysis — not surface-level summaries.

Rules:
- Be specific. Name actual features, protocols, UI patterns, and use cases found in the content.
- Never make generic statements like "they have a strong product" without backing it with specifics.
- If something is not mentioned in the source content, say "Not found in available sources" — do not hallucinate.
- When images are provided (UI screenshots, diagrams, pricing tables, roadmap slides), extract every 
  visible detail — button labels, menu items, field names, workflow steps, error states, data formats.
- Prioritize technical depth over breadth. A PM reading this should walk away knowing exactly how 
  this competitor works and where they are strong or weak.
- CRITICAL: The research question is the PRIMARY lens. Every section must directly answer or connect
  back to what was asked. Do not produce generic boilerplate — answer the actual question."""

# --- NEW: Research-first prompt that leads with a direct answer ---
SYNTHESIS_PROMPT = """
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

## IMPORTANT: Answer the research question first, then provide supporting detail.

The user's research question is: "{research_query}"

Produce your analysis in the following structure. Every section must be filtered through the lens
of the research question above — if a section is not relevant to the question, say so briefly 
rather than padding with generic content.

## Direct Answer
Provide a 2-4 sentence direct, specific answer to the research question based solely on what
is found in the source content above. This is the most important section. Be blunt and specific.

## Recent Feature Launches & Updates
List features/updates that are RELEVANT TO THE RESEARCH QUESTION. For each:
- Feature name and what it does
- When launched (if mentioned)
- Which customer segment it targets
- Technical implementation details if mentioned
If no relevant launches found in sources, say so explicitly.

## Use Cases & Target Segments
Focus only on use cases directly relevant to the research question.
- Specific problems this vendor solves, and for whom
- Concrete use cases with details
- Industries or company sizes explicitly targeted
- Workflows or jobs-to-be-done highlighted in case studies/docs

## Technical Architecture & Protocol Support
Technical details relevant to the research question:
- APIs, protocols, or standards (REST, GraphQL, WebSockets, etc.)
- Integration capabilities (connectors, webhooks, SDKs)
- Infrastructure/deployment options (cloud, on-prem, SOC2, GDPR)
- Known constraints or deprecations
- Data formats supported

## User Interface & User Experience
UI/UX aspects relevant to the research question:
- UI paradigm (wizard-based, drag-and-drop, code-first, dashboard-centric)
- Specific UI components or workflows visible in screenshots or docs
- Onboarding and first-run experience
- Notable UX patterns

## Pricing & Packaging
Pricing details relevant to the research question:
- Specific tier names, prices, and inclusions
- Usage limits or metering dimensions
- Freemium/trial/PLG motion
- Enterprise vs self-serve split

## Strategic Direction & Roadmap Signals
Where this vendor is headed, filtered through the research question:
- Direction for next 6-12 months based on content
- Dominant themes in blog posts, releases, talks
- Acquisitions, partnerships, platform bets
- Problems they are visibly investing in solving

## Gaps vs Your Product
- Where this vendor appears ahead — be specific
- Where they appear weaker or missing functionality
- Pain points revealed by reviews or support content
- Your best differentiation opportunity

## Key Watch Points
Top 3-5 things to monitor next quarter, directly tied to the research question. With reasoning.
"""


def _build_multimodal_message(prompt_text: str, images_base64: list[str]) -> HumanMessage:
    """Build a HumanMessage with text + images for GPT-4o vision input."""
    if not images_base64:
        return HumanMessage(content=prompt_text)

    content_blocks = [{"type": "text", "text": prompt_text}]
    for b64 in images_base64:
        content_blocks.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high",
            },
        })
    return HumanMessage(content=content_blocks)


def synthesizer_node(state: AgentState) -> AgentState:
    """
    Call GPT-4o to synthesize raw data (text + images) into deep structured intelligence per vendor.
    """
    raw_data = state.get("raw_data", [])
    research_query = state.get("research_query", "General competitive overview")
    syntheses: list[CompetitorSynthesis] = []
    errors = state.get("errors", [])

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
                f"{len(scrapbook_images)} image(s) attached below. Analyze every visible detail — "
                f"UI elements, field names, workflows, pricing tables, roadmap slides, diagrams.\n"
                if has_images else ""
            )

            prompt = SYNTHESIS_PROMPT.format(
                vendor_name=vendor_name,
                research_query=research_query,
                web_content=item.get("web_content", "Not available")[:4000],
                docs_content=item.get("docs_content", "Not available")[:4000],
                youtube_content=item.get("youtube_content", "Not available")[:3000],
                scrapbook_content=item.get("scrapbook_content", "Not available")[:2000],
                image_note=image_note,
            )

            human_msg = _build_multimodal_message(prompt, scrapbook_images)

            response = llm.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                human_msg,
            ])

            raw_synthesis = response.content

            synthesis: CompetitorSynthesis = {
                "vendor_name": vendor_name,
                # NEW: direct_answer is extracted and stored
                "direct_answer": _extract_section(raw_synthesis, "Direct Answer"),
                "recent_launches": _extract_section(raw_synthesis, "Recent Feature Launches"),
                "use_cases": _extract_section(raw_synthesis, "Use Cases"),
                "technical_details": _extract_section(raw_synthesis, "Technical Architecture"),
                "ui_ux": _extract_section(raw_synthesis, "User Interface"),
                "pricing_signals": _extract_section(raw_synthesis, "Pricing & Packaging"),
                "strategic_direction": _extract_section(raw_synthesis, "Strategic Direction"),
                "gap_vs_your_product": _extract_section(raw_synthesis, "Gaps vs Your Product"),
                "watch_points": _extract_section(raw_synthesis, "Key Watch Points"),
                "raw_synthesis": raw_synthesis,
            }
            syntheses.append(synthesis)

            if has_images:
                errors.append(
                    f"✅ {vendor_name}: synthesized with {len(scrapbook_images)} scrapbook image(s)"
                )

        except Exception as e:
            errors.append(f"Synthesis failed for {vendor_name}: {str(e)}")

    return {
        **state,
        "syntheses": syntheses,
        "errors": errors,
        "current_step": "synthesis_complete",
    }


def _extract_section(text: str, section_title: str) -> str:
    """Extract content under a specific ## heading."""
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
