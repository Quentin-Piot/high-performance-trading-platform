"""
Google OAuth authentication routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_dependencies import get_current_user_optional
from core.cognito import CognitoUser
from infrastructure.db import get_session
from infrastructure.repositories.user_repository import UserRepository
from services.cognito_google_integration import (
    CognitoGoogleIntegrationService,
    get_cognito_google_service,
)
from services.google_oauth import GoogleOAuthService, get_google_oauth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])


@router.get("/login")
async def google_login(
    redirect_url: str = Query(default="/", description="URL to redirect after successful login"),
    google_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """
    Initiate Google OAuth login flow.

    Args:
        redirect_url: URL to redirect user after successful authentication
        google_service: Google OAuth service

    Returns:
        Redirect to Google OAuth authorization URL
    """
    try:
        # Use redirect_url as state parameter for CSRF protection
        auth_url = google_service.get_authorization_url(state=redirect_url)
        return RedirectResponse(url=auth_url)

    except Exception as e:
        logger.error(f"Failed to initiate Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google authentication"
        )


@router.get("/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(default="/", description="State parameter (redirect URL)"),
    error: str = Query(default=None, description="Error from Google OAuth"),
    google_service: GoogleOAuthService = Depends(get_google_oauth_service),
    cognito_google_service: CognitoGoogleIntegrationService = Depends(get_cognito_google_service),
    db: AsyncSession = Depends(get_session)
):
    """
    Handle Google OAuth callback and integrate with Cognito.

    Args:
        code: Authorization code from Google
        state: State parameter containing redirect URL
        error: Error parameter from Google
        google_service: Google OAuth service
        cognito_google_service: Cognito Google integration service
        db: Database session

    Returns:
        Redirect to frontend with authentication result
    """
    if error:
        logger.error(f"Google OAuth error: {error}")
        # Redirect to frontend with error
        return RedirectResponse(url=f"{state}?error=oauth_error&message={error}")

    if not code:
        logger.error("No authorization code received from Google")
        return RedirectResponse(url=f"{state}?error=missing_code")

    try:
        # Exchange code for tokens
        token_data = await google_service.exchange_code_for_tokens(code)
        user_info = token_data["user_info"]

        # Create or link federated user in Cognito
        cognito_user = await cognito_google_service.create_federated_user(user_info)

        if not cognito_user:
            logger.error("Failed to create or link federated user")
            return RedirectResponse(url=f"{state}?error=federated_user_error")

        # Sync user with local database
        user_repo = UserRepository(db)
        db_user = await user_repo.get_or_create_from_cognito(cognito_user)

        # Get federated credentials for the user
        federated_creds = await cognito_google_service.get_federated_credentials(token_data["id_token"])

        # For now, redirect with success and user info
        # Check if we're in development mode and redirect to dashboard instead of simulate
        if state and "/simulate" in state:
            redirect_url = f"{google_service.settings.frontend_url}/dashboard"
        else:
            # Use frontend URL for proper redirection
            if state == "/" or not state:
                redirect_url = f"{google_service.settings.frontend_url}/dashboard"
            else:
                # If state contains a full URL, use it as is, otherwise prepend frontend URL
                if state.startswith("http"):
                    redirect_url = state
                else:
                    redirect_url = f"{google_service.settings.frontend_url}{state}"

        query_params = f"auth=success&provider=google&email={user_info['email']}&user_id={db_user.id}"

        if federated_creds:
            query_params += f"&identity_id={federated_creds['identity_id']}"

        return RedirectResponse(url=f"{redirect_url}?{query_params}")

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(url=f"{state}?error=callback_error&message=Authentication failed")


@router.get("/user-info")
async def get_google_user_info(
    current_user: CognitoUser = Depends(get_current_user_optional)
):
    """
    Get current user information (requires authentication).

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return {
        "sub": current_user.sub,
        "email": current_user.email,
        "name": current_user.name,
        "email_verified": current_user.email_verified,
        "provider": "google" if current_user.sub.startswith("google_") else "cognito"
    }


@router.post("/link-account")
async def link_google_account(
    current_user: CognitoUser = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_session)
):
    """
    Link Google account to existing Cognito user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # This would typically involve:
    # 1. Initiating Google OAuth flow
    # 2. Storing the association in database
    # 3. Allowing user to login with either method

    return {
        "message": "Account linking not yet implemented",
        "current_user": current_user.email
    }


@router.delete("/unlink-account")
async def unlink_google_account(
    current_user: CognitoUser = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_session)
):
    """
    Unlink Google account from current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Implementation would remove Google association
    return {
        "message": "Account unlinking not yet implemented",
        "current_user": current_user.email
    }
