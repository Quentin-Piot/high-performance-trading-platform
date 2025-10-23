"""
Database management utilities for the trading platform.
This module contains database connection, validation, and repair logic
extracted from bootstrap.py to improve separation of concerns.
"""
from __future__ import annotations

import sys
from urllib.parse import urlparse

import psycopg


class DatabaseManager:
    """Handles database operations and validation."""
    @staticmethod
    def to_psycopg_dsn(dsn: str) -> str:
        """Convert SQLAlchemy DSN to psycopg-compatible DSN."""
        if dsn.startswith("postgresql+"):
            return dsn.replace("postgresql+psycopg", "postgresql").replace(
                "postgresql+asyncpg", "postgresql"
            )
        return dsn
    @staticmethod
    def table_exists(dsn: str, table_name: str, schema: str = "public") -> bool:
        """Check if a table exists in the database."""
        try:
            with psycopg.connect(DatabaseManager.to_psycopg_dsn(dsn)) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_schema = %s AND table_name = %s
                        )
                        """,
                        (schema, table_name),
                    )
                    row = cur.fetchone()
                    return bool(row and row[0])
        except Exception:
            return False
    @staticmethod
    def get_alembic_version(dsn: str) -> str | None:
        """Get the current Alembic version from the database."""
        try:
            with psycopg.connect(DatabaseManager.to_psycopg_dsn(dsn)) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_schema = 'public' AND table_name = 'alembic_version'
                        )
                        """
                    )
                    exists = bool(cur.fetchone()[0])
                    if not exists:
                        return None
                    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception:
            return None
    @staticmethod
    def repair_jobs_table_if_corrupted(dsn: str) -> bool:
        """
        Detect and repair a corrupted 'jobs' table by dropping it.
        Returns True if the table was dropped (corrupted detected), False otherwise.
        """
        try:
            with psycopg.connect(DatabaseManager.to_psycopg_dsn(dsn)) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables
                            WHERE table_schema='public' AND table_name='jobs'
                        )
                        """
                    )
                    exists = bool(cur.fetchone()[0])
                    if not exists:
                        return False
                    cur.execute(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='jobs'
                        """
                    )
                    cols = {r[0] for r in cur.fetchall()}
                    expected_core = {
                        "id",
                        "payload",
                        "status",
                        "progress",
                        "priority",
                        "worker_id",
                        "attempts",
                        "error",
                        "artifact_url",
                        "dedup_key",
                        "created_at",
                        "updated_at",
                    }
                    if not expected_core.issubset(cols):
                        print(
                            "Detected corrupted 'jobs' table (missing core columns); dropping for clean migration..."
                        )
                        cur.execute("DROP TABLE IF EXISTS jobs CASCADE")
                        return True
                    try:
                        cur.execute(
                            """
                            SELECT COUNT(*) FROM pg_attribute
                            WHERE attrelid = 'jobs'::regclass AND attnum > 0
                            """
                        )
                        attcount = int(cur.fetchone()[0])
                        if attcount < len(expected_core):
                            print(
                                "Detected inconsistent pg_attribute for 'jobs'; dropping table to recover..."
                            )
                            cur.execute("DROP TABLE IF EXISTS jobs CASCADE")
                            return True
                    except Exception:
                        print(
                            "pg_attribute query failed for 'jobs'; dropping table to recover..."
                        )
                        cur.execute("DROP TABLE IF EXISTS jobs CASCADE")
                        return True
                    return False
        except Exception as e:
            print(f"Failed to inspect/repair jobs table: {e}", file=sys.stderr)
            return False
    @staticmethod
    def parse_database_url(dsn: str) -> dict[str, str | int]:
        """Parse database URL into components."""
        parsed = urlparse(dsn)
        return {
            "dbname": (parsed.path or "/").lstrip("/") or "postgres",
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "postgres",
            "password": parsed.password or "postgres",
        }
