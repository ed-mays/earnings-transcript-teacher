"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="EarningsFluency API")


@app.get("/health")
async def health() -> dict:
    """Return service health status."""
    return {"status": "ok"}
