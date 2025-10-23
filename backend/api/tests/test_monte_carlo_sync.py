"""
Tests for synchronous Monte Carlo simulation endpoint.

This module tests the new synchronous Monte Carlo endpoint that executes
simulations directly without using the queue system.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from core.simple_auth import SimpleUser, get_current_user_simple
from infrastructure.db import get_session


@pytest.fixture
def mock_simple_user():
    """Mock simple user for testing."""
    return SimpleUser(id=1, email="test@example.com", sub="1")


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def authenticated_client(mock_simple_user, mock_session):
    """Create a test client with mocked authentication."""
    
    async def mock_get_current_user():
        return mock_simple_user
    
    async def mock_get_session():
        return mock_session
    
    # Override dependencies
    app.dependency_overrides[get_current_user_simple] = mock_get_current_user
    app.dependency_overrides[get_session] = mock_get_session
    
    client = TestClient(app)
    
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


class TestSynchronousMonteCarlo:
    """Test synchronous Monte Carlo simulation endpoint."""

    def test_sync_monte_carlo_basic(self, authenticated_client):
        """Test basic synchronous Monte Carlo simulation."""
        params = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",
            "end_date": "2017-01-31T00:00:00",
            "num_runs": 5,
            "initial_capital": 10000.0,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = authenticated_client.post("/api/v1/monte-carlo/run", params=params)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "results" in data
        assert "aggregated_metrics" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 1

        # Verify first result structure
        result = data["results"][0]
        assert "filename" in result
        assert "method" in result
        assert "runs" in result
        assert "successful_runs" in result
        assert "metrics_distribution" in result
        assert result["runs"] == 5

    def test_sync_monte_carlo_invalid_symbol(self, authenticated_client):
        """Test Monte Carlo with invalid symbol."""
        params = {
            "symbol": "INVALID",
            "start_date": "2017-01-01T00:00:00",
            "end_date": "2017-01-31T00:00:00",
            "num_runs": 5,
            "initial_capital": 10000.0,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = authenticated_client.post("/api/v1/monte-carlo/run", params=params)

        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]

    def test_sync_monte_carlo_invalid_date_range(self, authenticated_client):
        """Test Monte Carlo with invalid date range."""
        params = {
            "symbol": "aapl",
            "start_date": "2025-01-01T00:00:00",  # Future date
            "end_date": "2025-01-31T00:00:00",
            "num_runs": 5,
            "initial_capital": 10000.0,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = authenticated_client.post("/api/v1/monte-carlo/run", params=params)

        assert response.status_code == 400

    def test_sync_monte_carlo_end_date_before_start_date(self, authenticated_client):
        """Test Monte Carlo with end date before start date."""
        params = {
            "symbol": "aapl",
            "start_date": "2017-01-31T00:00:00",
            "end_date": "2017-01-01T00:00:00",  # End before start
            "num_runs": 5,
            "initial_capital": 10000.0,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = authenticated_client.post("/api/v1/monte-carlo/run", params=params)

        assert response.status_code == 400
        assert "End date must be after start date" in response.json()["detail"]

    def test_sync_monte_carlo_zero_runs(self, authenticated_client):
        """Test Monte Carlo with zero runs."""
        params = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",
            "end_date": "2017-01-31T00:00:00",
            "num_runs": 0,  # Invalid
            "initial_capital": 10000.0,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = authenticated_client.post("/api/v1/monte-carlo/run", params=params)

        assert response.status_code == 422  # Validation error

    def test_sync_monte_carlo_negative_capital(self, authenticated_client):
        """Test Monte Carlo with negative capital."""
        params = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",
            "end_date": "2017-01-31T00:00:00",
            "num_runs": 5,
            "initial_capital": -1000.0,  # Invalid
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = authenticated_client.post("/api/v1/monte-carlo/run", params=params)

        assert response.status_code == 422  # Validation error

    def test_sync_monte_carlo_unauthorized(self):
        """Test Monte Carlo without authentication."""
        client = TestClient(app)
        
        params = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",
            "end_date": "2017-01-31T00:00:00",
            "num_runs": 5,
            "initial_capital": 10000.0,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 30,
        }

        response = client.post("/api/v1/monte-carlo/run", params=params)
        assert response.status_code == 403


class TestSymbolDateRanges:
    """Test symbol date ranges endpoint."""

    def test_get_symbol_date_ranges(self):
        """Test getting available symbol date ranges."""
        client = TestClient(app)
        response = client.get("/api/v1/monte-carlo/symbols/date-ranges")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "symbols" in data
        assert isinstance(data["symbols"], list)
        
        # Should have at least one symbol
        assert len(data["symbols"]) > 0
        
        # Check structure of first symbol
        if data["symbols"]:
            symbol = data["symbols"][0]
            assert "symbol" in symbol
            assert "min_date" in symbol
            assert "max_date" in symbol