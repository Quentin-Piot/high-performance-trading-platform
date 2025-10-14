"""
Repository for job database operations.

This module provides database operations for job persistence, deduplication,
and status tracking in the Monte Carlo queue system.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from infrastructure.models import Job
from domain.queue import JobStatus
from infrastructure.cache import cache_manager, cached_result

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for job database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_job(
        self,
        job_id: str,
        payload: Dict[str, Any],
        status: str = "pending",
        priority: str = "normal",
        dedup_key: Optional[str] = None
    ) -> Job:
        """
        Create a new job in the database.
        
        Args:
            job_id: Unique job identifier
            payload: Job payload data
            status: Initial job status
            priority: Job priority
            dedup_key: Deduplication key for idempotence
            
        Returns:
            Created job instance
            
        Raises:
            IntegrityError: If dedup_key already exists
        """
        job = Job(
            id=job_id,
            payload=payload,
            status=status,
            priority=priority,
            dedup_key=dedup_key
        )
        
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        
        return job
    
    @cached_result("job", ttl=300)  # Cache for 5 minutes
    async def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """Get job by ID with caching"""
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        # Invalidate cache if job is completed or failed
        if job and job.status in ["completed", "failed"]:
            cache_key = await cache_manager._generate_key("job", "get_job_by_id", args=str((job_id,)), kwargs=[])
            await cache_manager.delete(cache_key)
        
        return job
    
    async def get_job_by_dedup_key(self, dedup_key: str) -> Optional[Job]:
        """Get job by deduplication key"""
        result = await self.session.execute(
            select(Job).where(Job.dedup_key == dedup_key)
        )
        return result.scalar_one_or_none()
    
    async def find_existing_job(self, dedup_key: str) -> Optional[Job]:
        """
        Find existing job with same dedup_key in PENDING or RUNNING status.
        
        Args:
            dedup_key: Deduplication key to search for
            
        Returns:
            Existing job if found, None otherwise
        """
        if not dedup_key:
            return None
            
        result = await self.session.execute(
            select(Job).where(
                and_(
                    Job.dedup_key == dedup_key,
                    or_(
                        Job.status == "pending",
                        Job.status == "running"
                    )
                )
            )
        )
        return result.scalar_one_or_none()
    
    @cached_result("job_counts", ttl=60)  # Cache for 1 minute
    async def get_job_counts_by_status(self) -> Dict[str, int]:
        """
        Get job counts grouped by status for metrics with caching.
        
        Returns:
            Dictionary mapping status to count
        """
        try:
            # Use raw SQL for better performance
            result = await self.session.execute(
                text("""
                SELECT status, COUNT(*) as count
                FROM jobs
                GROUP BY status
                """)
            )
            
            rows = result.fetchall()
            
            # Convert to dictionary
            counts = {row.status: row.count for row in rows}
            
            # Ensure all statuses are represented
            all_statuses = ['pending', 'running', 'completed', 'failed', 'retry']
            for status in all_statuses:
                if status not in counts:
                    counts[status] = 0
                    
            logger.debug("Retrieved job counts by status", extra={
                "counts": counts,
                "total_jobs": sum(counts.values())
            })
                    
            return counts
            
        except Exception as e:
            logger.error("Failed to get job counts by status", extra={
                "error": str(e)
            })
            raise

    async def update_job_progress(
        self,
        job_id: str,
        progress: float,
        message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """
        Update job progress and timing information.
        
        Args:
            job_id: Job identifier
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            started_at: Job start timestamp
            completed_at: Job completion timestamp
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Clamp progress between 0 and 1
            progress = max(0.0, min(1.0, progress))
            
            # Build update values
            update_data = {
                Job.progress: progress,
                Job.updated_at: datetime.utcnow()
            }
            
            # Add timing fields if provided
            if started_at is not None:
                update_data[Job.started_at] = started_at
            if completed_at is not None:
                update_data[Job.completed_at] = completed_at
            
            # Store progress message in payload if provided
            if message:
                # Get current job to update payload
                result = await self.session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if job:
                    payload = job.payload.copy() if job.payload else {}
                    payload["progress_message"] = message
                    update_data[Job.payload] = payload
            
            result = await self.session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(**update_data)
            )
            
            await self.session.commit()
            return result.rowcount > 0
            
        except Exception as e:
            await self.session.rollback()
            return False

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        worker_id: Optional[str] = None,
        error: Optional[str] = None,
        progress: Optional[float] = None,
        artifact_url: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """
        Update job status and invalidate relevant caches.
        
        Args:
            job_id: Job identifier
            status: New job status
            worker_id: Worker processing the job
            error: Error message if failed
            progress: Job progress (0.0 to 1.0)
            artifact_url: URL to job artifacts
            completed_at: Job completion timestamp
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            update_data = {
                Job.status: status,
                Job.updated_at: datetime.utcnow()
            }
            
            if worker_id is not None:
                update_data[Job.worker_id] = worker_id
            if error is not None:
                update_data[Job.error] = error
            if progress is not None:
                update_data[Job.progress] = max(0.0, min(1.0, progress))
            if artifact_url is not None:
                update_data[Job.artifact_url] = artifact_url
            if completed_at is not None:
                update_data[Job.completed_at] = completed_at
            
            result = await self.session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(**update_data)
            )
            
            await self.session.commit()
            
            # Invalidate caches after successful update
            if result.rowcount > 0:
                await self._invalidate_job_caches(job_id)
                logger.debug("Updated job status", extra={
                    "job_id": job_id,
                    "status": status,
                    "worker_id": worker_id,
                    "progress": progress
                })
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.session.rollback()
            logger.error("Failed to update job status", extra={
                "job_id": job_id,
                "status": status,
                "error": str(e)
            })
            return False
    
    async def _invalidate_job_caches(self, job_id: str) -> None:
        """Invalidate caches related to a specific job"""
        try:
            # Invalidate job-specific cache
            job_cache_key = cache_manager._generate_key("job", "get_job_by_id", args=str((job_id,)), kwargs=[])
            await cache_manager.delete(job_cache_key)
            
            # Invalidate job counts cache
            await cache_manager.delete_pattern("job_counts:*")
            
            logger.debug("Invalidated job caches", extra={"job_id": job_id})
            
        except Exception as e:
            logger.warning("Failed to invalidate job caches", extra={
                "job_id": job_id,
                "error": str(e)
            })
    
    async def increment_attempts(self, job_id: str) -> bool:
        """
        Increment job attempt count.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was updated, False if not found
        """
        result = await self.session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                attempts=Job.attempts + 1,
                updated_at=datetime.utcnow()
            )
        )
        
        await self.session.commit()
        return result.rowcount > 0
    
    async def list_jobs(
        self,
        status: Optional[str] = None,
        worker_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """
        List jobs with optional filtering.
        
        Args:
            status: Filter by status
            worker_id: Filter by worker ID
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of jobs
        """
        query = select(Job)
        
        if status:
            query = query.where(Job.status == status)
        if worker_id:
            query = query.where(Job.worker_id == worker_id)
            
        query = query.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_job_counts_by_status_simple(self) -> Dict[str, int]:
        """Get count of jobs by status (simple version without caching)"""
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(Job.status, func.count(Job.id))
            .group_by(Job.status)
        )
        
        return {status: count for status, count in result.all()}
    
    async def cleanup_old_jobs(self, older_than_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs.
        
        Args:
            older_than_hours: Remove jobs older than this many hours
            
        Returns:
            Number of jobs removed
        """
        from sqlalchemy import delete
        
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        result = await self.session.execute(
            delete(Job).where(
                and_(
                    Job.updated_at < cutoff_time,
                    or_(
                        Job.status == "completed",
                        Job.status == "failed",
                        Job.status == "cancelled"
                    )
                )
            )
        )
        
        await self.session.commit()
        return result.rowcount