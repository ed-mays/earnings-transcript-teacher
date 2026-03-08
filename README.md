# Earnings Transcript Teacher

A robust Python pipeline for analyzing, structuring, and persisting financial earnings call transcripts. It extracts key insights using classical NLP models (TF-IDF, NMF, TextRank) alongside modern semantic search (Voyage AI + `pgvector`), saving all structured data to a local PostgreSQL database.

## Features

- **Structural Parsing**: Automatically splits raw transcripts into _Prepared Remarks_ and _Q&A_, identifies speakers by role (Executive, Analyst, Operator), and links questions to their corresponding answers.
- **Key Takeaways (TextRank)**: Extracts the most central, highly-connected sentences from the call using graph-based ranking.
- **Theme Extraction (NMF)**: Discovers core topics discussed during the call using Non-Negative Matrix Factorization.
- **Keyword Extraction (TF-IDF)**: Identifies the most statistically significant terms unique to the transcript.
- **Semantic Search (Voyage AI + pgvector)**: Embeds every speaker turn using `voyage-finance-2` and stores vectors in Postgres.
- **Feynman Learning Loop**: An interactive, multi-turn AI chat session guided by a strict pedagogical prompt (powered by Perplexity/OpenAI and RAG over the transcript) to help users deeply master the material.
- **Smart Caching**: Seamlessly caches Voyage AI embeddings in Postgres to eliminate redundant API calls on subsequent runs.

## Prerequisites

- **Python 3.10+**
- **PostgreSQL** (with the `pgvector` extension installed)
- **API Ninjas Key** (for downloading new transcripts)
- **Voyage AI API Key** (for semantic vector generation)
- **Perplexity API Key** (for the Feynman learning chat session)

## Setup

1. **Clone and setup the virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Setup PostgreSQL & pgvector:**
   Ensure PostgreSQL is running on your machine and you have installed the `pgvector` extension (e.g., `brew install pgvector` on macOS).

3. **Initialize the Database:**
   Create a database called `earnings_teacher` (or set a custom `DATABASE_URL` environment variable) and apply the schema:

   ```bash
   createdb earnings_teacher
   psql -d earnings_teacher -f db/schema.sql
   ```

4. **Set your API Keys:**
   Export your keys into your environment:
   ```bash
   export API_NINJAS_KEY="your-api-ninjas-key"
   export VOYAGE_API_KEY="your-voyage-api-key"
   export PERPLEXITY_API_KEY="your-perplexity-api-key"
   ```

## Usage

### 1. Download a Transcript

Use the provided shell script to download raw earning transcripts directly from the API Ninjas endpoint into the `transcripts/` directory.

```bash
./download_transcript.sh MSFT
```

### 2. Analyze a Transcript

The main script reads `.json` transcripts from the `transcripts/` directory, processes them through the NLP pipeline, and displays the results in the terminal.

```bash
# Analyze the Microsoft (MSFT) transcript and print insights
python3 main.py MSFT
```

### 3. Persist to Postgres

Use the `--save` flag to insert all extracted data (calls, speakers, spans, Q&A pairs, topics, keywords, and semantic embeddings) into your local `earnings_teacher` Postgres database.

```bash
# Analyze and save to the database
python3 main.py AAPL --save
```

_Note: If a transcript's embeddings already exist in the database, the pipeline will automatically load them from the cache instead of querying the Voyage API._

### 4. Semantic Search

Once you have persisted transcripts into the database with embeddings, you can run natural language searches across all ingested calls using the `search.py` utility.

```bash
# Search across all saved spans using cosine similarity
python3 db/search.py "AI infrastructure capital expenditures" -k 5
```

## Architecture

The project is broken down into modular components:

- `download_transcript.sh`: Bash script for fetching raw transcripts from API Ninjas.
- `transcript/`: Core NLP pipeline modules (`models.py`, `sections.py`, `keywords.py`, `themes.py`, `takeaways.py`, `embedder.py`).
- `db/`: Database layer (`schema.sql`, `persistence.py`, `search.py`).
- `main.py`: Orchestrator script that ties the pipeline together.
