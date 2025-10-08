from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from datetime import datetime
from typing import Dict, Any


@dataclass
class BacktestParams:
    """
    Paramètres passés à une stratégie pour un backtest.
    """

    start_date: datetime
    end_date: datetime
    strategy_params: Dict[
        str, Any
    ]  # Ex: {"short_window": 20, "long_window": 50} pour MovingAverage
    symbol: str  # Ex: "AAPL"


@dataclass
class BacktestResult:
    """
    Résultat d'un backtest.
    equity: Série temporelle représentant l'évolution de l'équity curve
    pnl: Profit & Loss total
    drawdown: Max drawdown
    sharpe: Ratio de Sharpe
    """

    equity: pd.Series
    pnl: float
    max_drawdown: float
    sharpe_ratio: float
