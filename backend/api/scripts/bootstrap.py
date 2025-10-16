import os
import sys
import time
import signal
from urllib.parse import urlparse
import subprocess

import psycopg
from dotenv import load_dotenv

# --- Alembic stamping helpers ---
def _to_psycopg_dsn(dsn: str) -> str:
    """Convert SQLAlchemy DSN to psycopg-compatible DSN."""
    if dsn.startswith("postgresql+"):
        return dsn.replace("postgresql+psycopg", "postgresql").replace("postgresql+asyncpg", "postgresql")
    return dsn

def _table_exists(dsn: str, table_name: str, schema: str = "public") -> bool:
    try:
        with psycopg.connect(_to_psycopg_dsn(dsn)) as conn:
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

def _alembic_version(dsn: str) -> str | None:
    try:
        with psycopg.connect(_to_psycopg_dsn(dsn)) as conn:
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

# Load environment variables from .env file
load_dotenv()


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
    # If schema was created out-of-band, align Alembic state to avoid DuplicateTable errors.
    current_rev = _alembic_version(dsn)
    jobs_exists = _table_exists(dsn, "jobs")

    if jobs_exists and (current_rev is None or current_rev == "0001_initial"):
        print("Detected existing 'jobs' table with outdated Alembic version; stamping to 0002_add_jobs_table...")
        subprocess.run(["alembic", "stamp", "0002_add_jobs_table"], check=True)

    print("Running Alembic migrations to head...")
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def start_uvicorn_process() -> subprocess.Popen:
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    print(f"Starting API on {host}:{port}...")
    return subprocess.Popen([
        "uvicorn", "api.main:app", "--host", host, "--port", str(port), "--app-dir", "src"
    ])


def start_worker_process() -> subprocess.Popen:
    """Start the Monte Carlo worker as a sidecar process."""
    # Ensure PYTHONPATH includes src when running locally
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", os.pathsep.join(filter(None, [env.get("PYTHONPATH"), "src"])))
    print("Starting Monte Carlo worker sidecar...")
    return subprocess.Popen([sys.executable, "src/workers/main.py"], env=env)


def main() -> None:
    url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/trading_db")
    dsn = _normalize_dsn(url)
    # Ensure Alembic uses psycopg v3 driver and not asyncpg.
    os.environ["DATABASE_URL"] = dsn
    ensure_database_exists(dsn)
    run_alembic_migrations(dsn)
    run_worker = os.getenv("RUN_WORKER", "false").lower() in ("1", "true", "yes")

    api_proc = start_uvicorn_process()
    worker_proc = None

    if run_worker:
        worker_proc = start_worker_process()

    # Graceful shutdown on signals
    def _shutdown(signum, frame):
        print(f"Received signal {signum}, shutting down processes...")
        try:
            if worker_proc and worker_proc.poll() is None:
                worker_proc.terminate()
        except Exception:
            pass
        try:
            if api_proc and api_proc.poll() is None:
                api_proc.terminate()
        except Exception:
            pass

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Monitor child processes; if one exits, stop the other
    try:
        while True:
            api_code = api_proc.poll()
            worker_code = worker_proc.poll() if worker_proc else None

            if api_code is not None:
                print(f"API process exited with code {api_code}")
                if worker_proc and worker_proc.poll() is None:
                    print("Stopping worker sidecar since API exited...")
                    worker_proc.terminate()
                break

            if worker_proc and worker_code is not None:
                print(f"Worker process exited with code {worker_code}")
                # Keep API running, but log the event
                worker_proc = None

            time.sleep(1)
    finally:
        # Ensure processes are cleaned up
        if worker_proc and worker_proc.poll() is None:
            worker_proc.terminate()
        if api_proc and api_proc.poll() is None:
            api_proc.terminate()


if __name__ == "__main__":
    main()