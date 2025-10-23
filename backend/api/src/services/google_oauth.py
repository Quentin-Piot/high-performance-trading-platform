"""
Google OAuth service for authentication integration.
"""
import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests
from google.oauth2 import id_token

from core.config import get_settings

logger = logging.getLogger(__name__)

class GoogleOAuthService:
    """Service for handling Google OAuth authentication."""

    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.google_client_id
        self.client_secret = self.settings.google_client_secret
        self.redirect_uri = self.settings.google_redirect_uri

        # OAuth 2.0 endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        # Configure HTTP timeout settings (30 seconds total, 10 seconds connect)
        self.timeout = httpx.Timeout(30.0, connect=10.0)

        # Check if we're in development mode with LocalStack AND using mock OAuth
        # Use mock ONLY when Google OAuth credentials are not configured
        self.is_development = (
            self.settings.env == "development" and
            hasattr(self.settings, 'aws_endpoint_url') and
            self.settings.aws_endpoint_url == "http://localhost:4566" and
            # Use mock only if Google OAuth credentials are not configured
            (not self.client_id or not self.client_secret)
        )

        # Debug logging
        logger.info(f"GoogleOAuthService initialized - Environment: {self.settings.env}, "
                   f"AWS Endpoint: {getattr(self.settings, 'aws_endpoint_url', 'None')}, "
                   f"Is Development: {self.is_development}")

    def get_authorization_url(self, state: str | None = None) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            str: Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and ID tokens.

        Args:
            code: Authorization code from Google

        Returns:
            Dict containing tokens and user info

        Raises:
            Exception: If token exchange fails
        """
        # Mock implementation for development with LocalStack
        if self.is_development:
            logger.info("Using mock Google OAuth token exchange for development")
            return {
                "access_token": f"mock_access_token_{code}",
                "id_token": f"mock_id_token_{code}",
                "refresh_token": f"mock_refresh_token_{code}",
                "user_info": {
                    "sub": f"mock_google_user_{code}",
                    "email": f"test.user.{code}@example.com",
                    "email_verified": True,
                    "name": f"Test User {code}",
                    "given_name": "Test",
                    "family_name": f"User {code}",
                    "picture": "https://example.com/avatar.jpg",
                    "locale": "en"
                }
            }

        # Production implementation
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.token_url, data=token_data)

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                logger.error(f"Request data: {token_data}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                raise Exception(f"Failed to exchange code for tokens: {response.text}")

            tokens = response.json()

            # Verify ID token
            try:
                id_info = id_token.verify_oauth2_token(
                    tokens["id_token"],
                    requests.Request(),
                    self.client_id
                )

                # Get additional user info
                user_info = await self._get_user_info(tokens["access_token"])

                return {
                    "access_token": tokens["access_token"],
                    "id_token": tokens["id_token"],
                    "refresh_token": tokens.get("refresh_token"),
                    "user_info": {
                        "sub": id_info["sub"],
                        "email": id_info["email"],
                        "email_verified": id_info.get("email_verified", False),
                        "name": user_info.get("name", ""),
                        "given_name": user_info.get("given_name", ""),
                        "family_name": user_info.get("family_name", ""),
                        "picture": user_info.get("picture", ""),
                        "locale": user_info.get("locale", "")
                    }
                }

            except ValueError as e:
                logger.error(f"ID token verification failed: {e}")
                raise Exception(f"Invalid ID token: {e}") from e

    async def _get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from Google API.

        Args:
            access_token: Google access token

        Returns:
            Dict containing user information
        """
        # Mock implementation for development
        if self.is_development:
            return {
                "name": "Test User",
                "given_name": "Test",
                "family_name": "User",
                "picture": "https://example.com/avatar.jpg",
                "locale": "en"
            }

        # Production implementation
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.userinfo_url, headers=headers)

            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise Exception(f"Failed to get user info: {response.text}")

            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any] | None:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Google refresh token

        Returns:
            Dict containing new tokens or None if failed
        """
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.token_url, data=token_data)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token refresh failed: {response.text}")
                return None

    def verify_id_token(self, id_token_str: str) -> dict[str, Any] | None:
        """
        Verify Google ID token.

        Args:
            id_token_str: ID token string

        Returns:
            Dict containing token claims or None if invalid
        """
        try:
            id_info = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                self.client_id
            )
            return id_info
        except ValueError as e:
            logger.error(f"ID token verification failed: {e}")
            return None


# Singleton instance
_google_oauth_service: GoogleOAuthService | None = None

def get_google_oauth_service() -> GoogleOAuthService:
    """Get Google OAuth service instance."""
    global _google_oauth_service
    if _google_oauth_service is None:
        _google_oauth_service = GoogleOAuthService()
    return _google_oauth_service
