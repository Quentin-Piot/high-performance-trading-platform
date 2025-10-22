"""
Authentication dependencies for FastAPI routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.cognito import CognitoService, CognitoUser, get_cognito_service

# Security scheme for Bearer token
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    cognito_service: CognitoService = Depends(get_cognito_service)
) -> CognitoUser:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token from Authorization header
        cognito_service: Cognito service instance
        
    Returns:
        CognitoUser: Authenticated user information
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = cognito_service.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    cognito_service: CognitoService = Depends(get_cognito_service)
) -> CognitoUser | None:
    """
    Optional dependency to get the current user if authenticated.
    
    Args:
        credentials: Optional Bearer token from Authorization header
        cognito_service: Cognito service instance
        
    Returns:
        Optional[CognitoUser]: User information if authenticated, None otherwise
    """
    if not credentials or not credentials.credentials:
        return None

    return cognito_service.verify_token(credentials.credentials)


async def require_verified_email(
    current_user: CognitoUser = Depends(get_current_user)
) -> CognitoUser:
    """
    Dependency that requires the user to have a verified email.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        CognitoUser: User with verified email
        
    Raises:
        HTTPException: If email is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )

    return current_user