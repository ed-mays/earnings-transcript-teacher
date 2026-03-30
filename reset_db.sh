#!/usr/bin/env bash
# reset_db.sh — Completely reset the database (drop and recreate)
# Run from the repo root: bash reset_db.sh

set -euo pipefail

# ── Helpers ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
step() { echo -e "\n${BOLD}$1${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }

echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD} Earnings Transcript Teacher — Full DB Reset${NC}"
echo -e "${BOLD}================================================${NC}"

step "Nuclear Reset Confirmation"
echo -e "${RED}WARNING:${NC} This will DROP the 'earnings_teacher' database."
echo "All stored transcripts, embeddings, and analysis will be PERMANENTLY DELETED."
echo "Raw transcript JSON files in transcripts/ will be preserved."
echo ""
read -p "Are you absolutely sure? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# ── 1. Drop Database ─────────────────────────────────────────────────────────
DB_NAME="earnings_teacher"

step "Dropping database..."
if dropdb "$DB_NAME" 2>/dev/null; then
    ok "Dropped database '$DB_NAME'"
else
    echo "  !  Database '$DB_NAME' did not exist or could not be dropped."
fi

# ── 2. Run setup.sh ──────────────────────────────────────────────────────────
step "Re-initializing database using setup.sh..."
bash setup.sh

echo ""
echo -e "${BOLD}Reset complete!${NC}"
echo ""
