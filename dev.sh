#!/usr/bin/env bash
# dev.sh — start all local development tiers
#
# Usage:
#   ./dev.sh          # start API + web (default)
#   ./dev.sh api      # start API only
#   ./dev.sh web      # start Next.js frontend only
#
# Prerequisites:
#   - api/.env exists with all required variables (copy api/.env.example)
#   - web/.env.local exists (copy web/.env.example)
#   - .venv is activated, or Python is on PATH
#   - Node.js is installed

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
API_ENV="$REPO_ROOT/api/.env"
WEB_ENV="$REPO_ROOT/web/.env.local"

# ── helpers ────────────────────────────────────────────────────────────────────

die() { echo "error: $*" >&2; exit 1; }

check_env_file() {
    local file="$1" example="$2" label="$3"
    if [[ ! -f "$file" ]]; then
        die "$label env file not found: $file\n  Copy $example and fill in your values."
    fi
}

start_api() {
    check_env_file "$API_ENV" "api/.env.example" "API"
    echo "→ Starting FastAPI (http://localhost:8000)"
    cd "$REPO_ROOT/api"
    # Load env vars and start uvicorn; PYTHONPATH lets routes import from project root
    env $(grep -v '^#' "$API_ENV" | xargs) PYTHONPATH="$REPO_ROOT" \
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

start_web() {
    check_env_file "$WEB_ENV" "web/.env.example" "Web"
    echo "→ Starting Next.js (http://localhost:3000)"
    cd "$REPO_ROOT/web"
    npm run dev
}

# ── main ───────────────────────────────────────────────────────────────────────

TARGET="${1:-all}"

case "$TARGET" in
    api)
        start_api
        ;;
    web)
        start_web
        ;;
    all)
        # Run both in parallel; kill both when either exits or Ctrl-C is pressed
        trap 'kill 0' INT TERM EXIT
        start_api &
        API_PID=$!
        start_web &
        WEB_PID=$!
        wait "$API_PID" "$WEB_PID"
        ;;
    *)
        echo "Usage: $0 [api|web|all]" >&2
        exit 1
        ;;
esac
