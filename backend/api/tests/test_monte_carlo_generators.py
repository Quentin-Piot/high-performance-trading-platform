import numpy as np
import pandas as pd

from services.mc_backtest_service import (
    bootstrap_returns_to_prices,
    gaussian_noise_returns_to_prices,
    monte_carlo_worker,
)


class TestBootstrapGenerator:
    """Test bootstrap returns to prices generator."""

    def test_bootstrap_deterministic_with_seed(self):
        """Test that bootstrap generator is deterministic with same seed."""
        # Create sample price series
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)

        # Generate with same seed twice
        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(42)

        result1 = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng1)
        result2 = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng2)

        # Should be identical
        pd.testing.assert_series_equal(result1, result2)

    def test_bootstrap_different_seeds_different_results(self):
        """Test that different seeds produce different results."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)

        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(123)

        result1 = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng1)
        result2 = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng2)

        # Should be different
        assert not result1.equals(result2)

    def test_bootstrap_preserves_length(self):
        """Test that bootstrap preserves series length."""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 30))), index=dates)

        rng = np.random.RandomState(42)
        result = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng)

        assert len(result) == len(prices)
        assert result.index.equals(prices.index)

    def test_bootstrap_sample_fraction(self):
        """Test that sample fraction affects the bootstrap sampling."""
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 100))), index=dates)

        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(42)

        result_full = bootstrap_returns_to_prices(prices, sample_fraction=1.0, rng=rng1)
        result_half = bootstrap_returns_to_prices(prices, sample_fraction=0.5, rng=rng2)

        # Full sample should have same length as original, half sample should be shorter
        assert len(result_full) == len(prices)
        assert len(result_half) == 50  # 50% of 100 returns + 1 initial price = 50 prices
        # With different sample fractions, results should be different
        assert not result_full.equals(result_half)


class TestGaussianGenerator:
    """Test gaussian noise returns to prices generator."""

    def test_gaussian_deterministic_with_seed(self):
        """Test that gaussian generator is deterministic with same seed."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)

        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(42)

        result1 = gaussian_noise_returns_to_prices(prices, scale=1.0, rng=rng1)
        result2 = gaussian_noise_returns_to_prices(prices, scale=1.0, rng=rng2)

        # Should be identical
        pd.testing.assert_series_equal(result1, result2)

    def test_gaussian_different_seeds_different_results(self):
        """Test that different seeds produce different results."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)

        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(123)

        result1 = gaussian_noise_returns_to_prices(prices, scale=1.0, rng=rng1)
        result2 = gaussian_noise_returns_to_prices(prices, scale=1.0, rng=rng2)

        # Should be different
        assert not result1.equals(result2)

    def test_gaussian_preserves_length(self):
        """Test that gaussian preserves series length."""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 30))), index=dates)

        rng = np.random.RandomState(42)
        result = gaussian_noise_returns_to_prices(prices, scale=1.0, rng=rng)

        assert len(result) == len(prices)
        assert result.index.equals(prices.index)

    def test_gaussian_scale_affects_variance(self):
        """Test that scale parameter affects the variance of results."""
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 100))), index=dates)

        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(42)

        result_low = gaussian_noise_returns_to_prices(prices, scale=0.1, rng=rng1)
        result_high = gaussian_noise_returns_to_prices(prices, scale=2.0, rng=rng2)

        # Higher scale should produce more variance from original
        prices.pct_change(fill_method=None).dropna()
        low_returns = result_low.pct_change(fill_method=None).dropna()
        high_returns = result_high.pct_change(fill_method=None).dropna()

        # Standard deviation should be different
        assert low_returns.std() != high_returns.std()


class TestMonteCarloWorker:
    """Test Monte Carlo worker deterministic behavior."""

    def test_worker_deterministic_with_seed(self):
        """Test that worker produces identical results with same seed."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)
        df = pd.DataFrame({"close": prices}, index=dates)

        args = {
            "df": df,
            "strategy_name": "sma_crossover",
            "strategy_params": {"sma_short": 5, "sma_long": 20},
            "method": "bootstrap",
            "method_params": {"sample_fraction": 1.0},
            "rng_seed": 42,
        }

        result1 = monte_carlo_worker(args)
        result2 = monte_carlo_worker(args)

        # Should be identical
        assert result1 is not None
        assert result2 is not None
        assert result1.pnl == result2.pnl
        assert result1.sharpe == result2.sharpe
        assert result1.drawdown == result2.drawdown

    def test_worker_different_seeds_different_results(self):
        """Test that different seeds produce different results."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)
        df = pd.DataFrame({"close": prices}, index=dates)

        args1 = {
            "df": df,
            "strategy_name": "sma_crossover",
            "strategy_params": {"sma_short": 5, "sma_long": 20},
            "method": "bootstrap",
            "method_params": {"sample_fraction": 1.0},
            "rng_seed": 42,
        }

        args2 = {
            "df": df,
            "strategy_name": "sma_crossover",
            "strategy_params": {"sma_short": 5, "sma_long": 20},
            "method": "bootstrap",
            "method_params": {"sample_fraction": 1.0},
            "rng_seed": 123,
        }

        result1 = monte_carlo_worker(args1)
        result2 = monte_carlo_worker(args2)

        # Should be different (with high probability)
        assert result1 is not None
        assert result2 is not None
        # At least one metric should be different
        assert (result1.pnl != result2.pnl or
                result1.sharpe != result2.sharpe or
                result1.drawdown != result2.drawdown)

    def test_worker_supports_both_strategies(self):
        """Test that worker supports both SMA and RSI strategies."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)
        df = pd.DataFrame({"close": prices}, index=dates)

        # Test SMA strategy
        sma_args = {
            "df": df,
            "strategy_name": "sma_crossover",
            "strategy_params": {"sma_short": 5, "sma_long": 20},
            "method": "bootstrap",
            "method_params": {"sample_fraction": 1.0},
            "rng_seed": 42,
        }

        # Test RSI strategy
        rsi_args = {
            "df": df,
            "strategy_name": "rsi",
            "strategy_params": {"period": 14, "overbought": 70, "oversold": 30},
            "method": "bootstrap",
            "method_params": {"sample_fraction": 1.0},
            "rng_seed": 42,
        }

        sma_result = monte_carlo_worker(sma_args)
        rsi_result = monte_carlo_worker(rsi_args)

        # Both should succeed
        assert sma_result is not None
        assert rsi_result is not None
        assert isinstance(sma_result.pnl, float)
        assert isinstance(rsi_result.pnl, float)

    def test_worker_supports_both_methods(self):
        """Test that worker supports both bootstrap and gaussian methods."""
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50))), index=dates)
        df = pd.DataFrame({"close": prices}, index=dates)

        # Test bootstrap method
        bootstrap_args = {
            "df": df,
            "strategy_name": "sma_crossover",
            "strategy_params": {"sma_short": 5, "sma_long": 20},
            "method": "bootstrap",
            "method_params": {"sample_fraction": 1.0},
            "rng_seed": 42,
        }

        # Test gaussian method
        gaussian_args = {
            "df": df,
            "strategy_name": "sma_crossover",
            "strategy_params": {"sma_short": 5, "sma_long": 20},
            "method": "gaussian",
            "method_params": {"gaussian_scale": 1.0},
            "rng_seed": 42,
        }

        bootstrap_result = monte_carlo_worker(bootstrap_args)
        gaussian_result = monte_carlo_worker(gaussian_args)

        # Both should succeed
        assert bootstrap_result is not None
        assert gaussian_result is not None
        assert isinstance(bootstrap_result.pnl, float)
        assert isinstance(gaussian_result.pnl, float)
