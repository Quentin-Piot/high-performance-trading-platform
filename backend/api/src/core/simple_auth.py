"""
Simple JWT authentication system for local development.
"""
import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from infrastructure.db import get_session
from infrastructure.repositories.users import get_user_by_id

logger = logging.getLogger(__name__)
settings = get_settings()

# Security scheme for Bearer token
security = HTTPBearer()
# Optional security scheme (doesn't raise exception if no token)
optional_security = HTTPBearer(auto_error=False)


class SimpleUser(BaseModel):
    """Simple user information extracted from JWT token."""
    id: int
    email: str
    sub: str  # For compatibility with CognitoUser


class SimpleAuthService:
    """Service for simple JWT authentication."""

    def __init__(self):
        self.settings = get_settings()

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None


# Global service instance
simple_auth_service = SimpleAuthService()


def get_simple_auth_service() -> SimpleAuthService:
    """Dependency to get simple auth service."""
    return simple_auth_service


async def get_current_user_simple(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: SimpleAuthService = Depends(get_simple_auth_service),
    db: AsyncSession = Depends(get_session)
) -> SimpleUser:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: Bearer token from Authorization header
        auth_service: Simple auth service instance
        db: Database session

    Returns:
        SimpleUser: Authenticated user information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return SimpleUser(
        id=user.id,
        email=user.email,
        sub=str(user.id)
    )


async def get_current_user_simple_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    auth_service: SimpleAuthService = Depends(get_simple_auth_service),
    db: AsyncSession = Depends(get_session)
) -> SimpleUser | None:
    """
    Optional dependency to get the current user if authenticated.

    Args:
        credentials: Optional Bearer token from Authorization header
        auth_service: Simple auth service instance
        db: Database session

    Returns:
        Optional[SimpleUser]: User information if authenticated, None otherwise
    """
    if not credentials or not credentials.credentials:
        return None

    payload = auth_service.verify_token(credentials.credentials)
    if not payload:
        # Log warning but don't raise exception for graceful degradation
        logger.warning("Invalid token provided, continuing without authentication")
        return None

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Invalid token payload, continuing without authentication")
        return None

    # Get user from database
    try:
        user = await get_user_by_id(db, int(user_id))
        if not user:
            logger.warning("User not found in database, continuing without authentication")
            return None

        return SimpleUser(
            id=user.id,
            email=user.email,
            sub=str(user.id)
        )
    except Exception as e:
        logger.warning(f"Error retrieving user from database: {e}, continuing without authentication")
        return None
