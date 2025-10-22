"""
Tests for Google OAuth integration with Cognito.
"""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.cognito import CognitoUser
from services.cognito_google_integration import CognitoGoogleIntegrationService
from services.google_oauth import GoogleOAuthService


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_google_user_info():
    """Mock Google user information."""
    return {
        "sub": "google-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True,
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/photo.jpg",
        "locale": "en"
    }


@pytest.fixture
def mock_google_token_data(mock_google_user_info):
    """Mock Google token exchange response."""
    return {
        "access_token": "google-access-token",
        "id_token": "google-id-token",
        "refresh_token": "google-refresh-token",
        "user_info": mock_google_user_info
    }


@pytest.fixture
def mock_cognito_user():
    """Mock Cognito user."""
    return CognitoUser(
        sub="google_google-user-123",
        email="test@example.com",
        name="Test User",
        email_verified=True,
        cognito_username="test@example.com"
    )


@pytest.fixture
def mock_db_user():
    """Mock database user."""
    user = Mock()
    user.id = 1
    user.email = "test@example.com"
    user.name = "Test User"
    user.cognito_sub = "google_google-user-123"
    return user


class TestGoogleOAuthRoutes:
    """Test cases for Google OAuth routes."""

    def test_google_login_redirect(self, client):
        """Test Google login initiates OAuth flow."""
        with patch('api.routers.google_auth.get_google_oauth_service') as mock_service:
            mock_oauth_service = Mock()
            mock_oauth_service.get_authorization_url.return_value = "https://accounts.google.com/oauth/authorize?..."
            mock_service.return_value = mock_oauth_service

            response = client.get("/auth/google/login?redirect_url=/dashboard")

            assert response.status_code == 307  # Redirect
            assert "accounts.google.com" in response.headers["location"]
            mock_oauth_service.get_authorization_url.assert_called_once_with(state="/dashboard")

    @patch('api.routers.google_auth.UserRepository')
    @patch('api.routers.google_auth.get_cognito_google_service')
    @patch('api.routers.google_auth.get_google_oauth_service')
    def test_google_callback_success(
        self,
        mock_google_service,
        mock_cognito_google_service,
        mock_user_repo_class,
        client,
        mock_google_token_data,
        mock_cognito_user,
        mock_db_user
    ):
        """Test successful Google OAuth callback."""
        # Mock Google OAuth service
        mock_oauth_service = Mock()
        mock_oauth_service.exchange_code_for_tokens = AsyncMock(return_value=mock_google_token_data)
        mock_google_service.return_value = mock_oauth_service

        # Mock Cognito Google integration service
        mock_integration_service = Mock()
        mock_integration_service.create_federated_user = AsyncMock(return_value=mock_cognito_user)
        mock_integration_service.get_federated_credentials = AsyncMock(return_value={
            "identity_id": "test-identity-id",
            "access_key_id": "test-access-key",
            "secret_key": "test-secret-key",
            "session_token": "test-session-token"
        })
        mock_cognito_google_service.return_value = mock_integration_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_db_user)
        mock_user_repo_class.return_value = mock_user_repo

        response = client.get("/auth/google/callback?code=test-code&state=/dashboard")

        assert response.status_code == 307  # Redirect
        location = response.headers["location"]
        assert "auth=success" in location
        assert "provider=google" in location
        assert "email=test@example.com" in location
        assert "user_id=1" in location
        assert "identity_id=test-identity-id" in location

        # Verify service calls
        mock_oauth_service.exchange_code_for_tokens.assert_called_once_with("test-code")
        mock_integration_service.create_federated_user.assert_called_once()
        mock_user_repo.get_or_create_from_cognito.assert_called_once_with(mock_cognito_user)

    def test_google_callback_error_parameter(self, client):
        """Test Google OAuth callback with error parameter."""
        response = client.get("/auth/google/callback?error=access_denied&state=/dashboard")

        assert response.status_code == 307  # Redirect
        location = response.headers["location"]
        assert "error=oauth_error" in location
        assert "message=access_denied" in location

    def test_google_callback_missing_code(self, client):
        """Test Google OAuth callback without authorization code."""
        response = client.get("/auth/google/callback?state=/dashboard")

        assert response.status_code == 307  # Redirect
        location = response.headers["location"]
        assert "error=missing_code" in location

    @patch('api.routers.google_auth.UserRepository')
    @patch('api.routers.google_auth.get_cognito_google_service')
    @patch('api.routers.google_auth.get_google_oauth_service')
    def test_google_callback_federated_user_error(
        self,
        mock_google_service,
        mock_cognito_google_service,
        mock_user_repo_class,
        client,
        mock_google_token_data
    ):
        """Test Google OAuth callback when federated user creation fails."""
        # Mock Google OAuth service
        mock_oauth_service = Mock()
        mock_oauth_service.exchange_code_for_tokens = AsyncMock(return_value=mock_google_token_data)
        mock_google_service.return_value = mock_oauth_service

        # Mock Cognito Google integration service to return None (failure)
        mock_integration_service = Mock()
        mock_integration_service.create_federated_user = AsyncMock(return_value=None)
        mock_cognito_google_service.return_value = mock_integration_service

        response = client.get("/auth/google/callback?code=test-code&state=/dashboard")

        assert response.status_code == 307  # Redirect
        location = response.headers["location"]
        assert "error=federated_user_error" in location


class TestCognitoGoogleIntegrationService:
    """Test cases for Cognito Google integration service."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        with patch('services.cognito_google_integration.get_settings') as mock_settings:
            mock_settings.return_value.cognito_region = "us-east-1"
            mock_settings.return_value.cognito_user_pool_id = "test-pool-id"
            mock_settings.return_value.cognito_identity_pool_id = "test-identity-pool-id"

            with patch('services.cognito_google_integration.boto3.client'):
                return CognitoGoogleIntegrationService()

    @patch('services.cognito_google_integration.boto3.client')
    def test_create_federated_user_new_user(self, mock_boto_client, mock_google_user_info):
        """Test creating a new federated user."""
        # Mock Cognito IDP client
        mock_idp_client = Mock()
        mock_idp_client.admin_get_user.side_effect = Exception("UserNotFoundException")
        mock_idp_client.admin_create_user.return_value = {
            "User": {"Username": "test@example.com"}
        }
        mock_idp_client.admin_update_user_attributes.return_value = {}

        mock_boto_client.return_value = mock_idp_client

        service = CognitoGoogleIntegrationService()

        # Test the method
        import asyncio
        result = asyncio.run(service.create_federated_user(mock_google_user_info))

        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.sub == "google_google-user-123"

        # Verify Cognito calls
        mock_idp_client.admin_create_user.assert_called_once()
        mock_idp_client.admin_update_user_attributes.assert_called_once()

    @patch('services.cognito_google_integration.boto3.client')
    def test_create_federated_user_existing_user(self, mock_boto_client, mock_google_user_info):
        """Test linking Google identity to existing user."""
        # Mock Cognito IDP client
        mock_idp_client = Mock()
        mock_idp_client.admin_get_user.return_value = {
            "Username": "test@example.com",
            "UserAttributes": [
                {"Name": "sub", "Value": "existing-sub-123"},
                {"Name": "email", "Value": "test@example.com"},
                {"Name": "name", "Value": "Test User"},
                {"Name": "email_verified", "Value": "true"}
            ]
        }
        mock_idp_client.admin_update_user_attributes.return_value = {}

        mock_boto_client.return_value = mock_idp_client

        service = CognitoGoogleIntegrationService()

        # Test the method
        import asyncio
        result = asyncio.run(service.create_federated_user(mock_google_user_info))

        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.sub == "existing-sub-123"

        # Verify Cognito calls
        mock_idp_client.admin_get_user.assert_called_once()
        mock_idp_client.admin_update_user_attributes.assert_called_once()

    @patch('services.cognito_google_integration.boto3.client')
    def test_get_federated_credentials(self, mock_boto_client):
        """Test getting federated credentials."""
        # Mock Cognito Identity client
        mock_identity_client = Mock()
        mock_identity_client.get_id.return_value = {"IdentityId": "test-identity-id"}
        mock_identity_client.get_credentials_for_identity.return_value = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretKey": "test-secret-key",
                "SessionToken": "test-session-token",
                "Expiration": "2024-01-01T00:00:00Z"
            }
        }

        mock_boto_client.return_value = mock_identity_client

        service = CognitoGoogleIntegrationService()

        # Test the method
        import asyncio
        result = asyncio.run(service.get_federated_credentials("google-id-token"))

        assert result is not None
        assert result["identity_id"] == "test-identity-id"
        assert result["access_key_id"] == "test-access-key"
        assert result["secret_key"] == "test-secret-key"
        assert result["session_token"] == "test-session-token"

        # Verify Cognito calls
        mock_identity_client.get_id.assert_called_once()
        mock_identity_client.get_credentials_for_identity.assert_called_once()


class TestGoogleOAuthService:
    """Test cases for Google OAuth service."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        with patch('services.google_oauth.get_settings') as mock_settings:
            mock_settings.return_value.google_client_id = "test-client-id"
            mock_settings.return_value.google_client_secret = "test-client-secret"
            mock_settings.return_value.google_redirect_uri = "http://localhost:8000/auth/google/callback"
            return GoogleOAuthService()

    def test_get_authorization_url(self, service):
        """Test generating Google OAuth authorization URL."""
        url = service.get_authorization_url(state="/dashboard")

        assert "accounts.google.com/o/oauth2/auth" in url
        assert "client_id=test-client-id" in url
        assert "state=/dashboard" in url
        assert "scope=openid+email+profile" in url

    @patch('services.google_oauth.httpx.AsyncClient')
    @patch('services.google_oauth.id_token.verify_oauth2_token')
    def test_exchange_code_for_tokens(self, mock_verify_token, mock_http_client, service):
        """Test exchanging authorization code for tokens."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "google-access-token",
            "id_token": "google-id-token",
            "refresh_token": "google-refresh-token"
        }

        mock_client_instance = Mock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_http_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock ID token verification
        mock_verify_token.return_value = {
            "sub": "google-user-123",
            "email": "test@example.com",
            "email_verified": True
        }

        # Mock user info response
        mock_response.json.return_value = {
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg"
        }

        # Test the method
        import asyncio
        result = asyncio.run(service.exchange_code_for_tokens("test-code"))

        assert result is not None
        assert result["access_token"] == "google-access-token"
        assert result["id_token"] == "google-id-token"
        assert "user_info" in result
        assert result["user_info"]["email"] == "test@example.com"