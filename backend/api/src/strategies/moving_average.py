from __future__ import annotations

import pandas as pd
from pydantic import Field, model_validator

from domain.backtest import BacktestResult
from strategies.backtest_result_builder import BacktestResultBuilder
from strategies.base import Strategy, StrategyParams
from strategies.data_processor import DataProcessor


class MovingAverageParams(StrategyParams):
    short_window: int = Field(20, gt=0)
    long_window: int = Field(50, gt=0)
    annualization: int = Field(252, gt=0)

    @model_validator(mode="after")
    def validate_windows(self):
        if self.short_window >= self.long_window:
            raise ValueError("short_window must be less than long_window")
        return self


class MovingAverageStrategy(Strategy):
    ParamsModel = MovingAverageParams
    name = "moving-average-crossover"

    def run(self, df: pd.DataFrame, params: MovingAverageParams) -> BacktestResult:  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Vectorized moving average crossover backtest.
        Assumptions:
          - df must contain 'close' column and datetime index (or 'date' column convertible)
          - positions are full/allocation (0 or 1) times position_size
          - commission is applied as a simple penalty on returns at trade times (approximation)
        """
        data = DataProcessor.prepare_dataframe(df, params.start_date, params.end_date)
        close = data["close"].astype(float)
        short_ma = close.rolling(
            window=params.short_window, min_periods=params.short_window
        ).mean()
        long_ma = close.rolling(
            window=params.long_window, min_periods=params.long_window
        ).mean()
        raw_signal = (short_ma > long_ma).astype(int)
        position = raw_signal.shift(1).fillna(0).astype(int) * params.position_size  # pyright: ignore[reportAttributeAccessIssue]
        strategy_returns, _ = DataProcessor.calculate_returns_and_costs(
            position,
            close,  # pyright: ignore[reportArgumentType]
            params.commission,
        )
        equity = DataProcessor.calculate_equity_curve(
            strategy_returns, params.initial_capital, close.index
        )
        return (
            BacktestResultBuilder()
            .with_equity(equity)
            .with_returns(strategy_returns)
            .with_position(position)
            .with_close_prices(close)  # pyright: ignore[reportArgumentType]
            .with_annualization(params.annualization)
            .build()
        )
