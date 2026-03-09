# ⚡ CompIntel — AI-Powered Competitive Intelligence Agent

An autonomous AI agent that monitors competitor websites, documentation, YouTube channels, and your personal Google Doc scrapbook — synthesizing everything into deep, structured intelligence reports with delta highlights showing only what changed since your last run.

Built with **LangGraph + GPT-4o Vision + Streamlit**.

---

## 🔗 Links

| | |
|---|---|
| 🎬 **Demo Video** | [Watch on Google Drive](https://drive.google.com/file/d/1Z_xV1Lia8C7GkLupHmS4O31_ylxXI2Tx/view?usp=sharing) |
| 🌐 **Live App** | [removed | available on request] |
| 💻 **GitHub** | [saparjaedu-blr/competitive-intel-agent](https://github.com/saparjaedu-blr/competitive-intel-agent) |

---

## ✨ Features

### Intelligence
- **8-dimension analysis** per vendor — Launches, Use Cases, Technical Architecture, UI/UX, Pricing, Strategic Direction, Competitive Gaps, Watch Points
- **GPT-4o Vision** — reads screenshots, pricing tables, roadmap slides, and diagrams from your scrapbook docs
- **Diff engine** — semantic comparison vs previous run, highlights only what's new

### Data Sources
- Competitor websites and blogs (BeautifulSoup + Playwright)
- Product documentation and changelogs
- YouTube video transcripts
- Personal Google Doc scrapbook (multi-tab, one doc per competitor, with images)

### Output & Delivery
- **Real-time streaming** — progress bar advances as each pipeline node completes, with live synthesis preview
- **Publish & Archive** — optional Google Drive upload + Report History (or run in live-only mode)
- **Email distribution** — send reports to multiple stakeholders via Gmail
- **Warm Neutral UI** — clean off-white Stripe/Vercel-style interface

---

## 🚀 Sample Competitor Configuration

### AI Platform Set

| Field | Anthropic | OpenAI |
|---|---|---|
| **Vendor Name** | Anthropic | OpenAI |
| **Website URL** | https://www.anthropic.com/ | https://openai.com |
| **Blog URL** | https://claude.com/blog | https://openai.com/news/ |
| **Documentation URL** | https://www.anthropic.com/learn | https://developers.openai.com/api-docs |
| **Changelog URL** | https://www.anthropic.com/news | https://openai.com/news/company-announcements/ |
| **YouTube Channel** | https://www.youtube.com/@anthropic-ai | @OpenAI |

---

## 💬 Sample Research Queries

### Anthropic + OpenAI Together
```
Compare pricing and free tiers between Anthropic and OpenAI
```
```
What are the latest models from Anthropic and OpenAI and how do they differ?
```
```
Which is better for developers — Anthropic or OpenAI, and why?
```
```
How do Anthropic and OpenAI approach AI safety differently?
```
```
Which is faster and cheaper for building AI apps — Claude or GPT-4o?
```

### Just Anthropic
```
What is Anthropic shipping right now?
```
```
What are the differences between Claude Haiku, Sonnet, and Opus?
```
```
What can developers do with the Claude API today?
```
```
How is Anthropic positioned for enterprise customers?
```
```
Where is Anthropic headed in the next 6 months?
```

---

## 🛠 Setup

### 1. Clone & install

```bash
git clone https://github.com/saparjaedu-blr/competitive-intel-agent.git
cd competitive-intel-agent

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your API keys — see Environment Variables section below
```

### 3. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (e.g. `CompIntelAgent`)
3. Enable **Google Drive API** and **Google Docs API**
4. OAuth consent screen → External → add your email as a Test User
5. Credentials → Create OAuth 2.0 Client ID → Desktop App → download as `credentials.json`
6. Place `credentials.json` in the project root
7. First run opens a browser for auth → saves `token.json` automatically

### 4. Gmail App Password

1. Enable 2-factor auth on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate for "Mail" → paste the 16-char password into `GMAIL_APP_PASSWORD` in `.env`

### 5. Google Doc Scrapbook

Create a folder in Google Drive (e.g. `Competitor Scrapbook`). Inside it, create **one Google Doc per competitor** — the filename should match the vendor name you configure in the app:

```
📁 Competitor Scrapbook/          ← copy this folder's ID into GOOGLE_DOC_SCRAPBOOK_ID
    📄 OpenAI                     ← tabs: "Models", "API Features", "Pricing", "Roadmap"
    📄 Anthropic                  ← tabs: "Claude Models", "Safety", "Enterprise"
    📄 Google DeepMind
```

Each doc supports **multiple tabs** (e.g. AI Features, Pricing, Integrations). The agent reads all tabs and extracts all inline images automatically using GPT-4o Vision.

Copy the **folder ID** from its URL:
```
https://drive.google.com/drive/folders/YOUR_FOLDER_ID_HERE
                                        ^^^^^^^^^^^^^^^^^^^
```

### 6. Run

```bash
streamlit run app.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API key (GPT-4o) |
| `GOOGLE_DRIVE_FOLDER_ID` | ✅ | Drive folder ID for report output |
| `GOOGLE_DOC_SCRAPBOOK_ID` | ✅ | Scrapbook **folder** ID (not a doc ID) |
| `GMAIL_SENDER` | ✅ | Your Gmail address |
| `GMAIL_APP_PASSWORD` | ✅ | Gmail App Password (16 chars) |
| `YOUTUBE_API_KEY` | ⚪ Optional | YouTube Data API v3 key for channel search |
| `DB_PATH` | ⚪ Optional | Custom SQLite path (default: `competitor_intel.db`) |

---

## 🏗 Architecture

### LangGraph Pipeline

```
web_scraper ──► youtube_scraper ──► gdoc_reader
                                         │
                                    synthesizer          ← GPT-4o Vision (text + images)
                                         │
                                    diff_engine          ← semantic delta vs last run
                                         │
                                    report_writer ──► SQLite + Google Drive (if enabled)
```

Each node streams its completion back to the UI in real time — the progress bar advances and a live synthesis preview appears as GPT-4o processes each vendor.

### Project Structure

```
competitive-intel-agent/
├── app.py                        # Streamlit entry point + global theme
├── .streamlit/config.toml        # Warm Neutral light theme config
├── config/settings.py            # Env + constants
├── db/database.py                # SQLite CRUD (competitors, reports, diff_log)
├── agent/
│   ├── graph.py                  # LangGraph definition + stream_agent()
│   ├── state.py                  # AgentState TypedDict
│   └── nodes/
│       ├── web_scraper.py        # Scrapes website + blog + docs + changelog
│       ├── youtube_scraper.py    # Fetches YouTube transcripts
│       ├── gdoc_reader.py        # Reads scrapbook folder (all tabs + images)
│       ├── synthesizer.py        # GPT-4o 8-section deep analysis
│       ├── diff_engine.py        # Semantic delta vs previous snapshot
│       └── report_writer.py     # Markdown report + conditional Drive upload
├── mailer/emailer.py             # Gmail SMTP distribution
└── ui/pages/
    ├── configure.py              # Competitor CRUD with docs/changelog URLs
    ├── evaluate.py               # Run agent + streaming progress + results
    └── history.py                # Archived reports viewer
```

---

## 📋 Report Structure

Each vendor gets 8 analysis sections:

| Tab | What it covers |
|---|---|
| 🚀 Launches | Specific features shipped, dates, target segments |
| 🎯 Use Cases | Concrete workflows, industries, jobs-to-be-done |
| ⚙️ Technical | APIs, protocols, SDKs, integrations, infrastructure |
| 🖥️ UI/UX | Interface patterns, onboarding, UX observations |
| 💰 Pricing | Tiers, limits, PLG motion, enterprise packaging |
| 🧭 Direction | Roadmap signals, investment themes, platform bets |
| ⚔️ Gaps | Where they're ahead of you, where they're weak |
| 👁️ Watch Points | Top 3–5 things to monitor next quarter |

---

## 🔒 Security Notes

The following are **gitignored** and never leave your machine:
- `.env` — all API keys
- `credentials.json` — Google OAuth client secret
- `token.json` — Google OAuth access token
- `*.db` — your SQLite database with reports

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| AI Orchestration | LangGraph |
| Language Model | GPT-4o (with Vision) |
| Web Scraping | BeautifulSoup4 + Playwright |
| Video Transcripts | youtube-transcript-api |
| Google Integration | Google Drive API + Docs API |
| Storage | SQLite |
| UI | Streamlit (Warm Neutral theme) |
| Email | Gmail SMTP |
