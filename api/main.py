"""FastAPI application entry point — CORS, lifespan, router registration."""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import admin, calls, chat


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    # Startup: validate required environment variables are present
    required = ["DATABASE_URL", "SUPABASE_JWT_SECRET", "ADMIN_SECRET_TOKEN"]
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
    return origins


app = FastAPI(title="EarningsFluency API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict:
    """Return service health status."""
    return {"status": "ok"}
