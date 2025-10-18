"""Monte Carlo simulation worker with retry logic and artifact storage.

This module implements the worker that processes Monte Carlo simulation jobs,
including exponential backoff retry logic, progress tracking, and S3 artifact storage.
"""
import asyncio
import json
import logging
import random
import signal
import traceback
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import StringIO
from typing import Any

import pandas as pd

from domain.queue import (
    Job,
    JobProcessorInterface,
    MonteCarloJobPayload,
    ProgressCallbackInterface,
    QueueInterface,
    WorkerInterface,
)
from infrastructure.repositories.jobs import JobRepository
from infrastructure.storage.s3_adapter import S3StorageAdapter
from services.mc_backtest_service import run_monte_carlo_on_df

# Configure logging to show stack traces

logger = logging.getLogger(__name__)

class MonteCarloJobProcessor(JobProcessorInterface[MonteCarloJobPayload, dict[str, Any]]):
    """Processor for Monte Carlo simulation jobs with artifact storage"""

    def __init__(
        self,
        processor_id: str,
        progress_callback: ProgressCallbackInterface | None = None,
        storage_adapter: S3StorageAdapter | None = None
    ):
        """
        Initialize Monte Carlo job processor.

        Args:
            processor_id: Unique processor identifier
            progress_callback: Optional progress reporting callback
            storage_adapter: S3 adapter for artifact storage
        """
        self.processor_id = processor_id
        self.progress_callback = progress_callback
        self.storage_adapter = storage_adapter

        logger.info(f"Initialized Monte Carlo processor: {processor_id}")

    async def process(self, job: Job[MonteCarloJobPayload]) -> dict[str, Any]:
        """
        Process a Monte Carlo simulation job with comprehensive tracking.

        Args:
            job: Monte Carlo job to process

        Returns:
            Simulation results with artifact URLs

        Raises:
            Exception: If processing fails
        """
        start_time = datetime.now(UTC)

        try:
            payload = job.payload
            job_id = job.metadata.job_id

            logger.info(f"Processing Monte Carlo job {job_id} with {payload.runs} runs", extra={
                "job_id": job_id,
                "processor_id": self.processor_id,
                "started_at": start_time.isoformat()
            })

            # Report initial progress with timing
            if self.progress_callback:
                await self.progress_callback.report_progress(
                    job_id, 0.0, "Starting simulation..."
                )

            # Create progress callback for the service
            async def service_progress_callback(progress: float, message: str = ""):
                if self.progress_callback:
                    await self.progress_callback.report_progress(job_id, progress, message)

            # Execute Monte Carlo simulation
            result = await self._execute_simulation(payload, service_progress_callback)

            # Store artifacts if storage adapter is available
            artifact_urls = {}
            if self.storage_adapter:
                try:
                    artifact_urls = await self._store_artifacts(job_id, result, payload)
                    result["artifact_urls"] = artifact_urls
                    logger.info(f"Stored artifacts for job {job_id}: {artifact_urls}")
                except Exception as e:
                    logger.error(f"Failed to store artifacts for job {job_id}: {str(e)}")
                    # Continue without artifacts rather than failing the job

            # Report completion with timing
            completion_time = datetime.now(UTC)
            duration = (completion_time - start_time).total_seconds()

            if self.progress_callback:
                await self.progress_callback.report_completion(job_id, result)

            logger.info(f"Completed Monte Carlo job {job_id}", extra={
                "job_id": job_id,
                "processor_id": self.processor_id,
                "duration_seconds": duration,
                "completed_at": completion_time.isoformat()
            })
            return result

        except Exception as e:
            completion_time = datetime.now(UTC)
            duration = (completion_time - start_time).total_seconds()

            error_msg = f"Failed to process Monte Carlo job {job.metadata.job_id}: {str(e)}"
            logger.error(error_msg, extra={
                "job_id": job.metadata.job_id,
                "processor_id": self.processor_id,
                "error": str(e),
                "duration_seconds": duration,
                "failed_at": completion_time.isoformat()
            })
            logger.error(traceback.format_exc())

            if self.progress_callback:
                await self.progress_callback.report_error(job.metadata.job_id, error_msg)

            raise

    async def _execute_simulation(
        self,
        payload: MonteCarloJobPayload,
        progress_callback: Callable[[float, str], None] | None = None
    ) -> dict[str, Any]:
        """Execute the Monte Carlo simulation"""

        # Progress tracking wrapper
        def sync_progress_callback(processed: int, total: int):
            if progress_callback:
                progress = processed / payload.runs if payload.runs > 0 else 0.0
                message = f"Completed {processed}/{payload.runs} simulations"
                # Create task for async callback with correct signature
                asyncio.create_task(progress_callback(progress, message))

        # Execute simulation using existing service
        try:
            result = run_monte_carlo_on_df(
                csv_data=payload.csv_data,
                filename=payload.filename,
                strategy_name=payload.strategy_name,
                strategy_params=payload.strategy_params,
                runs=payload.runs,
                method=payload.method,
                method_params=payload.method_params or {},
                parallel_workers=payload.parallel_workers or 1,
                seed=payload.seed,
                include_equity_envelope=True,
                progress_callback=sync_progress_callback
            )

            # Convert result to dictionary format
            return {
                "filename": result.filename,
                "method": result.method,
                "runs": result.runs,
                "successful_runs": result.successful_runs,
                "metrics_distribution": {
                    metric: {
                        "mean": dist.mean,
                        "std": dist.std,
                        "p5": dist.p5,
                        "p25": dist.p25,
                        "median": dist.median,
                        "p75": dist.p75,
                        "p95": dist.p95
                    }
                    for metric, dist in result.metrics_distribution.items()
                },
                "equity_envelope": {
                    "timestamps": result.equity_envelope.timestamps,
                    "p5": result.equity_envelope.p5,
                    "p25": result.equity_envelope.p25,
                    "median": result.equity_envelope.median,
                    "p75": result.equity_envelope.p75,
                    "p95": result.equity_envelope.p95
                } if result.equity_envelope else None
            }

        except Exception as e:
            logger.error(f"Simulation failed: {str(e)}")
            raise

    async def _store_artifacts(
        self,
        job_id: str,
        result: dict[str, Any],
        payload: MonteCarloJobPayload
    ) -> dict[str, str]:
        """
        Store simulation artifacts in S3.

        Args:
            job_id: Job identifier
            result: Simulation results
            payload: Job payload

        Returns:
            Dictionary mapping artifact names to URLs
        """
        artifact_urls = {}

        try:
            # Store results as JSON
            results_json = json.dumps(result, indent=2, default=str)
            results_url = await self.storage_adapter.upload_artifact(
                job_id=job_id,
                artifact_name="results.json",
                content=results_json,
                content_type="application/json",
                metadata={
                    "strategy": payload.strategy_name,
                    "runs": str(payload.runs),
                    "method": payload.method
                }
            )
            artifact_urls["results"] = results_url

            # Store equity envelope as CSV
            if "equity_envelope" in result:
                envelope = result["equity_envelope"]
                df = pd.DataFrame({
                    "timestamp": envelope["timestamps"],
                    "p5": envelope["p5"],
                    "p25": envelope["p25"],
                    "median": envelope["median"],
                    "p75": envelope["p75"],
                    "p95": envelope["p95"]
                })

                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_content = csv_buffer.getvalue()

                envelope_url = await self.storage_adapter.upload_artifact(
                    job_id=job_id,
                    artifact_name="equity_envelope.csv",
                    content=csv_content,
                    content_type="text/csv",
                    metadata={
                        "type": "equity_envelope",
                        "rows": str(len(df))
                    }
                )
                artifact_urls["equity_envelope"] = envelope_url

            # Store metrics distribution as CSV
            if "metrics_distribution" in result:
                metrics_data = []
                for metric, dist in result["metrics_distribution"].items():
                    metrics_data.append({
                        "metric": metric,
                        "mean": dist["mean"],
                        "std": dist["std"],
                        "p5": dist["p5"],
                        "p25": dist["p25"],
                        "median": dist["median"],
                        "p75": dist["p75"],
                        "p95": dist["p95"]
                    })

                metrics_df = pd.DataFrame(metrics_data)
                csv_buffer = StringIO()
                metrics_df.to_csv(csv_buffer, index=False)
                csv_content = csv_buffer.getvalue()

                metrics_url = await self.storage_adapter.upload_artifact(
                    job_id=job_id,
                    artifact_name="metrics_distribution.csv",
                    content=csv_content,
                    content_type="text/csv",
                    metadata={
                        "type": "metrics_distribution",
                        "metrics_count": str(len(metrics_data))
                    }
                )
                artifact_urls["metrics_distribution"] = metrics_url

            logger.info(f"Stored {len(artifact_urls)} artifacts for job {job_id}")
            return artifact_urls

        except Exception as e:
            logger.error(f"Failed to store artifacts for job {job_id}: {str(e)}")
            # Don't fail the job if artifact storage fails
            return {}

    def get_processor_id(self) -> str:
        """Get processor identifier"""
        return self.processor_id

class MonteCarloWorker(WorkerInterface):
    """Worker for processing Monte Carlo simulation jobs with artifact storage"""

    def __init__(
        self,
        worker_id: str,
        queue: QueueInterface[MonteCarloJobPayload],
        processor: JobProcessorInterface[MonteCarloJobPayload, dict[str, Any]],
        progress_callback: ProgressCallbackInterface | None = None,
        max_concurrent_jobs: int = 1,
        poll_interval: float = 1.0,
        health_check_interval: float = 30.0,
        storage_adapter: S3StorageAdapter | None = None
    ):
        """
        Initialize Monte Carlo worker.

        Args:
            worker_id: Unique worker identifier
            queue: Queue interface for job management
            processor: Job processor for executing simulations
            progress_callback: Optional progress reporting callback
            max_concurrent_jobs: Maximum concurrent jobs to process
            poll_interval: Queue polling interval in seconds
            health_check_interval: Health check interval in seconds
            storage_adapter: S3 adapter for artifact storage
        """
        self.worker_id = worker_id
        self.queue = queue
        self.processor = processor
        self.progress_callback = progress_callback
        self.max_concurrent_jobs = max_concurrent_jobs
        self.poll_interval = poll_interval
        self.health_check_interval = health_check_interval
        self.storage_adapter = storage_adapter

        self._running = False
        self._shutdown_event = asyncio.Event()
        self._active_jobs: dict[str, asyncio.Task] = {}
        self._last_health_check = datetime.now(UTC)

        # Setup signal handlers
        self._setup_signal_handlers()

        logger.info(f"Initialized Monte Carlo worker: {worker_id}")

    async def start(self) -> None:
        """Start the worker process"""
        if self._running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self._running = True
        logger.info(f"Starting Monte Carlo worker: {self.worker_id}")

        try:
            # Start main processing loop
            await self._process_loop()
        except Exception as e:
            logger.error(f"Worker {self.worker_id} encountered error: {str(e)}")
            raise
        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Stop the worker process gracefully"""
        logger.info(f"Stopping Monte Carlo worker: {self.worker_id}")
        self._running = False
        self._shutdown_event.set()

        # Wait for active jobs to complete (with timeout)
        if self._active_jobs:
            logger.info(f"Waiting for {len(self._active_jobs)} active jobs to complete")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_jobs.values(), return_exceptions=True),
                    timeout=300  # 5 minutes timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for jobs to complete, cancelling remaining jobs")
                for task in self._active_jobs.values():
                    task.cancel()

    async def health_check(self) -> bool:
        """Check if worker is healthy"""
        try:
            # Update last health check time
            self._last_health_check = datetime.now(UTC)

            # Check if worker is running
            if not self._running:
                return False

            # Check queue connectivity
            await self.queue.get_metrics()

            # Check if we're not overloaded
            active_job_count = len(self._active_jobs)
            if active_job_count > self.max_concurrent_jobs * 2:  # Allow some buffer
                logger.warning(f"Worker {self.worker_id} is overloaded: {active_job_count} active jobs")
                return False

            return True

        except Exception as e:
            logger.error(f"Health check failed for worker {self.worker_id}: {str(e)}")
            return False

    def get_worker_id(self) -> str:
        """Get worker identifier"""
        return self.worker_id

    async def _process_loop(self) -> None:
        """Main processing loop"""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Clean up completed jobs
                await self._cleanup_completed_jobs()

                # Check if we can accept more jobs
                if len(self._active_jobs) >= self.max_concurrent_jobs:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Try to dequeue a job
                job = await self.queue.dequeue(timeout_seconds=int(self.poll_interval))

                if job:
                    # Process job asynchronously
                    task = asyncio.create_task(self._process_job(job))
                    self._active_jobs[job.metadata.job_id] = task
                    logger.info(f"Started processing job {job.metadata.job_id}")

                # Periodic health check
                if (datetime.now(UTC) - self._last_health_check).total_seconds() > self.health_check_interval:
                    await self.health_check()

            except Exception as e:
                logger.error(f"Error in worker processing loop: {str(e)}")
                await asyncio.sleep(self.poll_interval)

    async def _process_job(self, job: Job[MonteCarloJobPayload]) -> None:
        """Process a single job, with error handling and status updates."""
        try:
            # Mark job as processing and set start time in DB
            async with self.progress_callback._get_repo() as repo:
                try:
                    await repo.update_job_status(
                        job.metadata.job_id,
                        "processing",
                        worker_id=self.worker_id
                    )
                except Exception:
                    # Non-fatal; continue processing
                    pass

                try:
                    await repo.update_job_progress(
                        job.metadata.job_id,
                        0.0,
                        "Job started",
                        started_at=datetime.utcnow()
                    )
                except Exception:
                    # Non-fatal; continue processing
                    pass

            # Also publish initial progress message for any listeners
            await self.progress_callback.report_progress(job.metadata.job_id, 0.0, "Job started")
            result = await self.processor.process(job)
            await self.progress_callback.report_completion(job.metadata.job_id, result)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Failed to process job {job.metadata.job_id}: {error_msg}", exc_info=True)
            await self.progress_callback.report_error(job.metadata.job_id, error_msg)

    async def _should_retry_job(self, job: Job, error: Exception) -> bool:
        """Determine if a job should be retried based on its state and error type."""
        # Check if we've exceeded max retries
        max_retries = job.metadata.max_retries or 3
        if job.metadata.retry_count >= max_retries:
            return False

        # Define non-retryable error types
        non_retryable_errors = (
            ValueError,  # Invalid input data
            TypeError,   # Type errors in payload
            KeyError,    # Missing required fields
        )

        # Don't retry for validation/input errors
        if isinstance(error, non_retryable_errors):
            logger.info(f"Non-retryable error for job {job.metadata.job_id}: {type(error).__name__}")
            return False

        # Retry for transient errors (network, temporary resource issues, etc.)
        return True

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Base delay: 2^attempt seconds, capped at 300 seconds (5 minutes)
        base_delay = min(2 ** attempt, 300)

        # Add jitter (±25% of base delay) to prevent thundering herd
        jitter = random.uniform(-0.25, 0.25) * base_delay

        # Ensure minimum delay of 1 second
        delay = max(1.0, base_delay + jitter)

        return delay

    async def _cleanup_completed_jobs(self) -> None:
        """Clean up completed job tasks"""
        completed_jobs = []

        for job_id, task in self._active_jobs.items():
            if task.done():
                completed_jobs.append(job_id)

                # Log any exceptions
                try:
                    await task
                except Exception as e:
                    logger.error(f"Job {job_id} completed with exception: {str(e)}", exc_info=True)

        # Remove completed jobs
        for job_id in completed_jobs:
            self._active_jobs.pop(job_id, None)

    async def _cleanup(self) -> None:
        """Cleanup worker resources"""
        logger.info(f"Cleaning up worker {self.worker_id}")

        # Cancel any remaining active jobs
        for task in self._active_jobs.values():
            if not task.done():
                task.cancel()

        # Clear active jobs
        self._active_jobs.clear()

        logger.info(f"Worker {self.worker_id} cleanup completed")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

class WorkerProgressCallback(ProgressCallbackInterface):
    """Progress callback that updates job status in queue and database"""

    def __init__(
        self,
        queue: QueueInterface[MonteCarloJobPayload],
        worker_id: str | None = None
    ):
        self.queue = queue
        self.worker_id = worker_id or "unknown"
        self._progress_semaphore = asyncio.Semaphore(1)  # Limit concurrent progress updates

    @asynccontextmanager
    async def _get_repo(self) -> 'JobRepository':
        from infrastructure.db import SessionLocal
        from infrastructure.repositories.jobs import JobRepository
        async with SessionLocal() as session:
            try:
                yield JobRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def report_progress(self, job_id: str, progress: float, message: str | None = None, current_run: int | None = None, total_runs: int | None = None) -> None:
        """Report job progress to queue and database with proper synchronization"""
        try:
            # Use a semaphore to limit concurrent progress updates
            async with self._progress_semaphore:
                # Update progress in the database first
                async with self._get_repo() as repo:
                    success = await repo.update_job_progress(job_id, progress, message, current_run, total_runs)

                if not success:
                    logger.warning(f"Failed to update progress in database for job {job_id}")
                    return

                # Update job in queue (optional, if queue needs real-time progress)
                try:
                    job = await self.queue.get_job_status(job_id)
                    if job:
                        job.update_progress(progress)
                except Exception as queue_error:
                    logger.warning(f"Failed to update progress in queue for job {job_id}: {str(queue_error)}")

                # Publish real-time notification via enhanced Redis pub/sub with retry logic
                try:
                    from infrastructure.cache import cache_manager

                    # Only publish if Redis is connected to avoid blocking
                    if cache_manager.is_connected():
                        notification_data = {
                            "job_id": job_id,
                            "progress": progress,
                            "message": message,
                            "current_run": current_run,
                            "total_runs": total_runs,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "worker_id": self.worker_id
                        }

                        # Use enhanced pub/sub with guaranteed delivery
                        success = await cache_manager.publish(
                            f"job_progress:{job_id}",
                            notification_data,
                            ensure_delivery=True
                        )

                        if success:
                            logger.debug(f"Published progress notification for job {job_id}: {progress:.2%}")
                        else:
                            logger.warning(f"Failed to publish progress notification for job {job_id} - delivery not guaranteed")
                    else:
                        logger.debug(f"Redis not connected, skipping progress notification for job {job_id}")

                except Exception as redis_error:
                    logger.warning(f"Failed to publish progress notification for job {job_id}: {str(redis_error)}")
                    # Log pub/sub health for debugging
                    try:
                        health_status = cache_manager.get_pubsub_health()
                        logger.warning(f"Redis pub/sub health during progress notification: {health_status}")
                    except Exception:
                        pass
                    # Don't fail the entire progress update if Redis fails

        except Exception as e:
            logger.error(f"Failed to report progress for job {job_id}: {str(e)}")

    async def report_completion(self, job_id: str, success: bool, error: str | None = None, artifact_url: str | None = None) -> None:
        """Report job completion with proper synchronization"""
        try:
            async with self._progress_semaphore:
                status = "completed" if success else "failed"

                # Update job status in database
                async with self._get_repo() as repo:
                    await repo.update_job_status(
                        job_id=job_id,
                        status=status,
                        worker_id=self.worker_id,
                        error=error,
                        progress=1.0 if success else None,
                        artifact_url=artifact_url,
                        completed_at=datetime.utcnow()
                    )

                # Publish completion notification
                try:
                    from infrastructure.cache import cache_manager

                    if cache_manager.is_connected():
                        completion_data = {
                            "job_id": job_id,
                            "status": status,
                            "progress": 1.0 if success else None,
                            "error": error,
                            "artifact_url": artifact_url,
                            "completed_at": datetime.utcnow().isoformat(),
                            "worker_id": self.worker_id
                        }

                        # Use enhanced pub/sub with guaranteed delivery for completion
                        success_published = await cache_manager.publish(
                            f"job_progress:{job_id}",
                            completion_data,
                            ensure_delivery=True
                        )

                        if success_published:
                            logger.info(f"Job {job_id} completed with status: {status}")
                        else:
                            logger.warning(f"Failed to publish completion notification for job {job_id} - delivery not guaranteed")

                except Exception as redis_error:
                    logger.warning(f"Failed to publish completion notification for job {job_id}: {str(redis_error)}")
                    # Log pub/sub health and metrics for debugging
                    try:
                        health_status = cache_manager.get_pubsub_health()
                        metrics = cache_manager.get_pubsub_metrics()
                        logger.warning(f"Redis pub/sub health during completion: {health_status}")
                        logger.warning(f"Redis pub/sub metrics during completion: {metrics}")
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Failed to report completion for job {job_id}: {str(e)}")

    async def report_error(self, job_id: str, error: str) -> None:
        """Report job error with proper synchronization"""
        try:
            async with self._progress_semaphore:
                # Update job status in database
                async with self._get_repo() as repo:
                    await repo.update_job_status(
                        job_id=job_id,
                        status="failed",
                        worker_id=self.worker_id,
                        error=error,
                        completed_at=datetime.utcnow()
                    )

                # Publish error notification
                try:
                    from infrastructure.cache import cache_manager

                    if cache_manager.is_connected():
                        error_data = {
                            "job_id": job_id,
                            "status": "failed",
                            "error": error,
                            "completed_at": datetime.utcnow().isoformat(),
                            "worker_id": self.worker_id
                        }

                        # Use enhanced pub/sub with guaranteed delivery for error notifications
                        success = await cache_manager.publish(
                            f"job_progress:{job_id}",
                            error_data,
                            ensure_delivery=True
                        )

                        if success:
                            logger.error(f"Job {job_id} failed with error: {error}")
                        else:
                            logger.warning(f"Failed to publish error notification for job {job_id} - delivery not guaranteed")
                            logger.error(f"Job {job_id} failed with error: {error}")

                except Exception as redis_error:
                    logger.warning(f"Failed to publish error notification for job {job_id}: {str(redis_error)}")
                    # Log pub/sub health and metrics for debugging
                    try:
                        health_status = cache_manager.get_pubsub_health()
                        metrics = cache_manager.get_pubsub_metrics()
                        logger.warning(f"Redis pub/sub health during error notification: {health_status}")
                        logger.warning(f"Redis pub/sub metrics during error notification: {metrics}")
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Failed to report error for job {job_id}: {str(e)}")
