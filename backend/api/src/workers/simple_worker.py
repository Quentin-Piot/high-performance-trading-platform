"""
Simple Monte Carlo worker that runs alongside the main backend without Redis/queue dependencies.

This worker provides asynchronous Monte Carlo execution capabilities while running
in the same process as the main backend, without requiring external queue systems.
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

from services.mc_backtest_service import run_monte_carlo_on_df

logger = logging.getLogger(__name__)


class SimpleMonteCarloJob:
    """Simple job representation for the sideloaded worker."""

    def __init__(
        self,
        job_id: str,
        csv_data: bytes,
        filename: str,
        strategy_name: str,
        strategy_params: dict,
        runs: int,
        method: str = "bootstrap",
        method_params: dict | None = None,
        callback: Callable[[str, dict], None] | None = None,
    ):
        self.job_id = job_id
        self.csv_data = csv_data
        self.filename = filename
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params
        self.runs = runs
        self.method = method
        self.method_params = method_params or {}
        self.callback = callback
        self.status = "pending"
        self.progress = 0.0
        self.result = None
        self.error = None
        self.created_at = datetime.now(UTC)
        self.started_at = None
        self.completed_at = None


class SimpleMonteCarloWorker:
    """Simple Monte Carlo worker that runs in the same process without external dependencies."""

    def __init__(self, max_concurrent_jobs: int = 2):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.jobs: dict[str, SimpleMonteCarloJob] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        self._lock = threading.Lock()

    def submit_job(
        self,
        csv_data: bytes,
        filename: str,
        strategy_name: str,
        strategy_params: dict,
        runs: int,
        method: str = "bootstrap",
        method_params: dict | None = None,
        callback: Callable[[str, dict], None] | None = None,
    ) -> str:
        """Submit a new Monte Carlo job for asynchronous execution."""
        job_id = str(uuid4())

        job = SimpleMonteCarloJob(
            job_id=job_id,
            csv_data=csv_data,
            filename=filename,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            runs=runs,
            method=method,
            method_params=method_params,
            callback=callback,
        )

        with self._lock:
            self.jobs[job_id] = job

        # Submit job to thread pool
        self.executor.submit(self._execute_job, job)

        logger.info(f"Submitted Monte Carlo job {job_id} with {runs} runs")
        return job_id

    def get_job_status(self, job_id: str) -> dict | None:
        """Get the status of a job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return None

            return {
                "job_id": job_id,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
                "result": job.result,
                "error": job.error,
                "runs": job.runs,
                "filename": job.filename,
            }

    def list_jobs(self, limit: int = 50) -> list[dict]:
        """List all jobs with their status."""
        with self._lock:
            jobs = list(self.jobs.values())

        # Sort by creation time, most recent first
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return [
            {
                "job_id": job.job_id,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
                "runs": job.runs,
                "filename": job.filename,
                "error": job.error,
            }
            for job in jobs[:limit]
        ]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job (limited capability - can only mark as cancelled)."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job.status in ["completed", "failed", "cancelled"]:
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now(UTC)
            return True

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs."""
        cutoff_time = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
        removed_count = 0

        with self._lock:
            job_ids_to_remove = []
            for job_id, job in self.jobs.items():
                if (
                    job.status in ["completed", "failed", "cancelled"]
                    and job.completed_at
                    and job.completed_at.timestamp() < cutoff_time
                ):
                    job_ids_to_remove.append(job_id)

            for job_id in job_ids_to_remove:
                del self.jobs[job_id]
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old jobs")

        return removed_count

    def get_stats(self) -> dict:
        """Get worker statistics."""
        with self._lock:
            jobs = list(self.jobs.values())

        stats = {
            "total_jobs": len(jobs),
            "pending": sum(1 for j in jobs if j.status == "pending"),
            "running": sum(1 for j in jobs if j.status == "running"),
            "completed": sum(1 for j in jobs if j.status == "completed"),
            "failed": sum(1 for j in jobs if j.status == "failed"),
            "cancelled": sum(1 for j in jobs if j.status == "cancelled"),
            "max_concurrent_jobs": self.max_concurrent_jobs,
        }

        return stats

    def _execute_job(self, job: SimpleMonteCarloJob) -> None:
        """Execute a Monte Carlo job in a thread."""
        try:
            # Update job status
            with self._lock:
                job.status = "running"
                job.started_at = datetime.now(UTC)

            logger.info(f"Starting execution of job {job.job_id}")

            # Progress callback
            def progress_callback(processed: int, total: int):
                progress = processed / total if total > 0 else 0.0
                with self._lock:
                    job.progress = progress
                logger.debug(f"Job {job.job_id} progress: {progress:.1%}")

            # Execute Monte Carlo simulation
            result = run_monte_carlo_on_df(
                csv_data=job.csv_data,
                filename=job.filename,
                strategy_name=job.strategy_name,
                strategy_params=job.strategy_params,
                runs=job.runs,
                method=job.method,
                method_params=job.method_params,
                parallel_workers=1,  # Single worker to avoid conflicts
                seed=None,
                include_equity_envelope=True,
                progress_callback=progress_callback,
            )

            # Convert result to dictionary
            result_dict = {
                "filename": result.filename,
                "method": result.method,
                "runs": result.runs,
                "successful_runs": result.successful_runs,
                "metrics_distribution": {
                    "pnl": {
                        "mean": result.metrics_distribution["pnl"].mean,
                        "std": result.metrics_distribution["pnl"].std,
                        "p5": result.metrics_distribution["pnl"].p5,
                        "p25": result.metrics_distribution["pnl"].p25,
                        "median": result.metrics_distribution["pnl"].median,
                        "p75": result.metrics_distribution["pnl"].p75,
                        "p95": result.metrics_distribution["pnl"].p95,
                    },
                    "sharpe": {
                        "mean": result.metrics_distribution["sharpe"].mean,
                        "std": result.metrics_distribution["sharpe"].std,
                        "p5": result.metrics_distribution["sharpe"].p5,
                        "p25": result.metrics_distribution["sharpe"].p25,
                        "median": result.metrics_distribution["sharpe"].median,
                        "p75": result.metrics_distribution["sharpe"].p75,
                        "p95": result.metrics_distribution["sharpe"].p95,
                    },
                    "drawdown": {
                        "mean": result.metrics_distribution["drawdown"].mean,
                        "std": result.metrics_distribution["drawdown"].std,
                        "p5": result.metrics_distribution["drawdown"].p5,
                        "p25": result.metrics_distribution["drawdown"].p25,
                        "median": result.metrics_distribution["drawdown"].median,
                        "p75": result.metrics_distribution["drawdown"].p75,
                        "p95": result.metrics_distribution["drawdown"].p95,
                    },
                },
            }

            # Include equity envelope if available
            if result.equity_envelope:
                result_dict["equity_envelope"] = {
                    "timestamps": result.equity_envelope.timestamps,
                    "p5": result.equity_envelope.p5,
                    "p25": result.equity_envelope.p25,
                    "median": result.equity_envelope.median,
                    "p75": result.equity_envelope.p75,
                    "p95": result.equity_envelope.p95,
                }

            # Update job with results
            with self._lock:
                job.status = "completed"
                job.progress = 1.0
                job.result = result_dict
                job.completed_at = datetime.now(UTC)

            logger.info(
                f"Job {job.job_id} completed successfully: {result.successful_runs}/{result.runs} runs"
            )

            # Call callback if provided
            if job.callback:
                try:
                    job.callback(job.job_id, result_dict)
                except Exception as callback_error:
                    logger.warning(
                        f"Callback failed for job {job.job_id}: {callback_error}"
                    )

        except Exception as e:
            error_msg = f"Job execution failed: {str(e)}"
            logger.error(f"Job {job.job_id} failed: {error_msg}")
            print(f"DEBUG: Worker job {job.job_id} exception: {str(e)}")  # Debug print
            import traceback

            print(
                f"DEBUG: Worker job {job.job_id} traceback: {traceback.format_exc()}"
            )  # Debug traceback

            # Update job with error
            with self._lock:
                job.status = "failed"
                job.error = error_msg
                job.completed_at = datetime.now(UTC)

            # Call callback with error if provided
            if job.callback:
                try:
                    job.callback(job.job_id, {"error": error_msg})
                except Exception as callback_error:
                    logger.warning(
                        f"Error callback failed for job {job.job_id}: {callback_error}"
                    )

    def shutdown(self):
        """Shutdown the worker and cleanup resources."""
        logger.info("Shutting down simple Monte Carlo worker")
        self.running = False
        self.executor.shutdown(wait=True)


# Global worker instance
_worker_instance: SimpleMonteCarloWorker | None = None


def get_simple_worker() -> SimpleMonteCarloWorker:
    """Get the global simple worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = SimpleMonteCarloWorker(max_concurrent_jobs=2)
        logger.info("Initialized simple Monte Carlo worker")
    return _worker_instance


def start_cleanup_task():
    """Start a background task to periodically cleanup old jobs."""

    def cleanup_loop():
        while True:
            try:
                worker = get_simple_worker()
                worker.cleanup_old_jobs(max_age_hours=24)
                time.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    cleanup_thread = threading.Thread(
        target=cleanup_loop, daemon=True, name="SimpleWorkerCleanup"
    )
    cleanup_thread.start()
    logger.info("Started simple worker cleanup task")
