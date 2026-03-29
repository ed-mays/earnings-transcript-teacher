#!/usr/bin/env bash
# setup.sh — one-time setup for Earnings Transcript Teacher
# Run from the repo root: bash setup.sh

set -euo pipefail

# ── Helpers ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }
warn() { echo -e "  ${YELLOW}!${NC}  $1"; }
fail() { echo -e "\n  ${RED}✗${NC}  $1\n"; exit 1; }
step() { echo -e "\n${BOLD}$1${NC}"; }

echo ""
echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD} Earnings Transcript Teacher — Setup${NC}"
echo -e "${BOLD}================================================${NC}"

# ── 1. Python 3.10+ ──────────────────────────────────────────────────────────
step "Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
    fail "Python 3 not found.
       Install Python 3.10 or later: https://www.python.org/downloads/
       macOS (Homebrew): brew install python@3.12"
fi

PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
PY_VERSION="$PY_MAJOR.$PY_MINOR"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    fail "Python 3.10+ required (found $PY_VERSION).
       Install from: https://www.python.org/downloads/"
fi
ok "Python $PY_VERSION"

# ── 2. PostgreSQL ─────────────────────────────────────────────────────────────
if ! command -v psql &>/dev/null; then
    fail "PostgreSQL not found.
       macOS (Homebrew): brew install postgresql@16 && brew services start postgresql@16
       Ubuntu/Debian:    sudo apt install postgresql && sudo service postgresql start"
fi

if ! pg_isready -q 2>/dev/null; then
    fail "PostgreSQL is installed but not running.
       macOS (Homebrew): brew services start postgresql@16
       Ubuntu/Debian:    sudo service postgresql start"
fi
ok "PostgreSQL $(psql --version | awk '{print $3}')"

# ── 3. Virtual environment ────────────────────────────────────────────────────
step "Setting up Python environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Created .venv"
else
    ok "Virtual environment already exists"
fi

# ── 4. Python dependencies ───────────────────────────────────────────────────
echo ""
echo "  Installing dependencies (this may take a minute)..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
ok "Dependencies installed"

# ── 5. Database ───────────────────────────────────────────────────────────────
step "Setting up database..."

DB_NAME="earnings_teacher"

if psql -lqt 2>/dev/null | cut -d '|' -f 1 | grep -qw "$DB_NAME"; then
    ok "Database '$DB_NAME' already exists"
else
    createdb "$DB_NAME"
    ok "Created database '$DB_NAME'"
fi

# ── 6. pgvector extension ─────────────────────────────────────────────────────
if ! psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" &>/dev/null; then
    fail "Failed to enable the pgvector extension.
       pgvector must be installed at the OS level before this script can enable it.

       macOS (Homebrew): brew install pgvector
       Ubuntu/Debian:    sudo apt install postgresql-16-pgvector
                         (replace 16 with your PostgreSQL major version)

       After installing, re-run: bash setup.sh"
fi
ok "pgvector extension enabled"

# ── 7. Schema ─────────────────────────────────────────────────────────────────
TABLE_EXISTS=$(psql -d "$DB_NAME" -tAc "SELECT EXISTS(SELECT FROM pg_tables WHERE schemaname='public' AND tablename='calls')" 2>/dev/null)
if [ "$TABLE_EXISTS" = "f" ]; then
    python migrate.py &>/dev/null
    ok "Database schema applied"
else
    ok "Schema already applied — skipping"
fi

# ── 8. Environment variables ──────────────────────────────────────────────────
step "Checking environment variables..."

if [ -f "set_env.sh" ]; then
    ok "set_env.sh already exists"
else
    cp set_env.sh.template set_env.sh
    warn "Created set_env.sh from template"
    echo ""
    echo "  You must fill in your API keys before running the app."
    echo "  Open set_env.sh and replace the placeholder values:"
    echo ""
    echo "    API_NINJAS_KEY      — transcript downloads  (api-ninjas.com)"
    echo "    VOYAGE_API_KEY      — semantic embeddings   (voyageai.com)"
    echo "    PERPLEXITY_API_KEY  — Feynman chat          (perplexity.ai)"
    echo "    ANTHROPIC_API_KEY   — LLM-based ingestion   (console.anthropic.com)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD} Setup complete!${NC}"
echo -e "${BOLD}================================================${NC}"
echo ""
echo "  To get started:"
echo ""
echo "    source .venv/bin/activate"
echo "    source set_env.sh"
echo "    python3 main.py AAPL --save   # ingest a transcript"
echo "    streamlit run app.py          # launch the web UI"
echo ""
