from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices


class Settings(BaseSettings):
    env: str = "development"
    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@pg:5432/trading_db",
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
    )
    jwt_secret: str = "changeme-dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    
    # Database connection pooling settings
    db_pool_size: int = Field(default=10, description="Number of connections to maintain in the pool")
    db_max_overflow: int = Field(default=20, description="Maximum number of connections that can overflow the pool")
    db_pool_timeout: int = Field(default=30, description="Timeout in seconds for getting connection from pool")
    db_pool_recycle: int = Field(default=3600, description="Time in seconds to recycle connections")
    db_pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    
    # Query performance settings
    db_echo: bool = Field(default=False, description="Enable SQL query logging")
    db_echo_pool: bool = Field(default=False, description="Enable connection pool logging")
    db_query_timeout: int = Field(default=30, description="Default query timeout in seconds")
    
    # Cache settings
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    cache_enabled: bool = Field(default=True, description="Enable caching layer")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def get_settings() -> Settings:
    return Settings()
