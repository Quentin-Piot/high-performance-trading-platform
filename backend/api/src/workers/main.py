"""Main entry point for running workers."""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from config.queue_config import get_config
from core.logging import setup_logging
from infrastructure.queue.sqs_adapter import SQSQueueAdapter
from infrastructure.storage.s3_adapter import S3StorageAdapter
from workers.monte_carlo_worker import (
    MonteCarloJobProcessor,
    MonteCarloWorker,
    WorkerProgressCallback,
)


async def main():
    """Main entry point for running a Monte Carlo worker"""
    # Load environment variables from .env file
    load_dotenv()

    # Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Logging setup complete.")

    # Configuration from environment
    worker_id = os.getenv("WORKER_ID", f"mc-worker-{os.getpid()}")
    max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
    logger.info(f"Worker ID: {worker_id}, Max Concurrent Jobs: {max_concurrent_jobs}")

    try:
        # Get configuration
        logger.info("Loading configuration...")
        config = get_config()
        logger.info("Configuration loaded.")

        # Initialize components
        logger.info("Initializing SQS queue adapter...")
        queue = SQSQueueAdapter(config.sqs)
        logger.info("SQS queue adapter initialized.")

        logger.info("Initializing worker progress callback...")
        worker_id = os.getenv("WORKER_ID", "worker-1")
        progress_callback = WorkerProgressCallback(queue, worker_id)
        logger.info("Worker progress callback initialized.")

        logger.info("Initializing S3 storage adapter...")
        storage_adapter = S3StorageAdapter(
            bucket_name=os.getenv("S3_ARTIFACTS_BUCKET", os.getenv("S3_BUCKET_NAME", "trading-platform-results")),
            region_name=os.getenv("AWS_REGION", "eu-west-3"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL")
        )
        logger.info("S3 storage adapter initialized.")

        logger.info("Initializing Monte Carlo job processor...")
        processor = MonteCarloJobProcessor(
            processor_id=f"{worker_id}-processor",
            progress_callback=progress_callback,
            storage_adapter=storage_adapter
        )
        logger.info("Monte Carlo job processor initialized.")

        # Create and start worker
        logger.info("Creating Monte Carlo worker...")
        worker = MonteCarloWorker(
            worker_id=worker_id,
            queue=queue,
            processor=processor,
            progress_callback=progress_callback,
            max_concurrent_jobs=max_concurrent_jobs,
            storage_adapter=storage_adapter
        )
        logger.info("Monte Carlo worker created.")

        logger.info(f"Starting Monte Carlo worker: {worker_id}")
        await worker.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Worker failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
