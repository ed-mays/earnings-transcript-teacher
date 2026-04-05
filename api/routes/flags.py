"""Feature flag routes: public read and admin CRUD."""

import logging
from datetime import datetime
from typing import Any

import psycopg.errors
import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from dependencies import DbDep, FlagsDep, RequireAdminDep, get_flag_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["flags"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FlagCreate(BaseModel):
    """Payload for creating a new feature flag."""

    key: str
    enabled: bool = False
    description: str = ""
    category: str = "feature"
    metadata: dict[str, Any] = {}


class FlagUpdate(BaseModel):
    """Payload for updating an existing feature flag (all fields optional)."""

    enabled: bool | None = None
    description: str | None = None
    category: str | None = None
    metadata: dict[str, Any] | None = None


class FlagResponse(BaseModel):
    """Full flag details returned from admin endpoints."""

    key: str
    enabled: bool
    description: str
    category: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FlagListResponse(BaseModel):
    """List of all feature flags."""

    flags: list[FlagResponse]


def _row_to_flag(row: tuple) -> FlagResponse:
    """Convert a DB row tuple to a FlagResponse."""
    key, enabled, description, category, metadata, created_at, updated_at = row
    return FlagResponse(
        key=key,
        enabled=enabled,
        description=description,
        category=category,
        metadata=metadata or {},
        created_at=created_at,
        updated_at=updated_at,
    )


# ---------------------------------------------------------------------------
# Public endpoint
# ---------------------------------------------------------------------------

@router.get("/flags", response_model=dict[str, bool])
def get_flags(flags: FlagsDep) -> dict[str, bool]:
    """Return all feature flags as a {key: enabled} dict. No authentication required."""
    return flags.get_all()


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/flags", response_model=FlagListResponse)
def list_flags(_: RequireAdminDep, conn: DbDep) -> FlagListResponse:
    """List all feature flags with full metadata. Admin only."""
    rows = conn.execute(
        "SELECT key, enabled, description, category, metadata, created_at, updated_at"
        " FROM public.feature_flags ORDER BY key"
    ).fetchall()
    return FlagListResponse(flags=[_row_to_flag(row) for row in rows])


@router.post("/admin/flags", response_model=FlagResponse, status_code=status.HTTP_201_CREATED)
def create_flag(_: RequireAdminDep, conn: DbDep, body: FlagCreate) -> FlagResponse:
    """Create a new feature flag. Returns 409 if the key already exists. Admin only."""
    try:
        row = conn.execute(
            "INSERT INTO public.feature_flags (key, enabled, description, category, metadata)"
            " VALUES (%s, %s, %s, %s, %s)"
            " RETURNING key, enabled, description, category, metadata, created_at, updated_at",
            (body.key, body.enabled, body.description, body.category, psycopg.types.json.Jsonb(body.metadata)),
        ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Flag '{body.key}' already exists",
        )
    return _row_to_flag(row)


@router.put("/admin/flags/{key}", response_model=FlagResponse)
def update_flag(_: RequireAdminDep, conn: DbDep, key: str, body: FlagUpdate) -> FlagResponse:
    """Update an existing flag's enabled state or description. Admin only."""
    # Build SET clause from provided fields only
    updates: list[str] = []
    params: list[Any] = []
    if body.enabled is not None:
        updates.append("enabled = %s")
        params.append(body.enabled)
    if body.description is not None:
        updates.append("description = %s")
        params.append(body.description)
    if body.category is not None:
        updates.append("category = %s")
        params.append(body.category)
    if body.metadata is not None:
        updates.append("metadata = %s")
        params.append(psycopg.types.json.Jsonb(body.metadata))

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update",
        )

    params.append(key)
    row = conn.execute(
        f"UPDATE public.feature_flags SET {', '.join(updates)}"
        f" WHERE key = %s"
        f" RETURNING key, enabled, description, category, metadata, created_at, updated_at",
        params,
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag '{key}' not found",
        )

    get_flag_provider().invalidate_cache()
    return _row_to_flag(row)


@router.delete("/admin/flags/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flag(_: RequireAdminDep, conn: DbDep, key: str) -> None:
    """Delete a feature flag. Admin only."""
    result = conn.execute(
        "DELETE FROM public.feature_flags WHERE key = %s", (key,)
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag '{key}' not found",
        )
    get_flag_provider().invalidate_cache()
