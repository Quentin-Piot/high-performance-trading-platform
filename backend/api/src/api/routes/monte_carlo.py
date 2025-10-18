"""
Monte Carlo simulation API endpoints.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    status,
)
from pydantic import BaseModel, Field, field_validator
from starlette.websockets import WebSocketDisconnect

from config.queue_config import get_config

# Import enhanced logging utilities
from core.background_task_logging import (
    log_websocket_connection,
)
from domain.queue import JobPriority, JobStatus, MonteCarloJobPayload
from infrastructure.queue.sqs_adapter import SQSQueueAdapter
from services.job_manager import MonteCarloJobManager
from utils.date_validation import (
    get_all_symbols_date_ranges,
    validate_date_range_for_csv_bytes,
    validate_date_range_for_symbol,
)

# Global dictionary to store locks for each job to prevent race conditions
_job_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class MonteCarloJobRequest(BaseModel):
    """Request model for creating a Monte Carlo job"""

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, MSFT)")
    start_date: datetime = Field(..., description="Start date for simulation")
    end_date: datetime = Field(..., description="End date for simulation")
    num_runs: int = Field(..., ge=1, le=10000, description="Number of simulation runs")
    initial_capital: float = Field(..., gt=0, description="Initial capital amount")
    strategy_params: dict[str, Any] = Field(
        default_factory=dict, description="Strategy parameters"
    )
    priority: JobPriority = Field(
        default=JobPriority.NORMAL, description="Job priority"
    )
    timeout_seconds: int | None = Field(
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

    jobs: list[MonteCarloJobRequest] = Field(..., min_length=1, max_length=50)
    batch_name: str | None = Field(
        None, description="Optional batch name for grouping"
    )

class JobResponse(BaseModel):
    """Response model for job information"""

    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime | None = None
    progress: float | None = Field(None, ge=0.0, le=1.0)
    result: dict[str, Any] | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class JobSubmissionResponse(BaseModel):
    """Response model for job submission"""

    job_id: str
    status: JobStatus
    message: str
    estimated_completion_time: datetime | None = None

class BulkJobSubmissionResponse(BaseModel):
    """Response model for bulk job submission"""

    batch_id: str | None = None
    jobs: list[JobSubmissionResponse]
    total_jobs: int
    successful_submissions: int
    failed_submissions: int

class JobProgressResponse(BaseModel):
    """Response model for job progress"""

    job_id: str
    status: JobStatus
    progress: float | None = None
    current_run: int | None = None
    total_runs: int | None = None
    estimated_completion_time: datetime | None = None
    last_updated: datetime

class QueueMetricsResponse(BaseModel):
    """Response model for queue metrics."""

    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time: float | None = None
    queue_depth: int
    worker_count: int

class SymbolDateRangeResponse(BaseModel):
    """Response model for symbol date ranges."""

    symbol: str
    min_date: datetime
    max_date: datetime

class AllSymbolsDateRangesResponse(BaseModel):
    """Response model for all symbols date ranges."""

    symbols: list[SymbolDateRangeResponse]

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
        from io import BytesIO

        import pandas as pd

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
        ) from e

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
        ) from e

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
        ) from e

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
            last_updated=progress.get("last_updated", datetime.now(UTC)),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job progress: {str(e)}",
        ) from e

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
        ) from e

@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    status_filter: JobStatus | None = Query(
        None, description="Filter jobs by status"
    ),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of jobs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> list[JobResponse]:
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
        ) from e

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
        ) from e

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
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to wait for job completion: {str(e)}",
        ) from e

# Export the router
monte_carlo_router = router

# WebSocket endpoint to stream job progress in real-time
@router.websocket("/jobs/{job_id}/progress")
@log_websocket_connection("monte_carlo_progress")
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

    # Add connection tracking and cleanup
    connection_id = f"ws_{job_id}_{id(websocket)}"
    logger.info(f"WebSocket connection established: {connection_id}")

    # Create a lock for this specific job to prevent race conditions
    job_lock = _job_locks[job_id]

    try:
        # Send immediate acknowledgment message to eliminate initial delay
        immediate_payload = {
            "job_id": job_id,
            "status": "connecting",
            "progress": None,
            "message": "WebSocket connection established, fetching job status...",
            "current_run": None,
            "total_runs": None,
            "estimated_completion_time": None,
            "last_updated": datetime.now(UTC).isoformat(),
        }
        await websocket.send_json(immediate_payload)
        logger.debug(f"Sent immediate connection acknowledgment: {connection_id}")

        # Send initial job state with proper error handling
        async with job_lock:
            progress = await job_manager.get_job_progress(job_id)

        if not progress:
            payload = {
                "job_id": job_id,
                "status": JobStatus.PENDING.value,
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
                "status": (status_val.value if isinstance(status_val, JobStatus) else status_val),
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
                # Include counters and ETA for frontend display
                "current_run": progress.get("current_run"),
                "total_runs": progress.get("total_runs"),
                "estimated_completion_time": progress.get("estimated_completion_time"),
                "last_updated": progress.get("last_updated"),
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
                finally:
                    logger.info(f"WebSocket connection closed (terminal state): {connection_id}")
                return

        # Subscribe to Redis pub/sub for real-time updates
        from infrastructure.cache import cache_manager

        # Create a task to listen for Redis notifications with enhanced pub/sub system
        async def listen_for_updates():
            subscription_active = False
            last_sequence_number = 0

            try:
                # Use the enhanced pub/sub system with automatic reconnection and message ordering
                async for message in cache_manager.subscribe(f"job_progress:{job_id}"):
                    subscription_active = True

                    # Check if WebSocket is still open before sending
                    if websocket.client_state.name != "CONNECTED":
                        logger.info(f"WebSocket disconnected for job {job_id}, stopping updates")
                        break

                    # Enhanced message handling with ordering and deduplication
                    if hasattr(message, 'sequence_number'):
                        # Skip duplicate or out-of-order messages
                        if message.sequence_number <= last_sequence_number:
                            logger.debug(f"Skipping duplicate/out-of-order message: seq={message.sequence_number}, last={last_sequence_number}")
                            continue
                        last_sequence_number = message.sequence_number

                    # Extract data from enhanced message format
                    # Extract data from enhanced message format (not used currently)
                    # Keeping for future use without assigning to an unused variable

                    # Get full job state for complete payload with lock protection
                    async with job_lock:
                        current_progress = await job_manager.get_job_progress(job_id)

                    if current_progress:
                        status_val = current_progress.get("status", JobStatus.PENDING)
                        payload = {
                            "job_id": job_id,
                            "status": (status_val.value if isinstance(status_val, JobStatus) else status_val),
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
                            # Include counters and ETA for frontend display
                            "current_run": current_progress.get("current_run"),
                            "total_runs": current_progress.get("total_runs"),
                            "estimated_completion_time": current_progress.get("estimated_completion_time"),
                            "eta_seconds": current_progress.get("eta_seconds"),
                            "last_updated": current_progress.get("last_updated"),
                            # Add message metadata for debugging
                            "message_sequence": getattr(message, 'sequence_number', None),
                            "message_timestamp": getattr(message, 'timestamp', None),
                        }

                        try:
                            await websocket.send_json(payload)
                            logger.debug(f"Sent progress update via enhanced Redis pub/sub: {connection_id} (seq: {getattr(message, 'sequence_number', 'N/A')})")
                        except Exception as send_error:
                            logger.warning(f"Failed to send WebSocket message for job {job_id}: {send_error}")
                            break

                        # Break on terminal states
                        if status_val in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                            logger.info(f"Job {job_id} reached terminal state: {status_val}")
                            break

            except Exception as e:
                logger.error(f"Enhanced Redis subscription error for job {job_id}: {str(e)}")
                # Check pub/sub health for better error reporting
                try:
                    health_status = cache_manager.get_pubsub_health()
                    logger.error(f"Redis pub/sub health status: {health_status}")
                except Exception:
                    pass

                if not subscription_active:
                    # If subscription never became active, Redis is likely down
                    raise

        # Create a fallback polling task with improved error handling and immediate start
        async def fallback_polling():
            poll_count = 0
            last_status = None
            last_progress = None
            last_current_run = None

            # Send immediate first update without delay
            try:
                async with job_lock:
                    current_progress = await job_manager.get_job_progress(job_id)
                
                if current_progress:
                    status_val = current_progress.get("status", JobStatus.PENDING)
                    payload = {
                        "job_id": job_id,
                        "status": (status_val.value if isinstance(status_val, JobStatus) else status_val),
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
                        "current_run": current_progress.get("current_run"),
                        "total_runs": current_progress.get("total_runs"),
                        "estimated_completion_time": current_progress.get("estimated_completion_time"),
                        "eta_seconds": current_progress.get("eta_seconds"),
                        "last_updated": current_progress.get("last_updated"),
                    }
                    
                    await websocket.send_json(payload)
                    logger.debug(f"Sent immediate progress update: {connection_id}")
                    
                    last_status = status_val
                    last_progress = float(current_progress.get("progress") or 0.0)
                    last_current_run = current_progress.get("current_run")
            except Exception as e:
                logger.error(f"Error sending immediate update for job {job_id}: {str(e)}")

            while True:
                # Check if WebSocket is still open before polling
                if websocket.client_state.name != "CONNECTED":
                    logger.info(f"WebSocket disconnected for job {job_id}, stopping polling")
                    break

                await asyncio.sleep(0.2)  # Much faster polling: 200ms instead of 500ms
                poll_count += 1

                try:
                    async with job_lock:
                        current_progress = await job_manager.get_job_progress(job_id)

                    if current_progress:
                        status_val = current_progress.get("status", JobStatus.PENDING)

                        # Detect progress/run changes
                        try:
                            progress_val = float(current_progress.get("progress") or 0.0)
                        except Exception:
                            progress_val = 0.0
                        curr_run = current_progress.get("current_run")

                        should_send = False
                        if status_val != last_status:
                            should_send = True
                        elif curr_run is not None and curr_run != last_current_run:
                            should_send = True
                        elif abs(progress_val - (last_progress or 0.0)) >= 0.001:
                            # Send on any progress change >= 0.1% (was 1%)
                            should_send = True
                        elif poll_count % 2 == 0:
                            # periodic heartbeat even without changes (every 400ms)
                            should_send = True

                        if should_send:
                            payload = {
                                "job_id": job_id,
                                "status": (status_val.value if isinstance(status_val, JobStatus) else status_val),
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
                                # Include counters and ETA for frontend display
                                "current_run": current_progress.get("current_run"),
                                "total_runs": current_progress.get("total_runs"),
                                "estimated_completion_time": current_progress.get("estimated_completion_time"),
                                "eta_seconds": current_progress.get("eta_seconds"),
                                "last_updated": current_progress.get("last_updated"),
                            }

                            try:
                                await websocket.send_json(payload)
                                if status_val != last_status:
                                    logger.debug(f"Sent progress update via polling: {connection_id}")
                                last_status = status_val
                                last_progress = progress_val
                                last_current_run = curr_run
                            except Exception as send_error:
                                logger.warning(f"Failed to send WebSocket message for job {job_id}: {send_error}")
                                break

                        # Break on terminal states
                        if status_val in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                            logger.info(f"Job {job_id} reached terminal state via polling: {status_val}")
                            break

                except Exception as e:
                    logger.error(f"Error during polling for job {job_id}: {str(e)}")
                    await asyncio.sleep(0.2)  # Continue polling even on errors

        # Try Redis pub/sub first, fallback to polling if Redis is not available
        try:
            # Check if Redis is available before trying pub/sub
            if not cache_manager.is_connected():
                logger.warning(f"Redis is not connected for {connection_id}, using fallback polling")
                await fallback_polling()
            else:
                # Check pub/sub health before attempting subscription
                try:
                    health_status = cache_manager.get_pubsub_health()
                    if not health_status.get('healthy', False):
                        logger.warning(f"Redis pub/sub is unhealthy for {connection_id}: {health_status}, falling back to polling")
                        await fallback_polling()
                        return
                except Exception as health_error:
                    logger.warning(f"Failed to check pub/sub health for {connection_id}: {health_error}, falling back to polling")
                    await fallback_polling()
                    return

                # Create a timeout for Redis pub/sub to detect if it's not working (disabled timeout to force polling)
                try:
                    # Force immediate fallback to polling for consistent behavior
                    raise asyncio.TimeoutError("Forcing fallback to polling for debugging")
                    await asyncio.wait_for(listen_for_updates(), timeout=10.0)
                except asyncio.TimeoutError:
                    # Always fallback to polling for now
                    logger.warning(f"Using fallback polling for {connection_id}")
                    await fallback_polling()
        except Exception as e:
            logger.warning(f"Enhanced Redis pub/sub failed for {connection_id}, falling back to polling: {str(e)}")
            # Log pub/sub metrics for debugging
            try:
                metrics = cache_manager.get_pubsub_metrics()
                logger.warning(f"Redis pub/sub metrics: {metrics}")
            except Exception:
                pass
            await fallback_polling()

    except WebSocketDisconnect:
        # Client disconnected; nothing to do
        logger.info(f"WebSocket disconnected: {connection_id}")
        return
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {str(e)}")
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

    # Close cleanly after terminal state update
    try:
        if websocket.client_state.name == "CONNECTED":
            await websocket.close(code=1000)
            logger.info(f"WebSocket connection closed cleanly: {connection_id}")
    except Exception as e:
        logger.warning(f"Error closing WebSocket for {connection_id}: {str(e)}")

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
        ) from e

@router.post(
    "/jobs/upload", response_model=JobSubmissionResponse, status_code=status.HTTP_201_CREATED
)
async def submit_job_upload(
    csv: UploadFile = File(..., description="CSV file with columns: date, close"),
    start_date: datetime = Form(..., description="Start date for simulation"),
    end_date: datetime = Form(..., description="End date for simulation"),
    num_runs: int = Form(..., description="Number of simulation runs"),
    initial_capital: float = Form(..., description="Initial capital amount"),
    strategy_params_json: str = Form("{}", description="Strategy parameters as JSON"),
    method: str = Form("bootstrap", description="Monte Carlo method: bootstrap or gaussian"),
    priority: JobPriority = Form(JobPriority.NORMAL),
    timeout_seconds: int | None = Form(None),
    job_manager: MonteCarloJobManager = Depends(get_job_manager),
) -> JobSubmissionResponse:
    """
    Submit a Monte Carlo job using an uploaded CSV (accepts arbitrary files).

    Performs real-time date validation against the uploaded CSV and filters
    the dataset to the requested date range before enqueuing the job.
    """
    try:
        import json
        from io import BytesIO

        import pandas as pd

        # Read uploaded CSV
        csv_bytes = await csv.read()
        if not csv_bytes:
            raise HTTPException(status_code=400, detail="Empty CSV upload")

        # Validate date range on uploaded data
        validation = validate_date_range_for_csv_bytes(csv_bytes, start_date, end_date)
        if not validation["valid"]:
            detail = validation["error_message"] or "Invalid date range for uploaded CSV"
            suggested = validation.get("suggested_range")
            if suggested:
                detail += (
                    f". Suggested range: "
                    f"{suggested['start_date'].strftime('%Y-%m-%d')} to "
                    f"{suggested['end_date'].strftime('%Y-%m-%d')}"
                )
            raise HTTPException(status_code=400, detail=detail)

        # Filter by requested date range
        df = pd.read_csv(BytesIO(csv_bytes))
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "date" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain a 'date' column")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]
        if df.empty:
            raise HTTPException(status_code=400, detail="No data in requested date range after filtering")

        # Convert filtered DataFrame back to CSV bytes
        buf = BytesIO()
        df.to_csv(buf, index=False)
        filtered_csv = buf.getvalue()

        # Parse strategy params JSON into dict
        try:
            strategy_params: dict[str, Any] = json.loads(strategy_params_json or "{}")
            if not isinstance(strategy_params, dict):
                raise ValueError("strategy_params_json must be a JSON object")
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid strategy_params_json; must be valid JSON object") from e

        # Build a filename from uploaded name and range
        safe_name = (csv.filename or "uploaded.csv").replace(" ", "_")
        filename = f"{safe_name.rsplit('.', 1)[0]}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"

        # Enqueue job via job manager (persisted and deduplicated)
        job_id = await job_manager.submit_monte_carlo_job(
            csv_file=BytesIO(filtered_csv),
            filename=filename,
            strategy_name="sma_crossover",
            strategy_params=strategy_params,
            runs=num_runs,
            method=method,
            method_params=None,
            seed=None,
            include_equity_envelope=True,
            priority=priority,
            timeout_seconds=timeout_seconds or 3600,
            max_retries=3,
        )

        return JobSubmissionResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Job submitted successfully",
            estimated_completion_time=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit uploaded CSV job: {str(e)}",
        ) from e
