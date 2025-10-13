"""
Monte Carlo simulation API endpoints.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, status
from pydantic import BaseModel, Field, validator

from src.domain.queue import JobStatus, JobPriority, MonteCarloJobPayload
from src.services.job_manager import MonteCarloJobManager
from src.infrastructure.queue.sqs_adapter import SQSQueueAdapter
from src.infrastructure.monitoring.metrics import MonitoringService
from src.config.queue_config import get_config


# Pydantic models for API requests/responses
class MonteCarloJobRequest(BaseModel):
    """Request model for creating a Monte Carlo job"""
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, MSFT)")
    start_date: datetime = Field(..., description="Start date for simulation")
    end_date: datetime = Field(..., description="End date for simulation")
    num_runs: int = Field(..., ge=1, le=10000, description="Number of simulation runs")
    initial_capital: float = Field(..., gt=0, description="Initial capital amount")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Job priority")
    timeout_seconds: Optional[int] = Field(None, ge=60, le=7200, description="Job timeout in seconds")
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('num_runs')
    def validate_num_runs(cls, v):
        if v > 100:
            # For jobs with more than 100 runs, we might want to split them
            pass
        return v


class BulkMonteCarloJobRequest(BaseModel):
    """Request model for creating multiple Monte Carlo jobs"""
    jobs: List[MonteCarloJobRequest] = Field(..., min_items=1, max_items=50)
    batch_name: Optional[str] = Field(None, description="Optional batch name for grouping")


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
    """Response model for queue metrics"""
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time: Optional[float] = None
    queue_depth: int
    worker_count: int


# Dependency injection
async def get_job_manager() -> MonteCarloJobManager:
    """Get Monte Carlo job manager instance"""
    config = get_config()
    queue_adapter = SQSQueueAdapter(config.sqs)
    monitoring_service = MonitoringService()
    return MonteCarloJobManager(queue_adapter, monitoring_service)


# Router setup
router = APIRouter(prefix="/monte-carlo", tags=["Monte Carlo Simulations"])


@router.post("/jobs", response_model=JobSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(
    job_request: MonteCarloJobRequest,
    background_tasks: BackgroundTasks,
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
        # Create job payload
        payload = MonteCarloJobPayload(
            symbol=job_request.symbol,
            start_date=job_request.start_date,
            end_date=job_request.end_date,
            num_runs=job_request.num_runs,
            initial_capital=job_request.initial_capital,
            strategy_params=job_request.strategy_params
        )
        
        # Submit job
        job_id = await job_manager.submit_job(
            payload=payload,
            priority=job_request.priority,
            timeout_seconds=job_request.timeout_seconds
        )
        
        return JobSubmissionResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Job submitted successfully",
            estimated_completion_time=None  # Could be calculated based on queue depth
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.post("/jobs/bulk", response_model=BulkJobSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_bulk_jobs(
    bulk_request: BulkMonteCarloJobRequest,
    background_tasks: BackgroundTasks,
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
                strategy_params=job_req.strategy_params
            )
            payloads.append(payload)
            priorities.append(job_req.priority)
            timeouts.append(job_req.timeout_seconds)
        
        # Submit bulk jobs
        job_ids = await job_manager.submit_bulk_jobs(
            payloads=payloads,
            priorities=priorities,
            timeout_seconds_list=timeouts,
            batch_name=bulk_request.batch_name
        )
        
        # Create response
        job_responses = [
            JobSubmissionResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="Job submitted successfully"
            )
            for job_id in job_ids
        ]
        
        return BulkJobSubmissionResponse(
            batch_id=bulk_request.batch_name,
            jobs=job_responses,
            total_jobs=len(job_ids),
            successful_submissions=len(job_ids),
            failed_submissions=0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit bulk jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
        job = await job_manager.get_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobResponse(
            job_id=job.id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            progress=job.metadata.progress,
            result=job.result,
            error_message=job.error_message,
            metadata=job.metadata.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(
    job_id: str,
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobProgressResponse(
            job_id=job_id,
            status=progress.get("status", JobStatus.UNKNOWN),
            progress=progress.get("progress"),
            current_run=progress.get("current_run"),
            total_runs=progress.get("total_runs"),
            estimated_completion_time=progress.get("estimated_completion_time"),
            last_updated=progress.get("last_updated", datetime.utcnow())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job progress: {str(e)}"
        )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: str,
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
                detail=f"Job {job_id} not found or cannot be cancelled"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, description="Filter jobs by status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
        # This would need to be implemented in the job manager
        # For now, return empty list as placeholder
        return []
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/metrics", response_model=QueueMetricsResponse)
async def get_queue_metrics(
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
            total_jobs=metrics.total_jobs,
            pending_jobs=metrics.pending_jobs,
            running_jobs=metrics.running_jobs,
            completed_jobs=metrics.completed_jobs,
            failed_jobs=metrics.failed_jobs,
            average_processing_time=metrics.average_processing_time,
            queue_depth=metrics.queue_depth,
            worker_count=metrics.worker_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue metrics: {str(e)}"
        )


@router.post("/jobs/{job_id}/wait", response_model=JobResponse)
async def wait_for_job_completion(
    job_id: str,
    timeout_seconds: int = Query(300, ge=1, le=3600, description="Maximum wait time in seconds"),
    job_manager: MonteCarloJobManager = Depends(get_job_manager)
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobResponse(
            job_id=job.id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            progress=job.metadata.progress,
            result=job.result,
            error_message=job.error_message,
            metadata=job.metadata.to_dict()
        )
        
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Job {job_id} did not complete within {timeout_seconds} seconds"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to wait for job completion: {str(e)}"
        )

# Export the router
monte_carlo_router = router