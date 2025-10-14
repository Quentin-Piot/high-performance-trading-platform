"""
Job manager implementation for coordinating Monte Carlo simulation jobs.

This module provides a high-level interface for submitting, tracking, and managing
Monte Carlo simulation jobs through the queue system with database persistence.
"""
import logging
import os
import json
import hashlib
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, BinaryIO
import uuid
import asyncio

from domain.queue import (
    JobManagerInterface, Job, JobStatus, JobMetadata, JobPriority,
    MonteCarloJobPayload, QueueInterface
)
from infrastructure.db import SessionLocal
from infrastructure.repositories.jobs import JobRepository
from infrastructure.cache import cache_manager, cached_result

logger = logging.getLogger(__name__)


class MonteCarloJobManager(JobManagerInterface):
    """Job manager for Monte Carlo simulation jobs with database persistence"""
    
    def __init__(
        self,
        queue: QueueInterface[MonteCarloJobPayload],
        default_timeout_seconds: int = 3600,  # 1 hour default
        default_max_retries: int = 3,
        max_runs: Optional[int] = None,
        max_payload_size: Optional[int] = None
    ):
        """
        Initialize Monte Carlo job manager.
        
        Args:
            queue: Queue interface for job management
            default_timeout_seconds: Default job timeout in seconds
            default_max_retries: Default maximum retry attempts
            max_runs: Maximum number of runs allowed (default: 20000)
            max_payload_size: Maximum payload size in bytes (default: 1MB)
        """
        self.queue = queue
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_retries = default_max_retries
        
        # Configurable hard limits with environment variable fallbacks
        self.max_runs = max_runs or int(os.getenv("MC_HARD_CAP_RUNS", "20000"))
        self.max_payload_size = max_payload_size or int(os.getenv("MC_HARD_CAP_PAYLOAD_SIZE", str(1024 * 1024)))  # 1MB default
        
        logger.info(f"Initialized Monte Carlo job manager with hard limits: max_runs={self.max_runs}, max_payload_size={self.max_payload_size} bytes")
    
    def _generate_dedup_key(self, payload: Dict[str, Any]) -> str:
        """
        Generate deduplication key from payload.
        
        Args:
            payload: Job payload
            
        Returns:
            SHA256 hash of normalized payload
        """
        # Create normalized payload for hashing (exclude non-deterministic fields)
        normalized = {
            "strategy_name": payload.get("strategy_name"),
            "strategy_params": payload.get("strategy_params"),
            "runs": payload.get("runs"),
            "method": payload.get("method"),
            "method_params": payload.get("method_params"),
            "seed": payload.get("seed"),
            # Include CSV data hash for uniqueness
            "csv_hash": hashlib.sha256(payload.get("csv_data", b"")).hexdigest()
        }
        
        # Sort keys for consistent hashing
        normalized_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(normalized_str.encode()).hexdigest()
    
    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """
        Validate job payload against hard limits.
        
        Args:
            payload: Job payload to validate
            
        Raises:
            ValueError: If payload exceeds limits
        """
        # Validate number of runs
        runs = payload.get("runs", 0)
        if runs <= 0:
            raise ValueError("Number of runs must be positive")
        if runs > self.max_runs:
            raise ValueError(f"Number of runs ({runs}) exceeds maximum allowed ({self.max_runs})")
        
        # Validate payload size
        payload_size = len(json.dumps(payload).encode())
        if payload_size > self.max_payload_size:
            raise ValueError(f"Payload size ({payload_size} bytes) exceeds maximum allowed ({self.max_payload_size} bytes)")
        
        # Validate required fields
        required_fields = ["strategy_name", "strategy_params", "runs", "csv_data"]
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate CSV data size specifically
        csv_data = payload.get("csv_data", b"")
        if isinstance(csv_data, str):
            csv_data = csv_data.encode()
        csv_size = len(csv_data)
        max_csv_size = self.max_payload_size // 2  # Reserve half payload size for CSV data
        if csv_size > max_csv_size:
            raise ValueError(f"CSV data size ({csv_size} bytes) exceeds maximum allowed ({max_csv_size} bytes)")
        
        # Validate strategy parameters
        strategy_params = payload.get("strategy_params", {})
        if not isinstance(strategy_params, dict):
            raise ValueError("Strategy parameters must be a dictionary")
        
        logger.debug(f"Payload validation passed: runs={runs}, size={payload_size} bytes, csv_size={csv_size} bytes")
    
    async def _get_job_repository(self) -> JobRepository:
        """Get job repository with database session"""
        session = SessionLocal()
        return JobRepository(session)
    
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
        tags: Optional[Dict[str, str]] = None,
        dedup_key: Optional[str] = None
    ) -> str:
        """
        Submit a Monte Carlo simulation job with database persistence and deduplication.
        
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
            dedup_key: Optional deduplication key for idempotence
            
        Returns:
            Job ID for tracking
            
        Raises:
            ValueError: If payload validation fails
        """
        try:
            # Read CSV data
            csv_file.seek(0)
            csv_data = csv_file.read()
            
            # Create job payload for validation and deduplication
            payload_dict = {
                "csv_data": csv_data,
                "filename": filename,
                "strategy_name": strategy_name,
                "strategy_params": strategy_params,
                "runs": runs,
                "method": method,
                "method_params": method_params or {},
                "seed": seed,
                "include_equity_envelope": include_equity_envelope,
                "parallel_workers": 1
            }
            
            # Validate payload
            self._validate_payload(payload_dict)
            
            # Generate deduplication key if not provided
            if dedup_key is None:
                dedup_key = self._generate_dedup_key(payload_dict)
            
            # Check for existing job with same dedup_key
            job_repo = await self._get_job_repository()
            try:
                existing_job = await job_repo.find_existing_job(dedup_key)
                if existing_job:
                    logger.info(f"Found existing job {existing_job.id} for dedup_key {dedup_key}")
                    return existing_job.id
                
                # Create new job in database
                job_id = str(uuid.uuid4())
                
                db_job = await job_repo.create_job(
                    job_id=job_id,
                    payload=payload_dict,
                    status="pending",
                    priority=priority.name.lower(),
                    dedup_key=dedup_key
                )
                
                # Create job payload for queue (only job_id)
                queue_payload = {"job_id": job_id}
                
                # Create job metadata
                metadata = JobMetadata(
                    job_id=job_id,
                    priority=priority,
                    max_retries=max_retries or self.default_max_retries,
                    timeout_seconds=timeout_seconds or self.default_timeout_seconds,
                    tags=tags or {},
                    user_id=user_id,
                    correlation_id=correlation_id
                )
                
                # Create job for queue
                job = Job(
                    payload=queue_payload,
                    metadata=metadata
                )
                
                # Enqueue job
                await self.queue.enqueue(job)
                
                logger.info(f"Submitted Monte Carlo job {job_id} with {runs} runs")
                return job_id
                
            finally:
                await job_repo.session.close()
                
        except Exception as e:
            logger.error(f"Failed to submit Monte Carlo job: {e}")
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
    
    async def get_job_progress(self, job_id: str) -> Dict[str, Any]:
        """
        Get job progress and status with artifact information and duration tracking.
        Uses caching for completed jobs to improve performance.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job progress information including artifacts and timing data
        """
        try:
            # Check cache first for completed jobs
            cache_key = await cache_manager._generate_key("job_progress", job_id)
            cached_progress = await cache_manager.get(cache_key)
            
            if cached_progress and cached_progress.get("status") in ["completed", "failed"]:
                logger.debug("Cache hit for job progress", extra={"job_id": job_id})
                return cached_progress
            
            # Get progress from queue (real-time)
            queue_progress = await self.queue.get_job_progress(job_id)
            
            # Get job from database (persistent data)
            job_repo = await self._get_job_repository()
            try:
                db_job = await job_repo.get_job_by_id(job_id)
                
                # Calculate duration if timing data is available
                duration_seconds = None
                if db_job and db_job.started_at:
                    end_time = db_job.completed_at or datetime.utcnow()
                    duration_seconds = (end_time - db_job.started_at).total_seconds()
                
                # Merge information from both sources
                progress_info = {
                    "job_id": job_id,
                    "status": queue_progress.status if queue_progress else (db_job.status if db_job else "unknown"),
                    "progress": queue_progress.progress if queue_progress else 0.0,
                    "message": queue_progress.message if queue_progress else None,
                    "created_at": db_job.created_at.isoformat() if db_job else None,
                    "updated_at": db_job.updated_at.isoformat() if db_job else None,
                    "started_at": db_job.started_at.isoformat() if db_job and db_job.started_at else None,
                    "completed_at": db_job.completed_at.isoformat() if db_job and db_job.completed_at else None,
                    "duration_seconds": duration_seconds,
                    "error": queue_progress.error if queue_progress else (db_job.error if db_job else None),
                    "retry_count": queue_progress.retry_count if queue_progress else (db_job.attempts if db_job else 0),
                    "worker_id": queue_progress.worker_id if queue_progress else (db_job.worker_id if db_job else None),
                    "artifact_url": db_job.artifact_url if db_job else None,
                    "artifacts": []
                }
                
                # If job is completed and has artifacts, get artifact list
                if (progress_info["status"] == "completed" and 
                    hasattr(self, 'storage_adapter') and 
                    self.storage_adapter):
                    try:
                        artifacts = await self.storage_adapter.list_job_artifacts(job_id)
                        progress_info["artifacts"] = artifacts
                    except Exception as e:
                        logger.warning("Failed to list artifacts for job", extra={
                            "job_id": job_id,
                            "error": str(e)
                        })
                
                # Cache completed/failed jobs for 15 minutes
                if progress_info["status"] in ["completed", "failed"]:
                    await cache_manager.set(cache_key, progress_info, ttl=900)
                    logger.debug("Cached job progress", extra={
                        "job_id": job_id,
                        "status": progress_info["status"]
                    })
                
                return progress_info
                
            finally:
                await job_repo.session.close()
            
        except Exception as e:
            logger.error("Failed to get job progress", extra={
                "job_id": job_id,
                "error": str(e)
            })
            raise
    
    async def get_queue_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive queue metrics including database statistics.
        
        Returns:
            Dictionary containing queue and database metrics
        """
        try:
            # Get queue metrics
            queue_metrics = await self.queue.get_metrics()
            
            # Get database statistics
            job_repo = await self._get_job_repository()
            db_stats = await job_repo.get_job_counts_by_status()
            
            # Calculate additional metrics
            total_jobs = sum(db_stats.values())
            retry_jobs = db_stats.get("retry", 0)
            
            # Enhanced metrics combining queue and database data
            enhanced_metrics = {
                # Basic queue metrics
                "queue_name": queue_metrics.queue_name,
                "pending_jobs": queue_metrics.pending_jobs,
                "processing_jobs": queue_metrics.processing_jobs,
                "completed_jobs": queue_metrics.completed_jobs,
                "failed_jobs": queue_metrics.failed_jobs,
                "average_processing_time": queue_metrics.average_processing_time,
                "throughput_per_minute": queue_metrics.throughput_per_minute,
                "last_updated": queue_metrics.last_updated.isoformat(),
                
                # Enhanced database statistics
                "database_stats": {
                    "total_jobs": total_jobs,
                    "jobs_by_status": db_stats,
                    "retry_rate": (retry_jobs / total_jobs * 100) if total_jobs > 0 else 0.0,
                    "success_rate": (db_stats.get("completed", 0) / total_jobs * 100) if total_jobs > 0 else 0.0,
                    "failure_rate": (db_stats.get("failed", 0) / total_jobs * 100) if total_jobs > 0 else 0.0
                },
                
                # System health indicators
                "health_indicators": {
                    "queue_backlog": queue_metrics.pending_jobs > 100,  # Alert if > 100 pending
                    "high_failure_rate": (db_stats.get("failed", 0) / total_jobs * 100) > 10 if total_jobs > 0 else False,
                    "dlq_messages": queue_metrics.failed_jobs,
                    "active_workers": 0,  # Would need worker registry for this
                }
            }
            
            return enhanced_metrics
            
        except Exception as e:
            logger.error(f"Failed to get enhanced queue metrics: {str(e)}")
            # Fallback to basic queue metrics
            try:
                basic_metrics = await self.queue.get_metrics()
                return {
                    "queue_name": basic_metrics.queue_name,
                    "pending_jobs": basic_metrics.pending_jobs,
                    "processing_jobs": basic_metrics.processing_jobs,
                    "completed_jobs": basic_metrics.completed_jobs,
                    "failed_jobs": basic_metrics.failed_jobs,
                    "average_processing_time": basic_metrics.average_processing_time,
                    "throughput_per_minute": basic_metrics.throughput_per_minute,
                    "last_updated": basic_metrics.last_updated.isoformat(),
                    "error": "Enhanced metrics unavailable"
                }
            except Exception as fallback_error:
                logger.error(f"Failed to get basic queue metrics: {str(fallback_error)}")
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