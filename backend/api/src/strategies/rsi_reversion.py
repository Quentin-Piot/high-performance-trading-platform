from __future__ import annotations
import pandas as pd
import numpy as np
from pydantic import Field

from domain.backtest import BacktestResult
from strategies.base import Strategy, StrategyParams
from strategies.metrics import (
    sharpe_ratio,
    max_drawdown,
    total_return,
    trade_summary_from_positions,
)


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
        rs = roll_up / (roll_down.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        return rsi

    def run(self, df: pd.DataFrame, params: RSIParams) -> BacktestResult:
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
        rsi = self._rsi(close, window=params.window)

        raw_signal = (rsi < params.rsi_low).astype(int)
        position = raw_signal.shift(1).fillna(0).astype(int) * params.position_size

        returns = close.pct_change(fill_method=None).fillna(0.0)
        trade_events = position.diff().abs().fillna(0)

        trade_costs = trade_events * params.commission
        strategy_returns = position * returns - trade_costs

        equity = (1.0 + strategy_returns).cumprod() * params.initial_capital
        if equity.isna().all():
            equity = pd.Series(params.initial_capital, index=close.index)

        total_ret = total_return(equity)
        sharpe_val = sharpe_ratio(strategy_returns, annualization=params.annualization)
        mdd_val = max_drawdown(equity)

        metrics = {
            "total_return": total_ret,
            "n_trades": int(trade_events.sum()),
        }

        trades = trade_summary_from_positions(position, close)

        return BacktestResult(
            equity=equity,
            pnl=total_ret,
            max_drawdown=mdd_val,
            sharpe_ratio=sharpe_val,
            returns=strategy_returns,
            metrics=metrics,
            signals=position,
            trades=trades,
        )
