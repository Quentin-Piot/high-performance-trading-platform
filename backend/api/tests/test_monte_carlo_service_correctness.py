import pandas as pd
from numpy.random import default_rng

from services.backtest_service import ServiceBacktestResult
from services.mc_backtest_service import (
    bootstrap_returns_to_prices,
    compute_equity_envelope,
    monte_carlo_worker,
)


def test_bootstrap_returns_preserves_length_and_index_for_any_fraction():
    prices = pd.Series(
        [100.0, 101.0, 99.0, 103.0, 102.0],
        index=pd.date_range("2023-01-01", periods=5, freq="D"),
    )
    for fraction in [0.5, 1.0, 2.0]:
        synthetic = bootstrap_returns_to_prices(
            prices, sample_fraction=fraction, rng=default_rng(123)
        )
        assert len(synthetic) == len(prices)
        assert synthetic.index.equals(prices.index)


def test_compute_equity_envelope_aligns_on_common_timestamps():
    curve_1 = pd.Series(
        [1.0, 1.1, 1.2], index=pd.date_range("2023-01-01", periods=3, freq="D")
    )
    curve_2 = pd.Series(
        [0.9, 1.0, 1.1], index=pd.date_range("2023-01-02", periods=3, freq="D")
    )
    envelope = compute_equity_envelope([curve_1, curve_2], [])
    assert envelope.timestamps == ["2023-01-02", "2023-01-03"]
    assert len(envelope.median) == 2


def test_monte_carlo_worker_supports_alias_and_passes_initial_capital(monkeypatch):
    captured: dict[str, float | int] = {}

    def fake_run_sma(source, sma_short, sma_long, initial_capital=1.0):
        captured["sma_short"] = sma_short
        captured["sma_long"] = sma_long
        captured["initial_capital"] = initial_capital
        return ServiceBacktestResult(
            equity=pd.Series([100.0, 101.0]),
            pnl=0.01,
            drawdown=-0.02,
            sharpe=1.23,
        )

    monkeypatch.setattr("services.mc_backtest_service.run_sma_crossover", fake_run_sma)
    csv = b"date,close\n2023-01-01,100\n2023-01-02,101\n2023-01-03,102\n"
    result = monte_carlo_worker(
        (
            csv,
            "sma",
            {"sma_short": 2, "sma_long": 3, "initial_capital": 5000.0},
            "bootstrap",
            {},
            42,
            "close",
        )
    )
    assert result is not None
    assert captured == {
        "sma_short": 2,
        "sma_long": 3,
        "initial_capital": 5000.0,
    }
