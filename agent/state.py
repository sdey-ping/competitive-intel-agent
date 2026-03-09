from typing import TypedDict, List, Optional


class CompetitorRawData(TypedDict):
    vendor_name: str
    web_content: str
    docs_content: str
    youtube_content: str
    scrapbook_content: str
    scrapbook_images: List[str]
    source_urls: List[str]       # URLs actually scraped — surfaced in UI as references


class CompetitorSynthesis(TypedDict):
    vendor_name: str
    direct_answer: str
    recent_launches: str
    use_cases: str
    technical_details: str
    ui_ux: str
    pricing_signals: str
    strategic_direction: str
    gap_vs_your_product: str
    watch_points: str
    raw_synthesis: str
    analysis_mode: str
    source_urls: List[str]       # Passed through from raw_data for reference links section


class DiffResult(TypedDict):
    vendor_name: str
    delta_summary: str
    is_first_run: bool


class AgentState(TypedDict):
    # ── Inputs ────────────────────────────────
    vendors: List[str]
    research_query: str
    save_to_drive: bool
    use_scrapbook: bool          # User toggle — whether to read Google Doc scrapbook

    # ── Intent Classification ──────────────────
    analysis_mode: str
    target_feature: str
    mode_confidence: str

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
