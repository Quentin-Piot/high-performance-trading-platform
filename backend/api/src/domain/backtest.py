from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass
class BacktestParams:
    """
    Paramètres passés à une stratégie pour un backtest.
    """

    start_date: datetime
    end_date: datetime
    strategy_params: dict[
        str, Any
    ]  # Ex: {"short_window": 20, "long_window": 50} pour MovingAverage
    symbol: str  # Ex: "AAPL"


@dataclass
class BacktestResult:
    """
    Résultat d'un backtest unifié pour toutes les stratégies.

    Champs obligatoires (utilisés par les services et l'API):
    - equity: Série d'équity (niveau, pas rendement)
    - pnl: P&L total (rendement cumulatif ou montant)
    - max_drawdown: drawdown maximal
    - sharpe_ratio: ratio de Sharpe annualisé

    Champs optionnels (stratégies vectorisées avancées):
    - returns: Série de rendements de la stratégie
    - metrics: Dict des métriques supplémentaires (ex: total_return, n_trades)
    - signals: Série de positions/allocations au fil du temps
    - trades: DataFrame de synthèse des trades
    """

    equity: pd.Series
    pnl: float
    max_drawdown: float
    sharpe_ratio: float

    # Champs additionnels, renseignés par certaines stratégies
    returns: pd.Series | None = None
    metrics: dict[str, Any] | None = None
    signals: pd.Series | None = None
    trades: pd.DataFrame | None = None
