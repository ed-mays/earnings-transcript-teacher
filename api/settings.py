"""Application-wide constants for rate limits and input bounds."""

CHAT_RATE_LIMIT = "60/hour"
SEARCH_RATE_LIMIT = "100/hour"
INGEST_RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes per user per ticker

CHAT_MESSAGE_MAX_LENGTH = 4000
SEARCH_QUERY_MAX_LENGTH = 500
SESSION_HISTORY_MAX_TURNS = 50  # turn = one user message
