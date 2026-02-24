import os
from datetime import datetime
from io import BytesIO

import pandas as pd
from fastapi import HTTPException, status

SYMBOL_TO_FILE = {
    "aapl": "AAPL.csv",
    "amzn": "AMZN.csv",
    "fb": "FB.csv",
    "googl": "GOOGL.csv",
    "msft": "MSFT.csv",
    "nflx": "NFLX.csv",
    "nvda": "NVDA.csv",
}


def validate_strategy_params(
    strategy: str,
    *,
    sma_short: int | None,
    sma_long: int | None,
    period: int | None,
    overbought: float | None,
    oversold: float | None,
) -> str:
    """Normalize and validate supported strategy names and required params."""
    strat = strategy.strip().lower()
    if strat in {"sma_crossover", "sma"}:
        if sma_short is None or sma_long is None:
            raise HTTPException(
                status_code=422,
                detail="Missing required parameters for SMA: sma_short and sma_long",
            )
    elif strat in {"rsi", "rsi_reversion"}:
        if period is None or overbought is None or oversold is None:
            raise HTTPException(
                status_code=422,
                detail="Missing required parameters for RSI: period, overbought, oversold",
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported strategy: {strategy}")
    return strat


def _parse_date_input(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail="Invalid date format. Use YYYY-MM-DD"
        ) from e


def load_filtered_local_dataset_df(
    symbol: str,
    start_date: str | datetime,
    end_date: str | datetime,
) -> tuple[pd.DataFrame, str]:
    """Load and date-filter a supported local CSV dataset."""
    symbol_lower = symbol.lower()
    if symbol_lower not in SYMBOL_TO_FILE:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} not supported. Available symbols: {list(SYMBOL_TO_FILE.keys())}",
        )

    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    datasets_path = os.path.join(current_dir, "datasets")
    data_file = SYMBOL_TO_FILE[symbol_lower]
    file_path = os.path.join(datasets_path, data_file)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset file not found for symbol {symbol}",
        )

    df = pd.read_csv(file_path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "date" not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset file for {symbol} does not contain a date column",
        )

    start_dt = _parse_date_input(start_date)
    end_dt = _parse_date_input(end_date)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
    filtered_df = df.loc[mask]
    if filtered_df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No data available for symbol {symbol} in the specified date range",
        )
    return filtered_df, data_file


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()
