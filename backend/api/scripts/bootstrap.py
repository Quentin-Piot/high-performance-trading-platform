import logging
import os
import signal
import subprocess
import time
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


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

    Returns True if the table was dropped (corruption detected), False otherwise.
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
                    logger.warning(
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
                        logger.warning(
                            "Detected inconsistent pg_attribute for 'jobs'; dropping table to recover..."
                        )
                        cur.execute("DROP TABLE IF EXISTS jobs CASCADE")
                        return True
                except Exception:
                    logger.warning(
                        "pg_attribute query failed for 'jobs'; dropping table to recover..."
                    )
                    cur.execute("DROP TABLE IF EXISTS jobs CASCADE")
                    return True

                return False
    except Exception:
        logger.exception("Failed to inspect/repair jobs table")
        return False


def _normalize_dsn(url: str) -> str:
    if url.startswith("postgresql+"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg")
    return url


def _alembic_env() -> dict:
    """Build environment with src/ on PYTHONPATH for alembic subprocesses."""
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    current = os.environ.get("PYTHONPATH", "")
    pythonpath = f"{src_path}:{current}" if current else src_path
    return {**os.environ, "PYTHONPATH": pythonpath}


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

    logger.info("Connecting to admin database to ensure '%s' exists...", dbname)
    deadline = time.time() + 120
    while True:
        try:
            with psycopg.connect(admin_dsn, connect_timeout=3) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
                    if cur.fetchone() is None:
                        logger.info("Creating database '%s'...", dbname)
                        cur.execute(f'CREATE DATABASE "{dbname}"')
            break
        except Exception as e:
            if time.time() > deadline:
                logger.error("Failed to connect/create DB: %s", e)
                raise
            time.sleep(2)


def reset_database(dsn: str) -> bool:
    """Drop and recreate the target database.

    Returns True if the reset was performed successfully.
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

    logger.info("RESET_DB: dropping database '%s' and recreating it...", dbname)
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
                except Exception:
                    logger.warning("Failed to terminate sessions for '%s'", dbname)

                try:
                    cur.execute(f'DROP DATABASE "{dbname}"')
                    logger.info("Database '%s' dropped.", dbname)
                except Exception as e:
                    logger.warning(
                        "DROP DATABASE failed: %s. Falling back to clearing schema.", e
                    )
                    with psycopg.connect(target_dsn) as tconn:
                        tconn.autocommit = True
                        with tconn.cursor() as tcur:
                            tcur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
                            tcur.execute("CREATE SCHEMA public;")
                            logger.info("Public schema recreated.")
                else:
                    cur.execute(f'CREATE DATABASE "{dbname}"')
                    logger.info("Database '%s' recreated.", dbname)
        return True
    except Exception:
        logger.exception("RESET_DB failed")
        return False


def run_alembic_migrations(dsn: str) -> None:
    dropped = _repair_jobs_table_if_corrupted(dsn)
    current_rev = _alembic_version(dsn)
    jobs_exists = _table_exists(dsn, "jobs")
    alembic_env = _alembic_env()

    if dropped:
        logger.info(
            "Corrupted 'jobs' table was dropped; resetting Alembic to 0001_initial before upgrade..."
        )
        subprocess.run(
            ["alembic", "stamp", "0001_initial"], check=True, env=alembic_env
        )
        current_rev = "0001_initial"
        jobs_exists = False

    if jobs_exists and (current_rev is None or current_rev == "0001_initial"):
        logger.info(
            "Detected existing 'jobs' table with outdated Alembic version; stamping to 0002_add_jobs_table..."
        )
        subprocess.run(
            ["alembic", "stamp", "0002_add_jobs_table"], check=True, env=alembic_env
        )

    logger.info("Running Alembic migrations to head...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, env=alembic_env)
    except Exception as e:
        logger.error("Alembic upgrade failed: %s. Attempting full database reset...", e)
        if reset_database(dsn):
            subprocess.run(["alembic", "upgrade", "head"], check=True, env=alembic_env)
        else:
            raise


def start_uvicorn() -> subprocess.Popen:
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    logger.info("Starting API on %s:%s...", host, port)
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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv()

    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/trading_db",
    )
    dsn = _normalize_dsn(url)
    os.environ["DATABASE_URL"] = dsn

    ensure_database_exists(dsn)

    if os.getenv("RESET_DB", "false").lower() in ("1", "true", "yes"):
        if not reset_database(dsn):
            logger.warning(
                "Requested DB reset failed; continuing startup, migrations may still fail."
            )

    run_alembic_migrations(dsn)

    api_proc = start_uvicorn()

    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        if api_proc.poll() is None:
            api_proc.terminate()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.pause()


if __name__ == "__main__":
    main()
