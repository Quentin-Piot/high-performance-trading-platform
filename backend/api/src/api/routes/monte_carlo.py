"""
Monte Carlo simulation API endpoints.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    BackgroundTasks,
    Query,
    status,
    WebSocket,
)
from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator

from domain.queue import JobStatus, JobPriority, MonteCarloJobPayload, JobMetadata
from services.job_manager import MonteCarloJobManager
from infrastructure.queue.sqs_adapter import SQSQueueAdapter
from infrastructure.monitoring.metrics import MonitoringService
from config.queue_config import get_config
from utils.date_validation import validate_date_range_for_symbol, get_all_symbols_date_ranges
import asyncio
from functools import lru_cache


# Pydantic models for API requests/responses
class MonteCarloJobRequest(BaseModel):
    """Request model for creating a Monte Carlo job"""

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, MSFT)")
    start_date: datetime = Field(..., description="Start date for simulation")
    end_date: datetime = Field(..., description="End date for simulation")
    num_runs: int = Field(..., ge=1, le=10000, description="Number of simulation runs")
    initial_capital: float = Field(..., gt=0, description="Initial capital amount")
    strategy_params: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy parameters"
    )
    priority: JobPriority = Field(
        default=JobPriority.NORMAL, description="Job priority"
    )
    timeout_seconds: Optional[int] = Field(
        None, ge=60, le=7200, description="Job timeout in seconds"
    )

    @field_validator("end_date")
    @classmethod
    def end_date_after_start_date(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("num_runs")
    @classmethod
    def validate_num_runs(cls, v):
        if v > 100:
            # For jobs with more than 100 runs, we might want to split them
            pass
        return v


class BulkMonteCarloJobRequest(BaseModel):
    """Request model for creating multiple Monte Carlo jobs"""

    jobs: List[MonteCarloJobRequest] = Field(..., min_length=1, max_length=50)
    batch_name: Optional[str] = Field(
        None, description="Optional batch name for grouping"
    )


class JobResponse(BaseModel):
    """Response model for job information"""

    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobSubmissionResponse(BaseModel):
    """Response model for job submission"""

    job_id: str
    status: JobStatus
    message: str
    estimated_completion_time: Optional[datetime] = None


class BulkJobSubmissionResponse(BaseModel):
    """Response model for bulk job submission"""

    batch_id: Optional[str] = None
    jobs: List[JobSubmissionResponse]
    total_jobs: int
    successful_submissions: int
    failed_submissions: int


class JobProgressResponse(BaseModel):
    """Response model for job progress"""

    job_id: str
    status: JobStatus
    progress: Optional[float] = None
    current_run: Optional[int] = None
    total_runs: Optional[int] = None
    estimated_completion_time: Optional[datetime] = None
    last_updated: datetime


class QueueMetricsResponse(BaseModel):
    """Response model for queue metrics."""

    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time: Optional[float] = None
    queue_depth: int
    worker_count: int


class SymbolDateRangeResponse(BaseModel):
    """Response model for symbol date ranges."""
    
    symbol: str
    min_date: datetime
    max_date: datetime


class AllSymbolsDateRangesResponse(BaseModel):
    """Response model for all symbols date ranges."""
    
    symbols: List[SymbolDateRangeResponse]


# Dependency injection
@lru_cache(maxsize=1)
def get_job_manager() -> MonteCarloJobManager:
    """Get a singleton Monte Carlo job manager instance.

    Using a shared instance ensures the SQS adapter's in-memory cache
    is consistent across HTTP endpoints and WebSocket streams.
    """
    config = get_config()
    queue_adapter = SQSQueueAdapter(config.sqs)
    return MonteCarloJobManager(queue_adapter)


# Router setup
router = APIRouter(prefix="/monte-carlo", tags=["Monte Carlo Simulations"])


@router.post(
    "/jobs", response_model=JobSubmissionResponse, status_code=status.HTTP_201_CREATED
)
async def submit_job(
    job_request: MonteCarloJobRequest,
    background_tasks: BackgroundTasks,
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> JobSubmissionResponse:
    """
    Submit a single Monte Carlo simulation job.

    Args:
        job_request: Job parameters and configuration
        background_tasks: FastAPI background tasks
        job_manager: Job manager dependency

    Returns:
        Job submission response with job ID and status

    Raises:
        HTTPException: If job submission fails
    """
    try:
        import os
        import pandas as pd
        from io import BytesIO

        # Map symbol to dataset file
        symbol_to_file = {
            "aapl": "AAPL.csv",
            "amzn": "AMZN.csv",
            "fb": "FB.csv",
            "googl": "GOOGL.csv",
            "msft": "MSFT.csv",
            "nflx": "NFLX.csv",
            "nvda": "NVDA.csv",
        }

        # Check if symbol is supported
        if job_request.symbol not in symbol_to_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol {job_request.symbol} not supported. Available symbols: {list(symbol_to_file.keys())}",
            )

        # Validate date range against available CSV data
        validation_result = validate_date_range_for_symbol(
            symbol=job_request.symbol,
            start_date=job_request.start_date,
            end_date=job_request.end_date
        )
        
        if not validation_result['valid']:
            error_detail = validation_result['error_message']
            if validation_result['suggested_range']:
                suggested = validation_result['suggested_range']
                error_detail += f" Suggested range: {suggested['start_date'].strftime('%Y-%m-%d')} to {suggested['end_date'].strftime('%Y-%m-%d')}"
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail,
            )

        # Load historical data from CSV file
        datasets_path = "/Users/juliettecattin/WebstormProjects/high-performance-trading-platform/web/public/data/datasets"
        csv_file_path = os.path.join(datasets_path, symbol_to_file[job_request.symbol])

        if not os.path.exists(csv_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset file not found for symbol {job_request.symbol}",
            )

        # Read and filter data by date range
        df = pd.read_csv(csv_file_path)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Convert date column to datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            # Filter by date range
            start_date = pd.to_datetime(job_request.start_date)
            end_date = pd.to_datetime(job_request.end_date)
            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

            if df.empty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No data available for {job_request.symbol} in the specified date range",
                )

        # Convert filtered DataFrame back to CSV bytes
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        csv_file = BytesIO(csv_data)

        # Submit job using the method that persists to database
        job_id = await job_manager.submit_monte_carlo_job(
            csv_file=csv_file,
            filename=f"{job_request.symbol}_{job_request.start_date.strftime('%Y%m%d')}_{job_request.end_date.strftime('%Y%m%d')}.csv",
            strategy_name="sma_crossover",  # Use supported strategy name
            strategy_params=job_request.strategy_params,
            runs=job_request.num_runs,
            method="bootstrap",
            method_params=None,
            seed=None,
            include_equity_envelope=True,
            priority=job_request.priority,
            timeout_seconds=job_request.timeout_seconds or 3600,
            max_retries=3,
        )

        return JobSubmissionResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Job submitted successfully",
            estimated_completion_time=None,  # Could be calculated based on queue depth
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}",
        )


@router.post(
    "/jobs/bulk",
    response_model=BulkJobSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_bulk_jobs(
    bulk_request: BulkMonteCarloJobRequest,
    background_tasks: BackgroundTasks,
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> BulkJobSubmissionResponse:
    """
    Submit multiple Monte Carlo simulation jobs.

    Args:
        bulk_request: Bulk job request with multiple jobs
        background_tasks: FastAPI background tasks
        job_manager: Job manager dependency

    Returns:
        Bulk job submission response

    Raises:
        HTTPException: If bulk submission fails
    """
    try:
        # Convert requests to payloads
        payloads = []
        priorities = []
        timeouts = []

        for job_req in bulk_request.jobs:
            payload = MonteCarloJobPayload(
                symbol=job_req.symbol,
                start_date=job_req.start_date,
                end_date=job_req.end_date,
                num_runs=job_req.num_runs,
                initial_capital=job_req.initial_capital,
                strategy_params=job_req.strategy_params,
            )
            payloads.append(payload)
            priorities.append(job_req.priority)
            timeouts.append(job_req.timeout_seconds)

        # Submit bulk jobs
        job_ids = await job_manager.submit_bulk_jobs(
            payloads=payloads,
            priorities=priorities,
            timeout_seconds_list=timeouts,
            batch_name=bulk_request.batch_name,
        )

        # Create response
        job_responses = [
            JobSubmissionResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="Job submitted successfully",
            )
            for job_id in job_ids
        ]

        return BulkJobSubmissionResponse(
            batch_id=bulk_request.batch_name,
            jobs=job_responses,
            total_jobs=len(job_ids),
            successful_submissions=len(job_ids),
            failed_submissions=0,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit bulk jobs: {str(e)}",
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str, job_manager: MonteCarloJobManager = Depends(get_job_manager)
) -> JobResponse:
    """
    Get the status and details of a specific job.

    Args:
        job_id: Unique job identifier
        job_manager: Job manager dependency

    Returns:
        Job status and details

    Raises:
        HTTPException: If job not found or retrieval fails
    """
    try:
        job = await job_manager.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        return JobResponse(
            job_id=job.metadata.job_id,
            status=job.status,
            created_at=job.metadata.created_at,
            updated_at=job.metadata.updated_at,
            progress=job.progress,
            result=job.result,
            error_message=job.error,
            metadata=job.metadata.tags,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        )


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(
    job_id: str, job_manager: MonteCarloJobManager = Depends(get_job_manager)
) -> JobProgressResponse:
    """
    Get detailed progress information for a specific job.

    Args:
        job_id: Unique job identifier
        job_manager: Job manager dependency

    Returns:
        Detailed job progress information

    Raises:
        HTTPException: If job not found or retrieval fails
    """
    try:
        progress = await job_manager.get_job_progress(job_id)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        return JobProgressResponse(
            job_id=job_id,
            status=progress.get("status", JobStatus.PENDING),
            progress=progress.get("progress"),
            current_run=progress.get("current_run"),
            total_runs=progress.get("total_runs"),
            estimated_completion_time=progress.get("estimated_completion_time"),
            last_updated=progress.get("last_updated", datetime.utcnow()),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job progress: {str(e)}",
        )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: str, job_manager: MonteCarloJobManager = Depends(get_job_manager)
) -> None:
    """
    Cancel a specific job.

    Args:
        job_id: Unique job identifier
        job_manager: Job manager dependency

    Raises:
        HTTPException: If job not found or cancellation fails
    """
    try:
        success = await job_manager.cancel_job(job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found or cannot be cancelled",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(
        None, description="Filter jobs by status"
    ),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of jobs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> List[JobResponse]:
    """
    List jobs with optional filtering and pagination.

    Args:
        status_filter: Optional status filter
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        job_manager: Job manager dependency

    Returns:
        List of job responses

    Raises:
        HTTPException: If listing fails
    """
    try:
        jobs = await job_manager.list_jobs(
            status=status_filter, limit=limit, offset=offset
        )

        return [
            JobResponse(
                job_id=job.metadata.job_id,
                status=job.status,
                created_at=job.metadata.created_at,
                updated_at=job.metadata.updated_at,
                progress=job.progress,
                result=job.result,
                error_message=job.error,
                metadata=job.metadata.tags,
            )
            for job in jobs
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
        )


@router.get("/metrics", response_model=QueueMetricsResponse)
async def get_queue_metrics(
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> QueueMetricsResponse:
    """
    Get queue metrics and statistics.

    Args:
        job_manager: Job manager dependency

    Returns:
        Queue metrics and statistics

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        metrics = await job_manager.get_queue_metrics()

        return QueueMetricsResponse(
            total_jobs=metrics.get("database_stats", {}).get("total_jobs", 0),
            pending_jobs=metrics.get("pending_jobs", 0),
            running_jobs=metrics.get("processing_jobs", 0),
            completed_jobs=metrics.get("completed_jobs", 0),
            failed_jobs=metrics.get("failed_jobs", 0),
            average_processing_time=metrics.get("average_processing_time"),
            queue_depth=metrics.get("pending_jobs", 0),
            worker_count=metrics.get("health_indicators", {}).get("active_workers", 0),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue metrics: {str(e)}",
        )


@router.post("/jobs/{job_id}/wait", response_model=JobResponse)
async def wait_for_job_completion(
    job_id: str,
    timeout_seconds: int = Query(
        300, ge=1, le=3600, description="Maximum wait time in seconds"
    ),
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> JobResponse:
    """
    Wait for a job to complete and return the result.

    Args:
        job_id: Unique job identifier
        timeout_seconds: Maximum wait time in seconds
        job_manager: Job manager dependency

    Returns:
        Final job status and result

    Raises:
        HTTPException: If job not found, timeout, or waiting fails
    """
    try:
        job = await job_manager.wait_for_completion(job_id, timeout_seconds)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        return JobResponse(
            job_id=job.id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            progress=job.metadata.progress,
            result=job.result,
            error_message=job.error_message,
            metadata=job.metadata.to_dict(),
        )

    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Job {job_id} did not complete within {timeout_seconds} seconds",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to wait for job completion: {str(e)}",
        )


# Export the router
monte_carlo_router = router


# WebSocket endpoint to stream job progress in real-time
@router.websocket("/jobs/{job_id}/progress")
async def monte_carlo_progress_ws(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates using Redis pub/sub.
    
    Args:
        websocket: WebSocket connection
        job_id: Job ID to monitor
    """
    await websocket.accept()
    
    # Use shared job manager to read initial job state
    job_manager = get_job_manager()
    
    try:
        # Send initial job state
        progress = await job_manager.get_job_progress(job_id)
        if not progress:
            payload = {
                "job_id": job_id,
                "status": str(JobStatus.PENDING),
                "progress": None,
                "current_run": None,
                "total_runs": None,
                "estimated_completion_time": None,
                "last_updated": None,
            }
            await websocket.send_json(payload)
        else:
            status_val = progress.get("status", JobStatus.PENDING)
            payload = {
                "job_id": job_id,
                "status": str(status_val),
                "progress": progress.get("progress"),
                "message": progress.get("message"),
                "created_at": progress.get("created_at"),
                "updated_at": progress.get("updated_at"),
                "started_at": progress.get("started_at"),
                "completed_at": progress.get("completed_at"),
                "duration_seconds": progress.get("duration_seconds"),
                "error": progress.get("error"),
                "retry_count": progress.get("retry_count"),
                "worker_id": progress.get("worker_id"),
                "artifact_url": progress.get("artifact_url"),
                "artifacts": progress.get("artifacts", []),
            }
            await websocket.send_json(payload)
            
            # If job is already in terminal state, wait for client to close or timeout
            if status_val in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                try:
                    # Wait for client to close the connection or timeout after 30 seconds
                    await asyncio.wait_for(websocket.receive(), timeout=30.0)
                except asyncio.TimeoutError:
                    await websocket.close(code=1000)
                except WebSocketDisconnect:
                    pass
                return

        # Subscribe to Redis pub/sub for real-time updates
        from infrastructure.cache import cache_manager
        
        # Create a task to listen for Redis notifications
        async def listen_for_updates():
            try:
                async for message in cache_manager.subscribe(f"job_progress:{job_id}"):
                    # Check if WebSocket is still open before sending
                    if websocket.client_state.name != "CONNECTED":
                        logger.info(f"WebSocket disconnected for job {job_id}, stopping updates")
                        break
                        
                    if message['channel'] == f"job_progress:{job_id}":
                        data = message['data']
                        
                        # Get full job state for complete payload
                        current_progress = await job_manager.get_job_progress(job_id)
                        if current_progress:
                            status_val = current_progress.get("status", JobStatus.PENDING)
                            payload = {
                                "job_id": job_id,
                                "status": str(status_val),
                                "progress": current_progress.get("progress"),
                                "message": current_progress.get("message"),
                                "created_at": current_progress.get("created_at"),
                                "updated_at": current_progress.get("updated_at"),
                                "started_at": current_progress.get("started_at"),
                                "completed_at": current_progress.get("completed_at"),
                                "duration_seconds": current_progress.get("duration_seconds"),
                                "error": current_progress.get("error"),
                                "retry_count": current_progress.get("retry_count"),
                                "worker_id": current_progress.get("worker_id"),
                                "artifact_url": current_progress.get("artifact_url"),
                                "artifacts": current_progress.get("artifacts", []),
                            }
                            
                            try:
                                await websocket.send_json(payload)
                            except Exception as send_error:
                                logger.warning(f"Failed to send WebSocket message for job {job_id}: {send_error}")
                                break
                            
                            # Break on terminal states
                            if status_val in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                                break
            except Exception as e:
                logger.error(f"Error in Redis subscription for job {job_id}: {str(e)}")

        # Create a fallback polling task in case Redis pub/sub is not available
        async def fallback_polling():
            while True:
                # Check if WebSocket is still open before polling
                if websocket.client_state.name != "CONNECTED":
                    logger.info(f"WebSocket disconnected for job {job_id}, stopping polling")
                    break
                    
                await asyncio.sleep(1.0)
                current_progress = await job_manager.get_job_progress(job_id)
                if current_progress:
                    status_val = current_progress.get("status", JobStatus.PENDING)
                    payload = {
                        "job_id": job_id,
                        "status": str(status_val),
                        "progress": current_progress.get("progress"),
                        "message": current_progress.get("message"),
                        "created_at": current_progress.get("created_at"),
                        "updated_at": current_progress.get("updated_at"),
                        "started_at": current_progress.get("started_at"),
                        "completed_at": current_progress.get("completed_at"),
                        "duration_seconds": current_progress.get("duration_seconds"),
                        "error": current_progress.get("error"),
                        "retry_count": current_progress.get("retry_count"),
                        "worker_id": current_progress.get("worker_id"),
                        "artifact_url": current_progress.get("artifact_url"),
                        "artifacts": current_progress.get("artifacts", []),
                    }
                    
                    try:
                        await websocket.send_json(payload)
                    except Exception as send_error:
                        logger.warning(f"Failed to send WebSocket message for job {job_id}: {send_error}")
                        break
                    
                    # Break on terminal states
                    if status_val in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                        break

        # Try Redis pub/sub first, fallback to polling if Redis is not available
        try:
            # Check if Redis is available before trying pub/sub
            if not cache_manager.is_connected():
                logger.warning("Redis is not connected, using fallback polling")
                await fallback_polling()
            else:
                # Create a timeout for Redis pub/sub to detect if it's not working
                try:
                    await asyncio.wait_for(listen_for_updates(), timeout=2.0)
                except asyncio.TimeoutError:
                    # If no Redis messages received within 2 seconds, fallback to polling
                    logger.warning("Redis pub/sub timeout, falling back to polling")
                    await fallback_polling()
        except Exception as e:
            logger.warning(f"Redis pub/sub failed, falling back to polling: {str(e)}")
            await fallback_polling()

    except WebSocketDisconnect:
        # Client disconnected; nothing to do
        logger.info(f"WebSocket disconnected for job {job_id}")
        return
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}")
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_json({"error": f"WS error: {str(e)}"})
        except Exception:
            pass  # Ignore errors when trying to send error message
        finally:
            try:
                await websocket.close(code=1011)
            except Exception:
                pass  # Ignore errors when trying to close
            return

    # Close cleanly after terminal state update
    try:
        if websocket.client_state.name == "CONNECTED":
            await websocket.close(code=1000)
    except Exception as e:
        logger.warning(f"Error closing WebSocket for job {job_id}: {str(e)}")


@router.get("/symbols/date-ranges", response_model=AllSymbolsDateRangesResponse)
async def get_symbols_date_ranges():
    """
    Get available date ranges for all supported symbols.
    
    Returns:
        AllSymbolsDateRangesResponse: Date ranges for all symbols
    """
    try:
        date_ranges = get_all_symbols_date_ranges()
        
        symbols = [
            SymbolDateRangeResponse(
                symbol=symbol,
                min_date=ranges['min_date'],
                max_date=ranges['max_date']
            )
            for symbol, ranges in date_ranges.items()
        ]
        
        return AllSymbolsDateRangesResponse(symbols=symbols)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving symbol date ranges: {str(e)}"
        )