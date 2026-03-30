"""Shared FastAPI dependencies: database connection, auth, admin check."""

import logging
import os
from collections.abc import Generator
from typing import Annotated

import jwt
import psycopg
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger(__name__)

try:
    from psycopg_pool import ConnectionPool as _ConnectionPool
except ImportError:  # psycopg-pool not installed (e.g. test environments)
    _ConnectionPool = None  # type: ignore[assignment,misc]

# Module-level JWKS client — initialized lazily, cached across requests.
_jwks_client: PyJWKClient | None = None

# Module-level connection pool — set during app lifespan; None in tests.
_pool: "_ConnectionPool | None" = None


def set_pool(pool: object) -> None:
    """Register the application-level connection pool (called from lifespan)."""
    global _pool
    _pool = pool  # type: ignore[assignment]


def _get_jwks_client() -> PyJWKClient:
    """Return the module-level PyJWKClient, initializing it on first call."""
    global _jwks_client
    if _jwks_client is None:
        supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
        _jwks_client = PyJWKClient(
            f"{supabase_url}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
        )
    return _jwks_client


def get_db() -> Generator[psycopg.Connection, None, None]:
    """Yield a psycopg connection, using the pool when available.

    Falls back to a direct psycopg.connect() call when the pool is not set
    (e.g. in unit tests that patch psycopg.connect directly).
    """
    if _pool is not None:
        with _pool.connection() as conn:
            yield conn
    else:
        database_url = os.environ["DATABASE_URL"]
        conn = psycopg.connect(database_url)
        try:
            yield conn
        finally:
            conn.close()


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    """Verify the Supabase JWT via JWKS and return the user UUID."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    token = authorization.removeprefix("Bearer ")

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except Exception:
        logger.warning("JWKS fetch failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return user_id


DbDep = Annotated[psycopg.Connection, Depends(get_db)]
CurrentUserDep = Annotated[str, Depends(get_current_user)]


def require_admin(user_id: CurrentUserDep, conn: DbDep) -> str:
    """Raise 403 if the authenticated user does not have the admin role in profiles."""
    row = conn.execute(
        "SELECT role FROM public.profiles WHERE id = %s", (user_id,)
    ).fetchone()
    if row is None or row[0] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user_id


RequireAdminDep = Annotated[str, Depends(require_admin)]
