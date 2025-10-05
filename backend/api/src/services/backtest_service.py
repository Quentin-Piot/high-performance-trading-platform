from __future__ import annotations

from typing import BinaryIO, Tuple, Union

import numpy as np
import pandas as pd
import io
import logging
from domain.interfaces import PriceSeriesSource
from domain.backtest import BacktestResult

logger = logging.getLogger("services.backtest")


def _read_csv_to_series(file_obj: Union[BinaryIO, bytes]) -> pd.Series:
    logger.info(
        "Reading CSV input",
        extra={
            "input_type": type(file_obj).__name__,
        },
    )
    if isinstance(file_obj, (bytes, bytearray)):
        buffer = io.BytesIO(file_obj)
        df = pd.read_csv(buffer)
    else:
        df = pd.read_csv(file_obj)

    # Normalisation des noms de colonnes (insensible à la casse)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Choix de la colonne de prix de clôture
    price_col = None
    if "close" in df.columns:
        price_col = "close"
    elif "adj close" in df.columns:
        price_col = "adj close"
    elif "adj_close" in df.columns:
        price_col = "adj_close"

    if not price_col:
        logger.error(
            "Price column not found",
            extra={"columns": df.columns.tolist()},
        )
        raise ValueError("CSV doit contenir une colonne 'close' ou 'adj close'")

    # Tri par date si présente
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        nat_count = int(df["date"].isna().sum())
        df = df.sort_values("date")
        logger.info(
            "Date column detected; sorted by date",
            extra={"rows": int(len(df)), "nat_dates": nat_count},
        )

    logger.info(
        "Selected price column",
        extra={"price_col": price_col, "rows": int(len(df))},
    )
    # Conserver l'index date si disponible
    if "date" in df.columns:
        series = df.set_index("date")[price_col].astype(float)
        series.index = pd.DatetimeIndex(series.index)
        return series
    # Sinon, retourner une Series simple avec RangeIndex
    return pd.Series(df[price_col].astype(float).values, dtype=float)


def sma_crossover_backtest(file_obj: Union[BinaryIO, bytes], sma_short: int, sma_long: int) -> Tuple[pd.Series, float, float, float]:
    if sma_short <= 0 or sma_long <= 0 or sma_short >= sma_long:
        logger.warning(
            "Invalid SMA parameters",
            extra={"sma_short": sma_short, "sma_long": sma_long},
        )
        raise ValueError("Paramètres SMA invalides: sma_short>0, sma_long>0 et sma_short<sma_long")

    prices = _read_csv_to_series(file_obj)
    logger.info(
        "Backtest starting",
        extra={"sma_short": sma_short, "sma_long": sma_long, "n_prices": int(len(prices))},
    )
    s_short = prices.rolling(window=sma_short, min_periods=sma_short).mean()
    s_long = prices.rolling(window=sma_long, min_periods=sma_long).mean()
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

    logger.info(
        "Backtest completed",
        extra={
            "equity_len": int(len(equity)),
            "pnl": pnl,
            "max_drawdown": max_dd,
            "sharpe": sharpe,
        },
    )

    return equity, pnl, max_dd, sharpe


def run_sma_crossover(source: PriceSeriesSource, sma_short: int, sma_long: int) -> BacktestResult:
    if sma_short <= 0 or sma_long <= 0 or sma_short >= sma_long:
        logger.warning(
            "Invalid SMA parameters",
            extra={"sma_short": sma_short, "sma_long": sma_long},
        )
        raise ValueError("Paramètres SMA invalides: sma_short>0, sma_long>0 et sma_short<sma_long")

    prices = source.get_prices()
    logger.info(
        "Backtest starting",
        extra={"sma_short": sma_short, "sma_long": sma_long, "n_prices": int(len(prices))},
    )

    s_short = prices.rolling(window=sma_short, min_periods=sma_short).mean()
    s_long = prices.rolling(window=sma_long, min_periods=sma_long).mean()
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

    logger.info(
        "Backtest completed",
        extra={
            "equity_len": int(len(equity)),
            "pnl": pnl,
            "max_drawdown": max_dd,
            "sharpe": sharpe,
        },
    )

    return BacktestResult(equity=equity, pnl=pnl, drawdown=max_dd, sharpe=sharpe)


class CsvBytesPriceSeriesSource(PriceSeriesSource):
    def __init__(self, data: Union[BinaryIO, bytes]):
        self._data = data

    def get_prices(self) -> pd.Series:
        return _read_csv_to_series(self._data)