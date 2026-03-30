"""Application-wide constants for rate limits and input bounds."""

LOG_LEVEL_DEFAULT = "INFO"
LOG_SLOW_QUERY_THRESHOLD_MS = 500  # warn if any DB operation exceeds this

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SUPABASE_URL",
    "VOYAGE_API_KEY",
    "PERPLEXITY_API_KEY",
    "MODAL_TOKEN_ID",
    "ANTHROPIC_API_KEY",
]

CHAT_RATE_LIMIT = "60/hour"
SEARCH_RATE_LIMIT = "100/hour"
INGEST_RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes per user per ticker

CHAT_MESSAGE_MAX_LENGTH = 4000
SEARCH_QUERY_MAX_LENGTH = 500
SESSION_HISTORY_MAX_TURNS = 50  # turn = one user message
