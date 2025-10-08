from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional
from pydantic import Field

from ..domain.models import BacktestResult
from ._base import Strategy, StrategyParams
from ._metrics import (
    sharpe_ratio,
    max_drawdown,
    total_return,
    trade_summary_from_positions,
)


class MovingAverageParams(StrategyParams):
    short_window: int = Field(20, gt=0)
    long_window: int = Field(50, gt=0)
    annualization: int = Field(252, gt=0)


class MovingAverageStrategy(Strategy):
    ParamsModel = MovingAverageParams
    name = "moving-average-crossover"

    def run(self, df: pd.DataFrame, params: MovingAverageParams) -> BacktestResult:
        """
        Vectorized moving average crossover backtest.
        Assumptions:
          - df must contain 'close' column and datetime index (or 'date' column convertible)
          - positions are full/allocation (0 or 1) times position_size
          - commission is applied as a simple penalty on returns at trade times (approximation)
        """
        # Validate / prepare data
        data = df.copy()
        if "date" in data.columns and not isinstance(data.index, pd.DatetimeIndex):
            data["date"] = pd.to_datetime(data["date"])
            data = data.set_index("date")
        data = data.sort_index()
        if params.start_date:
            data = data.loc[data.index >= pd.to_datetime(params.start_date)]
        if params.end_date:
            data = data.loc[data.index <= pd.to_datetime(params.end_date)]
        if data.empty:
            raise ValueError("No data in selected date range")

        close = data["close"].astype(float)

        # Compute moving averages
        short_ma = close.rolling(window=params.short_window, min_periods=1).mean()
        long_ma = close.rolling(window=params.long_window, min_periods=1).mean()

        # Generate signals (1 = long, 0 = flat). N.B. no leverage/shorts here.
        raw_signal = (short_ma > long_ma).astype(int)

        # Apply shift to avoid look-ahead: position is signal from previous bar
        position = raw_signal.shift(1).fillna(0).astype(int) * params.position_size

        # Returns
        returns = close.pct_change().fillna(0.0)
        # trade detection
        trade_events = position.diff().abs().fillna(0)

        # Approximate commission & slippage: subtract fractional cost at trade times.
        # Commission is expressed as fraction of portfolio per trade (approx). This is a pragmatic simplification.
        trade_costs = trade_events * params.commission

        strategy_returns = position * returns - trade_costs

        equity = (1.0 + strategy_returns).cumprod() * params.initial_capital
        # If equity all NaN (edge case), replace with initial capital series
        if equity.isna().all():
            equity = pd.Series(params.initial_capital, index=close.index)

        metrics = {
            "total_return": total_return(equity),
            "sharpe": sharpe_ratio(
                strategy_returns, annualization=params.annualization
            ),
            "max_drawdown": max_drawdown(equity),
            "n_trades": int(trade_events.sum()),
        }

        trades = trade_summary_from_positions(position, close)

        return BacktestResult(
            equity=equity,
            returns=strategy_returns,
            metrics=metrics,
            signals=position,
            trades=trades,
        )
