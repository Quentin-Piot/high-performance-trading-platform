"""Monte Carlo simulation worker with retry logic and artifact storage.

This module implements the worker that processes Monte Carlo simulation jobs,
including exponential backoff retry logic, progress tracking, and S3 artifact storage.
"""
import asyncio
import json
import logging
import signal
import sys
import random
import math
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List, Callable
import traceback
from contextlib import asynccontextmanager
import numpy as np
import pandas as pd
from io import StringIO

from domain.queue import (
    WorkerInterface, JobProcessorInterface, ProgressCallbackInterface,
    Job, JobStatus, MonteCarloJobPayload, QueueInterface
)
from services.mc_backtest_service import run_monte_carlo_on_df
from core.logging import setup_logging
from infrastructure.repositories.jobs import JobRepository
from infrastructure.storage.s3_adapter import S3StorageAdapter

logger = logging.getLogger(__name__)


class MonteCarloJobProcessor(JobProcessorInterface[MonteCarloJobPayload, Dict[str, Any]]):
    """Processor for Monte Carlo simulation jobs with artifact storage"""
    
    def __init__(
        self,
        processor_id: str,
        progress_callback: Optional[ProgressCallbackInterface] = None,
        storage_adapter: Optional[S3StorageAdapter] = None
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
    
    async def process(self, job: Job[MonteCarloJobPayload]) -> Dict[str, Any]:
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
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Execute the Monte Carlo simulation"""
        
        # Progress tracking wrapper
        def sync_progress_callback(processed: int, total: int):
            if progress_callback:
                progress = processed / total if total > 0 else 0.0
                message = f"Completed {processed}/{total} simulations"
                # Create task for async callback
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
                        "min": dist.min,
                        "max": dist.max,
                        "percentiles": dist.percentiles
                    }
                    for metric, dist in result.metrics_distribution.items()
                },
                "equity_envelope": {
                    "timestamps": result.equity_envelope.timestamps,
                    "upper_bound": result.equity_envelope.upper_bound,
                    "lower_bound": result.equity_envelope.lower_bound,
                    "median": result.equity_envelope.median
                } if result.equity_envelope else None
            }
            
        except Exception as e:
            logger.error(f"Simulation failed: {str(e)}")
            raise
    
    async def _store_artifacts(
        self,
        job_id: str,
        result: Dict[str, Any],
        payload: MonteCarloJobPayload
    ) -> Dict[str, str]:
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
                    "upper_bound": envelope["upper_bound"],
                    "lower_bound": envelope["lower_bound"],
                    "median": envelope["median"]
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
                        "min": dist["min"],
                        "max": dist["max"],
                        **{f"p{p}": v for p, v in dist["percentiles"].items()}
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
        processor: JobProcessorInterface[MonteCarloJobPayload, Dict[str, Any]],
        progress_callback: Optional[ProgressCallbackInterface] = None,
        max_concurrent_jobs: int = 1,
        poll_interval: float = 1.0,
        health_check_interval: float = 30.0,
        storage_adapter: Optional[S3StorageAdapter] = None
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
        self._active_jobs: Dict[str, asyncio.Task] = {}
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
        """Process a single job with exponential backoff retry logic"""
        job_id = job.metadata.job_id
        
        try:
            logger.info(f"Processing job {job_id}")
            
            # Process the job
            result = await self.processor.process(job)
            
            # Update job with result
            job.result = result
            job.update_status(JobStatus.COMPLETED)
            job.progress = 1.0
            
            # Acknowledge successful completion
            await self.queue.acknowledge(job_id)
            
            logger.info(f"Successfully completed job {job_id}")
            
        except Exception as e:
            error_msg = f"Failed to process job {job_id}: {str(e)}"
            logger.error(error_msg)
            
            # Update job with error
            job.update_status(JobStatus.FAILED, error_msg)
            
            # Determine if we should retry based on error type and attempt count
            should_retry = self._should_retry_job(job, e)
            
            if should_retry:
                # Calculate exponential backoff delay
                delay = self._calculate_retry_delay(job.metadata.retry_count)
                
                logger.info(f"Retrying job {job_id} after {delay:.2f}s delay (attempt {job.metadata.retry_count + 1})")
                
                # Wait for backoff delay before rejecting (which will requeue)
                await asyncio.sleep(delay)
                
                # Reject job with requeue=True to trigger retry
                await self.queue.reject(job_id, requeue=True)
            else:
                logger.warning(f"Job {job_id} will not be retried: max attempts reached or non-retryable error")
                
                # Reject job without requeue (will go to DLQ if configured)
                await self.queue.reject(job_id, requeue=False)
            
        finally:
            # Remove from active jobs
            self._active_jobs.pop(job_id, None)
    
    def _should_retry_job(self, job: Job[MonteCarloJobPayload], error: Exception) -> bool:
        """
        Determine if a job should be retried based on error type and attempt count.
        
        Args:
            job: The failed job
            error: The exception that caused the failure
            
        Returns:
            True if the job should be retried, False otherwise
        """
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
                    logger.error(f"Job {job_id} completed with exception: {str(e)}")
        
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
        job_repository: Optional['JobRepository'] = None
    ):
        self.queue = queue
        self.job_repository = job_repository
        
        # Import here to avoid circular imports
        if not job_repository:
            from infrastructure.db import SessionLocal
            from infrastructure.repositories.jobs import JobRepository
            session = SessionLocal()
            self.job_repository = JobRepository(session)
    
    async def report_progress(self, job_id: str, progress: float, message: Optional[str] = None) -> None:
        """Report job progress to queue and database"""
        try:
            # Update job in queue
            job = await self.queue.get_job_status(job_id)
            if job:
                job.update_progress(progress)
            
            # Update progress in database
            if self.job_repository:
                await self.job_repository.update_job_progress(job_id, progress, message)
                
        except Exception as e:
            logger.error(f"Failed to report progress for job {job_id}: {str(e)}")
    
    async def report_completion(self, job_id: str, result: Any) -> None:
        """Report job completion"""
        try:
            # Update job in queue
            job = await self.queue.get_job_status(job_id)
            if job:
                job.update_status(JobStatus.COMPLETED)
                job.update_progress(1.0)
            
            # Update status in database
            if self.job_repository:
                await self.job_repository.update_job_status(
                    job_id, 
                    "completed", 
                    progress=1.0
                )
                
        except Exception as e:
            logger.error(f"Failed to report completion for job {job_id}: {str(e)}")
    
    async def report_error(self, job_id: str, error: str) -> None:
        """Report job error"""
        try:
            # Update job in queue
            job = await self.queue.get_job_status(job_id)
            if job:
                job.update_status(JobStatus.FAILED)
            
            # Update status in database
            if self.job_repository:
                await self.job_repository.update_job_status(
                    job_id, 
                    "failed", 
                    error=error
                )
                
        except Exception as e:
            logger.error(f"Failed to report error for job {job_id}: {str(e)}")


async def main():
    """Main entry point for running a Monte Carlo worker"""
    import os
    from infrastructure.queue import SQSQueueAdapter
    
    # Setup logging
    setup_logging()
    
    # Configuration from environment
    worker_id = os.getenv("WORKER_ID", f"mc-worker-{os.getpid()}")
    queue_url = os.getenv("SQS_QUEUE_URL")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
    
    if not queue_url:
        logger.error("SQS_QUEUE_URL environment variable is required")
        sys.exit(1)
    
    try:
        # Initialize components
        queue = SQSQueueAdapter(queue_url=queue_url, region_name=aws_region)
        progress_callback = WorkerProgressCallback(queue)
        processor = MonteCarloJobProcessor(
            processor_id=f"{worker_id}-processor",
            progress_callback=progress_callback
        )
        
        # Create and start worker
        worker = MonteCarloWorker(
            worker_id=worker_id,
            queue=queue,
            processor=processor,
            progress_callback=progress_callback,
            max_concurrent_jobs=max_concurrent_jobs
        )
        
        logger.info(f"Starting Monte Carlo worker: {worker_id}")
        await worker.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Worker failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())