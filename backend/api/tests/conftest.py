"""
Configuration globale pour les tests avec mocking des services AWS.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.cognito import CognitoUser


@pytest.fixture(scope="session", autouse=True)
def mock_aws_services():
    """Mock tous les services AWS pour éviter les dépendances externes."""
    with (
        patch("boto3.client") as mock_boto_client,
        patch("core.cognito.urlopen") as mock_urlopen,
        patch("core.cognito.settings.env", "test"),
    ):
        # Mock Cognito IDP client
        mock_idp_client = Mock()
        mock_idp_client.admin_get_user.return_value = {
            "Username": "test@example.com",
            "UserStatus": "CONFIRMED",
            "UserAttributes": [
                {"Name": "sub", "Value": "test-user-123"},
                {"Name": "email", "Value": "test@example.com"},
                {"Name": "name", "Value": "Test User"},
                {"Name": "email_verified", "Value": "true"},
            ],
        }
        mock_idp_client.admin_create_user.return_value = {
            "User": {"Username": "test@example.com"}
        }
        mock_idp_client.admin_update_user_attributes.return_value = {}
        mock_idp_client.get_user.return_value = {
            "Username": "test-user",
            "UserStatus": "CONFIRMED",
            "UserAttributes": [
                {"Name": "email", "Value": "test@example.com"},
                {"Name": "name", "Value": "Test User"},
            ],
        }

        # Mock Cognito Identity client
        mock_identity_client = Mock()
        mock_identity_client.get_id.return_value = {"IdentityId": "test-identity-id"}
        mock_identity_client.get_credentials_for_identity.return_value = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretKey": "test-secret-key",
                "SessionToken": "test-session-token",
                "Expiration": "2024-01-01T00:00:00Z",
            }
        }

        # Configure boto3.client to return appropriate mock based on service
        def mock_client_factory(service_name, **kwargs):
            if service_name == "cognito-idp":
                return mock_idp_client
            elif service_name == "cognito-identity":
                return mock_identity_client
            else:
                return Mock()

        mock_boto_client.side_effect = mock_client_factory

        # Mock JWKS response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "keys": [
                {
                    "kid": "test-key-id",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test-n-value",
                    "e": "AQAB",
                }
            ]
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        yield


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_cognito_user():
    """Utilisateur Cognito mocké pour les tests."""
    return CognitoUser(
        sub="test-user-123",
        email="test@example.com",
        name="Test User",
        email_verified=True,
        cognito_username="test@example.com",
    )


@pytest.fixture
def mock_unverified_cognito_user():
    """Utilisateur Cognito non vérifié pour les tests."""
    return CognitoUser(
        sub="test-user-123",
        email="test@example.com",
        name="Test User",
        email_verified=False,
        cognito_username="test@example.com",
    )


@pytest.fixture
def mock_jwt_token():
    """Token JWT mocké pour les tests."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


@pytest.fixture
def mock_google_user_info():
    """Informations utilisateur Google mockées."""
    return {
        "id": "google-user-123",
        "sub": "google-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "verified_email": True,
    }


@pytest.fixture(autouse=True)
def mock_database_dependencies():
    """Mock automatique des dépendances de base de données."""
    with (
        patch("api.routers.history.get_user_repo") as mock_user_repo,
        patch("api.routers.history.get_history_repo") as mock_history_repo,
    ):
        # Mock user repository
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_or_create_from_cognito = AsyncMock(
            return_value=Mock(id=1, email="test@example.com", name="Test User")
        )
        mock_user_repo.return_value = mock_user_repo_instance

        # Mock history repository
        mock_history_repo_instance = Mock()
        mock_history_repo_instance.get_user_stats = AsyncMock(
            return_value={
                "total_backtests": 5,
                "strategies_used": ["MovingAverage", "RSIReversion"],
                "avg_return": 0.15,
                "best_return": 0.25,
                "worst_return": -0.05,
                "avg_sharpe": 1.2,
                "total_monte_carlo_runs": 3,
            }
        )
        mock_history_repo_instance.get_user_history = AsyncMock(
            return_value=[
                Mock(
                    id=1,
                    strategy_name="MovingAverage",
                    symbol="AAPL",
                    total_return=0.15,
                    sharpe_ratio=1.2,
                    max_drawdown=-0.08,
                    created_at="2024-01-01T00:00:00Z",
                )
            ]
        )
        mock_history_repo_instance.create_backtest_result = AsyncMock(
            return_value=Mock(id=1)
        )
        mock_history_repo_instance.create_monte_carlo_result = AsyncMock(
            return_value=Mock(id=1)
        )
        
        mock_history_repo.return_value = mock_history_repo_instance

        yield


@pytest.fixture(autouse=True)
def mock_cognito_service():
    """Mock automatique du service Cognito."""
    with patch("core.auth_dependencies.get_cognito_service") as mock_get_service:
        mock_service = Mock()
        mock_service.verify_token.return_value = CognitoUser(
            sub="test-user-123",
            email="test@example.com",
            name="Test User",
            email_verified=True,
            cognito_username="test@example.com",
        )
        mock_get_service.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_data_service():
    """Mock du service de données pour les tests de backtest."""
    with patch("services.data_service.DataService") as mock_service:
        mock_instance = Mock()
        mock_instance.get_stock_data = AsyncMock(
            return_value={
                "symbol": "AAPL",
                "data": [
                    {"date": "2023-01-01", "close": 100.0},
                    {"date": "2023-01-02", "close": 101.0},
                    {"date": "2023-01-03", "close": 102.0},
                ]
            }
        )
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_user():
    """Mock user for history tests."""
    return Mock(
        id=1,
        email="test@example.com",
        name="Test User",
        cognito_sub="test-user-123"
    )


@pytest.fixture
def mock_history_entry():
    """Mock history entry for tests."""
    return Mock(
        id=1,
        strategy="sma_crossover",
        symbol="AAPL",
        total_return=15.5,
        sharpe_ratio=1.2,
        max_drawdown=-0.08,
        created_at="2024-01-01T00:00:00Z",
        user_id=1,
        status="completed",
        start_date="2023-01-01",
        end_date="2023-12-31",
        initial_capital=10000.0,
        num_runs=100,
        completed_at="2024-01-01T01:00:00Z",
        total_trades=10,
        execution_time_seconds=60.0,
        metrics=["return", "sharpe_ratio"],
        price_type="close",
        win_rate=0.6,
        gaussian_scale=0.01,
        datasets_used=["AAPL_data"],
        num_simulations=1000,
        monte_carlo_method="historical_bootstrap",
        sample_fraction=0.7,
        strategy_type="momentum",
        strategy_params={"window": 20},
        monte_carlo_runs=100,
        user=Mock(id=1, email="test@example.com", name="Test User"),
    )