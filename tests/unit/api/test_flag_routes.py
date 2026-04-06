"""Unit tests for feature flag API routes (GET /flags, admin CRUD)."""

import os
import sys
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# Stub modal before app import
MODAL_STUB = MagicMock()
sys.modules.setdefault("modal", MODAL_STUB)

from main import app  # noqa: E402

ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_URL": "https://test.supabase.co",
    "VOYAGE_API_KEY": "voyage-test-key",
    "PERPLEXITY_API_KEY": "pplx-test-key",
    "MODAL_TOKEN_ID": "modal-test-id",
    "ANTHROPIC_API_KEY": "anth-test-key",
}

_RSA_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
_RSA_PUBLIC_KEY = _RSA_PRIVATE_KEY.public_key()

ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
LEARNER_UUID = "00000000-0000-0000-0000-000000000002"


def _make_jwt(user_id: str) -> str:
    return pyjwt.encode(
        {"sub": user_id, "aud": "authenticated"}, _RSA_PRIVATE_KEY, algorithm="RS256"
    )


def _mock_jwks_client() -> MagicMock:
    mock_key = MagicMock()
    mock_key.key = _RSA_PUBLIC_KEY
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_key
    return mock_client


ADMIN_AUTH = {"Authorization": f"Bearer {_make_jwt(ADMIN_UUID)}"}
LEARNER_AUTH = {"Authorization": f"Bearer {_make_jwt(LEARNER_UUID)}"}


def _make_mock_conn(role: str = "admin", fetchone=None, fetchall=None) -> MagicMock:
    """Build a mock psycopg connection.

    execute().fetchone() returns the role tuple on the first call (for require_admin),
    then the fetchone value on subsequent calls. fetchall always returns the given rows.
    """
    mock_conn = MagicMock()
    result = mock_conn.execute.return_value
    role_row = (role,)
    if fetchone is not None:
        # First call: role check. Second call: route data.
        result.fetchone.side_effect = [role_row, fetchone]
    else:
        result.fetchone.return_value = role_row
    result.fetchall.return_value = fetchall if fetchall is not None else []
    return mock_conn


def _mock_flag_provider(flags: dict[str, bool] | None = None) -> MagicMock:
    """Return a mock FeatureFlagProvider."""
    effective = flags if flags is not None else {"chat_enabled": True, "ingestion_enabled": True}
    mock = MagicMock()
    mock.get_all.return_value = effective
    mock.is_enabled.side_effect = lambda key, default=False: effective.get(key, default)
    return mock


@pytest.fixture()
def client():
    """TestClient with env vars, DB mocked for admin, and flag provider mocked."""
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, ENV))
        stack.enter_context(patch("dependencies._get_jwks_client", return_value=_mock_jwks_client()))
        stack.enter_context(patch("psycopg.connect", return_value=_make_mock_conn("admin")))
        try:
            stack.enter_context(
                patch("psycopg_pool.ConnectionPool", side_effect=Exception("no pool in unit tests"))
            )
        except ModuleNotFoundError:
            pass
        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            yield c


@pytest.fixture(autouse=True)
def reset_flag_provider():
    """Reset the flag provider singleton between tests."""
    import flags as flags_mod
    flags_mod._provider = None
    yield
    flags_mod._provider = None


# ---------------------------------------------------------------------------
# GET /flags — public read
# ---------------------------------------------------------------------------

def test_public_flags_returns_dict(client):
    mock_provider = _mock_flag_provider({"chat_enabled": True, "ingestion_enabled": True})
    import dependencies as deps
    app.dependency_overrides[deps.get_flag_provider] = lambda: mock_provider
    try:
        resp = client.get("/flags")
    finally:
        app.dependency_overrides.pop(deps.get_flag_provider, None)
    assert resp.status_code == 200
    assert resp.json() == {"chat_enabled": True, "ingestion_enabled": True}


def test_public_flags_no_auth_required(client):
    """No Authorization header — still returns 200."""
    mock_provider = _mock_flag_provider({})
    import dependencies as deps
    app.dependency_overrides[deps.get_flag_provider] = lambda: mock_provider
    try:
        resp = client.get("/flags")
    finally:
        app.dependency_overrides.pop(deps.get_flag_provider, None)
    assert resp.status_code == 200


def test_public_flags_returns_empty_when_no_flags(client):
    mock_provider = _mock_flag_provider({})
    import dependencies as deps
    app.dependency_overrides[deps.get_flag_provider] = lambda: mock_provider
    try:
        resp = client.get("/flags")
    finally:
        app.dependency_overrides.pop(deps.get_flag_provider, None)
    assert resp.json() == {}


# ---------------------------------------------------------------------------
# GET /admin/flags — list all flags
# ---------------------------------------------------------------------------

_SAMPLE_ROWS = [
    ("chat_enabled", True, "Kill switch for chat", "kill_switch", {}, "2026-04-06T00:00:00+00:00", "2026-04-06T00:00:00+00:00"),
    ("beta_feature", False, "Beta feature gate", "feature", {}, "2026-04-06T00:00:00+00:00", "2026-04-06T00:00:00+00:00"),
]


def test_admin_list_flags_returns_200(client):
    conn = _make_mock_conn("admin", fetchall=_SAMPLE_ROWS)
    with patch("psycopg.connect", return_value=conn):
        resp = client.get("/admin/flags", headers=ADMIN_AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert "flags" in body
    assert len(body["flags"]) == 2


def test_admin_list_flags_requires_admin(client):
    conn = _make_mock_conn("learner")
    with patch("psycopg.connect", return_value=conn):
        resp = client.get("/admin/flags", headers=LEARNER_AUTH)
    assert resp.status_code == 403


def test_admin_list_flags_requires_auth(client):
    resp = client.get("/admin/flags")
    assert resp.status_code == 401


def test_admin_list_flags_response_shape(client):
    conn = _make_mock_conn("admin", fetchall=_SAMPLE_ROWS)
    with patch("psycopg.connect", return_value=conn):
        resp = client.get("/admin/flags", headers=ADMIN_AUTH)
    flag = resp.json()["flags"][0]
    assert "key" in flag
    assert "enabled" in flag
    assert "description" in flag
    assert "category" in flag
    assert "created_at" in flag
    assert "updated_at" in flag


# ---------------------------------------------------------------------------
# POST /admin/flags — create flag
# ---------------------------------------------------------------------------

_NEW_FLAG_ROW = ("new_flag", False, "A new feature gate", "feature", {}, "2026-04-06T00:00:00+00:00", "2026-04-06T00:00:00+00:00")


def test_admin_create_flag_returns_201(client):
    conn = _make_mock_conn("admin", fetchone=_NEW_FLAG_ROW)
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        resp = client.post(
            "/admin/flags",
            json={"key": "new_flag", "enabled": False, "description": "A new feature gate", "category": "feature"},
            headers=ADMIN_AUTH,
        )
    assert resp.status_code == 201
    assert resp.json()["key"] == "new_flag"
    mock_provider.invalidate_cache.assert_called_once()


def test_admin_create_flag_requires_admin(client):
    conn = _make_mock_conn("learner")
    with patch("psycopg.connect", return_value=conn):
        resp = client.post(
            "/admin/flags",
            json={"key": "new_flag"},
            headers=LEARNER_AUTH,
        )
    assert resp.status_code == 403


def test_admin_create_duplicate_returns_409(client):
    import psycopg.errors

    # Role check must succeed first, then the INSERT raises UniqueViolation
    role_result = MagicMock()
    role_result.fetchone.return_value = ("admin",)
    insert_result = MagicMock()
    insert_result.fetchone.side_effect = psycopg.errors.UniqueViolation("duplicate key")
    conn = MagicMock()
    conn.execute.side_effect = [role_result, insert_result]
    with patch("psycopg.connect", return_value=conn):
        resp = client.post(
            "/admin/flags",
            json={"key": "chat_enabled"},
            headers=ADMIN_AUTH,
        )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PUT /admin/flags/{key} — update flag
# ---------------------------------------------------------------------------

_UPDATED_FLAG_ROW = ("chat_enabled", False, "Kill switch for chat", "kill_switch", {}, "2026-04-06T00:00:00+00:00", "2026-04-06T01:00:00+00:00")


def test_admin_update_flag_returns_200(client):
    conn = _make_mock_conn("admin", fetchone=_UPDATED_FLAG_ROW)
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        resp = client.put(
            "/admin/flags/chat_enabled",
            json={"enabled": False},
            headers=ADMIN_AUTH,
        )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_admin_update_flag_calls_invalidate_cache(client):
    conn = _make_mock_conn("admin", fetchone=_UPDATED_FLAG_ROW)
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        client.put("/admin/flags/chat_enabled", json={"enabled": False}, headers=ADMIN_AUTH)
    mock_provider.invalidate_cache.assert_called_once()


def test_admin_update_nonexistent_flag_returns_404(client):
    # side_effect list: [role_result, update_result_with_None]
    role_result = MagicMock()
    role_result.fetchone.return_value = ("admin",)
    update_result = MagicMock()
    update_result.fetchone.return_value = None
    conn = MagicMock()
    conn.execute.side_effect = [role_result, update_result]
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        resp = client.put(
            "/admin/flags/nonexistent",
            json={"enabled": True},
            headers=ADMIN_AUTH,
        )
    assert resp.status_code == 404


def test_admin_update_flag_requires_admin(client):
    conn = _make_mock_conn("learner")
    with patch("psycopg.connect", return_value=conn):
        resp = client.put(
            "/admin/flags/chat_enabled",
            json={"enabled": False},
            headers=LEARNER_AUTH,
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /admin/flags/{key} — delete flag
# ---------------------------------------------------------------------------

def _make_delete_conn(role: str = "admin", rowcount: int = 1) -> MagicMock:
    """Conn mock for DELETE: role check first, then DELETE with rowcount."""
    role_result = MagicMock()
    role_result.fetchone.return_value = (role,)
    delete_result = MagicMock()
    delete_result.rowcount = rowcount
    conn = MagicMock()
    conn.execute.side_effect = [role_result, delete_result]
    return conn


def test_admin_delete_flag_returns_204(client):
    conn = _make_delete_conn("admin", rowcount=1)
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        resp = client.delete("/admin/flags/chat_enabled", headers=ADMIN_AUTH)
    assert resp.status_code == 204


def test_admin_delete_flag_calls_invalidate_cache(client):
    conn = _make_delete_conn("admin", rowcount=1)
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        client.delete("/admin/flags/chat_enabled", headers=ADMIN_AUTH)
    mock_provider.invalidate_cache.assert_called_once()


def test_admin_delete_nonexistent_flag_returns_404(client):
    conn = _make_delete_conn("admin", rowcount=0)
    mock_provider = _mock_flag_provider()
    with patch("psycopg.connect", return_value=conn), \
         patch("routes.flags.get_flag_provider", return_value=mock_provider):
        resp = client.delete("/admin/flags/nonexistent", headers=ADMIN_AUTH)
    assert resp.status_code == 404


def test_admin_delete_flag_requires_admin(client):
    conn = _make_mock_conn("learner")
    with patch("psycopg.connect", return_value=conn):
        resp = client.delete("/admin/flags/chat_enabled", headers=LEARNER_AUTH)
    assert resp.status_code == 403
