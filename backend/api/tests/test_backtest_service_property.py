import io
import math
import datetime as dt

import numpy as np
import pandas as pd
from hypothesis import given, settings, strategies as st

from services.backtest_service import sma_crossover_backtest


def _csv_from_prices(prices):
    start = dt.date(2023, 1, 1)
    lines = ["date,close"]
    for i, p in enumerate(prices):
        day = start + dt.timedelta(days=i)
        lines.append(f"{day.isoformat()},{p}")
    return "\n".join(lines) + "\n"


valid_float = st.floats(min_value=0.001, max_value=1e6, allow_nan=False, allow_infinity=False)


@settings(max_examples=60, deadline=None)
@given(
    prices=st.lists(valid_float, min_size=20, max_size=300),
    sma_short=st.integers(min_value=2, max_value=50),
    sma_gap=st.integers(min_value=1, max_value=50),
)
def test_backtest_outputs_are_well_formed(prices, sma_short, sma_gap):
    sma_long = sma_short + sma_gap

    csv = _csv_from_prices(prices)
    buffer = io.BytesIO(csv.encode("utf-8"))

    equity, pnl, dd, sharpe = sma_crossover_backtest(buffer, sma_short=sma_short, sma_long=sma_long)

    # Longueur cohérente
    assert len(equity) == len(prices)

    # Première valeur d'équité à 1.0
    assert float(equity.iloc[0]) == 1.0

    # Pas de NaN/Inf dans equity
    assert np.isfinite(equity.values).all()

    # PnL/drawdown/sharpe finis
    for v in (pnl, dd, sharpe):
        assert isinstance(v, float)
        assert math.isfinite(v)

    # Drawdown négatif entre -1 et 0
    assert -1.0 <= dd <= 0.0