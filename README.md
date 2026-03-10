# Earnings Transcript Teacher

A Python pipeline that downloads, parses, and teaches earnings call transcripts. It extracts structured insights using classical NLP (TF-IDF, NMF, TextRank) and modern semantic search (Voyage AI + `pgvector`), stores everything in PostgreSQL, and surfaces it through two interfaces:

- **Console UI** (`main.py`) — interactive terminal menu and direct analysis
- **Web UI** (`app.py`) — Streamlit browser app with live chat and metadata exploration

---

## Features

- **Structural Parsing** — splits raw transcripts into *Prepared Remarks* and *Q&A*, identifies speakers by role (Executive, Analyst, Operator), and links questions to answers.
- **Key Takeaways (TextRank)** — extracts the most central sentences using graph-based ranking.
- **Theme Extraction (NMF)** — discovers core topics via Non-Negative Matrix Factorization.
- **Keyword Extraction (TF-IDF)** — identifies statistically significant terms unique to the transcript.
- **Semantic Search (Voyage AI + pgvector)** — embeds every speaker turn and stores vectors in Postgres for natural language search.
- **Feynman Learning Loop** — a multi-turn AI chat session guided by a 5-step pedagogical flow to help you deeply understand the material.
- **Smart Caching** — reuses cached Voyage AI embeddings from Postgres to avoid redundant API calls.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Check with `python3 --version` |
| PostgreSQL (with `pgvector`) | `brew install pgvector` on macOS |
| API Ninjas Key | For downloading transcripts |
| Voyage AI API Key | For generating semantic embeddings |
| Perplexity API Key | For the Feynman learning chat |

---

## Setup

### 1. Create and activate a virtual environment

A virtual environment keeps this project's Python packages isolated from your system Python. Think of it as a project-scoped package sandbox.

```bash
python3 -m venv .venv          # create the environment (one-time)
source .venv/bin/activate      # activate it (every new terminal session)
```

Your prompt will show `(.venv)` when the environment is active. To deactivate: `deactivate`.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

This installs all packages listed in `requirements.txt`. Re-run this whenever the file changes.

### 3. Set up PostgreSQL and pgvector

Ensure PostgreSQL is running and create the database:

```bash
createdb earnings_teacher
psql -d earnings_teacher -f db/schema.sql
```

> **macOS tip:** Install pgvector with `brew install pgvector`, then enable it in your DB: `psql -d earnings_teacher -c "CREATE EXTENSION vector;"`.

### 4. Configure API keys

Export your keys as environment variables. The easiest way is to add these lines to your shell profile (`~/.zshrc` or `~/.bash_profile`) so they're set automatically:

```bash
export API_NINJAS_KEY="your-api-ninjas-key"
export VOYAGE_API_KEY="your-voyage-api-key"
export PERPLEXITY_API_KEY="your-perplexity-api-key"
export DATABASE_URL="dbname=earnings_teacher"   # optional — this is the default
```

Reload your shell with `source ~/.zshrc` (or open a new terminal).

---

## Running the app

### Console UI (interactive terminal menu)

```bash
python3 main.py
```

This launches the interactive menu where you can download transcripts, run analysis, chat with the Feynman learning loop, and run semantic search.

### Console UI (direct analysis, no menu)

```bash
python3 main.py AAPL            # analyze and print results
python3 main.py AAPL --save     # analyze and save to PostgreSQL
```

### Web UI (Streamlit browser app)

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The web UI shows themes, takeaways, keywords, and vocabulary on the left; a live AI chat panel on the right.

You can also launch the web UI from the console menu by choosing `--mode gui`:

```bash
python3 main.py --mode gui
```

---

## Running tests

```bash
pytest                      # run all tests
pytest tests/unit/          # run only unit tests
pytest -v                   # verbose output (shows each test name)
pytest --cov=.              # run with coverage report
```

---

## Downloading a transcript

```bash
./download_transcript.sh MSFT
```

This calls the API Ninjas endpoint and saves the raw JSON to `transcripts/MSFT.json`. The `transcripts/` directory is git-ignored (local data only).

---

## Semantic search

Once transcripts are saved with `--save`, search across all of them:

```bash
python3 db/search.py "AI infrastructure capital expenditures" -k 5
```

---

## Architecture

```
earnings-transcript-teacher/
├── main.py             # Console UI entry point
├── app.py              # Web UI entry point (Streamlit)
├── requirements.txt    # Python dependencies
│
├── core/               # Shared dataclasses (CallAnalysis, SpanRecord, etc.)
├── parsing/            # Transcript loading and regex-based section extraction
├── nlp/                # NLP algorithms (TF-IDF keywords, NMF themes, TextRank takeaways)
├── services/           # Orchestration and LLM integration
│   ├── orchestrator.py # Main analysis pipeline — wires all modules together
│   └── llm.py          # Perplexity/Claude API client with rate limiting
├── ingestion/          # Agentic chunking pipeline for LLM enrichment
├── cli/                # Console UI display and interactive menu
├── db/                 # PostgreSQL access layer and semantic search
├── utils/              # Shared utilities (timing decorator)
├── prompts/feynman/    # Pedagogical prompt files for the Feynman learning loop
└── tests/              # pytest test suite (unit + integration)
```

---

## Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `API_NINJAS_KEY` | Yes (download) | API key for fetching raw transcripts |
| `VOYAGE_API_KEY` | Yes (embeddings) | Voyage AI key for semantic vector generation |
| `PERPLEXITY_API_KEY` | Yes (chat) | Perplexity key for Feynman learning chat |
| `DATABASE_URL` | No | PostgreSQL connection string (default: `dbname=earnings_teacher`) |
| `ANTHROPIC_API_KEY` | No | Anthropic key for Claude-based LLM tiers in ingestion |
