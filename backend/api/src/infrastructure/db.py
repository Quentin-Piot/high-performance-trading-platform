from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from urllib.parse import urlparse

from core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


def _to_async_url(url: str) -> str:
    # Convert common sync URLs to async driver equivalents when needed
    parsed = urlparse(url)
    if parsed.scheme.startswith("postgresql") and "+asyncpg" not in parsed.scheme:
        # Replace scheme to use asyncpg
        return url.replace("postgresql+psycopg", "postgresql+asyncpg").replace("postgresql://", "postgresql+asyncpg://")
    if parsed.scheme.startswith("sqlite") and "+aiosqlite" not in parsed.scheme:
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    return url

ASYNC_DB_URL = _to_async_url(settings.db_url)
engine = create_async_engine(
    ASYNC_DB_URL,
    echo=False,
    pool_size=getattr(settings, "db_pool_size", 5),
    max_overflow=getattr(settings, "db_max_overflow", 10),
    future=True,
)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)


async def init_db() -> None:
    # Import des modèles pour que metadata soit au courant
    from infrastructure.models import User, Strategy, Backtest  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with SessionLocal() as session:
        yield session