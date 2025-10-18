import io

import pandas as pd

from services.backtest_service import _read_csv_to_series


def test_read_csv_uses_adj_close_when_only_adj_available():
    csv = """date,adj close,open,high,low,volume
2023-01-01,100,99,101,98,1000
2023-01-02,101,100,102,99,1100
"""
    buf = io.BytesIO(csv.encode("utf-8"))
    series = _read_csv_to_series(buf)
    assert isinstance(series.index, pd.DatetimeIndex)
    assert series.iloc[0] == 100.0 and series.iloc[1] == 101.0


def test_read_csv_sorts_unsorted_dates():
    csv = """date,close
2023-01-03,103
2023-01-01,100
2023-01-02,101
"""
    buf = io.BytesIO(csv.encode("utf-8"))
    series = _read_csv_to_series(buf)
    assert list(series.index.astype(str)) == ["2023-01-01", "2023-01-02", "2023-01-03"]
    assert list(series.values) == [100.0, 101.0, 103.0]


def test_read_csv_without_date_column_returns_series():
    csv = """close,open
100,99
101,100
102,101
"""
    buf = io.BytesIO(csv.encode("utf-8"))
    series = _read_csv_to_series(buf)
    assert isinstance(series, pd.Series)
    assert list(series.values) == [100.0, 101.0, 102.0]
