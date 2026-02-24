"""
Monte Carlo simulation API endpoints.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    status,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes._backtest_route_utils import (
    dataframe_to_csv_bytes,
    load_filtered_local_dataset_df,
    validate_strategy_params,
)
from core.logging import JOB_ID
from core.simple_auth import SimpleUser, get_current_user_simple_optional
from infrastructure.db import get_session
from infrastructure.repositories.backtest_history_repository import (
    BacktestHistoryRepository,
)
from infrastructure.repositories.jobs import JobRepository
from infrastructure.repositories.user_repository import UserRepository
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


def _db_status_from_runtime(status_value: str | None) -> str:
    if status_value == "running":
        return "processing"
    if status_value == "submitted":
        return "pending"
    return status_value or "pending"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


async def _best_effort_create_async_job_record(
    session: AsyncSession,
    *,
    job_id: str,
    filename: str,
    symbol: str,
    strategy: str,
    runs: int,
    method: str,
    price_type: str,
    normalize: bool,
) -> None:
    try:
        repo = JobRepository(session)
        existing = await repo.get_job_by_id(job_id)
        if existing:
            return
        await repo.create_job(
            job_id=job_id,
            status="pending",
            payload={
                "job_type": "monte_carlo_async",
                "symbol": symbol,
                "filename": filename,
                "strategy": strategy,
                "runs": runs,
                "method": method,
                "price_type": price_type,
                "normalize": normalize,
            },
        )
    except Exception as e:
        logger.warning(
            "Failed to persist async job creation",
            extra={"job_id": job_id, "error": str(e)},
        )


async def _best_effort_mirror_runtime_job_status(
    session: AsyncSession, job_status: dict[str, Any]
) -> None:
    job_id = str(job_status.get("job_id", ""))
    if not job_id:
        return
    try:
        repo = JobRepository(session)
        existing = await repo.get_job_by_id(job_id)
        payload_patch: dict[str, Any] = {
            key: job_status[key]
            for key in ("runs", "filename", "result")
            if key in job_status and job_status[key] is not None
        }
        if not existing:
            await repo.create_job(
                job_id=job_id,
                status=_db_status_from_runtime(job_status.get("status")),
                payload={
                    "job_type": "monte_carlo_async",
                    **payload_patch,
                },
            )
        elif payload_patch:
            await repo.merge_job_payload(job_id, payload_patch)

        started_at = _parse_iso_datetime(job_status.get("started_at"))
        completed_at = _parse_iso_datetime(job_status.get("completed_at"))
        progress = (
            float(job_status["progress"])
            if isinstance(job_status.get("progress"), (float, int))
            else 0.0
        )
        await repo.update_job_progress(
            job_id=job_id,
            progress=progress,
            started_at=started_at,
            completed_at=completed_at,
        )
        await repo.update_job_status(
            job_id=job_id,
            status=_db_status_from_runtime(job_status.get("status")),
            error=job_status.get("error"),
            progress=progress,
            completed_at=completed_at,
        )
    except Exception as e:
        logger.warning(
            "Failed to mirror runtime job status to database",
            extra={"job_id": job_id, "error": str(e)},
        )


def _serialize_db_job(job: Any) -> dict[str, Any]:
    payload = job.payload if isinstance(job.payload, dict) else {}
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": payload.get("result"),
        "error": job.error,
        "runs": payload.get("runs"),
        "filename": payload.get("filename"),
    }


@router.post("/run")
async def run_monte_carlo_sync(
    symbol: str = Query(
        ..., description="Symbol to use from local datasets (e.g., AAPL, AMZN)"
    ),
    start_date: datetime = Query(
        ..., description="Start date for simulation (YYYY-MM-DD)"
    ),
    end_date: datetime = Query(..., description="End date for simulation (YYYY-MM-DD)"),
    num_runs: int = Query(
        ..., ge=1, le=10000, description="Number of Monte Carlo runs"
    ),
    initial_capital: float = Query(
        ..., gt=0, description="Initial capital for simulation"
    ),
    method: str = Query("bootstrap", description="Monte Carlo method"),
    sample_fraction: float = Query(
        1.0, gt=0, le=5.0, description="Bootstrap sample fraction"
    ),
    gaussian_scale: float = Query(
        1.0, gt=0, le=10.0, description="Gaussian noise scale"
    ),
    strategy: str = Query(
        "sma_crossover", description="Strategy name (e.g., sma_crossover, rsi)"
    ),
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(
        None, ge=0, le=100, description="Overbought threshold (0-100)"
    ),
    oversold: float | None = Query(
        None, ge=0, le=100, description="Oversold threshold (0-100)"
    ),
    normalize: bool = Query(
        False, description="Normalize equity curves to start at 1.0"
    ),
    price_type: str = Query(
        "close", description="Price type to use: 'close' or 'adj_close'"
    ),
    file: UploadFile | None = File(None),
    current_user: SimpleUser | None = Depends(get_current_user_simple_optional),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation synchronously.
    This endpoint executes the simulation immediately and returns results.
    For large simulations, consider using the /async endpoint.
    Supports both CSV file upload and local dataset usage.
    When using local datasets, provide symbol, start_date, and end_date parameters.
    """
    start_time = time.time()
    try:
        from io import BytesIO

        import pandas as pd

        strategy = validate_strategy_params(
            strategy,
            sma_short=sma_short,
            sma_long=sma_long,
            period=period,
            overbought=overbought,
            oversold=oversold,
        )
        strategy_params_dict = {
            "strategy": strategy,
            "sma_short": sma_short,
            "sma_long": sma_long,
            "period": period,
            "overbought": overbought,
            "oversold": oversold,
            "initial_capital": initial_capital,
        }
        if method not in {"bootstrap", "gaussian"}:
            raise HTTPException(
                status_code=400, detail=f"Unsupported Monte Carlo method: {method}"
            )
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date",
            )
        if file:
            contents = await file.read()
            df = pd.read_csv(BytesIO(contents))
            validate_date_range_for_csv_bytes(contents, start_date, end_date)
        else:
            validate_date_range_for_symbol(symbol, start_date, end_date)
            df, _data_file = load_filtered_local_dataset_df(symbol, start_date, end_date)
        date_column = "date" if "date" in df.columns else "Date"
        df[date_column] = pd.to_datetime(df[date_column])
        mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
        filtered_df = df.loc[mask]
        logger.debug(
            "Filtered local or uploaded dataframe for Monte Carlo run",
            extra={
                "symbol": symbol,
                "date_column": date_column,
                "row_count": int(len(filtered_df)),
                "is_empty": bool(filtered_df.empty),
            },
        )
        if filtered_df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data available for the specified date range",
            )
        csv_bytes = dataframe_to_csv_bytes(filtered_df)
        from services.mc_backtest_service import run_monte_carlo_on_df

        strategy_name = strategy_params_dict.get("strategy", "sma_crossover")
        result = run_monte_carlo_on_df(
            csv_data=csv_bytes,
            filename=file.filename if file else f"{symbol}.csv",  # pyright: ignore[reportArgumentType]
            strategy_name=strategy_name,  # pyright: ignore[reportArgumentType]
            strategy_params=strategy_params_dict,
            runs=num_runs,
            method=method,
            method_params={
                "sample_fraction": sample_fraction,
                "gaussian_scale": gaussian_scale,
            },
            price_type=price_type,
            parallel_workers=1,
        )
        from domain.schemas.backtest import MonteCarloBacktestResult, MonteCarloResponse

        if normalize and result.equity_envelope:
            envelope = result.equity_envelope

            def normalize_series(series: list[float]) -> list[float]:
                if not series or series[0] == 0:
                    return series
                first_value = series[0]
                return [value / first_value for value in series]

            from domain.schemas.backtest import EquityEnvelope

            normalized_envelope = EquityEnvelope(
                timestamps=envelope.timestamps,
                p5=normalize_series(envelope.p5),
                p25=normalize_series(envelope.p25),
                median=normalize_series(envelope.median),
                p75=normalize_series(envelope.p75),
                p95=normalize_series(envelope.p95),
            )
            result.equity_envelope = normalized_envelope

        monte_carlo_result = MonteCarloBacktestResult(
            filename=result.filename,
            method=result.method,
            runs=result.runs,
            successful_runs=result.successful_runs,
            metrics_distribution=result.metrics_distribution,
            equity_envelope=result.equity_envelope,
        )
        elapsed_time = time.time() - start_time
        response = MonteCarloResponse(
            results=[monte_carlo_result],
            aggregated_metrics=None,
            processing_time=f"{elapsed_time:.2f}s",
        )
        if current_user:
            try:
                user_repo = UserRepository(session)
                user = await user_repo.get_by_id(current_user.id)
                if user:
                    history_repo = BacktestHistoryRepository(session)
                    datasets_used = []
                    if symbol:
                        datasets_used = [symbol.upper()]
                    elif file:
                        datasets_used = [file.filename or "uploaded_file.csv"]
                    total_return = None
                    sharpe_ratio = None
                    max_drawdown = None
                    if result.metrics_distribution:
                        metrics = result.metrics_distribution
                        if "pnl" in metrics:
                            total_return = float(metrics["pnl"]["mean"])  # pyright: ignore[reportIndexIssue]
                        if "sharpe" in metrics:
                            sharpe_ratio = float(metrics["sharpe"]["mean"])  # pyright: ignore[reportIndexIssue]
                        if "drawdown" in metrics:
                            max_drawdown = float(metrics["drawdown"]["mean"])  # pyright: ignore[reportIndexIssue]
                    history_entry = await history_repo.create_history_entry(
                        user_id=user.id,
                        strategy=strategy,
                        strategy_params={
                            "sma_short": sma_short,
                            "sma_long": sma_long,
                            "period": period,
                            "overbought": overbought,
                            "oversold": oversold,
                        },
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        initial_capital=initial_capital,
                        monte_carlo_runs=num_runs,
                        monte_carlo_method=method,
                        datasets_used=datasets_used,
                        price_type=price_type,
                    )
                    if total_return is not None:
                        await history_repo.update_results(
                            history_id=history_entry.id,
                            total_return=total_return,
                            sharpe_ratio=sharpe_ratio,
                            max_drawdown=max_drawdown,
                            status="completed",
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to save Monte Carlo simulation to history: {str(e)}"
                )
        return response.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Monte Carlo simulation failed", extra={"symbol": symbol, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}",
        ) from e


@router.post("/async")
async def submit_async_job(
    symbol: str = Query(
        ..., description="Symbol to use from local datasets (e.g., AAPL, AMZN)"
    ),
    start_date: datetime = Query(
        ..., description="Start date for simulation (YYYY-MM-DD)"
    ),
    end_date: datetime = Query(..., description="End date for simulation (YYYY-MM-DD)"),
    num_runs: int = Query(
        ..., ge=1, le=10000, description="Number of Monte Carlo runs"
    ),
    initial_capital: float = Query(
        ..., gt=0, description="Initial capital for simulation"
    ),
    method: str = Query("bootstrap", description="Monte Carlo method"),
    sample_fraction: float = Query(
        1.0, gt=0, le=5.0, description="Bootstrap sample fraction"
    ),
    gaussian_scale: float = Query(
        1.0, gt=0, le=10.0, description="Gaussian noise scale"
    ),
    strategy: str = Query(
        "sma_crossover", description="Strategy name (e.g., sma_crossover, rsi)"
    ),
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(
        None, ge=0, le=100, description="Overbought threshold (0-100)"
    ),
    oversold: float | None = Query(
        None, ge=0, le=100, description="Oversold threshold (0-100)"
    ),
    normalize: bool = Query(
        False, description="Normalize equity curves to start at 1.0"
    ),
    price_type: str = Query(
        "close", description="Price type to use: 'close' or 'adj_close'"
    ),
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Submit Monte Carlo simulation job for asynchronous processing.
    This endpoint uses a simple in-process worker without Redis/queue dependencies.
    """
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        strategy = validate_strategy_params(
            strategy,
            sma_short=sma_short,
            sma_long=sma_long,
            period=period,
            overbought=overbought,
            oversold=oversold,
        )
        strategy_params_dict = {
            "strategy": strategy,
            "sma_short": sma_short,
            "sma_long": sma_long,
            "period": period,
            "overbought": overbought,
            "oversold": oversold,
            "initial_capital": initial_capital,
        }
        if method not in {"bootstrap", "gaussian"}:
            raise HTTPException(
                status_code=400, detail=f"Unsupported Monte Carlo method: {method}"
            )
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date",
            )
        csv_data = b""
        if file:
            csv_data = await file.read()
        else:
            from utils.date_validation import validate_date_range_for_symbol

            validation_result = validate_date_range_for_symbol(
                symbol, start_date, end_date
            )
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=validation_result["error_message"],
                )
            filtered_df, _data_file = load_filtered_local_dataset_df(
                symbol, start_date, end_date
            )
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        job_id = worker.submit_job(
            csv_data=csv_data,
            filename=file.filename if file else f"{symbol}_data.csv",  # pyright: ignore[reportArgumentType]
            strategy_name=strategy,
            strategy_params=strategy_params_dict,
            runs=num_runs,
            method=method,
            method_params={
                "sample_fraction": sample_fraction,
                "gaussian_scale": gaussian_scale,
            },
            price_type=price_type,
            normalize=normalize,
        )
        await _best_effort_create_async_job_record(
            session,
            job_id=job_id,
            filename=file.filename if file else f"{symbol}_data.csv",  # pyright: ignore[reportArgumentType]
            symbol=symbol,
            strategy=strategy,
            runs=num_runs,
            method=method,
            price_type=price_type,
            normalize=normalize,
        )
        return {
            "job_id": job_id,
            "status": "submitted",
            "message": "Job submitted for processing",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to submit async job", extra={"symbol": symbol, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}",
        ) from e


@router.get("/async/{job_id}")
async def get_async_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get status of an asynchronous job."""
    token = JOB_ID.set(job_id)
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        job_status = worker.get_job_status(job_id)
        if job_status:
            await _best_effort_mirror_runtime_job_status(session, job_status)
            return job_status

        repo = JobRepository(session)
        db_job = await repo.get_job_by_id(job_id)
        if db_job:
            return _serialize_db_job(db_job)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get job status", extra={"job_id": job_id, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        ) from e
    finally:
        JOB_ID.reset(token)


@router.delete("/async/{job_id}")
async def cancel_async_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Cancel an asynchronous job."""
    token = JOB_ID.set(job_id)
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        success = worker.cancel_job(job_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or cannot be cancelled",
            )
        try:
            repo = JobRepository(session)
            await repo.update_job_status(job_id=job_id, status="cancelled")
        except Exception as e:
            logger.warning(
                "Failed to persist cancelled job status",
                extra={"job_id": job_id, "error": str(e)},
            )
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel job", extra={"job_id": job_id, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        ) from e
    finally:
        JOB_ID.reset(token)


@router.get("/async")
async def list_async_jobs(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """List all asynchronous jobs."""
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        jobs = worker.list_jobs()
        if jobs:
            return {"jobs": jobs, "total": len(jobs)}
        try:
            repo = JobRepository(session)
            db_jobs = await repo.list_jobs(limit=50)
            serialized = [_serialize_db_job(job) for job in db_jobs]
            return {"jobs": serialized, "total": len(serialized)}
        except Exception as e:
            logger.warning("Failed to list jobs from database", extra={"error": str(e)})
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        logger.error("Failed to list jobs", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
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
                max_date=date_range["max_date"],
            )
            for symbol, date_range in date_ranges.items()
        ]
        return AllSymbolsDateRangesResponse(symbols=symbols)
    except Exception as e:
        logger.error("Failed to get symbols date ranges", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get date ranges: {str(e)}",
        ) from e


@router.websocket("/ws/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    This endpoint provides real-time updates for asynchronous jobs.
    """
    await websocket.accept()
    token = JOB_ID.set(job_id)
    try:
        from workers.simple_worker import get_simple_worker

        worker = get_simple_worker()
        logger.info("WebSocket connection established", extra={"job_id": job_id})
        # get_job_status est synchrone; ne pas utiliser await ici
        job_status = worker.get_job_status(job_id)
        if job_status:
            await websocket.send_json(job_status)
        else:
            await websocket.send_json(
                {"job_id": job_id, "status": "not_found", "error": "Job not found"}
            )
            return
        while True:
            try:
                job_status = worker.get_job_status(job_id)
                if job_status:
                    await websocket.send_json(job_status)
                    if job_status.get("status") in ["completed", "failed", "cancelled"]:
                        break
                else:
                    break
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(
                    "Error in WebSocket progress monitoring",
                    extra={"job_id": job_id, "error": str(e)},
                )
                await websocket.send_json(
                    {"job_id": job_id, "status": "error", "error": str(e)}
                )
                break
    except Exception as e:
        logger.error(
            "WebSocket connection error", extra={"job_id": job_id, "error": str(e)}
        )
    finally:
        logger.info("WebSocket connection closed", extra={"job_id": job_id})
        try:
            await websocket.close()
        except Exception:
            pass
        JOB_ID.reset(token)
