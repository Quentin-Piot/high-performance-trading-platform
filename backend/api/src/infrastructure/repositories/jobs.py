"""
Repository for job database operations.

This module provides database operations for job persistence, deduplication,
and status tracking in the Monte Carlo queue system.
"""
import base64
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.cache import cache_manager, cached_result
from infrastructure.models import Job
from infrastructure.repositories.db_utils import (
    BatchOperationManager,
    DatabaseError,
    db_operation_monitor,
    db_retry,
    execute_with_timeout,
)

logger = logging.getLogger(__name__)

class JobRepository:
    """Repository for job database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._batch_manager = BatchOperationManager(session)

    async def batch_update_job_statuses(self, updates: list[dict[str, Any]]) -> dict[str, int]:
        """
        Batch update multiple job statuses to reduce database round trips.

        Args:
            updates: List of job update dictionaries containing job_id, status, and other fields

        Returns:
            Dictionary with operation counts

        Raises:
            DatabaseError: If batch operation fails
        """
        try:
            for update_data in updates:
                self._batch_manager.add_operation("job_status_update", **update_data)

            results = await self._batch_manager.execute_batch()

            # Invalidate caches for all updated jobs
            for update_data in updates:
                if "job_id" in update_data:
                    await self._invalidate_job_caches(update_data["job_id"])

            logger.info("Batch job status update completed", extra={
                "total_updates": len(updates),
                "results": results
            })

            return results

        except Exception as e:
            logger.error("Batch job status update failed", extra={
                "update_count": len(updates),
                "error": str(e)
            })
            raise DatabaseError(f"Batch update failed: {str(e)}") from e

    async def batch_update_job_progress(self, updates: list[dict[str, Any]]) -> dict[str, int]:
        """
        Batch update multiple job progress values to reduce database round trips.

        Args:
            updates: List of job progress update dictionaries

        Returns:
            Dictionary with operation counts

        Raises:
            DatabaseError: If batch operation fails
        """
        try:
            for update_data in updates:
                # Ensure progress is clamped between 0 and 1
                if "progress" in update_data:
                    update_data["progress"] = max(0.0, min(1.0, update_data["progress"]))

                self._batch_manager.add_operation("job_progress_update", **update_data)

            results = await self._batch_manager.execute_batch()

            logger.info("Batch job progress update completed", extra={
                "total_updates": len(updates),
                "results": results
            })

            return results

        except Exception as e:
            logger.error("Batch job progress update failed", extra={
                "update_count": len(updates),
                "error": str(e)
            })
            raise DatabaseError(f"Batch progress update failed: {str(e)}") from e

    @db_retry(max_retries=3, delay=1.0)
    async def create_job(
        self,
        job_id: str,
        payload: dict[str, Any],
        status: str = "pending",
        priority: str = "normal",
        dedup_key: str | None = None
    ) -> Job:
        """
        Create a new job in the database with retry logic and performance monitoring.

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
            DatabaseError: If operation fails after retries
            DatabaseTimeoutError: If operation times out
        """
        async with db_operation_monitor("create_job", self.session):
            # Ensure payload is JSON-serializable (convert bytes to base64 if present)
            try:
                if payload is not None:
                    if isinstance(payload.get("csv_data"), (bytes, bytearray)):
                        safe_payload = payload.copy()
                        safe_payload["csv_data"] = base64.b64encode(payload["csv_data"]).decode("ascii")
                        safe_payload["encoding"] = "base64"
                        payload = safe_payload
            except Exception:
                # If any unexpected issue occurs, coerce payload to a string to avoid crashing
                payload = {"raw": str(payload)}

            job = Job(
                id=job_id,
                payload=payload,
                status=status,
                priority=priority,
                dedup_key=dedup_key
            )

            async def create_operation():
                self.session.add(job)
                await self.session.commit()
                await self.session.refresh(job)
                return job

            return await execute_with_timeout(
                self.session,
                create_operation,
                timeout=30.0,
                operation_name="create_job"
            )

    @cached_result("job", ttl=300)  # Cache for 5 minutes
    async def get_job_by_id(self, job_id: str) -> Job | None:
        """Get job by ID with caching"""
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        # Invalidate cache if job is completed or failed
        if job and job.status in ["completed", "failed"]:
            cache_key = cache_manager._generate_key("job", "get_job_by_id", args=str((job_id,)), kwargs=[])
            await cache_manager.delete(cache_key)

        return job

    async def get_job_by_dedup_key(self, dedup_key: str) -> Job | None:
        """Get job by deduplication key"""
        result = await self.session.execute(
            select(Job).where(Job.dedup_key == dedup_key)
        )
        return result.scalar_one_or_none()

    async def find_existing_job(self, dedup_key: str) -> Job | None:
        """
        Find existing job with same dedup_key in PENDING or PROCESSING status.

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
                        Job.status == "processing"
                    )
                )
            )
        )
        return result.scalar_one_or_none()

    @cached_result("job_counts", ttl=60)  # Cache for 1 minute
    async def get_job_counts_by_status(self) -> dict[str, int]:
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
            all_statuses = ['pending', 'processing', 'completed', 'failed', 'retry']
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
        message: str | None = None,
        current_run: int | None = None,
        total_runs: int | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None
    ) -> bool:
        """
        Update job progress and timing information.

        Args:
            job_id: Job identifier
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            current_run: Current run number
            total_runs: Total number of runs
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
                "progress": progress,
                "updated_at": datetime.utcnow()
            }

            # Add timing fields if provided
            if started_at is not None:
                update_data["started_at"] = started_at
            if completed_at is not None:
                update_data["completed_at"] = completed_at

            # Get current job to update payload
            result = await self.session.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()

            if job:
                payload = job.payload.copy() if job.payload else {}
                if message:
                    payload["progress_message"] = message
                if current_run is not None:
                    payload["current_run"] = current_run
                if total_runs is not None:
                    payload["total_runs"] = total_runs
                update_data["payload"] = payload

            result = await self.session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(**update_data)
            )

            await self.session.commit()

            # Invalidate caches so progress reads are fresh for WebSockets/UI
            try:
                await self._invalidate_job_caches(job_id)
            except Exception as e:
                logger.warning("Failed to invalidate job caches after progress update", extra={
                    "job_id": job_id,
                    "error": str(e)
                })

            return result.rowcount > 0

        except Exception:
            await self.session.rollback()
            return False

    @db_retry(max_retries=2, delay=0.5)
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        worker_id: str | None = None,
        error: str | None = None,
        progress: float | None = None,
        artifact_url: str | None = None,
        completed_at: datetime | None = None
    ) -> bool:
        """
        Update job status with retry logic, timeout handling, and cache invalidation.

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

        Raises:
            DatabaseError: If operation fails after retries
            DatabaseTimeoutError: If operation times out
        """
        async with db_operation_monitor("update_job_status", self.session):
            try:
                update_data = {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }

                if worker_id is not None:
                    update_data["worker_id"] = worker_id
                if error is not None:
                    update_data["error"] = error
                if progress is not None:
                    update_data["progress"] = max(0.0, min(1.0, progress))
                if artifact_url is not None:
                    update_data["artifact_url"] = artifact_url
                if completed_at is not None:
                    update_data["completed_at"] = completed_at

                async def update_operation():
                    result = await self.session.execute(
                        update(Job)
                        .where(Job.id == job_id)
                        .values(**update_data)
                    )
                    await self.session.commit()
                    return result.rowcount > 0

                success = await execute_with_timeout(
                    self.session,
                    update_operation,
                    timeout=15.0,
                    operation_name="update_job_status"
                )

                # Invalidate caches after successful update
                if success:
                    await self._invalidate_job_caches(job_id)
                    logger.debug("Updated job status", extra={
                        "job_id": job_id,
                        "status": status,
                        "worker_id": worker_id,
                        "progress": progress
                    })

                return success

            except Exception as e:
                try:
                    await self.session.rollback()
                except Exception as rollback_error:
                    logger.warning("Failed to rollback after update error", extra={
                        "job_id": job_id,
                        "rollback_error": str(rollback_error)
                    })

                logger.error("Failed to update job status", extra={
                    "job_id": job_id,
                    "status": status,
                    "error": str(e)
                })
                raise DatabaseError(f"Failed to update job status: {str(e)}") from e

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
        status: str | None = None,
        worker_id: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Job]:
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

    async def get_job_counts_by_status_simple(self) -> dict[str, int]:
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
