from typing import Any

from domain.schemas.backtest import EquityEnvelope, MetricsDistribution
from services.mc_backtest_service import MonteCarloSummary


def test_monte_carlo_sync_passes_method_and_params_to_service(client, monkeypatch):
    captured: dict[str, Any] = {}

    def fake_run_monte_carlo_on_df(**kwargs):
        captured.update(kwargs)
        return MonteCarloSummary(
            filename=kwargs["filename"],
            method=kwargs["method"],
            runs=kwargs["runs"],
            successful_runs=kwargs["runs"],
            metrics_distribution={
                "pnl": MetricsDistribution(
                    mean=0.1, std=0.01, p5=0.05, p25=0.08, median=0.1, p75=0.12, p95=0.15
                ),
                "sharpe": MetricsDistribution(
                    mean=1.0, std=0.1, p5=0.7, p25=0.9, median=1.0, p75=1.1, p95=1.3
                ),
                "drawdown": MetricsDistribution(
                    mean=-0.2,
                    std=0.05,
                    p5=-0.3,
                    p25=-0.25,
                    median=-0.2,
                    p75=-0.15,
                    p95=-0.1,
                ),
            },
            equity_envelope=EquityEnvelope(
                timestamps=["2023-01-01", "2023-01-02"],
                p5=[1.0, 0.95],
                p25=[1.0, 0.98],
                median=[1.0, 1.02],
                p75=[1.0, 1.04],
                p95=[1.0, 1.06],
            ),
        )

    monkeypatch.setattr(
        "services.mc_backtest_service.run_monte_carlo_on_df", fake_run_monte_carlo_on_df
    )
    resp = client.post(
        "/api/v1/monte-carlo/run",
        params={
            "symbol": "aapl",
            "start_date": "2017-01-01",
            "end_date": "2018-01-31",
            "num_runs": 5,
            "initial_capital": 25000,
            "strategy": "sma_crossover",
            "sma_short": 10,
            "sma_long": 20,
            "method": "gaussian",
            "gaussian_scale": 1.7,
            "sample_fraction": 0.4,
            "price_type": "adj_close",
        },
    )
    assert resp.status_code == 200, resp.text
    assert captured["method"] == "gaussian"
    assert captured["method_params"] == {"sample_fraction": 0.4, "gaussian_scale": 1.7}
    assert captured["price_type"] == "adj_close"
    assert captured["strategy_params"]["initial_capital"] == 25000
