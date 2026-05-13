# CompIntel — AI Competitive Intelligence Agent

## What This Project Is

A LangGraph-based AI agent that scrapes competitor websites, docs, YouTube channels, and a personal Google Doc scrapbook, then synthesizes structured competitive intelligence reports using Claude. Built for product managers at Ping Identity to monitor competitors (currently Okta, Descope, Transmit Security) against their own product (PingOne Multi Tenant Platform).

Entrypoint: `app.py` (Streamlit UI). Agent entrypoint: `agent/graph.py`.

---

## Architecture: LangGraph StateGraph

The pipeline is a **linear directed graph** of 8 nodes. A single `AgentState` TypedDict flows through every node — nodes read from state and return a partial state update. Nodes never call each other directly.

```
intent_classifier → home_company_scraper → web_scraper → youtube_scraper
  → gdoc_reader → synthesizer → diff_engine → report_writer
```

### Adding a new node

1. Create `agent/nodes/your_node.py` with a function `your_node(state: AgentState) -> AgentState`
2. Add the field(s) it produces to `AgentState` in `agent/state.py`
3. Register it in `agent/graph.py`: `graph.add_node(...)` + `graph.add_edge(...)`
4. Add it to `PIPELINE_STEPS` and `STEP_LABELS` in `agent/graph.py`

Never wire nodes by calling them directly from other nodes.

---

## State Schema (`agent/state.py`)

Key fields to know:

| Field | Set by | Purpose |
|---|---|---|
| `vendors` | Initial state | List of vendor names to research |
| `research_query` | Initial state | The user's plain-English question |
| `analysis_mode` | `intent_classifier` | One of 4 modes — drives prompt selection |
| `target_feature` | `intent_classifier` | Populated only in `feature_deep_dive` mode |
| `home_company_content` | `home_company_scraper` | Scraped Ping Identity context, injected into all synthesis prompts |
| `raw_data` | `web_scraper` / `youtube_scraper` / `gdoc_reader` | List of `CompetitorRawData` dicts, one per vendor |
| `syntheses` | `synthesizer` | List of `CompetitorSynthesis` dicts, one per vendor |
| `diffs` | `diff_engine` | List of `DiffResult` dicts, one per vendor |
| `errors` | Any node | Append-only list — never overwrite, always `list(state.get("errors", []))` |

Always initialise new state fields in `_make_initial_state()` in `agent/graph.py`.

---

## The 4 Analysis Modes

The `intent_classifier` node (Claude Haiku 4.5) reads the research query and sets `analysis_mode` to one of:

| Mode | Trigger signal | Output shape |
|---|---|---|
| `feature_deep_dive` | Specific named feature or capability | Step-by-step breakdown + direct comparison to Ping |
| `landscape_scan` | "What did X ship?", "What's new?" | Scannable launch list grouped by theme |
| `strategic` | Positioning, direction, SWOT, comparison | Full multi-section strategic analysis |
| `battle_card` | "How do we compare?", sales context | Sales-ready: strengths, weaknesses, objections, positioning |

Each mode has its own:
- Prompt template in `agent/nodes/synthesizer.py` (`PROMPT_TEMPLATES` dict)
- Section extraction map (`SECTIONS_BY_MODE` dict)
- Report builder function in `agent/nodes/report_writer.py`

When adding or changing a mode, update **all three** locations.

---

## LLM Usage

**Never use OpenAI or any provider other than Anthropic.**

| Node | Model | Why |
|---|---|---|
| `intent_classifier` | `claude-haiku-4-5-20251001` (`CLAUDE_HAIKU_MODEL`) | Fast, cheap — classification only |
| `synthesizer` | `claude-sonnet-4-6` (`CLAUDE_MODEL`) | Full synthesis + vision (scrapbook images) |
| `diff_engine` | `claude-sonnet-4-6` (`CLAUDE_MODEL`) | Semantic delta comparison |

All models and the API key are imported from `config/settings.py`:
```python
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_HAIKU_MODEL
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model=CLAUDE_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.2)
```

The system prompt in `synthesizer.py` is **dynamic** — always call `_build_system_prompt()` rather than using `BASE_SYSTEM_PROMPT` directly. It injects the company name from `config/your_company.json`.

### Multimodal images (scrapbook)

Claude's image format differs from OpenAI. Always use:
```python
{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}
```
Never use `image_url` — that's the OpenAI format and will fail.

---

## Parallelization Pattern

All nodes that loop over multiple vendors use `ThreadPoolExecutor`. **Do not write sequential vendor loops.**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=len(vendors)) as executor:
    futures = {executor.submit(_process_one, v, ...): v for v in vendors}
    for future in as_completed(futures):
        vendor_name = futures[future]
        result, error = future.result()
        ...

# Always re-sort to preserve original vendor order after parallel execution
ordered = [results[v] for v in vendors if v in results]
```

The LangChain Anthropic client is thread-safe. SQLite connections are opened per-call inside each helper function — do not share a single connection across threads.

---

## Scraper (`agent/tools/scraper_tool.py`)

**Strategy per vendor:**
1. Serper API seeds relevant deep-page URLs (`site:<domain>` restricted search)
2. BFS crawl up to `MAX_DEPTH=5` levels, following `TOP_K_PER_LEVEL=4` highest-scoring links per page
3. If BS4-extracted text is under `SPA_SHELL_THRESHOLD=200` chars (JS-rendered SPA), falls back to Jina Reader (`r.jina.ai/<url>`) — no API key required
4. Pages below `MIN_CONTENT_SCORE=2` query-word hits are discarded

Key constants (all at the top of the file):
- `MAX_CHARS_PER_PAGE = 8000` — per-page content limit
- `MAX_PAGES_TOTAL = 40` — hard cap per domain per run
- `CRAWL_DELAY = 0.25` — seconds between requests (politeness)
- `JINA_TIMEOUT = 30` — Jina needs more time than direct fetches

**URL fields support comma-separated values** in both `config/competitors.json` and `config/your_company.json`. Both `web_scraper_node` and `home_company_scraper_node` use `_split_urls()` to expand them before passing to the crawler. Always use `_split_urls()` — never pass raw config URL strings directly to `scrape_for_vendor`.

---

## Config Files (Source of Truth for Competitor Data)

### `config/competitors.json`
List of competitors with URLs. This is the **canonical source** — it seeds the SQLite `competitors` table on first run and is re-seeded after every Streamlit Cloud redeploy (which wipes SQLite). Any competitor added via the UI is also written back to this file.

### `config/your_company.json`
Ping Identity's own URLs. Scraped by `home_company_scraper_node` on a **24-hour TTL cache** stored in the `home_company_context` SQLite table. When stale, the node re-scrapes and updates the cache. When fresh, it returns instantly.

Do not hardcode Ping Identity product knowledge anywhere in prompts — it must come from this scraped content so it stays current.

---

## Database (`db/database.py`)

SQLite at `db/competitor_intel.db`. Three tables:

| Table | Purpose |
|---|---|
| `competitors` | Vendor config — seeded from `config/competitors.json` |
| `reports` | One row per run — stores full markdown report |
| `diff_log` | One row per vendor per run — stores previous/new snapshots and delta summary |
| `home_company_context` | Single-row cache of Ping Identity scraped content with `scraped_at` timestamp |

**Streamlit Cloud wipes the SQLite file on every redeploy.** This is why `competitors.json` exists as a seed file. The `home_company_context` cache and all report history are lost on redeploy — this is a known limitation, not a bug. If persistence across deploys matters, migrate to Postgres.

The `diff_engine` uses `get_last_report_for_vendor()` to retrieve the previous snapshot. On first run per vendor, it returns `None` and the diff is skipped gracefully.

---

## UI (`app.py`, `ui/pages/`)

Three pages: **Configure** (manage competitors), **Evaluate** (run analysis), **History** (past reports).

The evaluate page streams node completions via `stream_agent()` in `agent/graph.py` using LangGraph's `stream_mode="updates"`. The progress bar advances after each node completes — do not change to batch/non-streaming mode.

Reference sources render as a **collapsed `st.expander`** by default — do not change to an always-expanded list.

Custom CSS is injected via `st.markdown(..., unsafe_allow_html=True)` at the top of each page render function. The design language is warm neutral / Stripe-Vercel feel — `#f8f7f4` background, Inter font, `#1a56db` accent blue.

---

## Environment Variables (`.env`)

| Variable | Required | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | All LLM nodes |
| `SERPER_API_KEY` | Recommended | Scraper (falls back to direct BFS without it) |
| `GOOGLE_DRIVE_FOLDER_ID` | Optional | Drive upload in report_writer |
| `GOOGLE_DOC_SCRAPBOOK_ID` | Optional | gdoc_reader (scrapbook feature) |
| `GMAIL_SENDER` | Optional | Email distribution |
| `GMAIL_APP_PASSWORD` | Optional | Email distribution (must be Gmail App Password, not account password) |

The app runs without Google and Gmail credentials — those features are opt-in per run.

---

## What Not To Do

- **Do not add sequential vendor loops** — always use `ThreadPoolExecutor`
- **Do not use OpenAI / `langchain_openai` / `ChatOpenAI`** — the project is Anthropic-only
- **Do not hardcode "Ping Identity" product knowledge in prompts** — it must come from `home_company_content` in state, which is scraped live
- **Do not bypass `_split_urls()`** when reading URL fields from config — values may be comma-separated
- **Do not share SQLite connections across threads** — open a new connection per call via `get_connection()`
- **Do not add a new analysis mode** without updating `PROMPT_TEMPLATES`, `SECTIONS_BY_MODE` (synthesizer), and adding a `_build_*_report` function (report_writer)
- **Do not write the company name or product context as a static string** — load it via `_build_system_prompt()` which reads `config/your_company.json`
