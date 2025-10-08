import numpy as np
import pytest
import pandas as pd

from strategies.metrics import sharpe_ratio, max_drawdown, total_return, trade_summary_from_positions


def test_sharpe_ratio_nan_on_zero_returns():
    # Zero returns -> zero std -> NaN Sharpe per implementation
    returns = pd.Series([0.0] * 252, index=pd.date_range("2023-01-01", periods=252, freq="D"))
    s = sharpe_ratio(returns)
    assert np.isnan(s)


def test_max_drawdown_on_known_path():
    equity = pd.Series([100, 110, 105, 120, 90], index=pd.date_range("2023-01-01", periods=5, freq="D"))
    dd = max_drawdown(equity)
    # Peak at 120, trough at 90 => 90/120 - 1 = -0.25
    assert dd == -0.25


def test_total_return_basic_and_empty():
    equity = pd.Series([100, 110], index=pd.date_range("2023-01-01", periods=2, freq="D"))
    assert total_return(equity) == pytest.approx(0.10, rel=1e-12)
    assert total_return(pd.Series(dtype=float)) == 0.0


def test_trade_summary_from_positions_pairs_entries_exits():
    dates = pd.date_range("2023-01-01", periods=6, freq="D")
    price = pd.Series([100, 102, 101, 105, 104, 106], index=dates)
    # Long from day 2 to day 4, then again day 6 until close
    positions = pd.Series([0, 1, 1, 1, 0, 1], index=dates)
    trades = trade_summary_from_positions(positions, price)
    assert len(trades) == 2
    # First trade: enter at day 2 (102), exit at day 5 (104)
    t1 = trades.iloc[0]
    assert t1.entry_date == dates[1]
    assert t1.exit_date == dates[4]
    assert t1.entry_price == 102.0
    assert t1.exit_price == 104.0
    assert round(t1.pnl_pct, 6) == round(104.0 / 102.0 - 1.0, 6)
    # Second trade: enter at day 6 (106), exit at last price (day 6)
    t2 = trades.iloc[1]
    assert t2.entry_date == dates[5]
    assert t2.exit_date == dates[5]
    assert t2.entry_price == 106.0
    assert t2.exit_price == 106.0
    assert t2.pnl_pct == 0.0