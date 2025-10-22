"""
Utilities for validating date ranges against available CSV data.
"""

import io
import os
from datetime import datetime
from functools import lru_cache

import pandas as pd


@lru_cache(maxsize=10)
def get_csv_date_range(csv_file_path: str) -> tuple[datetime, datetime]:
    """
    Get the date range available in a CSV file.

    Args:
        csv_file_path: Path to the CSV file

    Returns:
        Tuple of (min_date, max_date)

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV doesn't have valid date column
    """
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    df = pd.read_csv(csv_file_path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "date" not in df.columns:
        raise ValueError("CSV file must contain a 'date' column")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    if df.empty:
        raise ValueError("No valid dates found in CSV file")

    min_date = df["date"].min().to_pydatetime()
    max_date = df["date"].max().to_pydatetime()

    return min_date, max_date


def get_csv_date_range_from_bytes(csv_bytes: bytes) -> tuple[datetime, datetime]:
    """
    Get the date range from CSV bytes.

    Args:
        csv_bytes: Raw CSV file content

    Returns:
        Tuple of (min_date, max_date)

    Raises:
        ValueError: If CSV doesn't have valid date column or no dates
    """
    df = pd.read_csv(io.BytesIO(csv_bytes))
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "date" not in df.columns:
        raise ValueError("CSV must contain a 'date' column")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    if df.empty:
        raise ValueError("No valid dates found in CSV data")

    min_date = df["date"].min().to_pydatetime()
    max_date = df["date"].max().to_pydatetime()
    return min_date, max_date


def validate_date_range_for_csv_bytes(
    csv_bytes: bytes,
    start_date: datetime,
    end_date: datetime,
) -> dict[str, any]:
    """
    Validate requested date range against the available dates in uploaded CSV bytes.

    Returns structure similar to validate_date_range_for_symbol with filtered CSV data.
    """
    try:
        min_date, max_date = get_csv_date_range_from_bytes(csv_bytes)

        # Parse CSV and filter by date range
        df = pd.read_csv(io.BytesIO(csv_bytes))

        # Ensure date column exists and is properly formatted
        if "date" not in df.columns:
            raise ValueError("CSV must contain a 'date' column")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        if df.empty:
            raise ValueError("No valid dates found in CSV")

        # Filter by date range
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        filtered_df = df.loc[mask]

        # Convert filtered DataFrame back to CSV bytes
        csv_buffer = io.BytesIO()
        filtered_df.to_csv(csv_buffer, index=False)
        filtered_csv_bytes = csv_buffer.getvalue()

    except ValueError as e:
        return {
            "valid": False,
            "error_message": str(e),
            "available_range": None,
            "suggested_range": None,
            "filtered_csv": None,
        }

    available_range = {"min_date": min_date, "max_date": max_date}

    # Check if requested range is within available data
    if start_date < min_date or end_date > max_date:
        suggested_start = max(start_date, min_date)
        suggested_end = min(end_date, max_date)

        if suggested_start >= suggested_end:
            data_span = (max_date - min_date).days
            if data_span >= 365:
                # Suggest the last year of available data
                suggested_start = max_date - pd.DateOffset(years=1)
                suggested_end = max_date
            else:
                suggested_start = min_date
                suggested_end = max_date

        return {
            "valid": False,
            "error_message": (
                f"Requested date range ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) "
                f"is outside available data range ({min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')})"
            ),
            "available_range": available_range,
            "suggested_range": {
                "start_date": suggested_start,
                "end_date": suggested_end,
            },
            "filtered_csv": None,
        }

    return {
        "valid": True,
        "error_message": None,
        "available_range": available_range,
        "suggested_range": None,
        "filtered_csv": filtered_csv_bytes,
    }


def validate_date_range_for_symbol(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    # Use relative path that works in both dev and prod
    datasets_path: str = None
) -> dict[str, any]:
    """
    Validate if the requested date range is available for a given symbol.

    Args:
        symbol: Trading symbol (e.g., 'aapl', 'msft')
        start_date: Requested start date
        end_date: Requested end date
        datasets_path: Path to datasets directory

    Returns:
        Dict with validation result:
        {
            'valid': bool,
            'error_message': str (if not valid),
            'available_range': {'min_date': datetime, 'max_date': datetime},
            'suggested_range': {'start_date': datetime, 'end_date': datetime} (if not valid)
        }
    """
    # Set default datasets path if not provided
    if datasets_path is None:
        current_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to src/
        datasets_path = os.path.join(current_dir, "datasets")
    
    symbol_to_file = {
        "aapl": "AAPL.csv",
        "amzn": "AMZN.csv",
        "fb": "FB.csv",
        "googl": "GOOGL.csv",
        "msft": "MSFT.csv",
        "nflx": "NFLX.csv",
        "nvda": "NVDA.csv",
    }

    if symbol.lower() not in symbol_to_file:
        return {
            'valid': False,
            'error_message': f"Symbol {symbol} not supported. Available symbols: {list(symbol_to_file.keys())}",
            'available_range': None,
            'suggested_range': None
        }

    csv_file_path = os.path.join(datasets_path, symbol_to_file[symbol.lower()])

    try:
        min_date, max_date = get_csv_date_range(csv_file_path)
    except (FileNotFoundError, ValueError) as e:
        return {
            'valid': False,
            'error_message': f"Error reading data for {symbol}: {str(e)}",
            'available_range': None,
            'suggested_range': None
        }

    available_range = {'min_date': min_date, 'max_date': max_date}

    # Check if requested range is within available data
    if start_date < min_date or end_date > max_date:
        # Suggest a valid range
        suggested_start = max(start_date, min_date)
        suggested_end = min(end_date, max_date)

        # If the suggested range is still invalid (start >= end), suggest a reasonable default
        if suggested_start >= suggested_end:
            # Suggest last year of available data or first year if less than a year available
            data_span = (max_date - min_date).days
            if data_span >= 365:
                suggested_start = max_date - pd.DateOffset(years=1)
                suggested_end = max_date
            else:
                suggested_start = min_date
                suggested_end = max_date

        return {
            'valid': False,
            'error_message': f"Requested date range ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) is outside available data range ({min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')})",
            'available_range': available_range,
            'suggested_range': {
                'start_date': suggested_start,
                'end_date': suggested_end
            }
        }

    return {
        'valid': True,
        'error_message': None,
        'available_range': available_range,
        'suggested_range': None
    }


def get_all_symbols_date_ranges(
    # Use relative path that works in both dev and prod
    datasets_path: str = None
) -> dict[str, dict[str, datetime]]:
    """
    Get date ranges for all available symbols.

    Args:
        datasets_path: Path to datasets directory

    Returns:
        Dict mapping symbol to {'min_date': datetime, 'max_date': datetime}
    """
    # Set default datasets path if not provided
    if datasets_path is None:
        current_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to src/
        datasets_path = os.path.join(current_dir, "datasets")
    
    symbol_to_file = {
        "aapl": "AAPL.csv",
        "amzn": "AMZN.csv",
        "fb": "FB.csv",
        "googl": "GOOGL.csv",
        "msft": "MSFT.csv",
        "nflx": "NFLX.csv",
        "nvda": "NVDA.csv",
    }

    result = {}
    for symbol, filename in symbol_to_file.items():
        csv_file_path = os.path.join(datasets_path, filename)
        try:
            min_date, max_date = get_csv_date_range(csv_file_path)
            result[symbol] = {'min_date': min_date, 'max_date': max_date}
        except (FileNotFoundError, ValueError):
            # Skip symbols with missing or invalid data
            continue

    return result
