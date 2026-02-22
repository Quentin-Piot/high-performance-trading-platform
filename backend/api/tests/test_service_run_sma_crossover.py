import pandas as pd
import pytest

from services.backtest_service import CsvBytesPriceSeriesSource, run_sma_crossover


def _csv_from_prices(prices):
    lines = ["date,close"]
    for i, p in enumerate(prices, start=1):
        lines.append(f"2023-01-{i:02d},{p}")
    return "\n".join(lines) + "\n"


def test_run_sma_crossover_returns_valid_result():
    prices = [100, 101, 102, 103, 102, 104, 105]
    csv = _csv_from_prices(prices)
    source = CsvBytesPriceSeriesSource(csv.encode("utf-8"))
    result = run_sma_crossover(source, sma_short=2, sma_long=3)

    assert isinstance(result.equity, pd.Series)
    assert len(result.equity) == len(prices)
    assert isinstance(result.pnl, float)
    assert isinstance(result.drawdown, float)
    assert isinstance(result.sharpe, float)


def test_run_sma_crossover_invalid_params_raise():
    prices = [100, 101, 102, 103]
    csv = _csv_from_prices(prices)
    source = CsvBytesPriceSeriesSource(csv.encode("utf-8"))
    with pytest.raises(ValueError):
        run_sma_crossover(source, sma_short=3, sma_long=3)
