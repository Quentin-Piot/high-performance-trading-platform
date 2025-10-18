from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.mc_backtest_service import (
    MetricsDistribution,
    MonteCarloSummary,
    bootstrap_returns_to_prices,
    gaussian_noise_returns_to_prices,
    monte_carlo_worker,
    run_monte_carlo_on_df,
)

client = TestClient(app)


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    # Create a simple upward trending price series with some volatility
    np.random.seed(42)
    prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 100)))
    return pd.DataFrame({"date": dates, "close": prices})


@pytest.fixture
def sample_csv_bytes(sample_price_data):
    """Convert sample data to CSV bytes."""
    csv_buffer = BytesIO()
    sample_price_data.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()


def test_bootstrap_returns_to_prices():
    """Test bootstrap resampling of returns."""
    # Create simple price series
    prices = pd.Series([100, 101, 102, 101, 103, 104])
    rng = np.random.RandomState(42)

    # Bootstrap with full sample
    new_prices = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng)

    # Should have same length
    assert len(new_prices) == len(prices)
    # Should start with same initial price
    assert new_prices.iloc[0] == prices.iloc[0]
    # Should be different from original (with high probability)
    assert not new_prices.equals(prices)


def test_gaussian_noise_returns_to_prices():
    """Test Gaussian noise addition to returns."""
    prices = pd.Series([100, 101, 102, 101, 103, 104])
    rng = np.random.RandomState(42)

    # Add noise
    new_prices = gaussian_noise_returns_to_prices(prices, scale=1.0, rng=rng)

    # Should have same length
    assert len(new_prices) == len(prices)
    # Should start with same initial price
    assert new_prices.iloc[0] == prices.iloc[0]
    # Should be different from original
    assert not new_prices.equals(prices)


def test_monte_carlo_worker():
    """Test Monte Carlo worker function."""
    # Create sample DataFrame
    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))))
    df = pd.DataFrame({"close": prices}, index=dates)

    # Test SMA strategy
    args = {
        "df": df,
        "strategy_name": "sma_crossover",
        "strategy_params": {"sma_short": 5, "sma_long": 20},
        "method": "bootstrap",
        "method_params": {"sample_fraction": 1.0},
        "rng_seed": 42,
    }

    result = monte_carlo_worker(args)

    # Should return metrics
    assert result is not None
    assert result.pnl is not None
    assert result.sharpe is not None
    assert result.drawdown is not None
    assert isinstance(result.pnl, float)
    assert isinstance(result.sharpe, float)
    assert isinstance(result.drawdown, float)


def test_run_monte_carlo_on_df(sample_csv_bytes):
    """Test full Monte Carlo orchestration."""
    # Progress callback
    progress_calls = []
    def progress_callback(processed, total):
        progress_calls.append((processed, total))

    # Run Monte Carlo with small number of runs
    result = run_monte_carlo_on_df(
        csv_data=sample_csv_bytes,
        filename="test.csv",
        strategy_name="sma_crossover",
        strategy_params={"sma_short": 5, "sma_long": 20},
        runs=10,
        method="bootstrap",
        method_params={"sample_fraction": 1.0},
        parallel_workers=1,
        include_equity_envelope=True,
        progress_callback=progress_callback,
    )

    # Verify result structure
    assert isinstance(result, MonteCarloSummary)
    assert isinstance(result.metrics_distribution, dict)
    assert "pnl" in result.metrics_distribution
    assert "sharpe" in result.metrics_distribution
    assert "drawdown" in result.metrics_distribution

    # Check metrics distribution
    pnl_dist = result.metrics_distribution["pnl"]
    assert isinstance(pnl_dist, MetricsDistribution)
    assert hasattr(pnl_dist, "mean")
    assert hasattr(pnl_dist, "std")

    # Check equity envelope
    if result.equity_envelope:
        assert len(result.equity_envelope.timestamps) > 0
        assert len(result.equity_envelope.p5) == len(result.equity_envelope.timestamps)
        assert len(result.equity_envelope.median) == len(result.equity_envelope.timestamps)
        assert len(result.equity_envelope.p95) == len(result.equity_envelope.timestamps)

    # Progress callback should have been called
    assert len(progress_calls) > 0


def test_monte_carlo_api_endpoint_single_file(sample_csv_bytes):
    """Test Monte Carlo API endpoint with single file."""
    response = client.post(
        "/api/v1/backtest",
        files={"csv": ("test.csv", sample_csv_bytes, "text/csv")},
        params={
            "strategy": "sma_crossover",
            "sma_short": 5,
            "sma_long": 20,
            "monte_carlo_runs": 5,  # Small number for testing
            "method": "bootstrap",
            "parallel_workers": 1,
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Should be Monte Carlo response
    assert "results" in data
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert result["method"] == "bootstrap"
    assert result["runs"] == 5
    assert "metrics_distribution" in result
    assert "equity_envelope" in result

    # Check metrics distribution structure
    metrics = result["metrics_distribution"]
    assert "pnl" in metrics
    assert "sharpe" in metrics
    assert "drawdown" in metrics

    for metric in ["pnl", "sharpe", "drawdown"]:
        assert "mean" in metrics[metric]
        assert "std" in metrics[metric]


def test_monte_carlo_api_endpoint_multiple_files(sample_csv_bytes):
    """Test Monte Carlo API endpoint with multiple files."""
    # Create second file with slightly different data
    sample_data_2 = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=100, freq="D"),
        "close": 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 100)))
    })
    csv_buffer_2 = BytesIO()
    sample_data_2.to_csv(csv_buffer_2, index=False)
    csv_bytes_2 = csv_buffer_2.getvalue()

    response = client.post(
        "/api/v1/backtest",
        files=[
            ("csv", ("test1.csv", sample_csv_bytes, "text/csv")),
            ("csv", ("test2.csv", csv_bytes_2, "text/csv")),
        ],
        params={
            "strategy": "sma_crossover",
            "sma_short": 5,
            "sma_long": 20,
            "monte_carlo_runs": 3,
            "method": "gaussian",
            "gaussian_scale": 1.0,
            "include_aggregated": True,
            "parallel_workers": 1,
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Should have results for both files
    assert "results" in data
    assert len(data["results"]) == 2

    # Should have aggregated metrics
    assert "aggregated_metrics" in data
    assert data["aggregated_metrics"] is not None
    assert "average_pnl" in data["aggregated_metrics"]
    assert "total_files_processed" in data["aggregated_metrics"]
    assert data["aggregated_metrics"]["total_files_processed"] == 2


def test_monte_carlo_api_validation():
    """Test Monte Carlo API validation."""
    # Test invalid method
    response = client.post(
        "/api/v1/backtest",
        files={"csv": ("test.csv", b"date,close\n2023-01-01,100.0\n", "text/csv")},
        params={
            "strategy": "sma_crossover",
            "sma_short": 5,
            "sma_long": 20,
            "monte_carlo_runs": 5,
            "method": "invalid_method",
        }
    )

    assert response.status_code == 400
    assert "Unsupported method" in response.json()["detail"]


def test_regular_backtest_still_works(sample_csv_bytes):
    """Test that regular backtests still work after Monte Carlo integration."""
    response = client.post(
        "/api/v1/backtest",
        files={"csv": ("test.csv", sample_csv_bytes, "text/csv")},
        params={
            "strategy": "sma_crossover",
            "sma_short": 5,
            "sma_long": 20,
            # No monte_carlo_runs parameter = regular backtest
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Should be regular backtest response (SingleBacktestResponse format)
    assert "pnl" in data
    assert "sharpe" in data
    assert "drawdown" in data
    assert "timestamps" in data
    assert "equity_curve" in data
