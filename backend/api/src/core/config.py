from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices


class Settings(BaseSettings):
    env: str = "development"
    # Default to SQLite (async) for local/dev to avoid startup failures without Postgres
    db_url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
    )
    jwt_secret: str = "changeme-dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # DB pool sizing (used for async engines)
    db_pool_size: int = 5
    db_max_overflow: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    return Settings()