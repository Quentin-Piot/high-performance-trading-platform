from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import Field, model_validator

from domain.backtest import BacktestResult
from strategies.backtest_result_builder import BacktestResultBuilder
from strategies.base import Strategy, StrategyParams
from strategies.data_processor import DataProcessor


class RSIParams(StrategyParams):
    window: int = Field(14, gt=0)
    rsi_low: int = Field(30, ge=1, le=100)
    rsi_high: int = Field(70, ge=1, le=100)
    annualization: int = Field(252, gt=0)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.rsi_low >= self.rsi_high:
            raise ValueError("rsi_low must be less than rsi_high")
        return self


class RSIReversionStrategy(Strategy):
    ParamsModel = RSIParams
    name = "rsi-reversion"

    def _rsi(self, series: pd.Series, window: int) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)
        roll_up = up.rolling(window=window, min_periods=window).mean()
        roll_down = down.rolling(window=window, min_periods=window).mean()
        rs = roll_up / roll_down.replace(0, np.nan)  # pyright: ignore[reportAttributeAccessIssue]
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.where(roll_down != 0, 100.0)  # pyright: ignore[reportAttributeAccessIssue]
        rsi = rsi.where(roll_up != 0, 0.0)  # pyright: ignore[reportAttributeAccessIssue]
        rsi = rsi.where(  # pyright: ignore[reportAttributeAccessIssue]
            ~((roll_up == 0) & (roll_down == 0)), 50.0
        )
        rsi = rsi.fillna(50)
        return rsi

    def run(self, df: pd.DataFrame, params: RSIParams) -> BacktestResult:  # pyright: ignore[reportIncompatibleMethodOverride]
        data = DataProcessor.prepare_dataframe(df, params.start_date, params.end_date)
        close = data["close"].astype(float)
        rsi = self._rsi(close, window=params.window)  # pyright: ignore[reportArgumentType]
        state = pd.Series(np.nan, index=close.index, dtype=float)
        state.loc[rsi < params.rsi_low] = 1.0
        state.loc[rsi > params.rsi_high] = 0.0
        raw_signal = state.ffill().fillna(0.0)
        position = raw_signal.shift(1).fillna(0.0) * params.position_size  # pyright: ignore[reportArgumentType]
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
