"""Shared FastAPI dependencies: database connection, auth, admin token."""

import os
from collections.abc import Generator
from typing import Annotated

import jwt
import psycopg
from fastapi import Depends, Header, HTTPException, status


def get_db() -> Generator[psycopg.Connection, None, None]:
    """Yield a psycopg connection from DATABASE_URL and close it after use."""
    database_url = os.environ["DATABASE_URL"]
    conn = psycopg.connect(database_url)
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    """Verify the Supabase JWT from Authorization: Bearer and return the user UUID."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    token = authorization.removeprefix("Bearer ")
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")

    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
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


def verify_admin_token(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    """Raise 403 if X-Admin-Token header does not match ADMIN_SECRET_TOKEN env var."""
    expected = os.environ.get("ADMIN_SECRET_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin token",
        )


DbDep = Annotated[psycopg.Connection, Depends(get_db)]
CurrentUserDep = Annotated[str, Depends(get_current_user)]
AdminDep = Annotated[None, Depends(verify_admin_token)]
