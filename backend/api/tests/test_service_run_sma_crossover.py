import io

import pandas as pd

from services.backtest_service import (
    CsvBytesPriceSeriesSource,
    run_sma_crossover,
    sma_crossover_backtest,
)


def _csv_from_prices(prices):
    lines = ["date,close"]
    for i, p in enumerate(prices, start=1):
        lines.append(f"2023-01-{i:02d},{p}")
    return "\n".join(lines) + "\n"


def test_run_sma_crossover_matches_compat_helper():
    prices = [100, 101, 102, 103, 102, 104, 105]
    csv = _csv_from_prices(prices)
    buf = io.BytesIO(csv.encode("utf-8"))

    # Using source and run_sma_crossover
    source = CsvBytesPriceSeriesSource(buf.getvalue())
    res = run_sma_crossover(source, sma_short=2, sma_long=3)

    # Using compatibility helper
    equity2, pnl2, dd2, sharpe2 = sma_crossover_backtest(
        buf.getvalue(), sma_short=2, sma_long=3
    )

    assert isinstance(res.equity, pd.Series)
    assert list(res.equity.values) == list(equity2.values)
    assert round(res.pnl, 10) == round(pnl2, 10)
    assert round(res.drawdown, 10) == round(dd2, 10)
    assert round(res.sharpe, 10) == round(sharpe2, 10)


def test_run_sma_crossover_invalid_params_raise():
    prices = [100, 101, 102, 103]
    csv = _csv_from_prices(prices)
    buf = io.BytesIO(csv.encode("utf-8"))
    source = CsvBytesPriceSeriesSource(buf.getvalue())
    # short >= long should raise ValueError from strategy
    import pytest

    with pytest.raises(ValueError):
        run_sma_crossover(source, sma_short=3, sma_long=3)
