"""
Monte Carlo worker implementation for processing simulation jobs.

This module provides a worker that processes Monte Carlo simulation jobs
from the queue system, with support for progress reporting and error handling.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import traceback
from contextlib import asynccontextmanager

from src.domain.queue import (
    WorkerInterface, JobProcessorInterface, ProgressCallbackInterface,
    Job, JobStatus, MonteCarloJobPayload, QueueInterface
)
from src.services.mc_backtest_service import run_monte_carlo_on_df
from src.core.logging import setup_logging

logger = logging.getLogger(__name__)


class MonteCarloJobProcessor(JobProcessorInterface[MonteCarloJobPayload, Dict[str, Any]]):
    """Processor for Monte Carlo simulation jobs"""
    
    def __init__(
        self,
        processor_id: str,
        progress_callback: Optional[ProgressCallbackInterface] = None
    ):
        """
        Initialize Monte Carlo job processor.
        
        Args:
            processor_id: Unique processor identifier
            progress_callback: Optional progress reporting callback
        """
        self.processor_id = processor_id
        self.progress_callback = progress_callback
        
        logger.info(f"Initialized Monte Carlo processor: {processor_id}")
    
    async def process(self, job: Job[MonteCarloJobPayload]) -> Dict[str, Any]:
        """
        Process a Monte Carlo simulation job.
        
        Args:
            job: Monte Carlo job to process
            
        Returns:
            Simulation results
            
        Raises:
            Exception: If processing fails
        """
        try:
            payload = job.payload
            job_id = job.metadata.job_id
            
            logger.info(f"Processing Monte Carlo job {job_id} with {payload.runs} runs")
            
            # Report initial progress
            if self.progress_callback:
                await self.progress_callback.report_progress(job_id, 0.0, "Starting simulation")
            
            # Create progress callback for the service
            async def service_progress_callback(progress: float, message: str = ""):
                if self.progress_callback:
                    await self.progress_callback.report_progress(job_id, progress, message)
            
            # Execute Monte Carlo simulation
            result = await self._execute_simulation(payload, service_progress_callback)
            
            # Report completion
            if self.progress_callback:
                await self.progress_callback.report_completion(job_id, result)
            
            logger.info(f"Completed Monte Carlo job {job_id}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to process Monte Carlo job {job.metadata.job_id}: {str(e)}"
            logger.error(error_msg)
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
    
    def get_processor_id(self) -> str:
        """Get processor identifier"""
        return self.processor_id


class MonteCarloWorker(WorkerInterface):
    """Worker for processing Monte Carlo simulation jobs"""
    
    def __init__(
        self,
        worker_id: str,
        queue: QueueInterface[MonteCarloJobPayload],
        processor: JobProcessorInterface[MonteCarloJobPayload, Dict[str, Any]],
        progress_callback: Optional[ProgressCallbackInterface] = None,
        max_concurrent_jobs: int = 1,
        poll_interval: float = 1.0,
        health_check_interval: float = 30.0
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
        """
        self.worker_id = worker_id
        self.queue = queue
        self.processor = processor
        self.progress_callback = progress_callback
        self.max_concurrent_jobs = max_concurrent_jobs
        self.poll_interval = poll_interval
        self.health_check_interval = health_check_interval
        
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
        """Process a single job"""
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
            
            # Reject job (may trigger retry)
            await self.queue.reject(job_id, requeue=True)
            
        finally:
            # Remove from active jobs
            self._active_jobs.pop(job_id, None)
    
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
    """Progress callback implementation for workers"""
    
    def __init__(self, queue: QueueInterface[MonteCarloJobPayload]):
        """
        Initialize progress callback.
        
        Args:
            queue: Queue interface for updating job status
        """
        self.queue = queue
    
    async def report_progress(self, job_id: str, progress: float, message: Optional[str] = None) -> None:
        """Report job progress"""
        try:
            job = await self.queue.get_job_status(job_id)
            if job:
                job.progress = progress
                if message:
                    job.metadata.tags["progress_message"] = message
                logger.debug(f"Job {job_id} progress: {progress:.1%} - {message or ''}")
        except Exception as e:
            logger.error(f"Failed to report progress for job {job_id}: {str(e)}")
    
    async def report_completion(self, job_id: str, result: Any) -> None:
        """Report job completion"""
        try:
            job = await self.queue.get_job_status(job_id)
            if job:
                job.result = result
                job.progress = 1.0
                job.update_status(JobStatus.COMPLETED)
                logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Failed to report completion for job {job_id}: {str(e)}")
    
    async def report_error(self, job_id: str, error: str) -> None:
        """Report job error"""
        try:
            job = await self.queue.get_job_status(job_id)
            if job:
                job.update_status(JobStatus.FAILED, error)
                logger.error(f"Job {job_id} failed: {error}")
        except Exception as e:
            logger.error(f"Failed to report error for job {job_id}: {str(e)}")


async def main():
    """Main entry point for running a Monte Carlo worker"""
    import os
    from src.infrastructure.queue import SQSQueueAdapter
    
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