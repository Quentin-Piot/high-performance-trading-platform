"""
Monte Carlo Backtesting Service

Provides data perturbation methods and orchestration for running multiple
backtest simulations with statistical analysis.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from numpy.random import Generator, default_rng

from domain.schemas.backtest import EquityEnvelope, MetricsDistribution
from services.backtest_service import (
    CsvBytesPriceSeriesSource,
    ServiceBacktestResult,
    run_rsi,
    run_sma_crossover,
)

logger = logging.getLogger("services.mc_backtest")

# Safety limits
MAX_MONTE_CARLO_RUNS = int(os.getenv("MAX_MONTE_CARLO_RUNS", "20000"))
DEFAULT_PARALLEL_WORKERS = os.cpu_count() or 1

@dataclass
class MonteCarloResult:
    """Results from a single Monte Carlo run"""
    pnl: float
    sharpe: float
    drawdown: float
    equity_curve: pd.Series | None = None

# Types supprimés - utiliser les définitions dans domain.schemas.backtest

@dataclass
class MonteCarloSummary:
    """Summary of Monte Carlo simulation results"""
    filename: str
    method: str
    runs: int
    successful_runs: int
    metrics_distribution: dict[str, MetricsDistribution]
    equity_envelope: EquityEnvelope | None = None

def bootstrap_returns_to_prices(prices: pd.Series, sample_fraction: float = 1.0, rng: Generator = None) -> pd.Series:
    """
    Bootstrap method: resample returns with replacement and reconstruct prices.

    Args:
        prices: Original price series
        sample_fraction: Fraction of returns to sample (1.0 = same length)
        rng: Random number generator

    Returns:
        Synthetic price series
    """
    if rng is None:
        rng = default_rng()

    # Convert prices to returns
    returns = prices.pct_change(fill_method=None).dropna()

    # Sample returns with replacement
    n_samples = int(len(returns) * sample_fraction)
    sampled_returns = rng.choice(returns.values, size=n_samples, replace=True)

    # Reconstruct prices starting from original first price
    synthetic_prices = [prices.iloc[0]]
    for ret in sampled_returns:
        synthetic_prices.append(synthetic_prices[-1] * (1 + ret))

    # Create series with same index structure as original (or new if different length)
    if len(synthetic_prices) == len(prices):
        return pd.Series(synthetic_prices, index=prices.index)
    else:
        return pd.Series(synthetic_prices)

def gaussian_noise_returns_to_prices(prices: pd.Series, scale: float = 1.0, rng: Generator = None) -> pd.Series:
    """
    Gaussian noise method: add noise to returns and reconstruct prices.

    Args:
        prices: Original price series
        scale: Scale factor for Gaussian noise (1.0 = same std as original returns)
        rng: Random number generator

    Returns:
        Synthetic price series
    """
    if rng is None:
        rng = default_rng()

    # Convert prices to returns
    returns = prices.pct_change(fill_method=None).dropna()
    returns_std = returns.std()

    # Add Gaussian noise to returns
    noise = rng.normal(0, returns_std * scale, size=len(returns))
    noisy_returns = returns.values + noise

    # Reconstruct prices
    synthetic_prices = [prices.iloc[0]]
    for ret in noisy_returns:
        synthetic_prices.append(synthetic_prices[-1] * (1 + ret))

    return pd.Series(synthetic_prices, index=prices.index)

def monte_carlo_worker(args) -> MonteCarloResult | None:
    """
    Worker function for Monte Carlo simulation.

    Args:
        args: Either a tuple (csv_data, strategy_name, strategy_params, method, method_params, seed)
              or a dict with keys: csv_data/df, strategy_name, strategy_params, method, method_params, seed/rng_seed

    Returns:
        MonteCarloResult or None if failed
    """
    # Logging must be configured within the worker process
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("services.mc_backtest_worker")

    try:
        # Handle both tuple and dict formats
        if isinstance(args, dict):
            csv_data = args.get("csv_data")
            df = args.get("df")
            strategy_name = args["strategy_name"]
            strategy_params = args["strategy_params"]
            method = args["method"]
            method_params = args.get("method_params", {})
            seed = args.get("seed") or args.get("rng_seed")
        else:
            csv_data, strategy_name, strategy_params, method, method_params, seed = args
            df = None

        # Set up RNG with seed
        rng = default_rng(seed)

        # Load original data
        if df is not None:
            # Use provided DataFrame
            original_prices = df["close"]
        else:
            # Load from CSV data
            source = CsvBytesPriceSeriesSource(csv_data)
            original_prices = source.get_prices()

        # Generate synthetic data based on method
        if method == "bootstrap":
            synthetic_prices = bootstrap_returns_to_prices(
                original_prices,
                sample_fraction=method_params.get("sample_fraction", 1.0),
                rng=rng
            )
        elif method == "gaussian":
            synthetic_prices = gaussian_noise_returns_to_prices(
                original_prices,
                scale=method_params.get("gaussian_scale", 1.0),
                rng=rng
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        # Create synthetic CSV data
        synthetic_df = pd.DataFrame({"close": synthetic_prices})
        if hasattr(synthetic_prices.index, 'to_pydatetime'):
            synthetic_df["date"] = synthetic_prices.index

        # Convert back to CSV bytes
        csv_buffer = synthetic_df.to_csv(index=False).encode()
        synthetic_source = CsvBytesPriceSeriesSource(csv_buffer)

        # Run strategy on synthetic data
        if strategy_name == "sma_crossover":
            # Support both parameter naming conventions
            sma_short = strategy_params.get("sma_short") or strategy_params.get("short_window")
            sma_long = strategy_params.get("sma_long") or strategy_params.get("long_window")

            if sma_short is None or sma_long is None:
                raise ValueError(f"Missing SMA parameters. Expected 'sma_short'/'sma_long' or 'short_window'/'long_window', got: {list(strategy_params.keys())}")

            result = run_sma_crossover(
                synthetic_source,
                sma_short,
                sma_long
            )
        elif strategy_name == "rsi":
            result = run_rsi(
                synthetic_source,
                strategy_params["period"],
                strategy_params["overbought"],
                strategy_params["oversold"]
            )
        elif strategy_name == "dummy":
            # Dummy strategy for testing
            result = ServiceBacktestResult(
                pnl=0.0,
                sharpe=0.0,
                drawdown=0.0,
                equity=pd.Series([1.0]),
                trades=[],
                metrics={},
                plot_html=None
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        return MonteCarloResult(
            pnl=result.pnl,
            sharpe=result.sharpe,
            drawdown=result.drawdown,
            equity_curve=result.equity
        )

    except Exception:
        logger.error("Monte Carlo worker failed:", exc_info=True)
        return None

def compute_equity_envelope(equity_curves: list[pd.Series], timestamps: list[str]) -> EquityEnvelope:
    """
    Compute equity envelope with percentiles from multiple equity curves.

    Args:
        equity_curves: List of equity curves from Monte Carlo runs
        timestamps: List of timestamp strings

    Returns:
        EquityEnvelope with percentiles
    """
    if not equity_curves:
        return EquityEnvelope(
            timestamps=timestamps,
            p5=[],
            p25=[],
            median=[],
            p75=[],
            p95=[]
        )

    # Align all curves to same length and compute percentiles
    min_length = min(len(curve) for curve in equity_curves)
    aligned_curves = [curve.iloc[:min_length].values for curve in equity_curves]
    equity_matrix = np.array(aligned_curves)

    return EquityEnvelope(
        timestamps=timestamps[:min_length],
        p5=np.percentile(equity_matrix, 5, axis=0).tolist(),
        p25=np.percentile(equity_matrix, 25, axis=0).tolist(),
        median=np.percentile(equity_matrix, 50, axis=0).tolist(),
        p75=np.percentile(equity_matrix, 75, axis=0).tolist(),
        p95=np.percentile(equity_matrix, 95, axis=0).tolist()
    )

def run_monte_carlo_on_df(
    csv_data: bytes,
    filename: str,
    strategy_name: str,
    strategy_params: dict[str, Any],
    runs: int,
    method: str = "bootstrap",
    method_params: dict[str, Any] | None = None,
    parallel_workers: int = DEFAULT_PARALLEL_WORKERS,
    seed: int | None = None,
    include_equity_envelope: bool = True,
    progress_callback: Callable[[int, int], None] | None = None
) -> MonteCarloSummary:
    """
    Run Monte Carlo simulation on CSV data with enhanced progress reporting.
    """
    if runs > MAX_MONTE_CARLO_RUNS:
        raise ValueError(f"Number of runs ({runs}) exceeds maximum allowed ({MAX_MONTE_CARLO_RUNS})")

    if method_params is None:
        method_params = {}

    logger.info(f"Starting Monte Carlo simulation: {runs} runs, method={method}")

    # Determine if we should use parallel processing
    use_parallel = runs > 1 and parallel_workers > 1

    # Prepare worker arguments
    worker_args = []
    rng = default_rng(seed)
    for _i in range(runs):
        worker_seed = rng.integers(0, 2**32 - 1)
        worker_args.append((csv_data, strategy_name, strategy_params, method, method_params, worker_seed))

    results = []
    successful_runs = 0

    # Enhanced progress tracking
    import threading
    import time

    progress_lock = threading.Lock()
    completed_runs = 0

    def update_progress():
        """Thread-safe progress update"""
        nonlocal completed_runs
        with progress_lock:
            completed_runs += 1
            if progress_callback:
                progress_callback(completed_runs, runs)

    if use_parallel:
        logger.info(f"Using {parallel_workers} parallel workers")

        # Start a background thread to send periodic progress updates
        stop_progress_thread = threading.Event()

        def periodic_progress_update():
            """Send progress updates every 2 seconds even if no new completions"""
            while not stop_progress_thread.is_set():
                if progress_callback:
                    with progress_lock:
                        progress_callback(completed_runs, runs)
                time.sleep(2)  # Update every 2 seconds

        progress_thread = threading.Thread(target=periodic_progress_update, daemon=True)
        progress_thread.start()

        try:
            with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
                # Submit all jobs
                future_to_idx = {executor.submit(monte_carlo_worker, args): i
                               for i, args in enumerate(worker_args)}

                # Collect results as they complete
                for future in as_completed(future_to_idx):
                    result = future.result()
                    if result is not None:
                        results.append(result)
                        successful_runs += 1

                    # Update progress immediately when a worker completes
                    update_progress()
        finally:
            # Stop the progress thread
            stop_progress_thread.set()
            progress_thread.join(timeout=1)
    else:
        # Sequential processing with more frequent updates
        logger.info("Using sequential processing")
        for i, args in enumerate(worker_args):
            # Send progress update before starting each run
            if progress_callback and i % max(1, runs // 20) == 0:  # Update every 5% or at least every run
                progress_callback(i, runs)

            result = monte_carlo_worker(args)
            if result is not None:
                results.append(result)
                successful_runs += 1

            # Update progress after each run
            update_progress()

    if not results:
        raise RuntimeError("All Monte Carlo runs failed")

    logger.info(f"Completed {successful_runs}/{runs} successful runs")

    # Send final progress update
    if progress_callback:
        progress_callback(runs, runs)

    # Compute metrics distributions
    pnl_values = [r.pnl for r in results]
    sharpe_values = [r.sharpe for r in results]
    drawdown_values = [r.drawdown for r in results]

    def create_metrics_distribution(values: list[float]) -> MetricsDistribution:
        """Create MetricsDistribution from list of values"""
        arr = np.array(values)
        return MetricsDistribution(
            mean=float(np.mean(arr)),
            std=float(np.std(arr)),
            p5=float(np.percentile(arr, 5)),
            p25=float(np.percentile(arr, 25)),
            median=float(np.percentile(arr, 50)),
            p75=float(np.percentile(arr, 75)),
            p95=float(np.percentile(arr, 95))
        )

    metrics_distribution = {
        "pnl": create_metrics_distribution(pnl_values),
        "sharpe": create_metrics_distribution(sharpe_values),
        "drawdown": create_metrics_distribution(drawdown_values)
    }

    # Compute equity envelope if requested and we have equity curves
    equity_envelope = None
    if include_equity_envelope and results and results[0].equity_curve is not None:
        equity_curves = [r.equity_curve for r in results if r.equity_curve is not None]
        if equity_curves:
            # Use first curve's index for timestamps
            first_curve = equity_curves[0]
            if hasattr(first_curve.index, 'strftime'):
                timestamps = [t.strftime('%Y-%m-%d') for t in first_curve.index]
            else:
                timestamps = [str(i) for i in range(len(first_curve))]

            equity_envelope = compute_equity_envelope(equity_curves, timestamps)

    return MonteCarloSummary(
        filename=filename,
        method=method,
        runs=runs,
        successful_runs=successful_runs,
        metrics_distribution=metrics_distribution,
        equity_envelope=equity_envelope
    )

class ProgressPublisher:
    """Simple progress publisher for logging or future SSE integration"""

    def __init__(self, logger_name: str = "mc_progress"):
        self.logger = logging.getLogger(logger_name)

    def publish_progress(self, processed: int, total: int, filename: str = ""):
        """Publish progress update"""
        percentage = (processed / total) * 100 if total > 0 else 0
        self.logger.info(f"Progress {filename}: {processed}/{total} ({percentage:.1f}%)")

    def publish_completion(self, summary: MonteCarloSummary):
        """Publish completion summary"""
        self.logger.info(f"Completed Monte Carlo for {summary.filename}: "
                        f"{summary.successful_runs}/{summary.runs} successful runs")
