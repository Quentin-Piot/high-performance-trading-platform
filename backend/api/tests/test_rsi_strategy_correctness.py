import pandas as pd

from strategies.rsi_reversion import RSIParams, RSIReversionStrategy


def test_rsi_reaches_high_values_on_monotonic_uptrend():
    series = pd.Series(
        [100, 101, 102, 103, 104, 105, 106, 107],
        index=pd.date_range("2023-01-01", periods=8, freq="D"),
    )
    strategy = RSIReversionStrategy()
    rsi = strategy._rsi(series, window=3)
    assert float(rsi.iloc[-1]) > 99.0


def test_rsi_strategy_uses_high_threshold_for_exit(monkeypatch):
    dates = pd.date_range("2023-01-01", periods=6, freq="D")
    df = pd.DataFrame({"date": dates, "close": [100, 100, 100, 100, 100, 100]})
    strategy = RSIReversionStrategy()

    def fake_rsi(_close: pd.Series, window: int) -> pd.Series:
        assert window == 3
        return pd.Series([50, 20, 20, 80, 80, 80], index=dates)

    monkeypatch.setattr(strategy, "_rsi", fake_rsi)
    params = RSIParams(window=3, rsi_low=30, rsi_high=70, annualization=252)
    result = strategy.run(df, params)
    assert result.signals is not None
    assert result.signals.fillna(0).tolist() == [0.0, 0.0, 1.0, 1.0, 0.0, 0.0]
