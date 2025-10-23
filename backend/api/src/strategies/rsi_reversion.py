from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import Field

from domain.backtest import BacktestResult
from strategies.backtest_result_builder import BacktestResultBuilder
from strategies.base import Strategy, StrategyParams
from strategies.data_processor import DataProcessor


class RSIParams(StrategyParams):
    window: int = Field(14, gt=0)
    rsi_low: int = Field(30, ge=1, le=100)
    rsi_high: int = Field(70, ge=1, le=100)
    annualization: int = Field(252, gt=0)


class RSIReversionStrategy(Strategy):
    ParamsModel = RSIParams
    name = "rsi-reversion"

    def _rsi(self, series: pd.Series, window: int) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)
        roll_up = up.rolling(window=window, min_periods=1).mean()
        roll_down = down.rolling(window=window, min_periods=1).mean()
        rs = roll_up / roll_down.replace(0, np.nan)
        # Avoid division by zero and handle NaN values properly
        rs = rs.replace([np.inf, -np.inf], np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        return rsi

    def run(self, df: pd.DataFrame, params: RSIParams) -> BacktestResult:
        # Prepare data using DataProcessor
        data = DataProcessor.prepare_dataframe(df, params.start_date, params.end_date)
        close = data["close"].astype(float)
        
        # Calculate RSI
        rsi = self._rsi(close, window=params.window)

        # Generate signals: buy when RSI < rsi_low
        raw_signal = (rsi < params.rsi_low).astype(int)
        position = raw_signal.shift(1).fillna(0).astype(int) * params.position_size

        # Calculate returns and costs using DataProcessor
        strategy_returns, _ = DataProcessor.calculate_returns_and_costs(
            position, close, params.commission
        )

        # Calculate equity curve using DataProcessor
        equity = DataProcessor.calculate_equity_curve(
            strategy_returns, params.initial_capital, close.index
        )

        # Build result using BacktestResultBuilder
        return (
            BacktestResultBuilder()
            .with_equity(equity)
            .with_returns(strategy_returns)
            .with_position(position)
            .with_close_prices(close)
            .with_annualization(params.annualization)
            .build()
        )
