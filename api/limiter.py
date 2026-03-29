"""Shared slowapi Limiter instance with user-aware rate-limit key function."""

import jwt as pyjwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_key(request: Request) -> str:
    """Return the user UUID from the Bearer JWT, or the remote IP as fallback.

    Does not verify the signature — auth is enforced separately by get_current_user.
    The key is used only for rate-limit bucketing.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return get_remote_address(request)
    try:
        payload = pyjwt.decode(
            auth.removeprefix("Bearer "),
            options={"verify_signature": False},
        )
        return payload.get("sub") or get_remote_address(request)
    except Exception:
        return get_remote_address(request)


limiter = Limiter(key_func=_user_key)
