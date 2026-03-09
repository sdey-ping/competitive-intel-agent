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
    direct_answer: str        # NEW: direct answer to the research question — shown first in UI
    recent_launches: str
    use_cases: str
    technical_details: str
    ui_ux: str
    pricing_signals: str
    strategic_direction: str
    gap_vs_your_product: str
    watch_points: str
    raw_synthesis: str


class DiffResult(TypedDict):
    vendor_name: str
    delta_summary: str
    is_first_run: bool


class AgentState(TypedDict):
    # ── Inputs ────────────────────────────────
    vendors: List[str]
    research_query: str
    save_to_drive: bool

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
