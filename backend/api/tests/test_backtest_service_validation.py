import io

import pytest

from services.backtest_service import _read_csv_to_series, sma_crossover_backtest


@pytest.mark.parametrize(
    "sma_short,sma_long",
    [
        (0, 10),
        (-1, 10),
        (10, 10),
        (15, 10),
    ],
)
def test_sma_params_invalid_raise_value_error(sma_short, sma_long):
    csv_content = """date,close\n2023-01-01,100\n2023-01-02,101\n"""
    buffer = io.BytesIO(csv_content.encode("utf-8"))
    with pytest.raises(ValueError):
        sma_crossover_backtest(buffer, sma_short=sma_short, sma_long=sma_long)


def test_read_csv_missing_price_column_raises():
    bad_csv = """date,open,high,low,volume\n2023-01-01,1,2,0,1000\n"""
    buffer = io.BytesIO(bad_csv.encode("utf-8"))
    with pytest.raises(ValueError):
        _read_csv_to_series(buffer)
