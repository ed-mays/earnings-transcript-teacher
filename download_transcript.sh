#!/usr/bin/env bash

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <TICKER_SYMBOL>" >&2
  exit 1
fi

TICKER="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "${API_NINJAS_KEY:-}" ]; then
  echo "Error: API_NINJAS_KEY environment variable is not set." >&2
  exit 1
fi

curl -s -X GET "https://api.api-ninjas.com/v1/earningstranscript?ticker=${TICKER}" \
  -H "X-Api-Key: ${API_NINJAS_KEY}" \
  -o "${SCRIPT_DIR}/transcripts/${TICKER}.json"

echo "Saved to ${SCRIPT_DIR}/transcripts/${TICKER}.json"
