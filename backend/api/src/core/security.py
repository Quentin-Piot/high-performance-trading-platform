from datetime import datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # Handle bcrypt 72 byte limitation by truncating password
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def create_access_token(subject: str, expires_minutes: int | None = None, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    now = datetime.utcnow()
    to_encode: dict[str, Any] = {"sub": subject, "iat": int(now.timestamp()), "exp": int((now + expire_delta).timestamp())}
    if extra_claims:
        to_encode.update(extra_claims)
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt
