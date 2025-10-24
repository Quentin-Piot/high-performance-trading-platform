import os
import signal
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv


def _to_psycopg_dsn(dsn: str) -> str:
    """Convert SQLAlchemy DSN to psycopg-compatible DSN."""
    if dsn.startswith("postgresql+"):
        return dsn.replace("postgresql+psycopg", "postgresql").replace(
            "postgresql+asyncpg", "postgresql"
        )
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
def _repair_jobs_table_if_corrupted(dsn: str) -> bool:
    """Detect and repair a corrupted 'jobs' table by dropping it.
    Returns True if the table was dropped (corrupted detected), False otherwise.
    """
    try:
        with psycopg.connect(_to_psycopg_dsn(dsn)) as conn:
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
load_dotenv()
def _normalize_dsn(url: str) -> str:
    if url.startswith("postgresql+"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg")
    return url
def ensure_database_exists(dsn: str) -> None:
    parsed = urlparse(dsn)
    if not parsed.scheme.startswith("postgresql"):
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
def reset_database(dsn: str) -> bool:
    """Drop and recreate the target database (or at least clear the public schema).
    Returns True if a reset was performed successfully.
    """
    parsed = urlparse(dsn)
    if not parsed.scheme.startswith("postgresql"):
        return False
    dbname = (parsed.path or "/").lstrip("/") or "postgres"
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"
    admin_dsn = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    target_dsn = _to_psycopg_dsn(dsn)
    print(f"RESET_DB: dropping database '{dbname}' and recreating it...")
    try:
        with psycopg.connect(admin_dsn) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = %s AND pid <> pg_backend_pid()
                        """,
                        (dbname,),
                    )
                except Exception as e:
                    print(
                        f"Failed to terminate sessions for '{dbname}': {e}",
                        file=sys.stderr,
                    )
                try:
                    cur.execute(f'DROP DATABASE "{dbname}"')
                    print(f"Database '{dbname}' dropped.")
                except Exception as e:
                    print(
                        f"DROP DATABASE failed: {e}. Falling back to clearing schema.",
                        file=sys.stderr,
                    )
                    try:
                        with psycopg.connect(target_dsn) as tconn:
                            tconn.autocommit = True
                            with tconn.cursor() as tcur:
                                tcur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
                                tcur.execute("CREATE SCHEMA public;")
                                print("Public schema recreated.")
                    except Exception as ee:
                        print(f"Failed to clear public schema: {ee}", file=sys.stderr)
                        raise
                else:
                    cur.execute(f'CREATE DATABASE "{dbname}"')
                    print(f"Database '{dbname}' recreated.")
        return True
    except Exception as e:
        print(f"RESET_DB failed: {e}", file=sys.stderr)
        return False
def run_alembic_migrations(dsn: str) -> None:
    dropped = _repair_jobs_table_if_corrupted(dsn)
    current_rev = _alembic_version(dsn)
    jobs_exists = _table_exists(dsn, "jobs")
    if dropped:
        print(
            "Corrupted 'jobs' table was dropped; resetting Alembic to 0001_initial before upgrade..."
        )
        subprocess.run(["alembic", "stamp", "0001_initial"], check=True)
        current_rev = "0001_initial"
        jobs_exists = False
    if jobs_exists and (current_rev is None or current_rev == "0001_initial"):
        print(
            "Detected existing 'jobs' table with outdated Alembic version; stamping to 0002_add_jobs_table..."
        )
        subprocess.run(["alembic", "stamp", "0002_add_jobs_table"], check=True)
    print("Running Alembic migrations to head...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    except Exception as e:
        print(
            f"Alembic upgrade failed: {e}. Attempting full database reset...",
            file=sys.stderr,
        )
        if reset_database(dsn):
            subprocess.run(["alembic", "upgrade", "head"], check=True)
        else:
            raise
def start_uvicorn_process() -> subprocess.Popen:
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    print(f"Starting API on {host}:{port}...")
    return subprocess.Popen(
        [
            "uvicorn",
            "api.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--app-dir",
            "src",
        ]
    )
def start_worker_in_thread() -> threading.Thread:
    """Start the Monte Carlo worker in a background thread (DISABLED for sync mode)."""
    def worker_main():
        print("Monte Carlo worker is disabled - using synchronous execution mode")
        try:
            sys.path.insert(0, os.path.abspath("src"))
            from workers.simple_worker import get_simple_worker, start_cleanup_task
            worker = get_simple_worker()
            print(
                f"Simple Monte Carlo worker initialized with {worker.max_concurrent_jobs} max concurrent jobs"
            )
            start_cleanup_task()
            print("Simple worker cleanup task started")
        except Exception as e:
            print(f"Failed to initialize simple worker: {e}")
        return
    thread = threading.Thread(
        target=worker_main, name="MonteCarloWorkerThread-Disabled", daemon=True
    )
    thread.start()
    print(
        "Monte Carlo worker disabled - using synchronous execution mode with simple async worker."
    )
    return thread
def main() -> None:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/trading_db",
    )
    dsn = _normalize_dsn(url)
    os.environ["DATABASE_URL"] = dsn
    ensure_database_exists(dsn)
    reset_requested = os.getenv("RESET_DB", "false").lower() in ("1", "true", "yes")
    if reset_requested:
        ok = reset_database(dsn)
        if not ok:
            print(
                "Requested DB reset failed; continuing startup, migrations may still fail.",
                file=sys.stderr,
            )
    run_alembic_migrations(dsn)
    run_worker = os.getenv("RUN_WORKER", "false").lower() in ("1", "true", "yes")
    api_proc = start_uvicorn_process()
    if run_worker:
        start_worker_in_thread()
    def _shutdown(signum, frame):
        print(f"Received signal {signum}, shutting down processes...")
        try:
            if api_proc and api_proc.poll() is None:
                api_proc.terminate()
        except Exception:
            pass
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.pause()
if __name__ == "__main__":
    main()
