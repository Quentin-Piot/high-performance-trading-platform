import datetime as dt
import math

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from services.backtest_service import CsvBytesPriceSeriesSource, run_sma_crossover


def _csv_from_prices(prices):
    start = dt.date(2023, 1, 1)
    lines = ["date,close"]
    for i, p in enumerate(prices):
        day = start + dt.timedelta(days=i)
        lines.append(f"{day.isoformat()},{p}")
    return "\n".join(lines) + "\n"


valid_float = st.floats(
    min_value=0.001, max_value=1e6, allow_nan=False, allow_infinity=False
)


@settings(max_examples=60, deadline=None)
@given(
    prices=st.lists(valid_float, min_size=20, max_size=300),
    sma_short=st.integers(min_value=2, max_value=50),
    sma_gap=st.integers(min_value=1, max_value=50),
)
def test_backtest_outputs_are_well_formed(prices, sma_short, sma_gap):
    sma_long = sma_short + sma_gap
    csv = _csv_from_prices(prices)
    source = CsvBytesPriceSeriesSource(csv.encode("utf-8"))
    result = run_sma_crossover(source, sma_short=sma_short, sma_long=sma_long)

    assert len(result.equity) == len(prices)
    assert float(result.equity.iloc[0]) == 1.0
    assert np.isfinite(result.equity.values).all()

    for v in (result.pnl, result.drawdown, result.sharpe):
        assert isinstance(v, float)
        assert math.isfinite(v)

    assert -1.0 <= result.drawdown <= 0.0
