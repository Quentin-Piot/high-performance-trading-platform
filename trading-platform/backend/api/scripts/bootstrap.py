import os
import sys
import time
from urllib.parse import urlparse
import subprocess

import psycopg


def _normalize_dsn(url: str) -> str:
    # Keep explicit driver markers; only normalize async driver for Alembic compatibility.
    if url.startswith("postgresql+"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg")
    return url


def ensure_database_exists(dsn: str) -> None:
    parsed = urlparse(dsn)
    if not parsed.scheme.startswith("postgresql"):
        # No-op for SQLite or other drivers
        return
    dbname = (parsed.path or "/").lstrip("/") or "postgres"
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"

    admin_dsn = f"postgresql://{user}:{password}@{host}:{port}/postgres"

    print(f"Connecting to admin database to ensure '{dbname}' exists...")
    deadline = time.time() + 120
    while True:
        try:
            with psycopg.connect(admin_dsn, connect_timeout=3) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
                    exists = cur.fetchone() is not None
                    if not exists:
                        print(f"Creating database '{dbname}'...")
                        cur.execute(f'CREATE DATABASE "{dbname}"')
                break
        except Exception as e:
            if time.time() > deadline:
                print(f"Failed to connect/create DB: {e}", file=sys.stderr)
                raise
            time.sleep(2)


def run_alembic_migrations(dsn: str) -> None:
    print("Running Alembic migrations to head...")
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def start_uvicorn() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    print(f"Starting API on {host}:{port}...")
    subprocess.run(["uvicorn", "api.main:app", "--host", host, "--port", str(port), "--app-dir", "src"], check=True)


def main() -> None:
    url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/trading_db")
    dsn = _normalize_dsn(url)
    # Ensure Alembic uses psycopg v3 driver and not asyncpg.
    os.environ["DATABASE_URL"] = dsn
    ensure_database_exists(dsn)
    run_alembic_migrations(dsn)
    start_uvicorn()


if __name__ == "__main__":
    main()