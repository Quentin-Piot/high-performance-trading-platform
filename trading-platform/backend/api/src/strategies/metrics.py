from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict


def sharpe_ratio(returns: pd.Series, annualization: int = 252) -> float:
    # returns: simple returns series (periodic, e.g., daily pct change)
    mean = returns.mean()
    std = returns.std(ddof=0)
    if std == 0 or np.isnan(std):
        return float("nan")
    return float((mean / std) * (annualization**0.5))


def max_drawdown(equity: pd.Series) -> float:
    # equity: cumulative portfolio value
    roll_max = equity.cummax()
    drawdown = equity / roll_max - 1.0
    return float(drawdown.min())


def total_return(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def trade_summary_from_positions(
    positions: pd.Series, price: pd.Series
) -> pd.DataFrame:
    """
    Build trades table from position series (0/1) representing full allocation.
    Returns DataFrame with columns: entry_date, exit_date, entry_price, exit_price, pnl_pct.
    """
    positions = positions.fillna(0).astype(int)
    diffs = positions.diff().fillna(0).astype(int)
    entries = diffs[diffs == 1].index.tolist()
    exits = diffs[diffs == -1].index.tolist()

    # handle unclosed position: if entries > exits, close at last price
    trades = []
    i_e = 0
    i_x = 0
    # pair entries/exits in order
    while i_e < len(entries):
        entry_date = entries[i_e]
        exit_date = exits[i_x] if i_x < len(exits) and exits[i_x] > entry_date else None
        if exit_date is None:
            exit_date = price.index[-1]
            i_e += 1
        else:
            i_e += 1
            i_x += 1

        entry_price = float(price.loc[entry_date])
        exit_price = float(price.loc[exit_date])
        pnl_pct = exit_price / entry_price - 1.0
        trades.append(
            {
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl_pct": pnl_pct,
            }
        )
    import pandas as pd

    return pd.DataFrame(trades)
