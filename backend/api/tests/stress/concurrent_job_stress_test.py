"""
Concurrent Job Stress Testing Tool

This module provides stress testing capabilities for concurrent job submission,
processing, and queue management scenarios.
"""

import argparse
import asyncio
import logging
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class JobSubmissionMetrics:
    """Metrics for job submission operations."""
    job_id: str | None = None
    submission_time: float = 0.0
    response_time: float = 0.0
    status_code: int = 0
    success: bool = False
    error_message: str | None = None
    job_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobProcessingMetrics:
    """Metrics for job processing and progress tracking."""
    job_id: str
    submission_time: float = 0.0
    start_processing_time: float | None = None
    completion_time: float | None = None
    final_status: str | None = None
    progress_updates: list[tuple[float, float]] = field(default_factory=list)  # (timestamp, progress)
    total_processing_time: float | None = None
    success: bool = False
    error_message: str | None = None


@dataclass
class ConcurrentStressTestResults:
    """Results from concurrent stress testing."""
    total_jobs_submitted: int
    successful_submissions: int
    failed_submissions: int
    total_jobs_completed: int
    successful_completions: int
    failed_completions: int
    test_duration: float
    submission_throughput: float  # jobs/second
    completion_throughput: float  # jobs/second
    average_submission_time: float
    average_processing_time: float
    median_processing_time: float
    p95_processing_time: float
    p99_processing_time: float
    queue_depth_samples: list[tuple[float, int]] = field(default_factory=list)  # (timestamp, depth)
    error_details: dict[str, int] = field(default_factory=dict)


class ConcurrentJobStressTester:
    """Comprehensive concurrent job stress testing tool."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def generate_test_job_data(self, job_index: int) -> dict[str, Any]:
        """Generate test job data with some randomization."""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX"]
        priorities = ["low", "normal", "high"]

        # Add some randomization to avoid identical jobs
        base_date = datetime(2023, 1, 1)
        start_offset = random.randint(0, 300)  # 0-300 days
        duration = random.randint(30, 365)  # 30-365 days

        start_date = base_date + timedelta(days=start_offset)
        end_date = start_date + timedelta(days=duration)

        return {
            "symbol": random.choice(symbols),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "num_runs": random.randint(100, 2000),
            "initial_capital": random.uniform(1000, 100000),
            "strategy_params": {
                "risk_tolerance": random.uniform(0.1, 0.9),
                "rebalance_frequency": random.choice(["daily", "weekly", "monthly"]),
                "test_param": f"job_{job_index}"
            },
            "priority": random.choice(priorities),
            "timeout_seconds": random.randint(300, 3600)
        }

    async def submit_single_job(self, job_index: int) -> JobSubmissionMetrics:
        """Submit a single job and measure metrics."""
        metrics = JobSubmissionMetrics()

        try:
            job_data = self.generate_test_job_data(job_index)
            metrics.job_data = job_data

            start_time = time.time()

            async with self.session.post(
                f"{self.base_url}/api/v1/monte-carlo/jobs",
                json=job_data
            ) as response:
                metrics.response_time = time.time() - start_time
                metrics.status_code = response.status

                if response.status == 200:
                    result = await response.json()
                    metrics.job_id = result.get("job_id")
                    metrics.success = True
                else:
                    error_text = await response.text()
                    metrics.error_message = f"HTTP {response.status}: {error_text}"

        except Exception as e:
            metrics.error_message = str(e)
            metrics.response_time = time.time() - start_time if 'start_time' in locals() else 0.0

        finally:
            metrics.submission_time = time.time()

        return metrics

    async def track_job_progress(self, job_id: str, timeout_seconds: int = 300) -> JobProcessingMetrics:
        """Track a job's progress until completion."""
        metrics = JobProcessingMetrics(job_id=job_id)
        metrics.submission_time = time.time()

        start_time = time.time()
        last_status = None

        try:
            while (time.time() - start_time) < timeout_seconds:
                try:
                    async with self.session.get(
                        f"{self.base_url}/api/v1/monte-carlo/jobs/{job_id}"
                    ) as response:
                        if response.status == 200:
                            job_data = await response.json()
                            current_status = job_data.get("status")
                            progress = job_data.get("progress", 0.0)

                            # Record progress update
                            metrics.progress_updates.append((time.time(), progress))

                            # Check if job started processing
                            if current_status in ["processing", "completed", "failed"] and metrics.start_processing_time is None:
                                metrics.start_processing_time = time.time()

                            # Check if job completed
                            if current_status in ["completed", "failed"]:
                                metrics.completion_time = time.time()
                                metrics.final_status = current_status
                                metrics.success = (current_status == "completed")

                                if metrics.start_processing_time:
                                    metrics.total_processing_time = metrics.completion_time - metrics.start_processing_time

                                break

                            last_status = current_status

                        else:
                            logger.warning(f"Failed to get job {job_id} status: {response.status}")

                except Exception as e:
                    logger.warning(f"Error checking job {job_id} progress: {str(e)}")

                # Wait before next check
                await asyncio.sleep(1.0)

            # Handle timeout
            if metrics.completion_time is None:
                metrics.error_message = f"Job tracking timeout after {timeout_seconds}s (last status: {last_status})"

        except Exception as e:
            metrics.error_message = str(e)

        return metrics

    async def get_queue_metrics(self) -> dict[str, Any]:
        """Get current queue metrics."""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/monte-carlo/queue/metrics") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def concurrent_submission_test(
        self,
        num_jobs: int,
        batch_size: int = 10,
        batch_delay: float = 0.1
    ) -> tuple[list[JobSubmissionMetrics], float]:
        """Test concurrent job submission with batching."""
        logger.info(f"Starting concurrent submission test: {num_jobs} jobs in batches of {batch_size}")

        start_time = time.time()
        all_metrics = []

        # Submit jobs in batches
        for batch_start in range(0, num_jobs, batch_size):
            batch_end = min(batch_start + batch_size, num_jobs)
            batch_jobs = range(batch_start, batch_end)

            # Submit batch concurrently
            batch_tasks = [
                asyncio.create_task(self.submit_single_job(job_index))
                for job_index in batch_jobs
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results
            for _i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    error_metrics = JobSubmissionMetrics()
                    error_metrics.error_message = str(result)
                    all_metrics.append(error_metrics)
                else:
                    all_metrics.append(result)

            logger.info(f"Completed batch {batch_start//batch_size + 1}/{(num_jobs-1)//batch_size + 1}")

            # Delay between batches
            if batch_end < num_jobs:
                await asyncio.sleep(batch_delay)

        total_time = time.time() - start_time
        logger.info(f"All {num_jobs} job submissions completed in {total_time:.2f}s")

        return all_metrics, total_time

    async def end_to_end_processing_test(
        self,
        num_jobs: int,
        submission_batch_size: int = 5,
        tracking_timeout: int = 600
    ) -> ConcurrentStressTestResults:
        """Test end-to-end job processing including submission and completion tracking."""
        logger.info(f"Starting end-to-end processing test: {num_jobs} jobs")

        test_start_time = time.time()

        # Phase 1: Submit all jobs
        submission_metrics, submission_duration = await self.concurrent_submission_test(
            num_jobs=num_jobs,
            batch_size=submission_batch_size
        )

        # Extract successful job IDs
        successful_jobs = [m for m in submission_metrics if m.success and m.job_id]
        job_ids = [m.job_id for m in successful_jobs]

        logger.info(f"Successfully submitted {len(job_ids)} out of {num_jobs} jobs")

        if not job_ids:
            logger.error("No jobs were successfully submitted")
            return self._create_empty_results()

        # Phase 2: Track job processing with queue monitoring
        queue_monitoring_task = asyncio.create_task(
            self._monitor_queue_depth(duration_seconds=tracking_timeout)
        )

        # Track all jobs concurrently
        tracking_tasks = [
            asyncio.create_task(self.track_job_progress(job_id, tracking_timeout))
            for job_id in job_ids
        ]

        logger.info(f"Tracking {len(job_ids)} jobs for up to {tracking_timeout}s...")
        processing_results = await asyncio.gather(*tracking_tasks, return_exceptions=True)

        # Stop queue monitoring
        queue_monitoring_task.cancel()
        try:
            queue_samples = await queue_monitoring_task
        except asyncio.CancelledError:
            queue_samples = []

        # Process tracking results
        processing_metrics = []
        for i, result in enumerate(processing_results):
            if isinstance(result, Exception):
                error_metrics = JobProcessingMetrics(job_id=job_ids[i])
                error_metrics.error_message = str(result)
                processing_metrics.append(error_metrics)
            else:
                processing_metrics.append(result)

        total_test_time = time.time() - test_start_time

        return self._calculate_concurrent_results(
            submission_metrics, processing_metrics, total_test_time, queue_samples
        )

    async def _monitor_queue_depth(self, duration_seconds: int) -> list[tuple[float, int]]:
        """Monitor queue depth over time."""
        samples = []
        start_time = time.time()

        while (time.time() - start_time) < duration_seconds:
            try:
                metrics = await self.get_queue_metrics()
                if "queue_depth" in metrics:
                    samples.append((time.time(), metrics["queue_depth"]))
                elif "error" not in metrics:
                    # Try to extract queue depth from other fields
                    pending = metrics.get("pending_jobs", 0)
                    running = metrics.get("processing_jobs", 0)
                    queue_depth = pending + running
                    samples.append((time.time(), queue_depth))

            except Exception as e:
                logger.warning(f"Error monitoring queue depth: {str(e)}")

            await asyncio.sleep(2.0)  # Sample every 2 seconds

        return samples

    def _calculate_concurrent_results(
        self,
        submission_metrics: list[JobSubmissionMetrics],
        processing_metrics: list[JobProcessingMetrics],
        total_duration: float,
        queue_samples: list[tuple[float, int]]
    ) -> ConcurrentStressTestResults:
        """Calculate comprehensive concurrent stress test results."""

        # Submission statistics
        successful_submissions = sum(1 for m in submission_metrics if m.success)
        failed_submissions = len(submission_metrics) - successful_submissions

        submission_times = [m.response_time for m in submission_metrics if m.response_time > 0]
        avg_submission_time = statistics.mean(submission_times) if submission_times else 0.0

        # Processing statistics
        completed_jobs = [m for m in processing_metrics if m.completion_time is not None]
        successful_completions = sum(1 for m in completed_jobs if m.success)
        failed_completions = len(completed_jobs) - successful_completions

        processing_times = [m.total_processing_time for m in completed_jobs if m.total_processing_time is not None]

        if processing_times:
            avg_processing_time = statistics.mean(processing_times)
            median_processing_time = statistics.median(processing_times)
            p95_processing_time = statistics.quantiles(processing_times, n=20)[18]
            p99_processing_time = statistics.quantiles(processing_times, n=100)[98]
        else:
            avg_processing_time = median_processing_time = p95_processing_time = p99_processing_time = 0.0

        # Throughput calculations
        submission_throughput = successful_submissions / total_duration if total_duration > 0 else 0.0
        completion_throughput = successful_completions / total_duration if total_duration > 0 else 0.0

        # Error collection
        error_details = {}
        for metrics in submission_metrics + processing_metrics:
            if hasattr(metrics, 'error_message') and metrics.error_message:
                error_type = metrics.error_message.split(':')[0] if ':' in metrics.error_message else metrics.error_message
                error_details[error_type] = error_details.get(error_type, 0) + 1

        return ConcurrentStressTestResults(
            total_jobs_submitted=len(submission_metrics),
            successful_submissions=successful_submissions,
            failed_submissions=failed_submissions,
            total_jobs_completed=len(completed_jobs),
            successful_completions=successful_completions,
            failed_completions=failed_completions,
            test_duration=total_duration,
            submission_throughput=submission_throughput,
            completion_throughput=completion_throughput,
            average_submission_time=avg_submission_time,
            average_processing_time=avg_processing_time,
            median_processing_time=median_processing_time,
            p95_processing_time=p95_processing_time,
            p99_processing_time=p99_processing_time,
            queue_depth_samples=queue_samples,
            error_details=error_details
        )

    def _create_empty_results(self) -> ConcurrentStressTestResults:
        """Create empty results for failed tests."""
        return ConcurrentStressTestResults(
            total_jobs_submitted=0,
            successful_submissions=0,
            failed_submissions=0,
            total_jobs_completed=0,
            successful_completions=0,
            failed_completions=0,
            test_duration=0.0,
            submission_throughput=0.0,
            completion_throughput=0.0,
            average_submission_time=0.0,
            average_processing_time=0.0,
            median_processing_time=0.0,
            p95_processing_time=0.0,
            p99_processing_time=0.0
        )

    def print_results(self, results: ConcurrentStressTestResults, test_name: str = "Concurrent Job Stress Test"):
        """Print formatted concurrent stress test results."""
        print(f"\n{'='*70}")
        print(f"{test_name} Results")
        print(f"{'='*70}")

        print("Job Submission:")
        print(f"  Total Jobs Submitted: {results.total_jobs_submitted}")
        print(f"  Successful Submissions: {results.successful_submissions}")
        print(f"  Failed Submissions: {results.failed_submissions}")
        print(f"  Submission Success Rate: {results.successful_submissions/results.total_jobs_submitted:.2%}" if results.total_jobs_submitted > 0 else "  Submission Success Rate: 0%")
        print(f"  Average Submission Time: {results.average_submission_time*1000:.2f}ms")
        print(f"  Submission Throughput: {results.submission_throughput:.2f} jobs/s")

        print("\nJob Processing:")
        print(f"  Total Jobs Completed: {results.total_jobs_completed}")
        print(f"  Successful Completions: {results.successful_completions}")
        print(f"  Failed Completions: {results.failed_completions}")
        print(f"  Completion Success Rate: {results.successful_completions/results.total_jobs_completed:.2%}" if results.total_jobs_completed > 0 else "  Completion Success Rate: 0%")
        print(f"  Completion Throughput: {results.completion_throughput:.2f} jobs/s")

        print("\nProcessing Time Statistics:")
        print(f"  Average: {results.average_processing_time:.2f}s")
        print(f"  Median: {results.median_processing_time:.2f}s")
        print(f"  95th Percentile: {results.p95_processing_time:.2f}s")
        print(f"  99th Percentile: {results.p99_processing_time:.2f}s")

        print(f"\nTest Duration: {results.test_duration:.2f}s")

        if results.queue_depth_samples:
            queue_depths = [depth for _, depth in results.queue_depth_samples]
            max_queue_depth = max(queue_depths)
            avg_queue_depth = statistics.mean(queue_depths)
            print("\nQueue Depth Statistics:")
            print(f"  Maximum Queue Depth: {max_queue_depth}")
            print(f"  Average Queue Depth: {avg_queue_depth:.1f}")

        if results.error_details:
            print("\nError Details:")
            for error_type, count in results.error_details.items():
                print(f"  {error_type}: {count}")

        print(f"{'='*70}\n")


async def main():
    """Main function to run concurrent job stress tests."""
    parser = argparse.ArgumentParser(description="Concurrent Job Stress Testing Tool")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--jobs", type=int, default=20, help="Number of jobs to submit")
    parser.add_argument("--batch-size", type=int, default=5, help="Submission batch size")
    parser.add_argument("--timeout", type=int, default=600, help="Job tracking timeout in seconds")
    parser.add_argument("--test-type", choices=["submission", "end-to-end", "all"],
                       default="all", help="Type of test to run")

    args = parser.parse_args()

    async with ConcurrentJobStressTester(args.url) as tester:
        if args.test_type in ["submission", "all"]:
            logger.info("Running concurrent submission test...")
            submission_metrics, duration = await tester.concurrent_submission_test(
                num_jobs=args.jobs,
                batch_size=args.batch_size
            )

            # Print submission results
            successful = sum(1 for m in submission_metrics if m.success)
            failed = len(submission_metrics) - successful
            throughput = successful / duration if duration > 0 else 0.0

            print(f"\n{'='*50}")
            print("Concurrent Submission Test Results")
            print(f"{'='*50}")
            print(f"Total Jobs: {len(submission_metrics)}")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Duration: {duration:.2f}s")
            print(f"Throughput: {throughput:.2f} jobs/s")
            print(f"{'='*50}\n")

        if args.test_type in ["end-to-end", "all"]:
            logger.info("Running end-to-end processing test...")
            results = await tester.end_to_end_processing_test(
                num_jobs=args.jobs,
                submission_batch_size=args.batch_size,
                tracking_timeout=args.timeout
            )
            tester.print_results(results, "End-to-End Processing Test")


if __name__ == "__main__":
    asyncio.run(main())
