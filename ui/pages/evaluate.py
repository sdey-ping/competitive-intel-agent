import streamlit as st
from db.database import get_all_competitors
from agent.graph import run_agent
from mailer.emailer import send_report_email


def render():
    st.header("🔍 Evaluate Competitors")
    st.caption("Run the AI agent against your configured competitors.")

    competitors = get_all_competitors()

    if not competitors:
        st.warning("No competitors configured yet. Go to **Configure Competitors** to add some.")
        return

    # ── Inputs ─────────────────────────────────────────────────────────────────
    research_query = st.text_area(
        "Research Focus",
        placeholder="e.g. What AI features are competitors shipping in their CRM workflows?",
        height=80,
        help="Be specific. This guides the entire synthesis."
    )

    vendor_names = [c["vendor_name"] for c in competitors]
    selected_vendors = st.multiselect(
        "Select Vendors to Evaluate",
        options=vendor_names,
        default=vendor_names,
    )

    run_button = st.button("🚀 Evaluate Competitors", type="primary", disabled=not selected_vendors)

    # ── Run Agent ──────────────────────────────────────────────────────────────
    if run_button:
        if not research_query.strip():
            st.warning("Please enter a research focus before running.")
            return

        with st.spinner("Agent is running... this may take 1–2 minutes."):
            _run_with_progress(selected_vendors, research_query)

    # ── Display Results ────────────────────────────────────────────────────────
    if "agent_result" in st.session_state:
        result = st.session_state["agent_result"]
        _render_results(result)


def _run_with_progress(selected_vendors, research_query):
    """Run the agent with a live progress display."""
    progress = st.empty()
    steps = [
        "🌐 Scraping websites and blogs...",
        "🎬 Fetching YouTube transcripts...",
        "📄 Reading Google Doc scrapbook...",
        "🧠 Synthesizing intelligence with GPT-4o...",
        "🔄 Computing diffs vs previous run...",
        "📝 Writing final report...",
    ]

    progress_bar = st.progress(0)
    status_text = st.empty()

    # We can't get live step updates from LangGraph in simple invoke mode,
    # so we show a pre-run animation then call the agent
    import time
    for i, step in enumerate(steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps) * 0.8)
        time.sleep(0.4)

    try:
        result = run_agent(selected_vendors, research_query)
        progress_bar.progress(1.0)
        status_text.text("✅ Done!")
        time.sleep(0.5)
        status_text.empty()
        progress_bar.empty()
        st.session_state["agent_result"] = result

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Agent failed: {str(e)}")


def _render_results(result: dict):
    st.divider()
    st.subheader("📋 Results")

    # ── Errors ──────────────────────────────────────────────────────────────
    if result.get("errors"):
        with st.expander("⚠️ Warnings", expanded=False):
            for err in result["errors"]:
                st.warning(err)

    # ── What's New (Delta) ──────────────────────────────────────────────────
    diffs = result.get("diffs", [])
    if diffs:
        st.subheader("🔔 What's New Since Last Run")
        for diff in diffs:
            with st.expander(f"{diff['vendor_name']}", expanded=True):
                if diff.get("is_first_run"):
                    st.info(diff["delta_summary"])
                else:
                    st.markdown(diff["delta_summary"])

    # ── Per-Vendor Synthesis ────────────────────────────────────────────────
    st.subheader("📊 Full Analysis by Vendor")
    syntheses = result.get("syntheses", [])
    for synthesis in syntheses:
        with st.expander(f"🏢 {synthesis['vendor_name']}", expanded=False):
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
                "🚀 Launches",
                "🎯 Use Cases",
                "⚙️ Technical",
                "🖥️ UI/UX",
                "💰 Pricing",
                "🧭 Direction",
                "⚔️ Gaps",
                "👁️ Watch",
            ])
            with tab1:
                st.markdown(synthesis.get("recent_launches", "_No data_"))
            with tab2:
                st.markdown(synthesis.get("use_cases", "_No data_"))
            with tab3:
                st.markdown(synthesis.get("technical_details", "_No data_"))
            with tab4:
                st.markdown(synthesis.get("ui_ux", "_No data_"))
            with tab5:
                st.markdown(synthesis.get("pricing_signals", "_No data_"))
            with tab6:
                st.markdown(synthesis.get("strategic_direction", "_No data_"))
            with tab7:
                st.markdown(synthesis.get("gap_vs_your_product", "_No data_"))
            with tab8:
                st.markdown(synthesis.get("watch_points", "_No data_"))

    # ── Action Bar ──────────────────────────────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        gdrive_link = result.get("gdrive_link", "")
        if gdrive_link and not gdrive_link.startswith("["):
            st.link_button("📁 View in Google Drive", gdrive_link, type="secondary")
        else:
            st.button("📁 Google Drive", disabled=True, help="Drive upload not configured")

    with col2:
        if st.button("📧 Send Email", type="primary"):
            st.session_state["show_email_modal"] = True

    # ── Email Modal ──────────────────────────────────────────────────────────
    if st.session_state.get("show_email_modal"):
        _render_email_modal(result)


def _render_email_modal(result: dict):
    with st.form("email_form"):
        st.subheader("📧 Send Report via Email")
        emails_raw = st.text_area(
            "Recipient Email Addresses",
            placeholder="alice@company.com\nbob@company.com\ncarol@company.com",
            help="One email address per line",
            height=120,
        )
        col_send, col_cancel = st.columns(2)
        with col_send:
            send = st.form_submit_button("Send", type="primary")
        with col_cancel:
            cancel = st.form_submit_button("Cancel")

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
                    st.success(f"✅ Report sent to {len(recipients)} recipient(s).")
                    st.session_state["show_email_modal"] = False
                else:
                    st.error(f"Send failed: {outcome['error']}")
