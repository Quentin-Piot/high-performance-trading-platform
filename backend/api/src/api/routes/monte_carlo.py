"""
Monte Carlo simulation API endpoints.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    status,
)
from pydantic import BaseModel

from utils.date_validation import (
    get_all_symbols_date_ranges,
    validate_date_range_for_csv_bytes,
    validate_date_range_for_symbol,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monte-carlo", tags=["monte-carlo"])


class SymbolDateRangeResponse(BaseModel):
    """Response model for symbol date range information"""
    symbol: str
    min_date: datetime
    max_date: datetime


class AllSymbolsDateRangesResponse(BaseModel):
    """Response model for all symbols date ranges"""
    symbols: list[SymbolDateRangeResponse]


@router.post("/run")
async def run_monte_carlo_sync(
    symbol: str = Query(..., description="Symbol to use from local datasets (e.g., AAPL, AMZN)"),
    start_date: datetime = Query(..., description="Start date for simulation (YYYY-MM-DD)"),
    end_date: datetime = Query(..., description="End date for simulation (YYYY-MM-DD)"),
    num_runs: int = Query(..., ge=1, le=10000, description="Number of Monte Carlo runs"),
    initial_capital: float = Query(..., gt=0, description="Initial capital for simulation"),
    # Strategy parameters (consistent with backtest.py)
    strategy: str = Query("sma_crossover", description="Strategy name (e.g., sma_crossover, rsi)"),
    # SMA parameters (optional, required only if strategy = sma_crossover/sma)
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    # RSI parameters (optional, required only if strategy = rsi/rsi_reversion)
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(None, ge=0, le=100, description="Overbought threshold (0-100)"),
    oversold: float | None = Query(None, ge=0, le=100, description="Oversold threshold (0-100)"),
    file: UploadFile | None = File(None),
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation synchronously.
    
    This endpoint executes the simulation immediately and returns results.
    For large simulations, consider using the /async endpoint.
    """
    try:
        import os
        from io import BytesIO

        import pandas as pd

        # Validate strategy parameters
        if strategy in {"sma_crossover", "sma"}:
            if sma_short is None or sma_long is None:
                raise HTTPException(
                    status_code=422,
                    detail="Missing required parameters for SMA: sma_short and sma_long",
                )
        elif strategy in {"rsi", "rsi_reversion"}:
            if period is None or overbought is None or oversold is None:
                raise HTTPException(
                    status_code=422,
                    detail="Missing required parameters for RSI: period, overbought, oversold",
                )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported strategy: {strategy}")

        # Build strategy parameters dict
        strategy_params_dict = {
            "strategy": strategy,
            "sma_short": sma_short,
            "sma_long": sma_long,
            "period": period,
            "overbought": overbought,
            "oversold": oversold,
        }

        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )

        # Load data
        if file:
            # Use uploaded file
            contents = await file.read()
            df = pd.read_csv(BytesIO(contents))

            # Validate date range for uploaded data
            validate_date_range_for_csv_bytes(contents, start_date, end_date)
        else:
            # Use symbol-based data
            validate_date_range_for_symbol(symbol, start_date, end_date)

            # Map symbol to dataset file (consistent with backtest.py)
            symbol_to_file = {
                "aapl": "AAPL.csv",
                "amzn": "AMZN.csv",
                "fb": "FB.csv",
                "googl": "GOOGL.csv",
                "msft": "MSFT.csv",
                "nflx": "NFLX.csv",
                "nvda": "NVDA.csv",
            }

            symbol_lower = symbol.lower()
            if symbol_lower not in symbol_to_file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Symbol {symbol} not supported. Available symbols: {list(symbol_to_file.keys())}"
                )

            # Load historical data
            datasets_path = "/Users/juliettecattin/WebstormProjects/high-performance-trading-platform/backend/api/src/datasets"
            data_file = symbol_to_file[symbol_lower]
            file_path = os.path.join(datasets_path, data_file)

            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Data file not found: {data_file}"
                )

            df = pd.read_csv(file_path)

        # Filter data by date range
        # Handle both 'date' and 'Date' column names
        date_column = 'date' if 'date' in df.columns else 'Date'
        df[date_column] = pd.to_datetime(df[date_column])
        filtered_df = df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]
        print(f"Date column: {date_column}")
        print(f"Filtered DataFrame head:\n{filtered_df.head()}")
        print(f"Filtered DataFrame tail:\n{filtered_df.tail()}")
        print(f"Filtered DataFrame empty: {filtered_df.empty}")

        if filtered_df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data available for the specified date range"
            )

        # Convert filtered DataFrame to CSV bytes
        csv_buffer = BytesIO()
        filtered_df.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue()

        # Set default strategy parameters - remove the old default_strategy_params logic
        # strategy_params_dict already contains all needed parameters

        # Run Monte Carlo simulation synchronously
        from services.mc_backtest_service import run_monte_carlo_on_df

        # Extract strategy name from strategy_params_dict
        strategy_name = strategy_params_dict.get("strategy", "sma_crossover")

        result = run_monte_carlo_on_df(
            csv_data=csv_bytes,
            filename=file.filename if file else f"{symbol}.csv",
            strategy_name=strategy_name,
            strategy_params=strategy_params_dict,
            runs=num_runs,
            method="bootstrap",  # Default method
            parallel_workers=1,  # Single worker for sync execution
        )

        # Convert MonteCarloSummary to MonteCarloResponse format expected by frontend
        from domain.schemas.backtest import MonteCarloBacktestResult, MonteCarloResponse
        
        monte_carlo_result = MonteCarloBacktestResult(
            filename=result.filename,
            method=result.method,
            runs=result.runs,
            successful_runs=result.successful_runs,
            metrics_distribution=result.metrics_distribution,
            equity_envelope=result.equity_envelope
        )
        
        response = MonteCarloResponse(
            results=[monte_carlo_result],
            aggregated_metrics=None  # Single file, no aggregation needed
        )
        
        return response.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Monte Carlo simulation failed", extra={
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        ) from e

@router.post("/async")
async def submit_async_job(
    symbol: str = Query(..., description="Symbol to use from local datasets (e.g., AAPL, AMZN)"),
    start_date: datetime = Query(..., description="Start date for simulation (YYYY-MM-DD)"),
    end_date: datetime = Query(..., description="End date for simulation (YYYY-MM-DD)"),
    num_runs: int = Query(..., ge=1, le=10000, description="Number of Monte Carlo runs"),
    initial_capital: float = Query(..., gt=0, description="Initial capital for simulation"),
    # Strategy parameters (consistent with sync endpoint)
    strategy: str = Query("sma_crossover", description="Strategy name (e.g., sma_crossover, rsi)"),
    # SMA parameters (optional, required only if strategy = sma_crossover/sma)
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    # RSI parameters (optional, required only if strategy = rsi/rsi_reversion)
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(None, ge=0, le=100, description="Overbought threshold (0-100)"),
    oversold: float | None = Query(None, ge=0, le=100, description="Oversold threshold (0-100)"),
    file: UploadFile | None = File(None),
) -> dict[str, Any]:
    """
    Submit Monte Carlo simulation job for asynchronous processing.
    
    This endpoint uses a simple in-process worker without Redis/queue dependencies.
    """
    try:

        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()

        # Validate strategy parameters (consistent with sync endpoint)
        if strategy in {"sma_crossover", "sma"}:
            if sma_short is None or sma_long is None:
                raise HTTPException(
                    status_code=422,
                    detail="Missing required parameters for SMA: sma_short and sma_long",
                )
        elif strategy in {"rsi", "rsi_reversion"}:
            if period is None or overbought is None or oversold is None:
                raise HTTPException(
                    status_code=422,
                    detail="Missing required parameters for RSI: period, overbought, oversold",
                )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported strategy: {strategy}")

        # Build strategy parameters dict (consistent with sync endpoint)
        strategy_params_dict = {
            "strategy": strategy,
            "sma_short": sma_short,
            "sma_long": sma_long,
            "period": period,
            "overbought": overbought,
            "oversold": oversold,
        }

        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )

        # Handle CSV data
        csv_data = b""
        if file:
            csv_data = await file.read()
        else:
            # Load symbol data like in sync endpoint
            import os

            import pandas as pd

            from utils.date_validation import validate_date_range_for_symbol

            # Validate symbol and date range
            validation_result = validate_date_range_for_symbol(symbol, start_date, end_date)
            if not validation_result['valid']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=validation_result['error_message']
                )

            # Map symbol to dataset file (consistent with backtest.py)
            symbol_to_file = {
                "aapl": "AAPL.csv",
                "amzn": "AMZN.csv",
                "fb": "FB.csv",
                "googl": "GOOGL.csv",
                "msft": "MSFT.csv",
                "nflx": "NFLX.csv",
                "nvda": "NVDA.csv",
            }

            symbol_lower = symbol.lower()
            if symbol_lower not in symbol_to_file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Symbol {symbol} not supported. Available symbols: {list(symbol_to_file.keys())}"
                )

            # Load and filter dataset
            datasets_path = "/Users/juliettecattin/WebstormProjects/high-performance-trading-platform/backend/api/src/datasets"
            csv_file_path = os.path.join(datasets_path, symbol_to_file[symbol_lower])

            if not os.path.exists(csv_file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dataset file not found for symbol {symbol}"
                )

            # Read and filter data by date range
            df = pd.read_csv(csv_file_path)
            df.columns = [str(c).strip().lower() for c in df.columns]

            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                # Filter data by date range
                filtered_df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

                if filtered_df.empty:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No data available for symbol {symbol} in the specified date range"
                    )

                # Convert filtered data to CSV bytes
                csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Dataset file for {symbol} does not contain a date column"
                )

        job_id = worker.submit_job(
            csv_data=csv_data,
            filename=file.filename if file else f"{symbol}_data.csv",
            strategy_name=strategy,  # Use the specified strategy
            strategy_params=strategy_params_dict,
            runs=num_runs
        )

        return {
            "job_id": job_id,
            "status": "submitted",
            "message": "Job submitted for processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit async job", extra={
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        ) from e

@router.get("/async/{job_id}")
async def get_async_job_status(job_id: str) -> dict[str, Any]:
    """Get status of an asynchronous job."""
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        job_status = worker.get_job_status(job_id)

        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        return job_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", extra={
            "job_id": job_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        ) from e

@router.delete("/async/{job_id}")
async def cancel_async_job(job_id: str) -> dict[str, Any]:
    """Cancel an asynchronous job."""
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        success = worker.cancel_job(job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or cannot be cancelled"
            )

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel job", extra={
            "job_id": job_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        ) from e

@router.get("/async")
async def list_async_jobs() -> dict[str, Any]:
    """List all asynchronous jobs."""
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        jobs = worker.list_jobs()

        return {
            "jobs": jobs,
            "total": len(jobs)
        }

    except Exception as e:
        logger.error("Failed to list jobs", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        ) from e

@router.get("/symbols/date-ranges", response_model=AllSymbolsDateRangesResponse)
async def get_symbols_date_ranges() -> AllSymbolsDateRangesResponse:
    """
    Get available date ranges for all supported symbols.
    
    Returns:
        Date range information for all symbols
    """
    try:
        date_ranges = get_all_symbols_date_ranges()

        symbols = [
            SymbolDateRangeResponse(
                symbol=symbol,
                min_date=date_range["min_date"],
                max_date=date_range["max_date"]
            )
            for symbol, date_range in date_ranges.items()
        ]

        return AllSymbolsDateRangesResponse(symbols=symbols)

    except Exception as e:
        logger.error("Failed to get symbols date ranges", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get date ranges: {str(e)}"
        ) from e

@router.websocket("/ws/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    
    This endpoint provides real-time updates for asynchronous jobs.
    """
    await websocket.accept()

    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()

        # Log WebSocket connection
        logger.info("WebSocket connection established", extra={"job_id": job_id})

        # Send initial status
        job_status = await worker.get_job_status(job_id)
        if job_status:
            await websocket.send_json(job_status)
        else:
            await websocket.send_json({
                "job_id": job_id,
                "status": "not_found",
                "error": "Job not found"
            })
            return

        # Monitor job progress
        while True:
            try:
                job_status = worker.get_job_status(job_id)
                if job_status:
                    await websocket.send_json(job_status)

                    # Break if job is completed or failed
                    if job_status.get("status") in ["completed", "failed", "cancelled"]:
                        break
                else:
                    break

                # Wait before next update
                await asyncio.sleep(1)

            except Exception as e:
                logger.error("Error in WebSocket progress monitoring", extra={
                    "job_id": job_id,
                    "error": str(e)
                })
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "error",
                    "error": str(e)
                })
                break

    except Exception as e:
        logger.error("WebSocket connection error", extra={
            "job_id": job_id,
            "error": str(e)
        })
    finally:
        logger.info("WebSocket connection closed", extra={"job_id": job_id})
        try:
            await websocket.close()
        except:
            pass
