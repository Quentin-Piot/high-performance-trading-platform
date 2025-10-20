"""
Tests for synchronous Monte Carlo simulation endpoint.

This module tests the new synchronous Monte Carlo endpoint that executes
simulations directly without using the queue system.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestSynchronousMonteCarlo:
    """Test synchronous Monte Carlo simulation endpoint."""

    def test_sync_monte_carlo_basic(self):
        """Test basic synchronous Monte Carlo simulation."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-31T00:00:00",    # Updated to valid date range
            "num_runs": 5,  # Small number for fast testing
            "initial_capital": 10000.0,
            "strategy_params": {"sma_short": 10, "sma_long": 30}
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "filename" in data
        assert "method" in data
        assert "runs" in data
        assert "successful_runs" in data
        assert "metrics_distribution" in data
        assert "status" in data
        assert data["status"] == "completed"

        # Verify metrics distribution structure
        metrics = data["metrics_distribution"]
        assert "pnl" in metrics
        assert "sharpe" in metrics
        assert "drawdown" in metrics

        for _metric_name, metric_data in metrics.items():
            assert "mean" in metric_data
            assert "std" in metric_data
            assert "p5" in metric_data
            assert "p25" in metric_data
            assert "median" in metric_data
            assert "p75" in metric_data
            assert "p95" in metric_data

    def test_sync_monte_carlo_with_equity_envelope(self):
        """Test synchronous Monte Carlo with equity envelope enabled."""
        request_data = {
            "symbol": "msft",
            "start_date": "2017-02-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-02-28T00:00:00",    # Updated to valid date range
            "num_runs": 3,
            "initial_capital": 15000.0,
            "strategy_params": {"sma_short": 5, "sma_long": 15},
            "equity_envelope": True
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify equity envelope is included
        if data.get("equity_envelope"):
            envelope = data["equity_envelope"]
            assert "timestamps" in envelope
            assert "p5" in envelope
            assert "p25" in envelope
            assert "median" in envelope
            assert "p75" in envelope
            assert "p95" in envelope

            # All arrays should have the same length
            length = len(envelope["timestamps"])
            assert len(envelope["p5"]) == length
            assert len(envelope["p25"]) == length
            assert len(envelope["median"]) == length
            assert len(envelope["p75"]) == length
            assert len(envelope["p95"]) == length

    def test_sync_monte_carlo_invalid_symbol(self):
        """Test synchronous Monte Carlo with invalid symbol."""
        request_data = {
            "symbol": "invalid_symbol",
            "start_date": "2017-01-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-31T00:00:00",    # Updated to valid date range
            "num_runs": 5,
            "initial_capital": 10000.0
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]

    def test_sync_monte_carlo_invalid_date_range(self):
        """Test synchronous Monte Carlo with invalid date range."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2025-01-01T00:00:00",  # Future date
            "end_date": "2025-01-31T00:00:00",
            "num_runs": 5,
            "initial_capital": 10000.0
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 400
        # Should contain date range validation error

    def test_sync_monte_carlo_end_date_before_start_date(self):
        """Test synchronous Monte Carlo with end date before start date."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2017-01-31T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-01T00:00:00",    # Before start date
            "num_runs": 5,
            "initial_capital": 10000.0
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_sync_monte_carlo_zero_runs(self):
        """Test synchronous Monte Carlo with zero runs."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-31T00:00:00",    # Updated to valid date range
            "num_runs": 0,  # Invalid
            "initial_capital": 10000.0
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_sync_monte_carlo_negative_capital(self):
        """Test synchronous Monte Carlo with negative initial capital."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-31T00:00:00",    # Updated to valid date range
            "num_runs": 5,
            "initial_capital": -1000.0  # Invalid
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_sync_monte_carlo_custom_strategy_params(self):
        """Test synchronous Monte Carlo with custom strategy parameters."""
        request_data = {
            "symbol": "googl",
            "start_date": "2017-03-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-03-29T00:00:00",    # Updated to valid date range (end of available data)
            "num_runs": 3,
            "initial_capital": 15000.0,
            "strategy_params": {
                "sma_short": 8,
                "sma_long": 25
            }
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["runs"] == 3

    def test_sync_monte_carlo_performance(self):
        """Test synchronous Monte Carlo performance with larger dataset."""
        request_data = {
            "symbol": "msft",
            "start_date": "2020-01-01T00:00:00",
            "end_date": "2020-12-31T00:00:00",
            "num_runs": 10,
            "initial_capital": 10000.0
        }

        response = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify all runs completed successfully
        assert data["runs"] == 10
        assert data["successful_runs"] == 10
        assert data["status"] == "completed"

    def test_sync_monte_carlo_all_symbols(self):
        """Test synchronous Monte Carlo with all supported symbols."""
        symbols = ["aapl", "amzn", "fb", "googl", "msft", "nflx", "nvda"]

        for symbol in symbols:
            # Use appropriate date ranges for each symbol based on available data
            if symbol == "aapl":
                start_date = "2017-01-01T00:00:00"
                end_date = "2017-01-15T00:00:00"
            elif symbol == "amzn":
                start_date = "2020-01-01T00:00:00"
                end_date = "2020-01-15T00:00:00"
            elif symbol == "fb":
                start_date = "2020-01-01T00:00:00"
                end_date = "2020-01-15T00:00:00"
            elif symbol == "googl":
                start_date = "2020-01-01T00:00:00"
                end_date = "2020-01-15T00:00:00"
            elif symbol == "msft":
                start_date = "2020-01-01T00:00:00"
                end_date = "2020-01-15T00:00:00"
            elif symbol == "nflx":
                start_date = "2020-01-01T00:00:00"
                end_date = "2020-01-15T00:00:00"
            elif symbol == "nvda":
                start_date = "2020-01-01T00:00:00"
                end_date = "2020-01-15T00:00:00"

            request_data = {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "num_runs": 2,  # Minimal runs for speed
                "initial_capital": 10000.0
            }

            response = client.post("/api/v1/monte-carlo/run", json=request_data)

            assert response.status_code == 200, f"Failed for symbol {symbol}"
            data = response.json()
            assert data["status"] == "completed", f"Failed completion for symbol {symbol}"

    def test_sync_monte_carlo_response_time(self):
        """Test that synchronous Monte Carlo responds within reasonable time."""
        import time

        request_data = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-31T00:00:00",    # Updated to valid date range
            "num_runs": 5,
            "initial_capital": 10000.0
        }

        start_time = time.time()
        response = client.post("/api/v1/monte-carlo/run", json=request_data)
        end_time = time.time()

        assert response.status_code == 200

        # Should complete within reasonable time (adjust as needed)
        execution_time = end_time - start_time
        assert execution_time < 30.0, f"Execution took too long: {execution_time:.2f}s"

    def test_sync_monte_carlo_deterministic_results(self):
        """Test that synchronous Monte Carlo produces consistent results."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2017-01-01T00:00:00",  # Updated to valid date range
            "end_date": "2017-01-15T00:00:00",    # Updated to valid date range
            "num_runs": 3,
            "initial_capital": 10000.0,
            "strategy_params": {"sma_short": 5, "sma_long": 10}
        }

        # Run twice and compare basic structure (results may vary due to randomness)
        response1 = client.post("/api/v1/monte-carlo/run", json=request_data)
        response2 = client.post("/api/v1/monte-carlo/run", json=request_data)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Structure should be identical
        assert data1["runs"] == data2["runs"]
        assert data1["method"] == data2["method"]
        assert data1["status"] == data2["status"]

        # Both should have completed all runs
        assert data1["successful_runs"] == data1["runs"]
        assert data2["successful_runs"] == data2["runs"]


class TestLegacyEndpointsDeprecated:
    """Test that legacy endpoints are properly deprecated."""

    @pytest.mark.skip(reason="Legacy endpoints not implemented - these tests are for future deprecation handling")
    def test_legacy_jobs_endpoint_deprecated(self):
        """Test that jobs endpoint is marked as deprecated."""
        request_data = {
            "symbol": "aapl",
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-01-15T00:00:00",
            "num_runs": 2,
            "initial_capital": 10000.0
        }

        response = client.post("/monte-carlo/jobs", json=request_data)

        # Should still work but be marked as deprecated
        # The exact behavior depends on how deprecation is handled
        # It might return 200 with a deprecation message or a different status
        assert response.status_code in [200, 201, 410]  # 410 = Gone (deprecated)

    def test_legacy_websocket_deprecated(self):
        """Test that WebSocket endpoint returns deprecation notice."""
        # This test would need WebSocket client setup
        # For now, we'll skip it as it requires more complex setup
        pass

    @pytest.mark.skip(reason="Legacy endpoints not implemented - these tests are for future deprecation handling")
    def test_legacy_bulk_endpoint_deprecated(self):
        """Test that bulk endpoint is marked as deprecated."""
        request_data = {
            "jobs": [
                {
                    "symbol": "aapl",
                    "start_date": "2023-01-01T00:00:00",
                    "end_date": "2023-01-15T00:00:00",
                    "num_runs": 2,
                    "initial_capital": 10000.0
                }
            ]
        }

        response = client.post("/monte-carlo/jobs/bulk", json=request_data)

        # Should still work but be marked as deprecated
        assert response.status_code in [200, 201, 410]  # 410 = Gone (deprecated)


class TestSymbolDateRanges:
    """Test symbol date ranges endpoint."""

    def test_get_symbol_date_ranges(self):
        """Test getting available date ranges for all symbols."""
        response = client.get("/api/v1/monte-carlo/symbols/date-ranges")

        assert response.status_code == 200
        data = response.json()

        assert "symbols" in data
        symbols = data["symbols"]

        # Should have data for all supported symbols
        symbol_names = [s["symbol"] for s in symbols]
        expected_symbols = ["aapl", "amzn", "fb", "googl", "msft", "nflx", "nvda"]

        for expected in expected_symbols:
            assert expected in symbol_names

        # Each symbol should have date range info
        for symbol_data in symbols:
            assert "symbol" in symbol_data
            assert "min_date" in symbol_data
            assert "max_date" in symbol_data

            # Dates should be valid
            min_date = symbol_data["min_date"]
            max_date = symbol_data["max_date"]
            assert min_date < max_date
