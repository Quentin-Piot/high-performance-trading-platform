"""
Builder for BacktestResult objects.

This module provides a consistent way to build BacktestResult objects
across different trading strategies.
"""
from __future__ import annotations

import pandas as pd

from domain.backtest import BacktestResult
from strategies.metrics import (
    max_drawdown,
    sharpe_ratio,
    total_return,
    trade_summary_from_positions,
)


class BacktestResultBuilder:
    """Builder class for creating BacktestResult objects consistently."""

    def __init__(self):
        self._equity: pd.Series | None = None
        self._returns: pd.Series | None = None
        self._position: pd.Series | None = None
        self._close: pd.Series | None = None
        self._annualization: int = 252

    def with_equity(self, equity: pd.Series) -> BacktestResultBuilder:
        """Set the equity curve."""
        self._equity = equity
        return self

    def with_returns(self, returns: pd.Series) -> BacktestResultBuilder:
        """Set the strategy returns."""
        self._returns = returns
        return self

    def with_position(self, position: pd.Series) -> BacktestResultBuilder:
        """Set the position series."""
        self._position = position
        return self

    def with_close_prices(self, close: pd.Series) -> BacktestResultBuilder:
        """Set the close price series."""
        self._close = close
        return self

    def with_annualization(self, annualization: int) -> BacktestResultBuilder:
        """Set the annualization factor."""
        self._annualization = annualization
        return self

    def build(self) -> BacktestResult:
        """
        Build the BacktestResult object.
        
        Returns:
            Complete BacktestResult object
            
        Raises:
            ValueError: If required data is missing
        """
        if self._equity is None:
            raise ValueError("Equity curve is required")
        if self._returns is None:
            raise ValueError("Strategy returns are required")
        if self._position is None:
            raise ValueError("Position series is required")
        if self._close is None:
            raise ValueError("Close price series is required")

        # Calculate core metrics
        total_ret = total_return(self._equity)
        sharpe_val = sharpe_ratio(self._returns, annualization=self._annualization)
        mdd_val = max_drawdown(self._equity)

        # Calculate trade events for metrics
        trade_events = self._position.diff().abs().fillna(0)
        
        # Build auxiliary metrics
        metrics = {
            "total_return": total_ret,
            "n_trades": int(trade_events.sum()),
        }

        # Generate trades summary
        trades = trade_summary_from_positions(self._position, self._close)

        return BacktestResult(
            equity=self._equity,
            pnl=total_ret,
            max_drawdown=mdd_val,
            sharpe_ratio=sharpe_val,
            returns=self._returns,
            metrics=metrics,
            signals=self._position,
            trades=trades,
        )