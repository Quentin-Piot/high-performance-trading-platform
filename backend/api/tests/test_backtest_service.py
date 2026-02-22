from services.backtest_service import CsvBytesPriceSeriesSource, run_sma_crossover


def test_sma_crossover_backtest_basic():
    csv_content = """date,close
2023-01-01,100
2023-01-02,101
2023-01-03,102
2023-01-04,103
2023-01-05,104
"""
    source = CsvBytesPriceSeriesSource(csv_content.encode("utf-8"))
    result = run_sma_crossover(source, sma_short=2, sma_long=3)

    assert len(result.equity) == 5
    assert isinstance(result.pnl, float)
    assert isinstance(result.drawdown, float)
    assert isinstance(result.sharpe, float)
    assert result.equity.iloc[-1] >= result.equity.iloc[0]
    assert result.sharpe >= 0.0
