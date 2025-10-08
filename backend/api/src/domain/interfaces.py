from __future__ import annotations

from typing import Protocol
import pandas as pd
from abc import ABC, abstractmethod
from domain.backtest import BacktestResult, BacktestParams


class PriceSeriesSource(Protocol):
    def get_prices(
        self,
    ) -> pd.Series:  # returns Series indexed by datetime if available
        ...


class StrategyInterface(ABC):
    """
    Interface pour toutes les stratégies de backtest.
    Chaque stratégie doit implémenter la méthode run().
    """

    @abstractmethod
    def run(self, source: PriceSeriesSource, params: BacktestParams) -> BacktestResult:
        """
        Exécute la stratégie sur les données fournies par la source.

        Args:
            source: Source des prix (PriceSeriesSource)
            params: Paramètres du backtest spécifiques à la stratégie

        Returns:
            BacktestResult avec equity, PnL, drawdown, sharpe
        """
        pass
