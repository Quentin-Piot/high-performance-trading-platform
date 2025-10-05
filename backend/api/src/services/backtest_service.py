from __future__ import annotations

from typing import BinaryIO, Tuple, Union

import numpy as np
import pandas as pd
import io


def _read_csv_to_series(file_obj: Union[BinaryIO, bytes]) -> pd.Series:
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
        raise ValueError("CSV doit contenir une colonne 'close' ou 'adj close'")

    # Tri par date si présente
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

    return pd.Series(df[price_col].astype(float).values, dtype=float)


def sma_crossover_backtest(file_obj: Union[BinaryIO, bytes], sma_short: int, sma_long: int) -> Tuple[pd.Series, float, float, float]:
    if sma_short <= 0 or sma_long <= 0 or sma_short >= sma_long:
        raise ValueError("Paramètres SMA invalides: sma_short>0, sma_long>0 et sma_short<sma_long")

    prices = _read_csv_to_series(file_obj)
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

    return equity, pnl, max_dd, sharpe
