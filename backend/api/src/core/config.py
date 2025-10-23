import secrets

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "development"
    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@pg:5432/trading_db",
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
    )
    jwt_secret: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT secret key - should be set via environment variable in production"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    @field_validator('jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Ensure JWT secret is secure in production."""
        env = info.data.get('env', 'development') if info.data else 'development'
        if env == 'production' and (not v or v == 'changeme-dev-secret' or len(v) < 32):
            raise ValueError(
                "JWT secret must be set to a secure value (at least 32 characters) in production. "
                "Use a strong random string and set it via the JWT_SECRET environment variable."
            )
        return v
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
    db_echo: bool = Field(default=False, description="Enable SQL query logging")
    db_echo_pool: bool = Field(
        default=False, description="Enable connection pool logging"
    )
    db_query_timeout: int = Field(
        default=30, description="Default query timeout in seconds"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    cache_enabled: bool = Field(default=True, description="Enable caching layer")
    aws_endpoint_url: str = Field(
        default="", description="AWS endpoint URL for LocalStack"
    )
    cognito_region: str = Field(default="eu-west-3", description="AWS Cognito region")
    cognito_user_pool_id: str = Field(default="", description="Cognito User Pool ID")
    cognito_client_id: str = Field(default="", description="Cognito App Client ID")
    cognito_identity_pool_id: str = Field(
        default="", description="Cognito Identity Pool ID"
    )
    google_client_id: str = Field(default="", description="Google OAuth Client ID")
    google_client_secret: str = Field(
        default="", description="Google OAuth Client Secret"
    )
    google_redirect_uri: str = Field(
        default="", description="Google OAuth Redirect URI"
    )
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend URL for redirects"
    )
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
def get_settings() -> Settings:
    return Settings()
