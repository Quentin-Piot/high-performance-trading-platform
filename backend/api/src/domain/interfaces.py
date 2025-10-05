from __future__ import annotations

from typing import Protocol
import pandas as pd


class PriceSeriesSource(Protocol):
    def get_prices(self) -> pd.Series:  # returns Series indexed by datetime if available
        ...