import pandas as pd

from strategies.moving_average import MovingAverageParams, MovingAverageStrategy


def test_sma_strategy_waits_for_long_window_before_entering():
    dates = pd.date_range("2023-01-01", periods=8, freq="D")
    df = pd.DataFrame(
        {"date": dates, "close": [100, 101, 102, 103, 104, 105, 106, 107]}
    )
    strategy = MovingAverageStrategy()
    params = MovingAverageParams(short_window=2, long_window=5, annualization=252)
    result = strategy.run(df, params)
    assert result.signals is not None
    assert result.signals.iloc[:5].fillna(0).eq(0).all()
