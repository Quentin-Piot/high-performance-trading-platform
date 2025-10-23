from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "development"
    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@pg:5432/trading_db",
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
    )
    jwt_secret: str = "changeme-dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days = 7 * 24 * 60 minutes

    # Database connection pooling settings
    db_pool_size: int = Field(
        default=10, description="Number of connections to maintain in the pool"
    )
    db_max_overflow: int = Field(
        default=20,
        description="Maximum number of connections that can overflow the pool",
    )
    db_pool_timeout: int = Field(
        default=30, description="Timeout in seconds for getting connection from pool"
    )
    db_pool_recycle: int = Field(
        default=3600, description="Time in seconds to recycle connections"
    )
    db_pool_pre_ping: bool = Field(
        default=True, description="Enable connection health checks"
    )

    # Query performance settings
    db_echo: bool = Field(default=False, description="Enable SQL query logging")
    db_echo_pool: bool = Field(
        default=False, description="Enable connection pool logging"
    )
    db_query_timeout: int = Field(
        default=30, description="Default query timeout in seconds"
    )

    # Cache settings
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    cache_enabled: bool = Field(default=True, description="Enable caching layer")

    # AWS Cognito settings
    aws_endpoint_url: str = Field(
        default="", description="AWS endpoint URL for LocalStack"
    )
    cognito_region: str = Field(default="eu-west-3", description="AWS Cognito region")
    cognito_user_pool_id: str = Field(default="", description="Cognito User Pool ID")
    cognito_client_id: str = Field(default="", description="Cognito App Client ID")
    cognito_identity_pool_id: str = Field(
        default="", description="Cognito Identity Pool ID"
    )

    # Google OAuth settings
    google_client_id: str = Field(default="", description="Google OAuth Client ID")
    google_client_secret: str = Field(
        default="", description="Google OAuth Client Secret"
    )
    google_redirect_uri: str = Field(
        default="", description="Google OAuth Redirect URI"
    )

    # Frontend URL settings
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend URL for redirects"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def get_settings() -> Settings:
    return Settings()
