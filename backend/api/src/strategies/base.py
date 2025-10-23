from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd
from pydantic import BaseModel


class StrategyParams(BaseModel):
    """
    Base Pydantic model for strategy parameters.
    All strategies should extend this.
    """

    model_config = {"arbitrary_types_allowed": True}

    # common params present in all strategies
    initial_capital: float = 10_000.0
    commission: float = 0.0  # fraction per trade (e.g. 0.001 = 0.1%)
    slippage: float = 0.0  # fraction applied similarly (approx.)
    position_size: float = 1.0  # fraction of capital per trade (1.0 = full)
    start_date: datetime | None = None
    end_date: datetime | None = None
    timeframe: str = "1d"  # informative


class Strategy(ABC):
    """
    Abstract strategy interface.
    Concrete strategies must:
    - provide a Params model (pydantic)
    - implement run(df, params) -> BacktestResult
    """

    ParamsModel: type[StrategyParams] = StrategyParams
    name: str = "base-strategy"

    @abstractmethod
    def run(self, df: pd.DataFrame, params: StrategyParams):
        """Execute strategy on df (must contain 'close' column)."""
        ...
