import streamlit as st
import json
from db.database import get_all_reports, get_report_by_id

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
.report-card { background:#ffffff; border:1px solid #e8e4dd; border-radius:12px;
               padding:18px 22px; margin-bottom:12px; transition:box-shadow 0.15s; }
.report-card:hover { box-shadow:0 4px 16px rgba(0,0,0,0.07); }
.report-query { font-size:14px; font-weight:600; color:#0f172a; line-height:1.4;
                margin-bottom:6px; }
.report-meta { font-size:11px; color:#94a3b8; letter-spacing:0.03em; }
.report-meta strong { color:#64748b; }
.badge-drive { display:inline-flex; align-items:center; gap:4px; background:#eff6ff;
               border:1px solid #bfdbfe; border-radius:10px; padding:2px 10px;
               font-size:11px; font-weight:600; color:#1d4ed8; }
.badge-local { display:inline-flex; align-items:center; gap:4px; background:#f8f7f4;
               border:1px solid #e8e4dd; border-radius:10px; padding:2px 10px;
               font-size:11px; font-weight:500; color:#94a3b8; }
.vendor-pill { display:inline-block; background:#f1f5f9; border-radius:8px;
               padding:2px 9px; font-size:11px; font-weight:600; color:#475569;
               margin-right:4px; margin-top:4px; }
.section-header { font-size:11px; font-weight:700; letter-spacing:0.08em;
                  text-transform:uppercase; color:#94a3b8; margin:28px 0 14px 0;
                  padding-bottom:10px; border-bottom:1px solid #e8e4dd; }
.viewer-header { background:#f8faff; border:1px solid #e0e9ff; border-radius:10px;
                 padding:14px 18px; margin-bottom:20px; }
.viewer-date { font-size:11px; font-weight:700; letter-spacing:0.07em;
               text-transform:uppercase; color:#1a56db; margin-bottom:4px; }
.viewer-query { font-size:14px; color:#1e293b; font-weight:600; line-height:1.5; }
</style>
"""


def _is_valid_drive_link(link: str) -> bool:
    if not link:
        return False
    if link.startswith("[") or link == "__local_only__":
        return False
    return link.startswith("http")


def _format_date(raw: str) -> str:
    """Convert '2026-05-14 13:22:45' → 'May 14, 2026 at 13:22'."""
    try:
        from datetime import datetime
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y at %H:%M")
    except Exception:
        return raw or "—"


def render():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown("## Report History")
    st.markdown(
        "<p style='color:#64748b;margin-top:-8px;font-size:14px'>"
        "All archived competitive intelligence reports.</p>",
        unsafe_allow_html=True,
    )

    reports = get_all_reports()
    published = [r for r in reports if r.get("gdrive_link") != "__local_only__"
                 or r.get("report_markdown")]

    if not published:
        st.info("No archived reports yet. Run an evaluation with **Publish & Archive Report** enabled.")
        return

    # ── Report list ────────────────────────────────────────────────────────────
    st.markdown(f"<div class='section-header'>{len(published)} Report(s)</div>",
                unsafe_allow_html=True)

    for report in published:
        vendors = json.loads(report.get("vendors_covered") or "[]")
        gdrive_link = report.get("gdrive_link", "")
        has_drive = _is_valid_drive_link(gdrive_link)
        query_text = (report.get("research_query") or "—")[:120]
        date_text = _format_date(report.get("run_date", ""))

        vendor_pills = "".join(
            f"<span class='vendor-pill'>{v}</span>" for v in vendors
        ) if vendors else "<span class='vendor-pill'>—</span>"

        badge = (
            "<span class='badge-drive'>☁ Google Drive</span>"
            if has_drive else
            "<span class='badge-local'>Local only</span>"
        )

        # Render card as a styled container
        st.markdown(
            f"<div class='report-card'>"
            f"<div class='report-query'>{query_text}</div>"
            f"<div class='report-meta'>"
            f"<strong>Date:</strong> {date_text} &nbsp;·&nbsp; {badge}"
            f"</div>"
            f"<div style='margin-top:8px'>{vendor_pills}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Action buttons right below the card
        btn_c1, btn_c2, btn_spacer = st.columns([1.4, 1.4, 4])
        with btn_c1:
            if has_drive:
                st.link_button("☁ Open in Drive", gdrive_link,
                               use_container_width=True)
            else:
                st.button("☁ Google Drive", disabled=True,
                          key=f"drive_{report['id']}",
                          help="Not published to Google Drive",
                          use_container_width=True)
        with btn_c2:
            if st.button("📄 View Report", key=f"view_{report['id']}",
                         use_container_width=True):
                if st.session_state.get("viewing_report_id") == report["id"]:
                    del st.session_state["viewing_report_id"]
                else:
                    st.session_state["viewing_report_id"] = report["id"]
                st.rerun()

        # Inline viewer — shown directly under the report it belongs to
        if st.session_state.get("viewing_report_id") == report["id"]:
            _render_report_viewer(report["id"])

    # Clean up viewer state if the report was deleted mid-session
    if "viewing_report_id" in st.session_state:
        ids = {r["id"] for r in published}
        if st.session_state["viewing_report_id"] not in ids:
            del st.session_state["viewing_report_id"]


def _render_report_viewer(report_id: int):
    report = get_report_by_id(report_id)
    if not report:
        return

    date_text = _format_date(report.get("run_date", ""))
    query_text = report.get("research_query", "")

    st.markdown(
        f"<div class='viewer-header'>"
        f"<div class='viewer-date'>{date_text}</div>"
        f"<div class='viewer-query'>{query_text}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Render the stored markdown — this includes Reference Sources sections
    st.markdown(report["report_markdown"])

    st.divider()
    if st.button("✕ Close Report", key=f"close_{report_id}", type="secondary"):
        del st.session_state["viewing_report_id"]
        st.rerun()
