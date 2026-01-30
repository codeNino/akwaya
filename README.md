# Akwaya — Lead Qualification & Cold Outreach Platform

A full-stack **lead generation and qualification** system that sources leads from Google Places and search, enriches them via website scraping and LLM evaluation, stores them in PostgreSQL, and runs AI-powered cold calls via [Retell](https://www.retellai.com/). The web UI provides a dashboard to run the pipeline, view prospects and qualified leads, trigger calls (single or bulk), run cold-call campaigns, and delete prospects.

---

## Features

- **Lead sourcing** — Search keywords (LLM-generated) across Google Places and web search (Serper), then preprocess and deduplicate.
- **Enrichment** — Score prospects, scrape websites, evaluate content with LLM, and merge in contact info (email, phone, about).
- **Persistence** — Save enriched leads to PostgreSQL with duplicate detection (by phone, email, or name).
- **Cold calling** — Initiate outbound calls via Retell AI; support for single-call, bulk “Call selected,” and campaigns (capped at 10 calls per run).
- **Feedback loop** — Retell webhook receives call analysis; prospects are updated with call summary, recording URL, and qualification flags.
- **Web dashboard** — React SPA: pipeline trigger, prospect/lead tables with checkboxes, select-all, bulk Call/Delete, cold-call campaign, and delete-by-id.

---

## How it works

1. **Pipeline (lead acquisition)**  
   You submit a search query (e.g. “forex bureaus Lagos”). The backend:
   - Generates keywords with LLM.
   - Runs **Google Places** and **Google Search** (Serper) in parallel.
   - Preprocesses and flattens results into a sourced-leads file.
   - Scores prospects, scrapes websites, evaluates with LLM, and merges enriched data.
   - Loads enriched leads into the DB (skipping duplicates by phone/email/name).

2. **Prospects**  
   Stored in PostgreSQL. “Callable” prospects are those with a phone number and not yet called (`is_called = false`).

3. **Calls**  
   - **Single call** — Trigger a Retell call for one prospect by ID.  
   - **Bulk call** — Select multiple prospects (or leads) in the UI and trigger calls for all.  
   - **Campaign** — Start a background job that calls up to 10 uncalled prospects (limit configurable, max 10).

4. **Qualification**  
   After a call, Retell sends a webhook with analysis. The app updates the prospect: `call_summary`, `recording_url`, `is_qualified`, `is_relevant_industry`, and sets `is_called = true`. “Qualified leads” are prospects where `is_qualified = true`.

---

## Tech stack

| Layer        | Technology |
|-------------|------------|
| Backend     | Python 3.11+, FastAPI, Uvicorn |
| Database    | PostgreSQL, SQLAlchemy 2.x |
| LLM / AI    | OpenAI (LangChain/LangGraph for scoring), keyword generation, website evaluation |
| Search      | Serper API (web search), Google Places API |
| Scraping    | Scrapfly, Parsel, BeautifulSoup |
| Voice       | Retell AI SDK (outbound calls) |
| Frontend    | React 19, Vite 7, Axios |
| Config      | python-dotenv, YAML (funnel config) |

---

## Project structure

```
akwaya/
├── main.py                 # FastAPI app, static files, CORS, routes
├── pyproject.toml          # Python deps (uv/pip)
├── client/                 # React SPA
│   ├── src/
│   │   ├── App.jsx        # Dashboard: pipeline, prospects, leads, campaign
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   └── vite.config.js     # Dev proxy /api -> backend
├── server/
│   ├── controller.py      # API routes (pipeline, prospects, leads, call, campaign, webhook, delete)
│   └── dto.py             # Pydantic request bodies
├── internal/
│   ├── config/
│   │   ├── paths_config.py
│   │   ├── secret.py      # Env vars (DB, APIs, Retell)
│   │   └── funnel_config.yaml
│   ├── domain/
│   │   ├── service.py     # Pipeline runner, cold-call campaign, single call, feedback
│   │   ├── pipeline/     # Ingestion, augmentation, loader (persist + dedup)
│   │   ├── scraper/       # WebSearcher (Places + Serper), crawler
│   │   ├── brainbox/     # Keywords, preprocess, evaluate, extract
│   │   ├── calling/      # Retell client, make_retell_call
│   │   ├── common/       # DTOs, scoring
│   │   └── deduplicator/
│   └── utils/
│       ├── database/      # Session, models (Prospect), manager (CRUD)
│       ├── normalizer.py  # Phone, email, URL
│       ├── logger.py
│       └── loader.py
└── artifacts/             # Generated JSON (leads_sourced, leads_augmented, etc.)
```

---

## Prerequisites

- **Python 3.11+** (e.g. `uv` or `pip`)
- **Node.js 20+** (for `client` build and dev)
- **PostgreSQL** (for prospect storage)
- **API keys**: Serper, Google (Places / CSE if used), OpenAI, Retell (API key, from-number, agent ID)

---

## Environment variables

Create a `.env` in the project root. Required for app startup (see `validate_environment` in `main.py`):

| Variable           | Description |
|--------------------|-------------|
| `SERPER_API_KEY`   | Serper.dev API key (web search) |
| `GOOGLE_API_KEY`   | Google API key (Places / other Google APIs) |
| `OPENAI_KEY`       | OpenAI API key (LLM, scoring, keywords) |

Database (PostgreSQL):

| Variable     | Description |
|-------------|-------------|
| `PG_URI`    | Full connection string, **or** set: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (used to build `PG_URI`) |

Retell (cold calling):

| Variable             | Description |
|----------------------|-------------|
| `RETELL_API_KEY`     | Retell API key |
| `RETELL_FROM_NUMBER` | Outbound caller number (E.164) |
| `RETELL_AGENT_ID`    | Retell agent ID for outbound calls |

Optional / other:

| Variable          | Description |
|-------------------|-------------|
| `PORT`            | Server port (default `8000`) |
| `ENV`             | `local` / `development` / `staging` / `production` |
| `ALLOWED_ORIGINS` | JSON array of CORS origins (default `["*"]`) |
| `SCRAPFLY_KEY`    | Scrapfly (if used for scraping) |

---

## Installation

**Backend**

```bash
# From project root (uv recommended)
uv sync
# or
pip install -e .
```

**Frontend**

```bash
cd client
npm install
```

**Database**

- Create a PostgreSQL database and run migrations / table creation (app uses SQLAlchemy `create_all`; see `internal.utils.database.session` and `init_db` where used, e.g. in loader).

---

## Running the app

**1. Start the backend**

```bash
python main.py
```

Server runs at `http://0.0.0.0:8000` (or the port set in `PORT`). It serves the **built** React app from `client/dist` and the API under `/api/v1`.

**2. Build the frontend (so UI changes appear)**

After any change in `client/src`, rebuild so the server serves the new assets:

```bash
cd client && npm run build
```

Then restart the server (or refresh with a hard reload, e.g. Ctrl+Shift+R).

**3. Frontend dev with hot reload**

Run Vite and the backend together:

- Terminal 1: `python main.py`
- Terminal 2: `cd client && npm run dev`

Open the URL Vite prints (e.g. `http://localhost:5173`). The Vite dev server proxies `/api` to the backend so the same API is used.

---

## API reference (prefix `/api/v1`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/leads/pipeline` | Start lead acquisition pipeline. Body: `{ "query": "e.g. forex bureaus Lagos" }`. Runs in background. |
| `GET`  | `/prospects`      | List callable prospects (has phone, not yet called). |
| `GET`  | `/leads`          | List qualified leads (`is_qualified = true`). |
| `POST` | `/call`           | Trigger a single Retell call. Body: `{ "prospect_id": "..." }`. |
| `POST` | `/cold_call/campaign` | Start cold-call campaign (background). Body: `{ "limit": 10 }` (optional; max 10). |
| `DELETE` | `/prospects/{prospect_id}` | Delete a prospect by ID. |
| `POST` | `/webhook/retell_feedback` | Retell webhook: call analysis and qualification flags; updates prospect. |

---

## Web UI (dashboard)

- **Overview** — Counts of callable prospects and qualified leads; quick links to other sections.
- **Lead search** — Input query and start the pipeline; optional “Stop watching” to stop polling.
- **Prospects (callable)** — Table with checkboxes (per row + “Select all”), Call and Delete per row, and bulk “Call selected” / “Delete selected.”
- **Qualified leads** — Same table pattern (checkboxes, Call/Delete per row, bulk actions).
- **Cold call campaign** — Optional limit (max 10), then “Start campaign” to run up to 10 calls in the background.

---

## Key components (summary)

- **Keywords generation / augmentation** — LLM-based expansion of the user query for search.
- **Leads sourcing** — Google Places + Serper (web search), async with semaphore-bound concurrency.
- **Leads information augmentation** — Website scraping, LLM evaluation, merging contact info (email, phone, about).
- **Leads scoring** — LLM ranking and points system (e.g. LangGraph-based scoring).
- **Leads verification** — Retell outbound calls; webhook updates prospect with summary and qualification.
- **Data persistence** — PostgreSQL (Prospect model), duplicate check by phone/email/name before insert; loader and pipeline write to DB and artifacts.

---
