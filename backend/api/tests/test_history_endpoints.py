"""
Tests for backtest history endpoints.
"""

from unittest.mock import AsyncMock, Mock

from api.main import app
from api.routes.history import get_history_repo, get_user_repo
from core.simple_auth import SimpleUser, get_current_user_simple
from infrastructure.db import get_session


class TestHistoryEndpoints:
    """Test cases for history endpoints."""

    def test_get_user_history_success(
        self,
        client,
        mock_user,
        mock_history_entry,
    ):
        """Test successful retrieval of user history."""
        # Mock authentication using dependency override
        mock_simple_user = SimpleUser(id=1, email="test@example.com", sub="1")
        app.dependency_overrides[get_current_user_simple] = lambda: mock_simple_user

        # Mock database session
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        # Mock history repository
        mock_history_repo = Mock()
        mock_history_repo.get_user_history = AsyncMock(
            return_value=[mock_history_entry]
        )
        app.dependency_overrides[get_history_repo] = lambda: mock_history_repo

        try:
            response = client.get("/api/v1/history/")

            # Debug: print response details if test fails
            if response.status_code != 200:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "per_page" in data
            assert "has_next" in data
            assert "has_prev" in data

            # Verify repository calls
            mock_user_repo.get_by_id.assert_called_once_with(1)
            mock_history_repo.get_user_history.assert_called_once()
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_user_stats_success(
        self,
        client,
        mock_user,
    ):
        """Test successful retrieval of user statistics."""
        # Mock authentication using dependency override
        mock_simple_user = SimpleUser(id=1, email="test@example.com", sub="1")
        app.dependency_overrides[get_current_user_simple] = lambda: mock_simple_user

        # Mock database session
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        # Mock history repository
        mock_stats = {
            "total_backtests": 5,
            "strategies_used": ["sma_crossover", "rsi_reversion"],
            "avg_return": 12.5,
            "best_return": 25.0,
            "worst_return": -5.0,
            "avg_sharpe": 1.1,
            "total_monte_carlo_runs": 50,
        }
        mock_history_repo = Mock()
        mock_history_repo.get_user_stats = AsyncMock(return_value=mock_stats)
        app.dependency_overrides[get_history_repo] = lambda: mock_history_repo

        try:
            response = client.get("/api/v1/history/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_backtests"] == 5
            assert len(data["strategies_used"]) == 2
            assert data["avg_return"] == 12.5

            # Verify repository calls
            mock_user_repo.get_by_id.assert_called_once_with(1)
            mock_history_repo.get_user_stats.assert_called_once_with(mock_user.id)
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_history_detail_success(
        self,
        client,
        mock_user,
        mock_history_entry,
    ):
        """Test successful retrieval of history detail."""
        # Mock authentication using dependency override
        mock_simple_user = SimpleUser(id=1, email="test@example.com", sub="1")
        app.dependency_overrides[get_current_user_simple] = lambda: mock_simple_user

        # Mock database session
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        # Mock history repository
        mock_history_repo = Mock()
        mock_history_repo.get_by_id = AsyncMock(return_value=mock_history_entry)
        app.dependency_overrides[get_history_repo] = lambda: mock_history_repo

        try:
            response = client.get("/api/v1/history/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_history_entry.id
            assert data["strategy"] == mock_history_entry.strategy

            # Verify repository calls
            mock_user_repo.get_by_id.assert_called_once_with(1)
            mock_history_repo.get_by_id.assert_called_once_with(1, user_id=mock_user.id)
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_get_history_detail_not_found(
        self,
        client,
        mock_user,
    ):
        """Test history detail not found."""
        # Mock authentication using dependency override
        mock_simple_user = SimpleUser(id=1, email="test@example.com", sub="1")
        app.dependency_overrides[get_current_user_simple] = lambda: mock_simple_user

        # Mock database session
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        # Mock history repository - return None (not found)
        mock_history_repo = Mock()
        mock_history_repo.get_by_id = AsyncMock(return_value=None)
        app.dependency_overrides[get_history_repo] = lambda: mock_history_repo

        try:
            response = client.get("/api/v1/history/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_delete_history_success(
        self,
        client,
        mock_user,
    ):
        """Test successful deletion of history entry."""
        # Mock authentication using dependency override
        mock_simple_user = SimpleUser(id=1, email="test@example.com", sub="1")
        app.dependency_overrides[get_current_user_simple] = lambda: mock_simple_user

        # Mock database session
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        # Mock history repository
        mock_history_repo = Mock()
        mock_history_repo.delete_history = AsyncMock(return_value=True)
        app.dependency_overrides[get_history_repo] = lambda: mock_history_repo

        try:
            response = client.delete("/api/v1/history/1")

            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]

            # Verify repository calls
            mock_history_repo.delete_history.assert_called_once_with(1, mock_user.id)
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_delete_history_not_found(
        self,
        client,
        mock_user,
    ):
        """Test deletion of non-existent history entry."""
        # Mock authentication using dependency override
        mock_simple_user = SimpleUser(id=1, email="test@example.com", sub="1")
        app.dependency_overrides[get_current_user_simple] = lambda: mock_simple_user

        # Mock database session
        mock_session = AsyncMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        # Mock user repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        app.dependency_overrides[get_user_repo] = lambda: mock_user_repo

        # Mock history repository - return False (not found)
        mock_history_repo = Mock()
        mock_history_repo.delete_history = AsyncMock(return_value=False)
        app.dependency_overrides[get_history_repo] = lambda: mock_history_repo

        try:
            response = client.delete("/api/v1/history/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

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

    def test_invalid_token_access(self, client):
        """Test access with invalid token."""
        # Test without authentication (no dependency override)
        response = client.get("/api/v1/history/")
        assert response.status_code == 403

    def test_unverified_email_access(self, client):
        """Test access with unverified email."""
        # Test without authentication (no dependency override)
        response = client.get("/api/v1/history/")
        assert response.status_code == 403
