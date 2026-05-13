import streamlit as st
from db.database import init_db
from ui.pages import configure, evaluate, history

st.set_page_config(
    page_title="CompIntel — Competitive Intelligence Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── Global CSS — Warm Neutral / Stripe-Vercel feel ─────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* App background — warm off-white */
.stApp {
    background: #f8f7f4;
}

/* Main content area */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1080px;
}

/* Sidebar — clean white with subtle border */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8e4dd;
    box-shadow: 1px 0 8px rgba(0,0,0,0.04);
}

/* Sidebar nav items */
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 13.5px;
    font-weight: 500;
    color: #64748b;
    padding: 8px 12px;
    border-radius: 8px;
    letter-spacing: -0.01em;
    transition: all 0.15s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: #f1f0ec;
    color: #1e293b;
}

/* Dividers */
hr {
    border-color: #e8e4dd !important;
    margin: 12px 0 !important;
}

/* Card surfaces */
.stExpander {
    background: #ffffff !important;
    border: 1px solid #e8e4dd !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
.streamlit-expanderHeader {
    background: #ffffff !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #1e293b !important;
    padding: 14px 16px !important;
}
.streamlit-expanderContent {
    border-top: 1px solid #f1f0ec !important;
}

/* Input fields */
.stTextInput input, .stTextArea textarea {
    background: #ffffff !important;
    border: 1.5px solid #e2ddd6 !important;
    border-radius: 8px !important;
    color: #1e293b !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #1a56db !important;
    box-shadow: 0 0 0 3px rgba(26,86,219,0.1) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #94a3b8 !important;
}

/* Labels */
.stTextInput label, .stTextArea label, .stMultiSelect label {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #475569 !important;
    letter-spacing: 0.01em !important;
}

/* Multiselect */
.stMultiSelect [data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1.5px solid #e2ddd6 !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 6px !important;
    color: #1d4ed8 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #f1f0ec;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #e8e4dd;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    font-size: 12px;
    font-weight: 500;
    color: #64748b;
    padding: 6px 14px;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #1a56db !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    font-weight: 600 !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: #1a56db !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: -0.01em !important;
    padding: 11px 24px !important;
    box-shadow: 0 1px 3px rgba(26,86,219,0.3), 0 4px 12px rgba(26,86,219,0.15) !important;
    transition: all 0.15s !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1e40af !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 6px rgba(26,86,219,0.35), 0 6px 16px rgba(26,86,219,0.2) !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    border: 1.5px solid #e2ddd6 !important;
    border-radius: 9px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    color: #475569 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #1a56db !important;
    color: #1a56db !important;
}

/* Checkbox */
.stCheckbox label {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #374151 !important;
}

/* Progress bar */
.stProgress > div > div {
    background: linear-gradient(90deg, #1a56db, #3b82f6) !important;
    border-radius: 4px !important;
}

/* Alerts */
.stAlert {
    border-radius: 10px !important;
    border-left-width: 3px !important;
    font-size: 13.5px !important;
}

/* Info box */
div[data-testid="stInfo"] {
    background: #eff6ff !important;
    border-color: #1a56db !important;
    color: #1e3a5f !important;
}

/* Success box */
div[data-testid="stSuccess"] {
    background: #f0fdf4 !important;
    border-color: #16a34a !important;
}

/* Warning box */
div[data-testid="stWarning"] {
    background: #fffbeb !important;
    border-color: #d97706 !important;
}

/* Subheaders */
h2, h3 {
    color: #0f172a !important;
    letter-spacing: -0.02em !important;
}

/* Caption text */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
    font-size: 12px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f8f7f4; }
::-webkit-scrollbar-thumb { background: #d1cec9; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #1a56db; }

/* Link buttons */
.stLinkButton a {
    background: #ffffff !important;
    border: 1.5px solid #e2ddd6 !important;
    border-radius: 9px !important;
    color: #1a56db !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    transition: all 0.15s !important;
}
.stLinkButton a:hover {
    border-color: #1a56db !important;
    box-shadow: 0 2px 6px rgba(26,86,219,0.15) !important;
}

/* Form submit buttons */
.stFormSubmitButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='padding:12px 4px 24px 4px'>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='background:#1a56db;color:white;border-radius:8px;
                    width:32px;height:32px;display:flex;align-items:center;
                    justify-content:center;font-size:16px;font-weight:700;
                    box-shadow:0 2px 8px rgba(26,86,219,0.3)'>⚡</div>
                <div>
                    <div style='font-size:16px;font-weight:700;color:#0f172a;
                        letter-spacing:-0.03em'>CompIntel</div>
                    <div style='font-size:10px;color:#94a3b8;letter-spacing:0.06em;
                        text-transform:uppercase;margin-top:1px'>Intelligence Agent</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "Navigation",
        options=["Evaluate Competitors", "Configure Competitors", "Report History"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("""
        <div style='padding:4px;'>
            <div style='font-size:11px;color:#cbd5e1;font-weight:600;
                letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px'>
                Powered by
            </div>
            <div style='display:flex;flex-direction:column;gap:5px'>
                <div style='display:flex;align-items:center;gap:7px'>
                    <div style='width:5px;height:5px;border-radius:50%;background:#1a56db'></div>
                    <span style='font-size:12px;color:#64748b'>LangGraph</span>
                </div>
                <div style='display:flex;align-items:center;gap:7px'>
                    <div style='width:5px;height:5px;border-radius:50%;background:#10b981'></div>
                    <span style='font-size:12px;color:#64748b'>Claude Sonnet 4.6</span>
                </div>
                <div style='display:flex;align-items:center;gap:7px'>
                    <div style='width:5px;height:5px;border-radius:50%;background:#f59e0b'></div>
                    <span style='font-size:12px;color:#64748b'>Streamlit</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ── Page Routing ───────────────────────────────────────────────────────────────
if page == "Configure Competitors":
    configure.render()
elif page == "Evaluate Competitors":
    evaluate.render()
elif page == "Report History":
    history.render()
