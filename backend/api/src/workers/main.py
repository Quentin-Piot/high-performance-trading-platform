"""Main entry point for running workers."""
import logging
import sys

from dotenv import load_dotenv

from core.logging import setup_logging
from workers.simple_worker import get_simple_worker, start_cleanup_task


def main():
    """Main entry point for running a simple Monte Carlo worker"""
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Logging setup complete.")
    try:
        worker = get_simple_worker()
        logger.info(
            f"Simple Monte Carlo worker initialized with {worker.max_concurrent_jobs} max concurrent jobs"
        )
        start_cleanup_task()
        logger.info("Simple worker cleanup task started")
        logger.info("Simple Monte Carlo worker is running. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
        worker.shutdown()
    except Exception as e:
        logger.error(f"Worker failed: {str(e)}", exc_info=True)
        sys.exit(1)
if __name__ == "__main__":
    main()
