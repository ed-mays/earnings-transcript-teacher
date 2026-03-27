"""Unit tests for the migrate.py file-based runner."""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_migrate():
    """Import migrate.py from the project root, bypassing any cached version."""
    project_root = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location("migrate", project_root / "migrate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


migrate = _load_migrate()
split_statements = migrate._split_statements


# ---------------------------------------------------------------------------
# _split_statements
# ---------------------------------------------------------------------------

class TestSplitStatements:
    def test_single_statement(self):
        sql = "ALTER TABLE foo ADD COLUMN bar TEXT;"
        result = split_statements(sql)
        assert result == ["ALTER TABLE foo ADD COLUMN bar TEXT;"]

    def test_multiple_statements(self):
        sql = (
            "ALTER TABLE foo ADD COLUMN bar TEXT;\n"
            "CREATE INDEX IF NOT EXISTS idx_foo ON foo (bar);\n"
            "INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;\n"
        )
        result = split_statements(sql)
        assert len(result) == 3

    def test_dollar_quote_block_preserved(self):
        sql = """\
DO $$
BEGIN
    IF true THEN
        ALTER TABLE foo ADD COLUMN baz INT;
    END IF;
END $$;

INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;
"""
        result = split_statements(sql)
        # The DO block is one statement; the INSERT is another.
        assert len(result) == 2
        assert result[0].startswith("DO $$")
        assert "schema_version" in result[1]

    def test_semicolons_inside_dollar_quote_not_split(self):
        sql = "DO $$\nBEGIN\n  RETURN;\nEND $$;\n"
        result = split_statements(sql)
        assert len(result) == 1

    def test_comment_only_lines_ignored(self):
        sql = "-- just a comment\n\nALTER TABLE foo ADD COLUMN bar TEXT;\n"
        result = split_statements(sql)
        assert len(result) == 1

    def test_empty_input(self):
        assert split_statements("") == []

    def test_only_comments(self):
        sql = "-- Migration 001: something\n-- another comment\n"
        assert split_statements(sql) == []


# ---------------------------------------------------------------------------
# run() — migration runner
# ---------------------------------------------------------------------------

class TestRun:
    """Tests for migrate.run() with a mocked psycopg connection."""

    def _make_mock_conn(self, applied_versions: set[int]):
        """Build a mock psycopg connection with schema_version pre-populated."""
        m_conn = MagicMock()
        m_conn.__enter__ = MagicMock(return_value=m_conn)
        m_conn.__exit__ = MagicMock(return_value=False)

        m_cur = MagicMock()
        m_cur.__enter__ = MagicMock(return_value=m_cur)
        m_cur.__exit__ = MagicMock(return_value=False)
        m_conn.cursor.return_value = m_cur

        # fetchall returns rows for applied versions; fetchone returns max version
        m_cur.fetchall.return_value = [(v,) for v in applied_versions]
        max_v = max(applied_versions) if applied_versions else 0
        m_cur.fetchone.return_value = (max_v,)

        return m_conn, m_cur

    def test_no_pending_migrations_prints_up_to_date(self, tmp_path, capsys):
        """When all file versions are already applied, runner prints 'up to date'."""
        sql_file = tmp_path / "001_test.sql"
        sql_file.write_text(
            "ALTER TABLE foo ADD COLUMN bar TEXT;\n"
            "INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;\n"
        )

        m_conn, m_cur = self._make_mock_conn(applied_versions={1})

        with (
            patch("psycopg.connect", return_value=m_conn),
            patch.object(migrate, "MIGRATIONS_DIR", tmp_path),
        ):
            migrate.run("fake_conn")

        captured = capsys.readouterr()
        assert "up to date" in captured.out

    def test_pending_migration_is_executed(self, tmp_path, capsys):
        """A file whose version is not in schema_version is executed."""
        sql_file = tmp_path / "001_test.sql"
        sql_file.write_text(
            "ALTER TABLE foo ADD COLUMN bar TEXT;\n"
            "INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;\n"
        )

        m_conn, m_cur = self._make_mock_conn(applied_versions=set())
        m_cur.fetchone.return_value = (1,)

        with (
            patch("psycopg.connect", return_value=m_conn),
            patch.object(migrate, "MIGRATIONS_DIR", tmp_path),
        ):
            migrate.run("fake_conn")

        captured = capsys.readouterr()
        assert "001_test.sql" in captured.out
        assert "Applied" in captured.out

    def test_already_applied_files_are_skipped(self, tmp_path, capsys):
        """Files whose version is already in schema_version are not re-executed."""
        (tmp_path / "001_a.sql").write_text(
            "ALTER TABLE a ADD COLUMN x TEXT;\n"
            "INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;\n"
        )
        (tmp_path / "002_b.sql").write_text(
            "ALTER TABLE b ADD COLUMN y TEXT;\n"
            "INSERT INTO schema_version (version) VALUES (2) ON CONFLICT DO NOTHING;\n"
        )

        # Only version 1 is applied; version 2 should run.
        m_conn, m_cur = self._make_mock_conn(applied_versions={1})
        m_cur.fetchone.return_value = (2,)

        with (
            patch("psycopg.connect", return_value=m_conn),
            patch.object(migrate, "MIGRATIONS_DIR", tmp_path),
        ):
            migrate.run("fake_conn")

        captured = capsys.readouterr()
        assert "001_a.sql" not in captured.out
        assert "002_b.sql" in captured.out

    def test_failed_migration_rolls_back(self, tmp_path):
        """If a migration raises, rollback is called and the error propagates."""
        sql_file = tmp_path / "001_bad.sql"
        sql_file.write_text("ALTER TABLE nonexistent ADD COLUMN x TEXT;\n")

        m_conn, m_cur = self._make_mock_conn(applied_versions=set())
        # execute calls in order: (1) CREATE TABLE schema_version bootstrap,
        # (2) SELECT version FROM schema_version, (3) the migration statement.
        m_cur.execute.side_effect = [None, None, Exception("relation does not exist")]

        with (
            patch("psycopg.connect", return_value=m_conn),
            patch.object(migrate, "MIGRATIONS_DIR", tmp_path),
        ):
            with pytest.raises(Exception, match="relation does not exist"):
                migrate.run("fake_conn")

        m_conn.rollback.assert_called_once()
