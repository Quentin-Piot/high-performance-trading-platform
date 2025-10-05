import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


class Settings:
    env: str
    db_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    def __init__(
        self,
        env: Optional[str] = None,
        db_url: Optional[str] = None,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: Optional[str] = None,
        access_token_expire_minutes: Optional[int] = None,
    ) -> None:
        self.env = env or os.getenv("ENV", "development")
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/trading_db")
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET", "changeme-dev-secret")
        self.jwt_algorithm = jwt_algorithm or os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            access_token_expire_minutes or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )


def get_settings() -> Settings:
    return Settings()