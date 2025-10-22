"""
Tests for backtest history endpoints.
"""
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.cognito import CognitoUser
from infrastructure.models import BacktestHistory, User


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
        cognito_username="test@example.com"
    )


@pytest.fixture
def mock_user():
    """Mock database user."""
    user = Mock(spec=User)
    user.id = 1
    user.cognito_sub = "test-user-123"
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def mock_history_entry():
    """Mock backtest history entry."""
    history = Mock(spec=BacktestHistory)
    history.id = 1
    history.user_id = 1
    history.strategy = "sma_crossover"
    history.strategy_params = {"sma_short": 10, "sma_long": 30}
    history.start_date = "2023-01-01"
    history.end_date = "2023-12-31"
    history.initial_capital = 10000.0
    history.monte_carlo_runs = 1
    history.monte_carlo_method = None
    history.sample_fraction = None
    history.gaussian_scale = None
    history.datasets_used = ["AAPL"]
    history.price_type = "close"
    history.total_return = 15.5
    history.sharpe_ratio = 1.2
    history.max_drawdown = -8.3
    history.win_rate = 65.0
    history.total_trades = 42
    history.execution_time_seconds = 2.5
    history.status = "completed"
    history.created_at = datetime(2023, 1, 1, 12, 0, 0)
    history.completed_at = datetime(2023, 1, 1, 12, 0, 3)
    return history


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


class TestHistoryEndpoints:
    """Test cases for history endpoints."""

    @patch('api.routers.history.get_history_repo')
    @patch('api.routers.history.get_user_repo')
    @patch('core.auth_dependencies.get_cognito_service')
    def test_get_user_history_success(
        self,
        mock_get_cognito_service,
        mock_get_user_repo,
        mock_get_history_repo,
        client,
        mock_cognito_user,
        mock_user,
        mock_history_entry,
        mock_jwt_token
    ):
        """Test successful retrieval of user history."""
        # Mock authentication
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_cognito_service.return_value = mock_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_user)
        mock_get_user_repo.return_value = mock_user_repo

        # Mock history repository
        mock_history_repo = Mock()
        mock_history_repo.get_user_history = AsyncMock(return_value=[mock_history_entry])
        mock_get_history_repo.return_value = mock_history_repo

        response = client.get(
            "/api/v1/history/",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "has_next" in data
        assert "has_prev" in data

        # Verify repository calls
        mock_user_repo.get_or_create_from_cognito.assert_called_once_with(mock_cognito_user)
        mock_history_repo.get_user_history.assert_called_once()

    @patch('api.routers.history.get_history_repo')
    @patch('api.routers.history.get_user_repo')
    @patch('core.auth_dependencies.get_cognito_service')
    def test_get_user_stats_success(
        self,
        mock_get_cognito_service,
        mock_get_user_repo,
        mock_get_history_repo,
        client,
        mock_cognito_user,
        mock_user,
        mock_jwt_token
    ):
        """Test successful retrieval of user statistics."""
        # Mock authentication
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_cognito_service.return_value = mock_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_user)
        mock_get_user_repo.return_value = mock_user_repo

        # Mock history repository
        mock_stats = {
            "total_backtests": 5,
            "strategies_used": ["sma_crossover", "rsi_reversion"],
            "avg_return": 12.5,
            "best_return": 25.0,
            "worst_return": -5.0,
            "avg_sharpe": 1.1,
            "total_monte_carlo_runs": 50
        }
        mock_history_repo = Mock()
        mock_history_repo.get_user_stats = AsyncMock(return_value=mock_stats)
        mock_get_history_repo.return_value = mock_history_repo

        response = client.get(
            "/api/v1/history/stats",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_backtests"] == 5
        assert len(data["strategies_used"]) == 2
        assert data["avg_return"] == 12.5

        # Verify repository calls
        mock_history_repo.get_user_stats.assert_called_once_with(mock_user.id)

    @patch('api.routers.history.get_history_repo')
    @patch('api.routers.history.get_user_repo')
    @patch('core.auth_dependencies.get_cognito_service')
    def test_get_history_detail_success(
        self,
        mock_get_cognito_service,
        mock_get_user_repo,
        mock_get_history_repo,
        client,
        mock_cognito_user,
        mock_user,
        mock_history_entry,
        mock_jwt_token
    ):
        """Test successful retrieval of history detail."""
        # Mock authentication
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_cognito_service.return_value = mock_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_user)
        mock_get_user_repo.return_value = mock_user_repo

        # Mock history repository
        mock_history_repo = Mock()
        mock_history_repo.get_by_id = AsyncMock(return_value=mock_history_entry)
        mock_get_history_repo.return_value = mock_history_repo

        response = client.get(
            "/api/v1/history/1",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["strategy"] == "sma_crossover"
        assert data["total_return"] == 15.5

        # Verify repository calls
        mock_history_repo.get_by_id.assert_called_once_with(1, user_id=mock_user.id)

    @patch('api.routers.history.get_history_repo')
    @patch('api.routers.history.get_user_repo')
    @patch('core.auth_dependencies.get_cognito_service')
    def test_get_history_detail_not_found(
        self,
        mock_get_cognito_service,
        mock_get_user_repo,
        mock_get_history_repo,
        client,
        mock_cognito_user,
        mock_user,
        mock_jwt_token
    ):
        """Test history detail not found."""
        # Mock authentication
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_cognito_service.return_value = mock_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_user)
        mock_get_user_repo.return_value = mock_user_repo

        # Mock history repository - return None (not found)
        mock_history_repo = Mock()
        mock_history_repo.get_by_id = AsyncMock(return_value=None)
        mock_get_history_repo.return_value = mock_history_repo

        response = client.get(
            "/api/v1/history/999",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('api.routers.history.get_history_repo')
    @patch('api.routers.history.get_user_repo')
    @patch('core.auth_dependencies.get_cognito_service')
    def test_delete_history_success(
        self,
        mock_get_cognito_service,
        mock_get_user_repo,
        mock_get_history_repo,
        client,
        mock_cognito_user,
        mock_user,
        mock_jwt_token
    ):
        """Test successful deletion of history entry."""
        # Mock authentication
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_cognito_service.return_value = mock_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_user)
        mock_get_user_repo.return_value = mock_user_repo

        # Mock history repository
        mock_history_repo = Mock()
        mock_history_repo.delete_history = AsyncMock(return_value=True)
        mock_get_history_repo.return_value = mock_history_repo

        response = client.delete(
            "/api/v1/history/1",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify repository calls
        mock_history_repo.delete_history.assert_called_once_with(1, mock_user.id)

    @patch('api.routers.history.get_history_repo')
    @patch('api.routers.history.get_user_repo')
    @patch('core.auth_dependencies.get_cognito_service')
    def test_delete_history_not_found(
        self,
        mock_get_cognito_service,
        mock_get_user_repo,
        mock_get_history_repo,
        client,
        mock_cognito_user,
        mock_user,
        mock_jwt_token
    ):
        """Test deletion of non-existent history entry."""
        # Mock authentication
        mock_service = Mock()
        mock_service.verify_token.return_value = mock_cognito_user
        mock_get_cognito_service.return_value = mock_service

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_or_create_from_cognito = AsyncMock(return_value=mock_user)
        mock_get_user_repo.return_value = mock_user_repo

        # Mock history repository - return False (not found/deleted)
        mock_history_repo = Mock()
        mock_history_repo.delete_history = AsyncMock(return_value=False)
        mock_get_history_repo.return_value = mock_history_repo

        response = client.delete(
            "/api/v1/history/999",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints."""
        # Test without token
        response = client.get("/api/v1/history/")
        assert response.status_code == 403

        response = client.get("/api/v1/history/stats")
        assert response.status_code == 403

        response = client.get("/api/v1/history/1")
        assert response.status_code == 403

        response = client.delete("/api/v1/history/1")
        assert response.status_code == 403

    @patch('core.auth_dependencies.get_cognito_service')
    def test_invalid_token_access(self, mock_get_cognito_service, client, mock_jwt_token):
        """Test access with invalid token."""
        # Mock authentication failure
        mock_service = Mock()
        mock_service.verify_token.return_value = None
        mock_get_cognito_service.return_value = mock_service

        response = client.get(
            "/api/v1/history/",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 401
        assert "Invalid authentication token" in response.json()["detail"]

    @patch('core.auth_dependencies.get_cognito_service')
    def test_unverified_email_access(self, mock_get_cognito_service, client, mock_jwt_token):
        """Test access with unverified email."""
        # Mock user with unverified email
        unverified_user = CognitoUser(
            sub="test-user-123",
            email="test@example.com",
            name="Test User",
            email_verified=False,  # Not verified
            cognito_username="test@example.com"
        )

        mock_service = Mock()
        mock_service.verify_token.return_value = unverified_user
        mock_get_cognito_service.return_value = mock_service

        response = client.get(
            "/api/v1/history/",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 403
        assert "Email verification required" in response.json()["detail"]
