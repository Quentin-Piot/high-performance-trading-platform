from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class BacktestResult:
    equity: pd.Series
    pnl: float
    drawdown: float
    sharpe: float