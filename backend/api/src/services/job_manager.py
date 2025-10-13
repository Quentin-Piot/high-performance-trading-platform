"""
Job manager implementation for coordinating Monte Carlo simulation jobs.

This module provides a high-level interface for submitting, tracking, and managing
Monte Carlo simulation jobs through the queue system.
"""
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, BinaryIO
import uuid
import asyncio

from src.domain.queue import (
    JobManagerInterface, Job, JobStatus, JobMetadata, JobPriority,
    MonteCarloJobPayload, QueueInterface
)

logger = logging.getLogger(__name__)


class MonteCarloJobManager(JobManagerInterface):
    """Job manager for Monte Carlo simulation jobs"""
    
    def __init__(
        self,
        queue: QueueInterface[MonteCarloJobPayload],
        default_timeout_seconds: int = 3600,  # 1 hour default
        default_max_retries: int = 3
    ):
        """
        Initialize Monte Carlo job manager.
        
        Args:
            queue: Queue interface for job management
            default_timeout_seconds: Default job timeout in seconds
            default_max_retries: Default maximum retry attempts
        """
        self.queue = queue
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_retries = default_max_retries
        
        logger.info("Initialized Monte Carlo job manager")
    
    async def submit_monte_carlo_job(
        self,
        csv_file: BinaryIO,
        filename: str,
        strategy_name: str,
        strategy_params: Dict[str, Any],
        runs: int,
        method: str = "bootstrap",
        method_params: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        include_equity_envelope: bool = True,
        priority: JobPriority = JobPriority.NORMAL,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Submit a Monte Carlo simulation job.
        
        Args:
            csv_file: CSV file containing price data
            filename: Original filename
            strategy_name: Name of the trading strategy
            strategy_params: Strategy parameters
            runs: Number of Monte Carlo runs
            method: Simulation method ("bootstrap" or "gaussian")
            method_params: Method-specific parameters
            seed: Random seed for reproducibility
            include_equity_envelope: Whether to include equity envelope
            priority: Job priority
            user_id: User ID for tracking
            correlation_id: Correlation ID for request tracking
            timeout_seconds: Job timeout in seconds
            max_retries: Maximum retry attempts
            tags: Additional tags for job metadata
            
        Returns:
            Job ID for tracking
        """
        try:
            # Read CSV data
            csv_file.seek(0)
            csv_data = csv_file.read()
            
            # Create job payload
            payload = MonteCarloJobPayload(
                csv_data=csv_data,
                filename=filename,
                strategy_name=strategy_name,
                strategy_params=strategy_params,
                runs=runs,
                method=method,
                method_params=method_params or {},
                seed=seed,
                include_equity_envelope=include_equity_envelope
            )
            
            # Create job metadata
            job_tags = tags or {}
            job_tags.update({
                "strategy": strategy_name,
                "method": method,
                "runs": str(runs),
                "filename": filename
            })
            
            metadata = JobMetadata(
                priority=priority,
                max_retries=max_retries or self.default_max_retries,
                timeout_seconds=timeout_seconds or self.default_timeout_seconds,
                tags=job_tags,
                user_id=user_id,
                correlation_id=correlation_id or str(uuid.uuid4())
            )
            
            # Create job
            job = Job(payload=payload, metadata=metadata)
            
            # Submit to queue
            job_id = await self.queue.enqueue(job)
            
            logger.info(
                f"Submitted Monte Carlo job {job_id}: "
                f"strategy={strategy_name}, runs={runs}, method={method}"
            )
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit Monte Carlo job: {str(e)}")
            raise
    
    async def submit_job(self, payload: Any, metadata: Optional[JobMetadata] = None) -> str:
        """
        Submit a generic job (implements JobManagerInterface).
        
        Args:
            payload: Job payload (should be MonteCarloJobPayload)
            metadata: Optional job metadata
            
        Returns:
            Job ID
        """
        if not isinstance(payload, MonteCarloJobPayload):
            raise ValueError("Payload must be MonteCarloJobPayload")
        
        # Use default metadata if not provided
        if metadata is None:
            metadata = JobMetadata(
                max_retries=self.default_max_retries,
                timeout_seconds=self.default_timeout_seconds
            )
        
        # Create and submit job
        job = Job(payload=payload, metadata=metadata)
        return await self.queue.enqueue(job)
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job or None if not found
        """
        return await self.queue.get_job_status(job_id)
    
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """
        List jobs with optional filtering.
        
        Note: This is a simplified implementation. In a production system,
        you would typically store job metadata in a database for efficient querying.
        
        Args:
            status: Filter by status
            user_id: Filter by user
            limit: Maximum number of jobs
            offset: Pagination offset
            
        Returns:
            List of jobs
        """
        # This is a placeholder implementation
        # In practice, you would query a job database or cache
        logger.warning("list_jobs is not fully implemented - requires job database")
        return []
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        return await self.queue.cancel_job(job_id)
    
    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job result if completed.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job result or None if not completed
        """
        job = await self.get_job(job_id)
        if job and job.status == JobStatus.COMPLETED:
            return job.result
        return None
    
    async def wait_for_job_completion(
        self,
        job_id: str,
        timeout_seconds: Optional[int] = None,
        poll_interval: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for job completion and return result.
        
        Args:
            job_id: Job ID to wait for
            timeout_seconds: Maximum time to wait
            poll_interval: Polling interval in seconds
            
        Returns:
            Job result or None if timeout/failed
        """
        start_time = datetime.now(UTC)
        
        while True:
            job = await self.get_job(job_id)
            
            if not job:
                logger.warning(f"Job {job_id} not found")
                return None
            
            if job.status == JobStatus.COMPLETED:
                return job.result
            elif job.status == JobStatus.FAILED:
                logger.error(f"Job {job_id} failed: {job.error}")
                return None
            elif job.status == JobStatus.CANCELLED:
                logger.info(f"Job {job_id} was cancelled")
                return None
            
            # Check timeout
            if timeout_seconds:
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                if elapsed >= timeout_seconds:
                    logger.warning(f"Timeout waiting for job {job_id}")
                    return None
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
    
    async def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job progress information.
        
        Args:
            job_id: Job ID
            
        Returns:
            Progress information or None if not found
        """
        job = await self.get_job(job_id)
        if not job:
            return None
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "progress": job.progress,
            "created_at": job.metadata.created_at.isoformat(),
            "updated_at": job.metadata.updated_at.isoformat(),
            "error": job.error,
            "progress_message": job.metadata.tags.get("progress_message"),
            "retry_count": job.metadata.retry_count,
            "max_retries": job.metadata.max_retries
        }
    
    async def get_queue_metrics(self) -> Dict[str, Any]:
        """
        Get queue metrics for monitoring.
        
        Returns:
            Queue metrics
        """
        try:
            metrics = await self.queue.get_metrics()
            return {
                "queue_name": metrics.queue_name,
                "pending_jobs": metrics.pending_jobs,
                "processing_jobs": metrics.processing_jobs,
                "completed_jobs": metrics.completed_jobs,
                "failed_jobs": metrics.failed_jobs,
                "average_processing_time": metrics.average_processing_time,
                "throughput_per_minute": metrics.throughput_per_minute,
                "last_updated": metrics.last_updated.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get queue metrics: {str(e)}")
            raise
    
    async def bulk_submit_jobs(
        self,
        job_requests: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[str]:
        """
        Submit multiple jobs in batches.
        
        Args:
            job_requests: List of job request dictionaries
            batch_size: Number of jobs to submit per batch
            
        Returns:
            List of job IDs
        """
        job_ids = []
        
        for i in range(0, len(job_requests), batch_size):
            batch = job_requests[i:i + batch_size]
            batch_tasks = []
            
            for job_request in batch:
                task = self.submit_monte_carlo_job(**job_request)
                batch_tasks.append(task)
            
            # Submit batch concurrently
            batch_job_ids = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for job_id in batch_job_ids:
                if isinstance(job_id, Exception):
                    logger.error(f"Failed to submit job in batch: {str(job_id)}")
                else:
                    job_ids.append(job_id)
            
            # Small delay between batches to avoid overwhelming the queue
            if i + batch_size < len(job_requests):
                await asyncio.sleep(0.1)
        
        logger.info(f"Bulk submitted {len(job_ids)} jobs successfully")
        return job_ids
    
    async def cleanup_completed_jobs(self, older_than_hours: int = 24) -> int:
        """
        Cleanup completed jobs older than specified hours.
        
        Args:
            older_than_hours: Remove jobs completed more than this many hours ago
            
        Returns:
            Number of jobs cleaned up
        """
        # This would typically involve cleaning up job metadata from a database
        # For now, this is a placeholder
        logger.info(f"Cleanup completed jobs older than {older_than_hours} hours")
        return 0