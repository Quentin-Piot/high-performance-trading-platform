"""
Tests for Cognito authentication integration.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from api.main import app
from core.cognito import CognitoService, CognitoUser


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_cognito_user():
    """Mock Cognito user for testing."""
    return CognitoUser(
        sub="test-user-123",
        email="test@example.com",
        name="Test User",
        email_verified=True,
        cognito_username="test@example.com",
    )


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


class TestCognitoService:
    """Test cases for CognitoService."""

    def test_cognito_service_initialization(self):
        """Test CognitoService initialization."""
        service = CognitoService()
        assert service.region == "eu-west-3"  # Default from config
        assert service.cognito_client is not None

    @patch("core.cognito.settings.env", "production")
    @patch("core.cognito.urlopen")
    def test_get_jwks_success(self, mock_urlopen):
        """Test successful JWKS retrieval."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "keys": [
                    {
                        "kid": "test-key-id",
                        "kty": "RSA",
                        "use": "sig",
                        "n": "test-n",
                        "e": "AQAB",
                    }
                ]
            }
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service = CognitoService()
        service._jwks = None  # Reset cache
        jwks = service.get_jwks()

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        assert jwks["keys"][0]["kid"] == "test-key-id"

    @patch("core.cognito.settings.env", "production")
    @patch("core.cognito.urlopen")
    def test_get_jwks_failure(self, mock_urlopen):
        """Test JWKS retrieval failure."""
        mock_urlopen.side_effect = Exception("Network error")

        service = CognitoService()
        service._jwks = None  # Reset cache

        with pytest.raises(Exception, match="Network error"):
            service.get_jwks()

    def test_get_public_key_found(self):
        """Test getting public key when key ID matches."""
        service = CognitoService()
        service._jwks = {
            "keys": [{"kid": "key1", "kty": "RSA"}, {"kid": "key2", "kty": "RSA"}]
        }

        key = service.get_public_key({"kid": "key2"})
        assert key == {"kid": "key2", "kty": "RSA"}

    def test_get_public_key_not_found(self):
        """Test getting public key when key ID doesn't match."""
        service = CognitoService()
        service._jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}

        key = service.get_public_key({"kid": "nonexistent"})
        assert key is None

    @patch("core.cognito.jwt.decode")
    @patch("core.cognito.jwt.get_unverified_header")
    def test_verify_token_success(
        self, mock_get_header, mock_decode, mock_cognito_user
    ):
        """Test successful token verification."""
        mock_get_header.return_value = {"kid": "test-key"}
        mock_decode.return_value = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "name": "Test User",
            "email_verified": True,
            "cognito:username": "test@example.com",
        }

        service = CognitoService()
        service._jwks = {"keys": [{"kid": "test-key", "kty": "RSA"}]}

        user = service.verify_token("valid.jwt.token")

        assert user is not None
        assert user.sub == "test-user-123"
        assert user.email == "test@example.com"
        assert user.email_verified is True

    @patch("core.cognito.jwt.get_unverified_header")
    def test_verify_token_no_public_key(self, mock_get_header):
        """Test token verification when public key is not found."""
        mock_get_header.return_value = {"kid": "nonexistent-key"}

        service = CognitoService()
        service._jwks = {"keys": [{"kid": "different-key", "kty": "RSA"}]}

        user = service.verify_token("invalid.jwt.token")
        assert user is None

    @patch("core.cognito.jwt.decode")
    @patch("core.cognito.jwt.get_unverified_header")
    def test_verify_token_jwt_error(self, mock_get_header, mock_decode):
        """Test token verification with JWT error."""
        mock_get_header.return_value = {"kid": "test-key"}
        mock_decode.side_effect = jwt.JWTError("Invalid token")

        service = CognitoService()
        service._jwks = {"keys": [{"kid": "test-key", "kty": "RSA"}]}

        user = service.verify_token("invalid.jwt.token")
        assert user is None

    @patch("core.cognito.boto3.client")
    def test_get_user_info_success(self, mock_boto_client):
        """Test successful user info retrieval."""
        mock_client = Mock()
        mock_client.get_user.return_value = {
            "Username": "test-user",
            "UserStatus": "CONFIRMED",
            "UserAttributes": [
                {"Name": "email", "Value": "test@example.com"},
                {"Name": "name", "Value": "Test User"},
            ],
        }
        mock_boto_client.return_value = mock_client

        service = CognitoService()
        user_info = service.get_user_info("valid-access-token")

        assert user_info is not None
        assert user_info["username"] == "test-user"
        assert user_info["attributes"]["email"] == "test@example.com"


class TestAuthDependencies:
    """Test cases for authentication dependencies."""

    @patch("core.auth_dependencies.get_cognito_service")
    def test_get_current_user_success(
        self, mock_get_service, client, mock_cognito_user, mock_jwt_token
    ):
        """Test successful user authentication."""
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_service.return_value = mock_service

        # Mock the database dependencies as well
        with (
            patch("api.routers.history.get_user_repo") as mock_user_repo,
            patch("api.routers.history.get_history_repo") as mock_history_repo,
        ):
            mock_user_repo_instance = Mock()
            mock_user_repo_instance.get_or_create_from_cognito = AsyncMock(
                return_value=Mock(id=1)
            )
            mock_user_repo.return_value = mock_user_repo_instance

            mock_history_repo_instance = Mock()
            mock_history_repo_instance.get_user_stats = AsyncMock(
                return_value={
                    "total_backtests": 0,
                    "strategies_used": [],
                    "avg_return": None,
                    "best_return": None,
                    "worst_return": None,
                    "avg_sharpe": None,
                    "total_monte_carlo_runs": 0,
                }
            )
            mock_history_repo.return_value = mock_history_repo_instance

            response = client.get(
                "/api/v1/history/stats",
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            # Should succeed with proper authentication
            assert response.status_code == 200

    def test_get_current_user_no_token(self, client):
        """Test authentication failure without token."""
        response = client.get("/api/v1/history/stats")
        assert response.status_code == 403  # FastAPI returns 403 for missing auth

    @patch("core.auth_dependencies.get_cognito_service")
    def test_get_current_user_invalid_token(
        self, mock_get_service, client, mock_jwt_token
    ):
        """Test authentication failure with invalid token."""
        mock_service = Mock()
        mock_service.verify_token.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/history/stats",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
        )

        assert response.status_code == 401
        assert "Invalid authentication token" in response.json()["detail"]

    @patch("core.auth_dependencies.get_cognito_service")
    def test_require_verified_email_success(
        self, mock_get_service, client, mock_jwt_token
    ):
        """Test verified email requirement with verified user."""
        mock_user = CognitoUser(
            sub="test-user-123",
            email="test@example.com",
            name="Test User",
            email_verified=True,
            cognito_username="test@example.com",
        )

        mock_service = Mock()
        mock_service.verify_token.return_value = mock_user
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/history/stats",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
        )

        # Should not fail due to email verification
        assert (
            response.status_code != 403
            or "Email verification required" not in response.json().get("detail", "")
        )

    @patch("core.auth_dependencies.get_cognito_service")
    def test_require_verified_email_failure(
        self, mock_get_service, client, mock_jwt_token
    ):
        """Test verified email requirement with unverified user."""
        mock_user = CognitoUser(
            sub="test-user-123",
            email="test@example.com",
            name="Test User",
            email_verified=False,  # Not verified
            cognito_username="test@example.com",
        )

        mock_service = Mock()
        mock_service.verify_token.return_value = mock_user
        mock_get_service.return_value = mock_service

        # Mock the database dependencies to avoid other errors
        with (
            patch("api.routers.history.get_user_repo") as mock_user_repo,
            patch("api.routers.history.get_history_repo") as mock_history_repo,
        ):
            mock_user_repo_instance = Mock()
            mock_user_repo_instance.get_or_create_from_cognito = AsyncMock(
                return_value=Mock(id=1)
            )
            mock_user_repo.return_value = mock_user_repo_instance

            mock_history_repo_instance = Mock()
            mock_history_repo_instance.get_user_stats = AsyncMock(return_value={})
            mock_history_repo.return_value = mock_history_repo_instance

            response = client.get(
                "/api/v1/history/stats",
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

        assert response.status_code == 403
        assert "Email verification required" in response.json()["detail"]


class TestCognitoUser:
    """Test cases for CognitoUser model."""

    def test_cognito_user_creation(self):
        """Test CognitoUser model creation."""
        user = CognitoUser(
            sub="test-123",
            email="test@example.com",
            name="Test User",
            email_verified=True,
            cognito_username="testuser",
        )

        assert user.sub == "test-123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.email_verified is True
        assert user.cognito_username == "testuser"

    def test_cognito_user_optional_fields(self):
        """Test CognitoUser with optional fields."""
        user = CognitoUser(
            sub="test-123", email="test@example.com", cognito_username="testuser"
        )

        assert user.sub == "test-123"
        assert user.email == "test@example.com"
        assert user.name is None
        assert user.email_verified is False  # Default value
        assert user.cognito_username == "testuser"
