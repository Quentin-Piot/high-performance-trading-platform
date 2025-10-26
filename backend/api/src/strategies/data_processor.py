"""
Data processing utilities for trading strategies.
This module contains common data preparation and validation logic
shared across different trading strategies.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd


class DataProcessor:
    """Handles common data preparation tasks for trading strategies."""
    @staticmethod
    def prepare_dataframe(
        df: pd.DataFrame,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pd.DataFrame:
        """
        Prepare and validate DataFrame for strategy execution.
        Args:
            df: Input DataFrame with market data
            start_date: Optional start date filter
            end_date: Optional end date filter
        Returns:
            Processed DataFrame with datetime index
        Raises:
            ValueError: If no data in selected date range or missing required columns
        """
        data = df.copy()
        if "date" in data.columns and not isinstance(data.index, pd.DatetimeIndex):
            data["date"] = pd.to_datetime(data["date"])
            data = data.set_index("date")
        data = data.sort_index()
        if start_date:
            mask = data.index >= pd.to_datetime(start_date)
            data = data.loc[mask]
        if end_date:
            mask = data.index <= pd.to_datetime(end_date)
            data = data.loc[mask]
        if data.empty:
            raise ValueError("No data in selected date range")
        if "close" not in data.columns:
            raise ValueError("DataFrame must contain 'close' column")
        return data
    @staticmethod
    def calculate_returns_and_costs(
        position: pd.Series,
        close: pd.Series,
        commission: float,
    ) -> tuple[pd.Series, pd.Series]:
        """
        Calculate strategy returns and trading costs.
        Args:
            position: Position series (0/1 allocation)
            close: Close price series
            commission: Commission rate as fraction
        Returns:
            Tuple of (strategy_returns, trade_costs)
        """
        returns = close.pct_change(fill_method=None).fillna(0.0)
        trade_events = position.diff().abs().fillna(0)
        trade_costs = trade_events * commission
        strategy_returns = position * returns - trade_costs
        return strategy_returns, trade_costs
    @staticmethod
    def calculate_equity_curve(
        strategy_returns: pd.Series,
        initial_capital: float,
        close_index: pd.Index,
    ) -> pd.Series:
        """
        Calculate equity curve from strategy returns.
        Args:
            strategy_returns: Series of strategy returns
            initial_capital: Starting capital amount
            close_index: Index for fallback equity series
        Returns:
            Equity curve series
        """
        equity = (1.0 + strategy_returns).cumprod() * initial_capital
        if len(equity.dropna()) == 0:
            equity = pd.Series(initial_capital, index=close_index)
        return equity
