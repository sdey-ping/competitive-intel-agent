# ⚡ CompIntel — AI-Powered Competitive Intelligence Agent

An autonomous AI agent that deep-crawls competitor websites and documentation, scrapes YouTube transcripts, and optionally reads your personal Google Doc scrapbook — then synthesizes everything into structured intelligence reports with delta highlights showing only what changed since your last run.

Built with **LangGraph + GPT-4o Vision + Streamlit**.

---

## 🔗 Links

| | |
|---|---|
| 🎬 **Demo Video** | [Watch on Google Drive](https://drive.google.com/file/d/1Z_xV1Lia8C7GkLupHmS4O31_ylxXI2Tx/view?usp=sharing) |
| 🌐 **Live App** | [Available on request] |
| 💻 **GitHub** | [sdey-ping/competitive-intel-agent](https://github.com/sdey-ping/competitive-intel-agent) |

---

## ✨ Features

### 🕷️ Deep Web Crawling (New)
- **Serper-powered seed discovery** — queries Google restricted to each vendor's domain, finding the top 8 most query-relevant deep pages (not just the homepage)
- **5-level BFS crawl** — breadth-first crawl from each seed, following up to 4 highest-scoring links per page, up to 5 levels deep
- **Relevance-guided traversal** — every link is scored by query-word overlap in its URL path before being followed; high-value paths (`/docs/`, `/use-cases/`, `/changelog/`, `/integrations/`, etc.) get a bonus score
- **Content filtering** — pages are kept only if they contain at least 2 distinct query-relevant terms; irrelevant pages are silently discarded
- **Hard cap of 40 pages per domain** — prevents runaway crawls while ensuring deep coverage
- **Graceful fallback** — if Serper is unavailable, crawls directly from configured URLs

### 🧠 Intelligence Synthesis
- **Intent-classified analysis** — GPT-4o-mini auto-detects query intent and routes to the right mode (or user overrides manually)
- **4 analysis modes** — each with its own prompt, structure, and UI layout (see below)
- **GPT-4o Vision** — reads screenshots, pricing tables, roadmap slides, and diagrams from your scrapbook docs
- **Diff engine** — semantic comparison vs previous run, filtered to only highlight changes relevant to your research question

### 📊 4 Analysis Modes

| Mode | When it activates | Output shape |
|---|---|---|
| 🔬 **Feature Deep Dive** | Asked about a specific named feature or capability | Flowing single-page: what it does, who it's for, how it fits their strategy |
| 📋 **Landscape Scan** | "What did X ship", "what's new", "recent updates" | Scannable bullet digest grouped by launch theme |
| 🧭 **Strategic Analysis** | Positioning, SWOT, comparison, roadmap, "where is X headed" | Dynamic tabs — only sections with substantive content are shown |
| ⚔️ **Battle Card** | "Where are we ahead/behind", sales differentiation | Two-column strengths/weaknesses, objections, one-line positioning |

### 🗂️ Data Sources
- Competitor websites, blogs, product docs, and changelogs — crawled 5 levels deep
- YouTube video transcripts (requires `YOUTUBE_API_KEY`)
- Personal Google Doc scrapbook (opt-in per run, multi-tab, with inline image extraction via GPT-4o Vision)

### 📤 Output & Delivery
- **Real-time streaming** — progress bar advances as each pipeline node completes, with live synthesis preview
- **Publish & Archive** — optional Google Drive upload + SQLite Report History
- **Live-only mode** — run without saving for quick ad-hoc queries
- **Email distribution** — send reports to multiple stakeholders via Gmail SMTP
- **Reference links** — every report surfaces the specific deep-page URLs that were actually used as sources

---

## 🏗️ Architecture

### LangGraph Pipeline

```
intent_classifier → web_scraper → youtube_scraper → gdoc_reader
                                                          │
                                                     synthesizer     ← GPT-4o Vision (text + images)
                                                          │
                                                     diff_engine     ← semantic delta vs last run
                                                          │
                                                     report_writer → SQLite + Google Drive (if enabled)
```

Each node streams its completion back to the UI in real time — the progress bar advances and a live synthesis preview appears as GPT-4o processes each vendor.

### Web Scraper Detail

```
For each configured vendor URL domain:
  1. Serper search → top 8 query-relevant deep page URLs via Google
  2. BFS from seeds:
       depth 0: Serper seeds + configured root URL
       depth 1-5: follow top-4 query-scored links per page
  3. Per page: content-score against query words → keep if score ≥ 2
  4. Cap at 40 pages/domain → ~60-120s per domain
  5. Fallback: direct BFS from root URL if Serper key missing
```

### Project Structure

```
competitive-intel-agent/
├── app.py                          # Streamlit entry point + global theme
├── .streamlit/config.toml          # Warm Neutral light theme
├── config/
│   ├── settings.py                 # Env vars + constants (incl. SERPER_API_KEY)
│   └── competitors.json            # Seed file — survives Streamlit Cloud redeploys
├── db/database.py                  # SQLite CRUD (competitors, reports, diff_log)
│                                   # Auto-seeds from competitors.json on startup
├── agent/
│   ├── graph.py                    # LangGraph pipeline + stream_agent()
│   ├── state.py                    # AgentState TypedDict
│   └── nodes/
│       ├── intent_classifier.py    # GPT-4o-mini: routes query to 1 of 4 modes
│       ├── web_scraper.py          # Calls scrape_for_vendor() per competitor
│       ├── youtube_scraper.py      # Fetches YouTube transcripts via API
│       ├── gdoc_reader.py          # Reads scrapbook folder (opt-in, all tabs + images)
│       ├── synthesizer.py          # GPT-4o: 8-section deep analysis, mode-aware
│       ├── diff_engine.py          # GPT-4o: semantic delta vs previous snapshot
│       └── report_writer.py        # Markdown report, conditional Drive upload
├── agent/tools/
│   ├── scraper_tool.py             # Serper + 5-level BFS deep crawler
│   ├── gdrive_tool.py              # Google Drive + Docs API (OAuth)
│   └── youtube_tool.py            # YouTube Data API + transcript-api
├── mailer/emailer.py               # Gmail SMTP distribution
└── ui/pages/
    ├── configure.py                # Competitor CRUD
    ├── evaluate.py                 # Run agent, streaming progress, results rendering
    └── history.py                  # Archived reports viewer
```

---

## 🚀 Setup

### 1. Clone & install

```bash
git clone https://github.com/sdey-ping/competitive-intel-agent.git
cd competitive-intel-agent

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> ℹ️ **Playwright removed** — the scraper now uses `requests` + `BeautifulSoup` only. No `playwright install` step needed.

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your keys — see Environment Variables below
```

### 3. Get a Serper API key (recommended — enables deep crawling)

1. Go to [serper.dev](https://serper.dev) and sign up
2. Copy your API key
3. Add `SERPER_API_KEY=your_key` to `.env`

Free tier: **2,500 searches/month** ≈ ~300 full vendor evaluations. Without this key the crawler falls back to BFS from configured root URLs directly (still works, just less targeted at depth).

### 4. Set up Google OAuth (for Scrapbook + Drive features)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (e.g. `CompIntelAgent`)
3. Enable **Google Drive API** and **Google Docs API**
4. OAuth consent screen → External → add your email as a Test User
5. Credentials → Create OAuth 2.0 Client ID → Desktop App → download as `credentials.json`
6. Place `credentials.json` in the project root
7. First run opens a browser for auth → saves `token.json` automatically

### 5. Gmail App Password

1. Enable 2-factor auth on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate for "Mail" → paste the 16-char password into `GMAIL_APP_PASSWORD` in `.env`

### 6. Google Doc Scrapbook (optional)

Create a folder in Google Drive. Inside it, create **one Google Doc per competitor** — filename should match the vendor name configured in the app:

```
📁 Competitor Scrapbook/          ← copy this folder's ID into GOOGLE_DOC_SCRAPBOOK_ID
    📄 Okta                       ← tabs: "Workflows", "Pricing", "Roadmap", "Screenshots"
    📄 PingOne DaVinci
    📄 Microsoft Entra
```

Each doc supports multiple tabs. The agent reads all tabs and extracts all inline images automatically using GPT-4o Vision. Enable per-run via the **"Include Google Doc Scrapbook"** checkbox in the UI.

Copy the **folder ID** from its Drive URL:
```
https://drive.google.com/drive/folders/YOUR_FOLDER_ID_HERE
```

### 7. Run

```bash
streamlit run app.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | GPT-4o + GPT-4o-mini for synthesis, classification, and diff |
| `SERPER_API_KEY` | ✅ Recommended | Google search via Serper — powers deep crawl seed discovery. Free tier: 2,500/mo |
| `GOOGLE_DRIVE_FOLDER_ID` | ⚪ Optional | Drive folder ID for archived report output |
| `GOOGLE_DOC_SCRAPBOOK_ID` | ⚪ Optional | Scrapbook **folder** ID (not a doc ID) |
| `GMAIL_SENDER` | ⚪ Optional | Your Gmail address for email distribution |
| `GMAIL_APP_PASSWORD` | ⚪ Optional | Gmail App Password (16 chars) |
| `YOUTUBE_API_KEY` | ⚪ Optional | YouTube Data API v3 key for channel video search |
| `DB_PATH` | ⚪ Optional | Custom SQLite path (default: `db/competitor_intel.db`) |

---

## 📋 Competitor Configuration

Each competitor has 6 configurable fields:

| Field | Purpose |
|---|---|
| **Vendor Name** | Must match your Google Doc scrapbook filename if using scrapbook |
| **Website URL** | Homepage — used as marketing crawl seed |
| **Blog URL** | Blog/news — second marketing crawl seed |
| **Documentation URL** | Product docs — technical crawl seed |
| **Changelog URL** | Release notes — second technical crawl seed |
| **YouTube Channel** | `@Handle` or channel ID — for transcript fetching |

Competitors are stored in both **SQLite** and **`config/competitors.json`** (checked into repo). The JSON file seeds the database on startup — so your competitor list survives Streamlit Cloud redeploys automatically.

### Sample Configuration (Identity / IAM space)

| Field | Okta | PingOne DaVinci |
|---|---|---|
| **Website URL** | https://www.okta.com | https://www.pingidentity.com |
| **Blog URL** | https://www.okta.com/blog/ | https://www.pingidentity.com/en/resources/blog.html |
| **Docs URL** | https://help.okta.com/wf/en-us/content/topics/workflows/workflows-main.htm | https://docs.pingidentity.com/davinci |
| **Changelog URL** | https://help.okta.com/wf/en-us/content/topics/releasenotes/workflows/production.htm | https://docs.pingidentity.com/davinci/release-notes |
| **YouTube** | @OktaInc | @PingIdentityTV |

---

## 💬 Sample Research Queries

### Strategic / SWOT
```
Perform an in-depth SWOT analysis for Okta Workflows from a workforce implementation perspective
```
```
Compare Okta Workflows vs PingOne DaVinci for enterprise no-code automation — where is each stronger?
```
```
How is Okta positioned for enterprise identity orchestration heading into next year?
```

### Landscape Scan
```
What did Okta ship in the last 90 days?
```
```
List the most recent feature launches across Okta and PingOne DaVinci
```

### Feature Deep Dive
```
How does Okta Workflows handle error branching and retry logic in multi-step flows?
```
```
What integrations does PingOne DaVinci support out of the box — especially for HR and ITSM?
```

### Battle Card
```
Where are we ahead and behind Okta Workflows? Give me a sales-ready battle card.
```
```
What objections do prospects raise when comparing us to Okta, and how should we respond?
```

---

## 📊 Report Structure

Analysis sections vary by mode. Here's the full set across all 4 modes:

| Section | Feature Deep Dive | Landscape Scan | Strategic | Battle Card |
|---|:---:|:---:|:---:|:---:|
| Direct Answer | ✅ | ✅ | ✅ | ✅ |
| What This Feature Does / Recent Launches | ✅ | ✅ | ✅ | → Strengths |
| Who It's Built For / Use Cases | ✅ | — | ✅ | → Objections |
| Technical Architecture | — | — | ✅ | — |
| UI/UX Observations | ✅ | — | — | — |
| Pricing & Packaging | — | — | ✅ | ✅ |
| Strategic Direction | ✅ | ✅ | ✅ | → Where We Win |
| Gaps vs Your Product | ✅ | ✅ | ✅ | → Weaknesses |
| Watch Points / Positioning | ✅ | — | ✅ | → One-Line Positioning |
| Reference Links | ✅ | ✅ | ✅ | ✅ |
| Delta (What's New Since Last Run) | ✅ | ✅ | ✅ | ✅ |

---

## 🔒 Security Notes

The following are **gitignored** and never leave your machine:

- `.env` — all API keys
- `credentials.json` — Google OAuth client secret
- `token.json` — Google OAuth access token
- `*.db` — SQLite database (reports, diff log)

`config/competitors.json` **is** checked into the repo by design — it contains only public vendor URLs and is the persistence mechanism for Streamlit Cloud redeploys.

---

## 📦 Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| AI Orchestration | LangGraph ≥ 0.2 | `stream_mode="updates"` for real-time UI |
| Intent Classification | GPT-4o-mini | Fast, cheap — 4-mode classifier |
| Synthesis & Diff | GPT-4o (with Vision) | Full analysis + scrapbook image reading |
| Web Scraping | requests + BeautifulSoup4 + lxml | 5-level BFS, Serper-seeded |
| Search Seed Discovery | Serper API | Google search restricted to vendor domain |
| Video Transcripts | youtube-transcript-api | No API key needed for transcripts |
| YouTube Channel Search | Google YouTube Data API v3 | API key needed for channel → video lookup |
| Google Integration | Google Drive API + Docs API | OAuth 2.0, multi-tab doc reading |
| Storage | SQLite | Competitors, reports, diff log |
| UI | Streamlit (Warm Neutral theme) | Real-time streaming, tab-based results |
| Email | Gmail SMTP | App Password auth |
