# Legacy stack setup

> **Deprecated.** The original Python/Streamlit interface is no longer the primary development target. The primary stack is FastAPI + Next.js + Supabase. This document is preserved for contributors who need to run the legacy pipeline.

---

## Prerequisites

The setup scripts handle most of the installation automatically. You need to install the following manually first:

**macOS / Linux**

| Requirement | Notes |
|---|---|
| Python 3.10+ | `brew install python@3.12` or [python.org](https://www.python.org/downloads/) |
| PostgreSQL | `brew install postgresql@16 && brew services start postgresql@16` |
| pgvector | `brew install pgvector` |

**Windows**

| Requirement | Notes |
|---|---|
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" |
| Docker Desktop | [docker.com](https://www.docker.com/products/docker-desktop/) — used to run PostgreSQL + pgvector |

You will also need API keys for the services listed in the [Environment variable reference](../README.md#environment-variable-reference).

---

## Setup

### macOS / Linux

```bash
bash setup.sh
```

The script will:
1. Verify Python 3.10+ and PostgreSQL are available
2. Create a `.venv` virtual environment and install all dependencies
3. Create the `earnings_teacher` database, enable the pgvector extension, and apply the schema
4. Copy `set_env.sh.template` to `set_env.sh` if it doesn't already exist

Then open `set_env.sh` and fill in your API keys. Once done, activate the environment for each new terminal session:

```bash
source .venv/bin/activate
source set_env.sh
```

### Windows (PowerShell)

```powershell
.\setup.ps1
```

The script will:
1. Verify Python 3.10+ and Docker Desktop are available
2. Create a `.venv` virtual environment and install all dependencies
3. Pull and start the `pgvector/pgvector:pg16` Docker image, create the database, and apply the schema
4. Copy `set_env.ps1.template` to `set_env.ps1` if it doesn't already exist

Then open `set_env.ps1` and fill in your API keys. The `DATABASE_URL` entry is pre-filled to point at the Docker container and does not need to be changed. Activate the environment for each new terminal session:

```powershell
.venv\Scripts\Activate.ps1
. .\set_env.ps1
```

> **Note:** The database runs in a Docker container named `earnings_teacher_db`. Stop it when not in use with `docker stop earnings_teacher_db` and restart it with `docker start earnings_teacher_db`.

---

## Running the legacy app

### Console UI (interactive terminal menu)

```bash
python3 main.py
python3 main.py --mode cli    # explicit; same as above
```

### Console UI (direct analysis)

```bash
python3 main.py AAPL            # analyze and print results
python3 main.py AAPL --save     # analyze and save to PostgreSQL
python3 main.py --reset-db      # clear all data (prompts for confirmation)
```

### Web UI (Streamlit)

```bash
python3 main.py --mode gui      # launch via main.py
# or directly:
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

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

## Database management

The legacy pipeline uses PostgreSQL with `pgvector` managed via `migrate.py`.

### Schema migrations

```bash
python3 migrate.py
```

This is idempotent — safe to run multiple times. Migration files live in `db/migrations/` as `NNN_name.sql`.

> **After any migration:** Re-verify Supabase Row Level Security policies on user-data tables using the checklist in [`docs/runbooks/rls-verification.md`](runbooks/rls-verification.md). The authoritative policy SQL lives in [`db/rls-policies.sql`](../db/rls-policies.sql) and is applied via the Supabase SQL Editor (not `migrate.py`).

### Clearing data

```bash
python3 main.py --reset-db
```

Deletes all stored analysis while keeping the database schema intact.

### Full reset (schema changes)

```bash
./reset_db.sh
```

Drops and recreates the database. Preserves raw transcript files in `transcripts/` but deletes all processed data.
