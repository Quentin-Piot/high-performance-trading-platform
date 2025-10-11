import os
import sys
import time
import subprocess
from urllib.parse import urlparse

import psycopg


def _normalize_dsn(url: str) -> str:
    if url.startswith("postgresql+"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg")
    return url


def wait_for_db(admin_dsn: str, timeout=120):
    """Retry connection until DB is ready"""
    deadline = time.time() + timeout
    while True:
        try:
            with psycopg.connect(admin_dsn, connect_timeout=3) as conn:
                conn.autocommit = True
                return
        except Exception as e:
            if time.time() > deadline:
                print(f"Failed to connect to DB: {e}", file=sys.stderr)
                raise
            print("Waiting for DB to be ready...")
            time.sleep(2)


def ensure_database_exists(dsn: str) -> None:
    parsed = urlparse(dsn)
    dbname = (parsed.path or "/").lstrip("/") or "postgres"
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"

    admin_dsn = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    print(f"Connecting to admin database to ensure '{dbname}' exists...")

    wait_for_db(admin_dsn)

    with psycopg.connect(admin_dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                print(f"Creating database '{dbname}'...")
                cur.execute(f'CREATE DATABASE "{dbname}"')


def run_alembic_migrations(dsn: str) -> None:
    print("Running Alembic migrations to head...")
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def start_uvicorn() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"Starting API on {host}:{port}...")
    subprocess.run(
        [
            "uvicorn",
            "api.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--app-dir",
            "src",
        ],
        check=True,
    )


def main():
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/trading_db",
    )
    dsn = _normalize_dsn(url)
    os.environ["DATABASE_URL"] = dsn

    ensure_database_exists(dsn)
    run_alembic_migrations(dsn)
    start_uvicorn()


if __name__ == "__main__":
    main()
