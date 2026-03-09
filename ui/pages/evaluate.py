import time
import streamlit as st
from db.database import get_all_competitors
from mailer.emailer import send_report_email
from agent.nodes.intent_classifier import MODE_META

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

.timing-card {
    background: #ffffff;
    border: 1px solid #e8e4dd;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 4px 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.timing-label {
    font-size: 11px; font-weight: 600; letter-spacing: 0.07em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: 6px;
}
.timing-value {
    font-family: 'JetBrains Mono', monospace; font-size: 30px;
    font-weight: 500; color: #1a56db; line-height: 1;
}
.timing-sub { font-size: 11px; color: #94a3b8; margin-top: 5px; }

.section-header {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #94a3b8;
    margin: 28px 0 14px 0; padding-bottom: 10px;
    border-bottom: 1px solid #e8e4dd;
}

/* Mode selector pills */
.mode-pill-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 20px 0; }
.mode-pill {
    display: inline-flex; align-items: center; gap: 6px;
    border: 1.5px solid #e2ddd6; border-radius: 20px;
    padding: 7px 16px; font-size: 13px; font-weight: 500;
    color: #64748b; background: #ffffff; cursor: pointer;
    transition: all 0.15s;
}
.mode-pill:hover { border-color: #1a56db; color: #1a56db; }
.mode-pill.active {
    background: #eff6ff; border-color: #1a56db;
    color: #1a56db; font-weight: 600;
}
.mode-pill .mode-icon { font-size: 15px; }

/* Mode banner shown in results */
.mode-banner {
    display: inline-flex; align-items: center; gap: 8px;
    background: #f0f7ff; border: 1px solid #bfdbfe;
    border-radius: 8px; padding: 8px 16px; margin-bottom: 16px;
    font-size: 13px; font-weight: 600; color: #1a56db;
}
.mode-auto-badge {
    font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; background: #e0f2fe;
    color: #0369a1; border-radius: 10px; padding: 2px 8px;
}

/* Research question banner */
.research-banner {
    background: #f8faff; border: 1px solid #e0e9ff;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 20px;
}
.research-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #1a56db; margin-bottom: 4px;
}
.research-text { font-size: 13.5px; color: #1e293b; font-weight: 500; line-height: 1.5; }

/* Direct answer card */
.direct-answer-card {
    background: #eff6ff; border: 1.5px solid #bfdbfe;
    border-left: 4px solid #1a56db; border-radius: 12px;
    padding: 20px 24px; margin: 8px 0 16px 0;
}
.direct-answer-vendor {
    font-size: 11px; font-weight: 700; letter-spacing: 0.07em;
    text-transform: uppercase; color: #1a56db; margin-bottom: 8px;
}
.direct-answer-text { font-size: 14px; color: #1e3a5f; line-height: 1.7; }

/* Battle card layout */
.battle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 12px 0; }
.battle-cell {
    background: #ffffff; border: 1px solid #e8e4dd;
    border-radius: 10px; padding: 16px 18px;
}
.battle-cell.green { border-left: 3px solid #16a34a; }
.battle-cell.red   { border-left: 3px solid #dc2626; }
.battle-cell.blue  { border-left: 3px solid #1a56db; }
.battle-cell-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.07em;
    text-transform: uppercase; margin-bottom: 10px;
}

/* Positioning statement */
.positioning-statement {
    background: #0f172a; color: #f8fafc;
    border-radius: 12px; padding: 20px 24px;
    font-size: 16px; font-weight: 600; line-height: 1.5;
    margin: 16px 0; font-style: italic;
}

/* Save pills */
.save-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #f0fdf4; border: 1px solid #86efac;
    color: #15803d; border-radius: 20px;
    padding: 5px 14px; font-size: 12px; font-weight: 600;
}
.nosave-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #fffbeb; border: 1px solid #fcd34d;
    color: #b45309; border-radius: 20px;
    padding: 5px 14px; font-size: 12px; font-weight: 600;
}
</style>
"""

# Ordered list for rendering mode pills in UI
MODE_ORDER = ["feature_deep_dive", "landscape_scan", "strategic", "battle_card"]

# All 8 strategic sections in display order
STRATEGIC_SECTION_DEFS = [
    ("recent_launches",     "🚀 Launches"),
    ("use_cases",           "🎯 Use Cases"),
    ("technical_details",   "⚙️ Technical"),
    ("ui_ux",               "🖥️ UI/UX"),
    ("pricing_signals",     "💰 Pricing"),
    ("strategic_direction", "🧭 Direction"),
    ("gap_vs_your_product", "⚔️ Gaps"),
    ("watch_points",        "👁️ Watch"),
]

# Phrases the LLM emits when a section is not relevant — treated as empty
_IRRELEVANT_PHRASES = (
    "not directly relevant",
    "not found in available sources",
    "not available",
    "no data",
    "n/a",
)


def _is_content_relevant(content: str) -> bool:
    """Return True only if this section has real, substantive content."""
    if not content:
        return False
    stripped = content.strip()
    if not stripped or len(stripped) < 40:
        return False
    lower = stripped.lower()
    for phrase in _IRRELEVANT_PHRASES:
        if lower.startswith(phrase):
            return False
    return True


def render():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown("## Intelligence Evaluation")
    st.markdown(
        "<p style='color:#64748b;margin-top:-8px;font-size:14px'>"
        "Configure your research scope and run the AI agent across selected competitors.</p>",
        unsafe_allow_html=True
    )

    competitors = get_all_competitors()
    if not competitors:
        st.warning("No competitors configured yet. Go to **Configure Competitors** to add some.")
        return

    # ── Research Query ─────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Research Question</div>", unsafe_allow_html=True)

    research_query = st.text_area(
        "Research Focus",
        placeholder=(
            "Ask anything — e.g.\n"
            "• 'What is the Export User Created Columns feature and how does Okta Workflows fit in?'\n"
            "• 'What did Okta ship in the last 90 days?'\n"
            "• 'How does Okta approach enterprise identity vs our product?'\n"
            "• 'Where are we ahead and behind Okta — give me a battle card.'"
        ),
        height=110,
        label_visibility="collapsed",
    )

    # ── Analysis Mode Selector ─────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Analysis Mode</div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:13px;color:#64748b;margin:-8px 0 12px 0'>"
        "Auto-detect reads your question and picks the right mode. "
        "Or select manually to override.</p>",
        unsafe_allow_html=True
    )

    if "selected_mode" not in st.session_state:
        st.session_state["selected_mode"] = "auto"

    cols = st.columns(5)

    modes_with_auto = [("auto", "🤖", "Auto-Detect", "Let AI pick the best mode")] + [
        (mode_id, MODE_META[mode_id]["icon"], MODE_META[mode_id]["label"], MODE_META[mode_id]["description"])
        for mode_id in MODE_ORDER
    ]

    for i, (mode_id, icon, label, desc) in enumerate(modes_with_auto):
        with cols[i]:
            is_active = st.session_state["selected_mode"] == mode_id
            border = "2px solid #1a56db" if is_active else "1.5px solid #e2ddd6"
            bg = "#eff6ff" if is_active else "#ffffff"
            text_color = "#1a56db" if is_active else "#475569"
            weight = "700" if is_active else "500"

            st.markdown(
                f"<div style='background:{bg};border:{border};border-radius:12px;"
                f"padding:12px 14px;text-align:center;margin-bottom:4px'>"
                f"<div style='font-size:20px;margin-bottom:4px'>{icon}</div>"
                f"<div style='font-size:12px;font-weight:{weight};color:{text_color}'>{label}</div>"
                f"<div style='font-size:10px;color:#94a3b8;margin-top:3px;line-height:1.3'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("Select", key=f"mode_btn_{mode_id}",
                         type="primary" if is_active else "secondary",
                         use_container_width=True):
                st.session_state["selected_mode"] = mode_id
                st.rerun()

    # ── Vendors ────────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Vendors to Evaluate</div>", unsafe_allow_html=True)
    vendor_names = [c["vendor_name"] for c in competitors]
    selected_vendors = st.multiselect(
        "Vendors", options=vendor_names, default=vendor_names, label_visibility="collapsed"
    )

    # ── Report Persistence ─────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Report Persistence</div>", unsafe_allow_html=True)
    col_drive, col_info = st.columns([2, 3])
    with col_drive:
        save_to_drive = st.checkbox(
            "📤  Publish & Archive Report", value=False,
            help="Saves to Report History and uploads to Google Drive."
        )
    with col_info:
        if save_to_drive:
            st.markdown("<div class='save-pill'>✦ Will be archived to History & Google Drive</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='nosave-pill'>⚡ Live analysis only — not saved</div>",
                        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Run ────────────────────────────────────────────────────────────────────
    run_button = st.button(
        "⚡  Run Intelligence Evaluation",
        type="primary", disabled=not selected_vendors, use_container_width=True,
    )

    if run_button:
        if not research_query.strip():
            st.warning("Please enter a research question before running.")
            return

        selected_mode = st.session_state.get("selected_mode", "auto")
        user_mode = "" if selected_mode == "auto" else selected_mode

        _run_with_progress(selected_vendors, research_query, save_to_drive, user_mode)

    if "agent_result" in st.session_state:
        _render_results(st.session_state["agent_result"])


# ── Pipeline runner ────────────────────────────────────────────────────────────

def _run_with_progress(selected_vendors, research_query, save_to_drive, user_mode=""):
    from agent.graph import stream_agent, PIPELINE_STEPS, STEP_LABELS

    total_steps = len(PIPELINE_STEPS)

    prog_col, pct_col = st.columns([11, 1])
    with prog_col:
        progress_bar = st.progress(0)
    with pct_col:
        pct_text = st.empty()

    status_text  = st.empty()
    live_preview = st.empty()

    pct_text.markdown(
        "<p style='font-family:JetBrains Mono,monospace;font-size:13px;"
        "font-weight:600;color:#94a3b8;text-align:right;margin-top:6px'>0%</p>",
        unsafe_allow_html=True
    )

    try:
        analysis_start = time.time()
        result = None
        completed = 0

        for node_name, partial_state in stream_agent(
            selected_vendors, research_query,
            save_to_drive=save_to_drive,
            analysis_mode=user_mode,
        ):
            if node_name == "__end__":
                result = partial_state
                break

            if node_name in PIPELINE_STEPS:
                completed = PIPELINE_STEPS.index(node_name) + 1
            pct = int((completed / total_steps) * 100)
            progress_bar.progress(completed / total_steps)
            pct_text.markdown(
                f"<p style='font-family:JetBrains Mono,monospace;font-size:13px;"
                f"font-weight:700;color:#1a56db;text-align:right;margin-top:6px'>{pct}%</p>",
                unsafe_allow_html=True
            )

            icon, label = STEP_LABELS.get(node_name, ("⚙️", node_name))

            extra = ""
            if node_name == "intent_classifier":
                detected_mode = partial_state.get("analysis_mode", "strategic")
                mode_info = MODE_META.get(detected_mode, {})
                is_auto = partial_state.get("mode_confidence") == "auto"
                badge = (
                    " <span style='background:#dbeafe;color:#1d4ed8;font-size:10px;font-weight:700;"
                    "letter-spacing:0.05em;text-transform:uppercase;border-radius:8px;padding:2px 8px'>"
                    "AUTO-DETECTED</span>"
                ) if is_auto else ""
                extra = f" → {mode_info.get('icon','')} <b>{mode_info.get('label','')}</b>{badge}"

            status_text.markdown(
                f"<p style='color:#64748b;font-size:13px;font-weight:500'>"
                f"<span style='color:#15803d'>✓</span>&nbsp; <b>{icon} {label}</b>"
                f" — done{extra}</p>",
                unsafe_allow_html=True
            )

            syntheses = partial_state.get("syntheses", [])
            if syntheses and node_name == "synthesizer":
                preview_lines = []
                for s in syntheses:
                    vendor = s.get("vendor_name", "")
                    preview_text = (s.get("direct_answer") or s.get("recent_launches") or "")[:280]
                    if preview_text:
                        preview_lines.append(
                            f"<div style='margin-bottom:12px'>"
                            f"<span style='font-size:11px;font-weight:700;letter-spacing:0.06em;"
                            f"text-transform:uppercase;color:#1a56db'>{vendor}</span>"
                            f"<p style='font-size:13px;color:#475569;margin:4px 0 0 0;"
                            f"line-height:1.6'>{preview_text}…</p></div>"
                        )
                if preview_lines:
                    live_preview.markdown(
                        "<div style='background:#ffffff;border:1px solid #e8e4dd;border-radius:10px;"
                        "padding:16px 20px;margin-top:8px'>"
                        "<p style='font-size:11px;font-weight:700;letter-spacing:0.07em;"
                        "text-transform:uppercase;color:#94a3b8;margin:0 0 12px 0'>"
                        "⚡ Live Preview</p>" + "".join(preview_lines) + "</div>",
                        unsafe_allow_html=True
                    )

        analysis_duration = round(time.time() - analysis_start, 1)
        progress_bar.progress(1.0)
        pct_text.markdown(
            "<p style='font-family:JetBrains Mono,monospace;font-size:13px;"
            "font-weight:700;color:#15803d;text-align:right;margin-top:6px'>100%</p>",
            unsafe_allow_html=True
        )
        status_text.markdown(
            "<p style='color:#15803d;font-size:13px;font-weight:700'>"
            "✓&nbsp; Evaluation complete</p>",
            unsafe_allow_html=True
        )
        time.sleep(0.8)

        progress_bar.empty()
        pct_text.empty()
        status_text.empty()
        live_preview.empty()

        if result:
            result["analysis_duration_seconds"] = analysis_duration
            result["save_to_drive"] = save_to_drive
            st.session_state["agent_result"] = result
        else:
            st.error("Agent completed but returned no result.")

    except Exception as e:
        progress_bar.empty()
        pct_text.empty()
        status_text.empty()
        live_preview.empty()
        st.error(f"Evaluation failed: {str(e)}")


# ── Results rendering — routes per mode ───────────────────────────────────────

def _render_results(result: dict):
    st.divider()

    analysis_mode = result.get("analysis_mode", "strategic")
    mode_info = MODE_META.get(analysis_mode, {})
    mode_confidence = result.get("mode_confidence", "auto")
    research_query = result.get("research_query", "")
    syntheses = result.get("syntheses", [])

    auto_badge = (
        "<span class='mode-auto-badge'>AUTO-DETECTED</span>"
        if mode_confidence == "auto" else
        "<span class='mode-auto-badge' style='background:#fef9c3;color:#854d0e'>MANUAL</span>"
    )
    st.markdown(
        f"<div class='mode-banner'>"
        f"{mode_info.get('icon','')} {mode_info.get('label','Analysis')} {auto_badge}"
        f"</div>",
        unsafe_allow_html=True
    )

    if research_query:
        st.markdown(
            f"<div class='research-banner'>"
            f"<div class='research-label'>🔍 Research Question</div>"
            f"<div class='research-text'>{research_query}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    renderer = {
        "feature_deep_dive": _render_feature_deep_dive,
        "landscape_scan":    _render_landscape_scan,
        "strategic":         _render_strategic,
        "battle_card":       _render_battle_card,
    }.get(analysis_mode, _render_strategic)

    renderer(result)

    _render_timing(result)

    if result.get("errors"):
        with st.expander("⚠️ Run Warnings", expanded=False):
            for err in result["errors"]:
                st.caption(err)

    diffs = result.get("diffs", [])
    if diffs:
        st.markdown("<div class='section-header'>Delta — What's New Since Last Run</div>",
                    unsafe_allow_html=True)
        for diff in diffs:
            with st.expander(f"  {diff['vendor_name']}", expanded=True):
                if diff.get("is_first_run"):
                    st.info(diff["delta_summary"])
                else:
                    st.markdown(diff["delta_summary"])

    _render_action_bar(result)


# ── Per-mode renderers ─────────────────────────────────────────────────────────

def _render_feature_deep_dive(result: dict):
    syntheses = result.get("syntheses", [])

    st.markdown("<div class='section-header'>Direct Answer</div>", unsafe_allow_html=True)
    for s in syntheses:
        direct = s.get("direct_answer", "").strip()
        if direct:
            st.markdown(
                f"<div class='direct-answer-card'>"
                f"<div class='direct-answer-vendor'>{s['vendor_name']}</div>"
                f"<div class='direct-answer-text'>{direct}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<div class='section-header'>Feature Analysis</div>", unsafe_allow_html=True)
    for s in syntheses:
        with st.expander(f"  {s['vendor_name']} — Full Feature Breakdown", expanded=True):
            st.markdown("#### What This Feature Does")
            st.markdown(s.get("recent_launches", "_No data retrieved_"))

            st.markdown("#### Who It's Built For")
            st.markdown(s.get("use_cases", "_No data retrieved_"))

            st.markdown("#### How It Fits Into Their Product Strategy")
            st.markdown(s.get("strategic_direction", "_No data retrieved_"))

            st.markdown("#### How It Compares to Our Product")
            st.markdown(s.get("gap_vs_your_product", "_No data retrieved_"))

            st.markdown("#### Watch Points")
            st.markdown(s.get("watch_points", "_No data retrieved_"))


def _render_landscape_scan(result: dict):
    syntheses = result.get("syntheses", [])

    st.markdown("<div class='section-header'>Summary</div>", unsafe_allow_html=True)
    for s in syntheses:
        direct = s.get("direct_answer", "").strip()
        if direct:
            st.markdown(
                f"<div class='direct-answer-card'>"
                f"<div class='direct-answer-vendor'>{s['vendor_name']}</div>"
                f"<div class='direct-answer-text'>{direct}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<div class='section-header'>Recent Launches</div>", unsafe_allow_html=True)
    for s in syntheses:
        with st.expander(f"  {s['vendor_name']}", expanded=True):
            st.markdown(s.get("recent_launches", "_No data retrieved_"))

    st.markdown("<div class='section-header'>Signals & Themes</div>", unsafe_allow_html=True)
    for s in syntheses:
        with st.expander(f"  {s['vendor_name']}", expanded=False):
            st.markdown(s.get("strategic_direction", "_No data retrieved_"))
            st.markdown("**Gaps in Their Activity**")
            st.markdown(s.get("gap_vs_your_product", "_No data retrieved_"))


def _render_strategic(result: dict):
    syntheses = result.get("syntheses", [])

    # Direct answers — always shown first and prominently
    has_direct = any(s.get("direct_answer") for s in syntheses)
    if has_direct:
        st.markdown("<div class='section-header'>Direct Answer to Your Research Question</div>",
                    unsafe_allow_html=True)
        for s in syntheses:
            direct = s.get("direct_answer", "").strip()
            if direct:
                st.markdown(
                    f"<div class='direct-answer-card'>"
                    f"<div class='direct-answer-vendor'>{s['vendor_name']}</div>"
                    f"<div class='direct-answer-text'>{direct}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # Supporting details — only show tabs that have relevant content
    st.markdown("<div class='section-header'>Supporting Intelligence</div>",
                unsafe_allow_html=True)

    for s in syntheses:
        # Filter to only sections with real content
        relevant = [
            (key, label)
            for key, label in STRATEGIC_SECTION_DEFS
            if _is_content_relevant(s.get(key, ""))
        ]

        if not relevant:
            st.info(f"No additional supporting data found for {s['vendor_name']}.")
            continue

        with st.expander(
            f"  {s['vendor_name']} — {len(relevant)} relevant section(s)",
            expanded=True
        ):
            if len(relevant) == 1:
                # Single section — no tab chrome needed
                key, label = relevant[0]
                st.markdown(f"#### {label}")
                st.markdown(s.get(key, "_No data_"))
            else:
                # Only render the tabs that have content
                tab_labels = [label for _, label in relevant]
                tabs = st.tabs(tab_labels)
                for tab, (key, _) in zip(tabs, relevant):
                    with tab:
                        st.markdown(s.get(key, "_No data_"))


def _render_battle_card(result: dict):
    syntheses = result.get("syntheses", [])

    for s in syntheses:
        st.markdown(f"### ⚔️ {s['vendor_name']}")

        direct = s.get("direct_answer", "").strip()
        if direct:
            st.markdown(
                f"<div class='direct-answer-card'>"
                f"<div class='direct-answer-vendor'>BOTTOM LINE</div>"
                f"<div class='direct-answer-text'>{direct}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                "<div class='battle-cell green'>"
                "<div class='battle-cell-label' style='color:#16a34a'>✅ Their Strengths</div>",
                unsafe_allow_html=True
            )
            st.markdown(s.get("recent_launches", "_No data_"))
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown(
                "<div class='battle-cell red'>"
                "<div class='battle-cell-label' style='color:#dc2626'>❌ Their Weaknesses</div>",
                unsafe_allow_html=True
            )
            st.markdown(s.get("gap_vs_your_product", "_No data_"))
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("**🏆 Where We Win**")
        st.markdown(s.get("strategic_direction", "_No data_"))

        with st.expander("💬 Common Objections & Responses", expanded=False):
            st.markdown(s.get("use_cases", "_No data_"))

        with st.expander("💰 Pricing Summary", expanded=False):
            st.markdown(s.get("pricing_signals", "_No data_"))

        positioning = s.get("watch_points", "").strip()
        if positioning:
            st.markdown(
                f"<div class='positioning-statement'>&ldquo;{positioning}&rdquo;</div>",
                unsafe_allow_html=True
            )

        st.divider()


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _render_timing(result: dict):
    analysis_secs = result.get("analysis_duration_seconds", 0)
    drive_secs = result.get("drive_duration_seconds", 0)
    save_to_drive = result.get("save_to_drive", False)
    syntheses = result.get("syntheses", [])

    st.markdown("<div class='section-header'>Evaluation Performance</div>",
                unsafe_allow_html=True)

    if save_to_drive and drive_secs > 0:
        c1, c2, c3 = st.columns(3)
        total = round(analysis_secs + drive_secs, 1)
        with c1:
            st.markdown(f"<div class='timing-card'><div class='timing-label'>AI Analysis</div>"
                        f"<div class='timing-value'>{analysis_secs}s</div>"
                        f"<div class='timing-sub'>Scraping → Synthesis → Diff</div></div>",
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='timing-card'><div class='timing-label'>Drive Archive</div>"
                        f"<div class='timing-value'>{drive_secs}s</div>"
                        f"<div class='timing-sub'>Upload + History save</div></div>",
                        unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='timing-card'><div class='timing-label'>Total Duration</div>"
                        f"<div class='timing-value'>{total}s</div>"
                        f"<div class='timing-sub'>{len(syntheses)} vendor(s)</div></div>",
                        unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='timing-card'><div class='timing-label'>AI Analysis Duration</div>"
                        f"<div class='timing-value'>{analysis_secs}s</div>"
                        f"<div class='timing-sub'>Scraping → Synthesis → Diff</div></div>",
                        unsafe_allow_html=True)
        with c2:
            vendor_count = len(syntheses)
            per_vendor = round(analysis_secs / vendor_count, 1) if vendor_count else 0
            st.markdown(f"<div class='timing-card'><div class='timing-label'>Avg. Per Vendor</div>"
                        f"<div class='timing-value'>{per_vendor}s</div>"
                        f"<div class='timing-sub'>{vendor_count} vendor(s)</div></div>",
                        unsafe_allow_html=True)


def _render_action_bar(result: dict):
    st.divider()
    col1, col2, _ = st.columns([2, 2, 1])

    with col1:
        gdrive_link = result.get("gdrive_link", "")
        save_to_drive = result.get("save_to_drive", False)
        if gdrive_link and not gdrive_link.startswith("[") and gdrive_link != "__local_only__":
            st.link_button("📁  Open in Google Drive", gdrive_link,
                           type="secondary", use_container_width=True)
        elif not save_to_drive:
            st.button("📁  Google Drive", disabled=True,
                      help="Enable 'Publish & Archive Report' to upload to Drive",
                      use_container_width=True)

    with col2:
        if st.button("📧  Distribute via Email", type="primary", use_container_width=True):
            st.session_state["show_email_modal"] = True

    if st.session_state.get("show_email_modal"):
        _render_email_modal(result)


def _render_email_modal(result: dict):
    st.markdown("---")
    with st.form("email_form"):
        st.markdown("#### 📧 Distribute Report")
        st.caption("Enter one email address per line.")
        emails_raw = st.text_area("Recipients",
                                   placeholder="alice@company.com\nbob@company.com",
                                   height=100, label_visibility="collapsed")
        col_send, col_cancel = st.columns(2)
        with col_send:
            send = st.form_submit_button("Send Report", type="primary", use_container_width=True)
        with col_cancel:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if cancel:
            st.session_state["show_email_modal"] = False
            st.rerun()

        if send:
            recipients = [e.strip() for e in emails_raw.splitlines() if e.strip()]
            if not recipients:
                st.error("Please enter at least one email address.")
            else:
                with st.spinner("Sending..."):
                    outcome = send_report_email(
                        recipients=recipients,
                        report_markdown=result.get("final_report_markdown", ""),
                        gdrive_link=result.get("gdrive_link", ""),
                    )
                if outcome["success"]:
                    st.success(f"✅ Report distributed to {len(recipients)} recipient(s).")
                    st.session_state["show_email_modal"] = False
                else:
                    st.error(f"Send failed: {outcome['error']}")
