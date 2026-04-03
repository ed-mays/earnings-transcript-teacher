"""FastAPI application entry point — CORS, lifespan, router registration."""

import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from context import request_id_var
from settings import LOG_FORMAT_DEFAULT, LOG_LEVEL_DEFAULT, SENTRY_DSN_ENV_VAR


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object for log aggregation tools."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the log record to a JSON string."""
        record.message = record.getMessage()
        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


class _RequestIdFilter(logging.Filter):
    """Inject request_id from ContextVar into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id attribute so the log format can reference it."""
        record.request_id = request_id_var.get("-")
        return True


_log_format = os.environ.get("LOG_FORMAT", LOG_FORMAT_DEFAULT).lower()
_handler = logging.StreamHandler(sys.stdout)
if _log_format == "json":
    _handler.setFormatter(JsonFormatter())
else:
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")
    )
_handler.addFilter(_RequestIdFilter())
logging.getLogger().setLevel(os.environ.get("LOG_LEVEL", LOG_LEVEL_DEFAULT).upper())
logging.getLogger().addHandler(_handler)

def _configure_sentry() -> None:
    """Initialise Sentry SDK if SENTRY_DSN is configured; warn if absent."""
    dsn = os.environ.get(SENTRY_DSN_ENV_VAR)
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("ENV", "production"),
            integrations=[StarletteIntegration(), FastApiIntegration()],
        )
    else:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN is not set — exception alerting disabled"
        )


_configure_sentry()

logger = logging.getLogger(__name__)

from db.analytics import drain as drain_analytics
from dependencies import set_pool
from limiter import limiter
from routes import admin, calls, chat, define
from settings import REQUIRED_ENV_VARS
from shutdown import shutdown_event


def _handle_sigterm(signum: int, frame: object) -> None:
    """Set the shutdown flag so active SSE generators can emit a terminal event."""
    shutdown_event.set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, _handle_sigterm)

    # Startup: validate all required environment variables are present
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        logger.critical("Missing required environment variables: %s", ", ".join(missing))
        app.state.startup_ok = False
        app.state.missing_vars = missing
        yield
        return

    app.state.startup_ok = True
    app.state.missing_vars = []

    # Cache validation snapshot for health endpoint reporting
    app.state.env_var_status = {var: bool(os.environ.get(var)) for var in REQUIRED_ENV_VARS}

    # Start connection pool
    try:
        from psycopg_pool import ConnectionPool
        pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=2, max_size=10, open=True)
        set_pool(pool)
        logger.info("Database connection pool started (min=2, max=10)")
    except Exception as exc:
        logger.warning("Could not start connection pool, falling back to per-request connections: %s", exc)
        pool = None

    yield

    # Shutdown: drain in-flight analytics inserts, then close the connection pool
    drain_analytics(timeout=5.0)
    if pool is not None:
        pool.close()
        logger.info("Database connection pool closed")
    set_pool(None)


def build_cors_origins() -> list[str]:
    """Return the list of allowed CORS origins from environment and defaults."""
    origins = ["http://localhost:3000"]
    production_url = os.environ.get("NEXT_PUBLIC_VERCEL_URL")
    if production_url:
        origins.append(f"https://{production_url}")
    extra = os.environ.get("CORS_EXTRA_ORIGINS", "")
    if extra:
        origins.extend(o.strip() for o in extra.split(",") if o.strip())
    return origins


def build_cors_origin_regex() -> str | None:
    """Return a regex matching allowed origin patterns from CORS_ORIGIN_REGEX env var."""
    return os.environ.get("CORS_ORIGIN_REGEX") or None


class CorrelationTimingMiddleware(BaseHTTPMiddleware):
    """Read or generate X-Request-ID; log request duration; propagate ID to response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Set request ID ContextVar, time the request, log on completion."""
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "completed %s %s in %.0fms [request_id=%s]",
                request.method,
                request.url.path,
                elapsed_ms,
                request_id,
            )
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(title="EarningsFluency API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CorrelationTimingMiddleware is added first (becomes inner); CORSMiddleware added
# last (becomes outermost) so CORS handles OPTIONS preflight before our middleware.
app.add_middleware(CorrelationTimingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=build_cors_origins(),
    allow_origin_regex=build_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(define.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a generic 500 without leaking internals."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    """Return service health status. Returns 503 if startup failed."""
    if not getattr(request.app.state, "startup_ok", False):
        missing = getattr(request.app.state, "missing_vars", [])
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "missing_vars": missing},
        )
    return JSONResponse(status_code=200, content={"status": "ok"})
