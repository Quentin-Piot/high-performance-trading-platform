from __future__ import annotations
import io
import logging
from typing import Union

import numpy as np
import pandas as pd

from dataclasses import dataclass
from domain.backtest import BacktestResult, BacktestParams
from domain.interfaces import PriceSeriesSource, StrategyInterface

logger = logging.getLogger("services.backtest")


def _read_csv_to_series(file_obj: Union[io.BytesIO, bytes]) -> pd.Series:
    """
    Lit un CSV et retourne une pd.Series des prix.
    """
    if isinstance(file_obj, (bytes, bytearray)):
        buffer = io.BytesIO(file_obj)
        df = pd.read_csv(buffer)
    else:
        df = pd.read_csv(file_obj)

    df.columns = [str(c).strip().lower() for c in df.columns]

    # Détection colonne prix
    price_col = next(
        (c for c in ["close", "adj close", "adj_close"] if c in df.columns), None
    )
    if not price_col:
        raise ValueError("CSV doit contenir une colonne 'close' ou 'adj close'")

    # Tri par date si présent
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
        series = df.set_index("date")[price_col].astype(float)
        series.index = pd.DatetimeIndex(series.index)
        return series

    return pd.Series(df[price_col].astype(float).values, dtype=float)


class CsvBytesPriceSeriesSource(PriceSeriesSource):
    """
    Source de prix à partir de CSV (bytes ou BinaryIO)
    """

    def __init__(self, data: Union[bytes, io.BytesIO]):
        self._data = data

    def get_prices(self) -> pd.Series:
        return _read_csv_to_series(self._data)


class SmaCrossoverStrategy(StrategyInterface):
    """
    Stratégie SMA Crossover implémentée comme StrategyInterface
    """

    def __init__(self, short_window: int, long_window: int):
        if short_window <= 0 or long_window <= 0 or short_window >= long_window:
            raise ValueError("Paramètres SMA invalides: short>0, long>0 et short<long")
        self.short_window = short_window
        self.long_window = long_window

    def run(self, source: PriceSeriesSource, params: BacktestParams) -> BacktestResult:
        prices = source.get_prices()
        s_short = prices.rolling(
            window=self.short_window, min_periods=self.short_window
        ).mean()
        s_long = prices.rolling(
            window=self.long_window, min_periods=self.long_window
        ).mean()
        position = (s_short > s_long).astype(int)

        returns = prices.pct_change().fillna(0.0)
        strat_returns = (position.shift(1).fillna(0) * returns).astype(float)

        equity = (1.0 + strat_returns).cumprod()
        pnl = float(equity.iloc[-1] - 1.0)

        peak = equity.cummax()
        drawdown = ((peak - equity) / peak).fillna(0.0)
        max_dd = float(drawdown.max())

        mean_ret, std_ret = strat_returns.mean(), strat_returns.std()
        sharpe = float((mean_ret / std_ret) * np.sqrt(252)) if std_ret > 0 else 0.0

        return BacktestResult(
            equity=equity,
            pnl=pnl,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
        )

class RsiStrategy(StrategyInterface):
    def __init__(self, period: int, overbought: float, oversold: float):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def run(self, source: PriceSeriesSource, params: BacktestParams) -> BacktestResult:
        prices = source.get_prices()
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(self.period, min_periods=self.period).mean()
        avg_loss = loss.rolling(self.period, min_periods=self.period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        position = rsi.apply(lambda x: 1 if x < self.oversold else (-1 if x > self.overbought else 0))
        returns = prices.pct_change().fillna(0.0)
        strat_returns = (position.shift(1).fillna(0) * returns).astype(float)

        equity = (1.0 + strat_returns).cumprod()
        pnl = float(equity.iloc[-1] - 1.0)
        peak = equity.cummax()
        drawdown = ((peak - equity) / peak).fillna(0.0)
        max_dd = float(drawdown.max())
        mean_ret, std_ret = strat_returns.mean(), strat_returns.std()
        sharpe = float((mean_ret / std_ret) * np.sqrt(252)) if std_ret > 0 else 0.0

        return BacktestResult(
            equity=equity,
            pnl=pnl,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe
        )


# --- Service-level orchestration helpers ---

@dataclass
class ServiceBacktestResult:
    """
    Thin wrapper tailored for API/consumer expectations.
    Mirrors BacktestResult but exposes drawdown/sharpe naming.
    """
    equity: pd.Series
    pnl: float
    drawdown: float
    sharpe: float


def run_sma_crossover(source: PriceSeriesSource, sma_short: int, sma_long: int) -> ServiceBacktestResult:
    """Run SMA crossover using the shared StrategyInterface and return API-friendly result."""
    logger.info("Run SMA crossover", extra={"sma_short": sma_short, "sma_long": sma_long})
    strat = SmaCrossoverStrategy(short_window=sma_short, long_window=sma_long)
    params = BacktestParams(
        start_date=pd.Timestamp.min.to_pydatetime(),
        end_date=pd.Timestamp.max.to_pydatetime(),
        strategy_params={"short_window": sma_short, "long_window": sma_long},
        symbol="unknown",
    )
    res: BacktestResult = strat.run(source, params)
    return ServiceBacktestResult(
        equity=res.equity,
        pnl=res.pnl,
        drawdown=res.max_drawdown,
        sharpe=res.sharpe_ratio,
    )


def sma_crossover_backtest(file_obj: Union[io.BytesIO, bytes], sma_short: int, sma_long: int):
    """
    Compatibility helper used by tests:
    Reads CSV, runs SMA crossover, returns tuple: (equity, pnl, drawdown, sharpe).
    """
    source = CsvBytesPriceSeriesSource(file_obj)
    result = run_sma_crossover(source, sma_short, sma_long)
    return result.equity, float(result.pnl), float(result.drawdown), float(result.sharpe)

def run_rsi(source: PriceSeriesSource, period: int, overbought: float, oversold: float) -> ServiceBacktestResult:
    strat = RsiStrategy(period=period, overbought=overbought, oversold=oversold)
    params = BacktestParams(
        start_date=pd.Timestamp.min.to_pydatetime(),
        end_date=pd.Timestamp.max.to_pydatetime(),
        strategy_params={"period": period, "overbought": overbought, "oversold": oversold},
        symbol="unknown",
    )
    res: BacktestResult = strat.run(source, params)
    return ServiceBacktestResult(
        equity=res.equity,
        pnl=res.pnl,
        drawdown=res.max_drawdown,
        sharpe=res.sharpe_ratio
    )
