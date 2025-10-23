import logging
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


def _to_async_url(url: str) -> str:
    """Convert synchronous database URL to async format"""
    parsed = urlparse(url)
    if parsed.scheme.startswith("postgresql") and "+asyncpg" not in parsed.scheme:
        return url.replace("postgresql+psycopg", "postgresql+asyncpg").replace(
            "postgresql://", "postgresql+asyncpg://"
        )
    return url


# Enhanced database engine with performance optimizations
ASYNC_DB_URL = _to_async_url(settings.db_url)
engine = create_async_engine(
    ASYNC_DB_URL,
    echo=settings.db_echo,
    echo_pool=settings.db_echo_pool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=settings.db_pool_pre_ping,
    poolclass=AsyncAdaptedQueuePool,
    future=True,
    # Additional performance settings
    connect_args={
        "command_timeout": settings.db_query_timeout,
        "server_settings": {
            "jit": "off",  # Disable JIT for faster connection times
            "application_name": "trading_platform_api",
        },
    },
)

# Enhanced session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# Connection pool monitoring
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level settings for performance"""
    if hasattr(dbapi_connection, "execute"):
        # For PostgreSQL connections, we can set session-level parameters
        pass


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring"""
    logger.debug(
        "Connection checked out from pool",
        extra={
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin(),
        },
    )


@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring"""
    logger.debug(
        "Connection returned to pool",
        extra={
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin(),
        },
    )


async def init_db() -> None:
    """Initialize database with performance monitoring"""
    from infrastructure.models import Backtest, Job, Strategy, User  # noqa: F401

    logger.info(
        "Database initialized",
        extra={
            "db_url": ASYNC_DB_URL.split("@")[0] + "@[REDACTED]",  # Mask credentials
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
        },
    )


async def get_session():
    """Get database session with performance monitoring"""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(
                "Database session error",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_pool_status() -> dict:
    """Get current connection pool status for monitoring"""
    return {
        "pool_size": engine.pool.size(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "checked_in": engine.pool.checkedin(),
        "total_connections": engine.pool.size() + engine.pool.overflow(),
    }
