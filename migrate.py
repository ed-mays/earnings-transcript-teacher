"""Database migration runner.

Run before starting the app:
    python3 migrate.py

Migration files live in db/migrations/ as NNN_name.sql, where NNN is the
integer version number. The runner applies every file whose version is not yet
recorded in the schema_version table, in ascending order.

The .sql files are the single source of truth. Each file is self-contained:
it performs the schema change and ends with an INSERT into schema_version so
that both this runner and manual runs (e.g. via the Supabase SQL Editor) keep
the version table in sync.
"""
import os
import re
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "db" / "migrations"
_CONN_STR = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")


def _split_statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements.

    Handles dollar-quoted blocks (DO $$ ... $$) by tracking open/close tags
    so that semicolons inside those blocks are not treated as statement ends.
    Only $$ (anonymous dollar-quoting) is supported — sufficient for our files.
    """
    statements: list[str] = []
    buf: list[str] = []
    in_dollar_quote = False
    i = 0

    while i < len(sql):
        if sql[i : i + 2] == "$$":
            in_dollar_quote = not in_dollar_quote
            buf.append("$$")
            i += 2
            continue

        if not in_dollar_quote and sql[i] == ";":
            buf.append(";")
            stmt = "".join(buf).strip()
            # Strip comment-only statements
            non_comment = "\n".join(
                line for line in stmt.splitlines() if not line.strip().startswith("--")
            ).strip()
            if non_comment.rstrip(";").strip():
                statements.append(stmt)
            buf = []
        else:
            buf.append(sql[i])

        i += 1

    # Trailing content without a final semicolon
    remaining = "".join(buf).strip()
    if remaining:
        non_comment = "\n".join(
            line for line in remaining.splitlines() if not line.strip().startswith("--")
        ).strip()
        if non_comment:
            statements.append(remaining)

    return statements


def run(conn_str: str = _CONN_STR) -> None:
    """Apply all pending migrations and print a summary."""
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Bootstrap: create schema_version if it doesn't exist yet.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version      INTEGER PRIMARY KEY,
                    installed_at TIMESTAMPTZ DEFAULT now()
                );
            """)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_version")
            applied: set[int] = {row[0] for row in cur.fetchall()}

        # Discover migration files sorted by their numeric prefix.
        pattern = re.compile(r"^(\d+)_.+\.sql$")
        migration_files = sorted(
            (f for f in MIGRATIONS_DIR.iterdir() if pattern.match(f.name)),
            key=lambda f: int(pattern.match(f.name).group(1)),
        )

        pending = [
            f for f in migration_files
            if int(pattern.match(f.name).group(1)) not in applied
        ]

        if not pending:
            print("No migrations to apply — schema is up to date.")
            return

        applied_count = 0
        for sql_file in pending:
            version = int(pattern.match(sql_file.name).group(1))
            sql = sql_file.read_text(encoding="utf-8")
            statements = _split_statements(sql)
            try:
                with conn.cursor() as cur:
                    for stmt in statements:
                        cur.execute(stmt)
                conn.commit()
                print(f"  Applied {sql_file.name}")
                applied_count += 1
            except Exception as exc:
                conn.rollback()
                print(f"  ERROR applying {sql_file.name}: {exc}", file=sys.stderr)
                raise

        with conn.cursor() as cur:
            cur.execute("SELECT MAX(version) FROM schema_version")
            final_version = cur.fetchone()[0]

        print(f"Migration complete — {applied_count} file(s) applied, schema is at version {final_version}.")


if __name__ == "__main__":
    run()
