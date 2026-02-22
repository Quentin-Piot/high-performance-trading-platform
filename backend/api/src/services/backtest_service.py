from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import pandas as pd

from domain.interfaces import PriceSeriesSource
from strategies.moving_average import MovingAverageParams, MovingAverageStrategy
from strategies.rsi_reversion import RSIParams, RSIReversionStrategy

logger = logging.getLogger("services.backtest")


def _resolve_price_column(df: pd.DataFrame, price_type: str) -> str:
    """Return the name of the price column to use, raising ValueError if not found."""
    if price_type == "adj_close":
        col = next((c for c in ["adj close", "adj_close"] if c in df.columns), None)
        if col:
            return col
    col = next((c for c in ["close"] if c in df.columns), None)
    if col:
        return col
    col = next((c for c in ["adj close", "adj_close"] if c in df.columns), None)
    if col:
        return col
    raise ValueError("CSV must contain a 'close' or 'adj close' column")


def _read_csv_to_series(
    file_obj: io.BytesIO | bytes, price_type: str = "close"
) -> pd.Series:
    if isinstance(file_obj, (bytes, bytearray)):
        buffer = io.BytesIO(file_obj)
        df = pd.read_csv(buffer)
    else:
        df = pd.read_csv(file_obj)
    df.columns = [str(c).strip().lower() for c in df.columns]
    price_col = _resolve_price_column(df, price_type)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
        series = pd.Series(df.set_index("date")[price_col].astype(float))
        series.index = pd.DatetimeIndex(series.index)
        return series
    return pd.Series(df[price_col].astype(float).values, dtype=float)


class CsvBytesPriceSeriesSource(PriceSeriesSource):
    def __init__(self, data: bytes | io.BytesIO, price_type: str = "close"):
        self._data = data
        self._price_type = price_type

    def get_prices(self) -> pd.Series:
        return _read_csv_to_series(self._data, self._price_type)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert CSV data to DataFrame for Monte Carlo processing."""
        if isinstance(self._data, (bytes, bytearray)):
            buffer = io.BytesIO(self._data)
            df = pd.read_csv(buffer)
        else:
            df = pd.read_csv(self._data)
        df.columns = [str(c).strip().lower() for c in df.columns]
        price_col = _resolve_price_column(df, self._price_type)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.sort_values("date")
            df = df.set_index("date")
        if price_col != "close":
            if "close" in df.columns:
                df = df.drop(columns=["close"])
            df = df.rename(columns={price_col: "close"})
        df["close"] = df["close"].astype(float)
        return df


@dataclass
class ServiceBacktestResult:
    equity: pd.Series
    pnl: float
    drawdown: float
    sharpe: float


def run_sma_crossover(
    source: PriceSeriesSource, sma_short: int, sma_long: int
) -> ServiceBacktestResult:
    df = source.to_dataframe()
    params = MovingAverageParams(  # pyright: ignore[reportCallIssue]
        short_window=sma_short,
        long_window=sma_long,
        position_size=1.0,
        initial_capital=1.0,
        commission=0.0,
    )
    strategy = MovingAverageStrategy()
    result = strategy.run(df, params)
    return ServiceBacktestResult(
        equity=result.equity,
        pnl=result.pnl,
        drawdown=result.max_drawdown,
        sharpe=result.sharpe_ratio,
    )


def run_rsi(
    source: PriceSeriesSource, period: int, overbought: float, oversold: float
) -> ServiceBacktestResult:
    df = source.to_dataframe()
    params = RSIParams(  # pyright: ignore[reportCallIssue]
        window=period,
        rsi_low=oversold,
        rsi_high=overbought,
        position_size=1.0,
        initial_capital=1.0,
        commission=0.0,
    )
    strategy = RSIReversionStrategy()
    result = strategy.run(df, params)
    return ServiceBacktestResult(
        equity=result.equity,
        pnl=result.pnl,
        drawdown=result.max_drawdown,
        sharpe=result.sharpe_ratio,
    )
