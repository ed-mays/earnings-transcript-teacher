"""FastAPI application entry point — CORS, lifespan, router registration."""

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from routes import admin, calls, chat


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    # Startup: validate required environment variables are present
    required = ["DATABASE_URL", "SUPABASE_URL"]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    yield
    # Shutdown: nothing to clean up yet


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


app = FastAPI(title="EarningsFluency API", lifespan=lifespan)

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a generic 500 without leaking internals."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/health")
async def health() -> dict:
    """Return service health status."""
    return {"status": "ok"}
