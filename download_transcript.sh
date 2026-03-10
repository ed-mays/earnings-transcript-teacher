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

mkdir -p "${SCRIPT_DIR}/transcripts"
OUT_FILE="${SCRIPT_DIR}/transcripts/${TICKER}.json"

HTTP_STATUS=$(curl -s -o "${OUT_FILE}" -w "%{http_code}" -X GET "https://api.api-ninjas.com/v1/earningstranscript?ticker=${TICKER}" \
  -H "X-Api-Key: ${API_NINJAS_KEY}")

if [ "$HTTP_STATUS" -ne 200 ]; then
  echo "Error downloading transcript: HTTP ${HTTP_STATUS}" >&2
  if [ -s "${OUT_FILE}" ]; then
    echo "Details: $(cat "${OUT_FILE}")" >&2
  fi
  rm -f "${OUT_FILE}"
  exit 1
fi

echo "Saved to ${OUT_FILE}"
