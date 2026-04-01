import sys
import os
from unittest.mock import patch

import pytest

# Add the project root to sys.path so we can import parsing, nlp, core, etc.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add api/ to sys.path so fixtures can resolve `main`, `routes.*`, `dependencies`, etc.
_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

# Add tests/ to sys.path so test files can import from tests/factories/.
_TESTS_DIR = os.path.dirname(__file__)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

# Shared environment variables used across all API unit tests.
TEST_ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_URL": "https://test.supabase.co",
    "VOYAGE_API_KEY": "voyage-test-key",
    "PERPLEXITY_API_KEY": "pplx-test-key",
    "MODAL_TOKEN_ID": "modal-test-id",
    "ANTHROPIC_API_KEY": "anth-test-key",
}


@pytest.fixture()
def api_client():
    """TestClient for the FastAPI app with env vars set, DB mocked, and auth bypassed.

    Suitable for unauthenticated or role-bypassed API tests.  get_current_user is
    overridden to return "test-user-id" unconditionally so routes that require auth
    work without a real JWT.  Tests that need real JWT verification (e.g. chat, admin)
    should define their own client fixture with the appropriate auth mock.
    """
    with patch.dict(os.environ, TEST_ENV):
        with patch("psycopg.connect"):
            from fastapi.testclient import TestClient
            from main import app
            from dependencies import get_db, get_current_user

            def _get_db():
                """Bypass the pool; delegate to the (possibly re-patched) psycopg.connect."""
                import psycopg as _psycopg
                conn = _psycopg.connect(os.environ["DATABASE_URL"])
                yield conn

            def _get_current_user():
                """Return a fixed user ID for all authenticated routes."""
                return "test-user-id"

            app.dependency_overrides[get_db] = _get_db
            app.dependency_overrides[get_current_user] = _get_current_user
            with TestClient(app) as c:
                yield c
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)
