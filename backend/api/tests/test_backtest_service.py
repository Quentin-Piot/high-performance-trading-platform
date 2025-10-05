import io

from services.backtest_service import sma_crossover_backtest


def test_sma_crossover_backtest_basic():
    # Simple CSV with ascending prices to test calculations
    csv_content = """date,close
2023-01-01,100
2023-01-02,101
2023-01-03,102
2023-01-04,103
2023-01-05,104
"""
    buffer = io.BytesIO(csv_content.encode("utf-8"))

    equity, pnl, dd, sharpe = sma_crossover_backtest(buffer, sma_short=2, sma_long=3)

    assert len(equity) == 5
    assert isinstance(pnl, float)
    assert isinstance(dd, float)
    assert isinstance(sharpe, float)
    # Equity should grow in an uptrend with crossover
    assert equity.iloc[-1] >= equity.iloc[0]
    # Sharpe should be non-negative in this simple uptrend case
    assert sharpe >= 0.0