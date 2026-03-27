"""Modal ingestion pipeline — downloads and processes earnings transcripts."""

import logging
import os
from pathlib import Path

import modal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modal image — includes all core pipeline modules from the repo
# ---------------------------------------------------------------------------

# Kept inline (not in a separate file) so Modal evaluates this list locally
# at image-build time without trying to read the file inside the container.
_IGNORE = [
    ".git/",
    ".gitignore",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".venv/",
    "*.egg-info/",
    "tests/",
    "coverage.xml",
    ".coverage",
    "transcripts/",
    "transcript/",
    "web/",
    "node_modules/",
    "docs/",
    "ideation/",
    "set_env.sh",
    "set_env.sh.template",
    "set_env.ps1.template",
    "download_transcript.sh",
    "reset_db.sh",
    "dev.sh",
    "*.md",
    "test_query_out.txt",
]

_repo_root = Path(__file__).parent.parent

_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("pipeline/requirements.txt")
    .env({"PYTHONPATH": "/root"})
    .workdir("/root")
    .add_local_dir(str(_repo_root), remote_path="/root", ignore=_IGNORE)
)

app = modal.App("earnings-ingestion", image=_image)


# ---------------------------------------------------------------------------
# Ingestion function
# ---------------------------------------------------------------------------


@app.function(
    secrets=[modal.Secret.from_name("earnings-secrets")],
    timeout=3600,
)
def ingest_ticker(ticker: str) -> None:
    """Download and ingest an earnings transcript for the given ticker."""
    import json

    import httpx
    from db.persistence import save_analysis
    from services.orchestrator import analyze

    ticker = ticker.upper()
    logger.info("Starting ingestion for %s", ticker)

    # 1. Download transcript JSON from API Ninjas
    api_key = os.environ["API_NINJAS_KEY"]
    url = f"https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}"
    response = httpx.get(url, headers={"X-Api-Key": api_key}, timeout=60)
    response.raise_for_status()

    transcript_json = response.text
    if not transcript_json or transcript_json.strip() in ("", "[]", "{}"):
        raise ValueError(f"No transcript returned for ticker {ticker}")

    # Validate it parses before writing
    json.loads(transcript_json)

    # 2. Write to ./transcripts/ — workdir is /root so this resolves correctly
    os.makedirs("transcripts", exist_ok=True)
    with open(f"transcripts/{ticker}.json", "w") as f:
        f.write(transcript_json)

    # 3. Run the full analysis pipeline
    result = analyze(ticker)

    # 4. Persist to Supabase
    conn_str = os.environ["DATABASE_URL"]
    save_analysis(conn_str, result)
    logger.info("Ingestion complete for %s", ticker)
