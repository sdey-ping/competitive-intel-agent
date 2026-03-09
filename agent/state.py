from typing import TypedDict, List, Optional


class CompetitorRawData(TypedDict):
    vendor_name: str
    web_content: str
    docs_content: str
    youtube_content: str
    scrapbook_content: str
    scrapbook_images: List[str]


class CompetitorSynthesis(TypedDict):
    vendor_name: str
    direct_answer: str          # Direct answer to the research question
    recent_launches: str
    use_cases: str
    technical_details: str
    ui_ux: str
    pricing_signals: str
    strategic_direction: str
    gap_vs_your_product: str
    watch_points: str
    raw_synthesis: str
    analysis_mode: str          # Which mode was used for this synthesis


class DiffResult(TypedDict):
    vendor_name: str
    delta_summary: str
    is_first_run: bool


class AgentState(TypedDict):
    # ── Inputs ────────────────────────────────
    vendors: List[str]
    research_query: str
    save_to_drive: bool

    # ── Intent Classification ──────────────────
    analysis_mode: str          # "feature_deep_dive" | "landscape_scan" | "strategic" | "battle_card"
    target_feature: str         # Populated when mode == "feature_deep_dive"
    mode_confidence: str        # "auto" | "user_override"

    # ── Intermediate ──────────────────────────
    raw_data: List[CompetitorRawData]
    syntheses: List[CompetitorSynthesis]
    diffs: List[DiffResult]

    # ── Outputs ───────────────────────────────
    final_report_markdown: str
    gdrive_link: str

    # ── Timing ────────────────────────────────
    analysis_duration_seconds: float
    drive_duration_seconds: float

    # ── Meta ──────────────────────────────────
    errors: List[str]
    current_step: str
