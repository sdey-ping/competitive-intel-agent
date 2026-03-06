import streamlit as st
from db.database import (
    get_all_competitors, add_competitor,
    update_competitor, delete_competitor
)
from agent.tools.gdrive_tool import list_scrapbook_vendors


def render():
    st.markdown("## Competitor Configuration")
    st.markdown(
        "<p style='color:#64748b;margin-top:-8px;font-size:14px'>"
        "Manage the vendors you want to track and configure their data sources.</p>",
        unsafe_allow_html=True
    )

    # ── Add New Competitor ─────────────────────────────────────────────────────
    with st.expander("➕  Add New Competitor", expanded=False):
        with st.form("add_competitor_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Vendor Name *", placeholder="e.g. Salesforce")
                website = st.text_input("Website URL", placeholder="https://salesforce.com")
                docs = st.text_input("Documentation URL", placeholder="https://developer.salesforce.com/docs")
            with col2:
                blog = st.text_input("Blog URL", placeholder="https://salesforce.com/blog")
                changelog = st.text_input("Changelog / Release Notes URL", placeholder="https://salesforce.com/releases")
                youtube = st.text_input("YouTube Channel", placeholder="@SalesforceYT or channel ID")

            st.caption("💡 Docs and Changelog URLs significantly improve technical depth of the analysis.")

            submitted = st.form_submit_button("Save Competitor", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Vendor name is required.")
                else:
                    success = add_competitor(
                        name.strip(), website, blog, docs, changelog, youtube
                    )
                    if success:
                        # Feature 4: "Saved" indicator on click
                        st.markdown("""
                            <div style='display:flex;align-items:center;gap:8px;
                                background:#f0fdf4;border:1px solid #86efac;
                                border-radius:8px;padding:10px 16px;margin-top:8px'>
                                <span style='font-size:16px'>✓</span>
                                <span style='color:#15803d;font-weight:600;font-size:14px'>Saved</span>
                                <span style='color:#94a3b8;font-size:13px'>— {name} added to your competitor list.</span>
                            </div>
                        """.replace("{name}", name), unsafe_allow_html=True)
                        st.rerun()
                    else:
                        st.error(f"A competitor named '{name}' already exists.")

    st.divider()

    # ── Existing Competitors ───────────────────────────────────────────────────
    competitors = get_all_competitors()

    if not competitors:
        st.info("No competitors configured yet. Add your first one above.")
        return

    st.markdown(
        f"<p style='color:#64748b;font-size:13px;font-weight:600;letter-spacing:0.04em;"
        f"text-transform:uppercase'>Configured Vendors ({len(competitors)})</p>",
        unsafe_allow_html=True
    )

    try:
        scrapbook_vendors = [v.lower() for v in list_scrapbook_vendors()]
    except Exception:
        scrapbook_vendors = []

    for comp in competitors:
        has_scrapbook = any(
            comp["vendor_name"].lower() in v or v in comp["vendor_name"].lower()
            for v in scrapbook_vendors
        )
        has_docs = bool(comp.get("docs_url") or comp.get("changelog_url"))

        badges = []
        if has_scrapbook:
            badges.append("📄 Scrapbook")
        if has_docs:
            badges.append("📚 Docs")
        badge_str = "  ·  " + "  ".join(badges) if badges else ""

        with st.expander(f"🏢  {comp['vendor_name']}{badge_str}", expanded=False):
            with st.form(f"edit_{comp['id']}"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Vendor Name", value=comp["vendor_name"])
                    new_website = st.text_input("Website URL", value=comp.get("website_url") or "")
                    new_docs = st.text_input("Documentation URL", value=comp.get("docs_url") or "")
                with col2:
                    new_blog = st.text_input("Blog URL", value=comp.get("blog_url") or "")
                    new_changelog = st.text_input("Changelog URL", value=comp.get("changelog_url") or "")
                    new_youtube = st.text_input("YouTube Channel", value=comp.get("youtube_channel") or "")

                col_save, col_delete = st.columns([3, 1])
                with col_save:
                    if st.form_submit_button("💾  Save Changes", type="primary"):
                        update_competitor(
                            comp["id"], new_name, new_website, new_blog,
                            new_docs, new_changelog, new_youtube
                        )
                        # Feature 4: Saved indicator on edit save too
                        st.markdown("""
                            <div style='display:inline-flex;align-items:center;gap:6px;
                                background:#f0fdf4;border:1px solid #86efac;
                                border-radius:6px;padding:6px 14px;margin-top:4px'>
                                <span style='color:#15803d;font-weight:600;font-size:13px'>✓ Saved</span>
                            </div>
                        """, unsafe_allow_html=True)
                        st.rerun()
                with col_delete:
                    if st.form_submit_button("🗑️  Delete", type="secondary"):
                        delete_competitor(comp["id"])
                        st.rerun()
