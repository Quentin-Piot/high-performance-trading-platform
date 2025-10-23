"""
Database utilities for connection management, retry logic, and performance monitoring.

This module provides utilities to handle database connection timeouts, implement
retry logic, and monitor database performance for the trading platform.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, TypeVar

from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    TimeoutError,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Database operation retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_MAX_DELAY = 30.0

# Performance monitoring thresholds
SLOW_QUERY_THRESHOLD = 1.0  # seconds
VERY_SLOW_QUERY_THRESHOLD = 5.0  # seconds


class DatabaseError(Exception):
    """Custom database error for better error handling"""

    pass


class DatabaseTimeoutError(DatabaseError):
    """Raised when database operations timeout"""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""

    pass


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if a database error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable, False otherwise
    """
    retryable_errors = (
        DisconnectionError,
        TimeoutError,
        OperationalError,
        ConnectionError,
        OSError,
    )

    # Check for specific error messages that indicate retryable conditions
    error_message = str(error).lower()
    retryable_messages = [
        "connection reset",
        "connection refused",
        "timeout",
        "connection lost",
        "server closed the connection",
        "connection broken",
        "connection pool exhausted",
    ]

    return isinstance(error, retryable_errors) or any(
        msg in error_message for msg in retryable_messages
    )


def db_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_BACKOFF_MULTIPLIER,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: tuple = None,
):
    """
    Decorator for database operations with retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Decorated function with retry logic
    """
    if exceptions is None:
        exceptions = (DatabaseError, DisconnectionError, TimeoutError, OperationalError)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            "Database operation failed after all retries",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        raise DatabaseError(
                            f"Operation failed after {max_retries} retries: {str(e)}"
                        ) from e

                    if not (isinstance(e, exceptions) or is_retryable_error(e)):
                        logger.error(
                            "Non-retryable database error",
                            extra={
                                "function": func.__name__,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        raise

                    logger.warning(
                        "Database operation failed, retrying",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": current_delay,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * backoff, max_delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator


@asynccontextmanager
async def db_operation_monitor(operation_name: str, session: AsyncSession):
    """
    Context manager for monitoring database operation performance.

    Args:
        operation_name: Name of the database operation
        session: Database session

    Yields:
        Dictionary containing operation metrics
    """
    start_time = time.time()
    metrics = {
        "operation": operation_name,
        "start_time": start_time,
        "duration": 0.0,
        "success": False,
        "error": None,
    }

    try:
        logger.debug(f"Starting database operation: {operation_name}")
        yield metrics

        metrics["success"] = True

    except Exception as e:
        metrics["error"] = str(e)
        metrics["error_type"] = type(e).__name__

        logger.error(
            "Database operation failed",
            extra={
                "operation": operation_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": time.time() - start_time,
            },
        )
        raise

    finally:
        end_time = time.time()
        metrics["duration"] = end_time - start_time

        # Log performance metrics
        if metrics["duration"] > VERY_SLOW_QUERY_THRESHOLD:
            logger.warning("Very slow database operation detected", extra=metrics)
        elif metrics["duration"] > SLOW_QUERY_THRESHOLD:
            logger.info("Slow database operation detected", extra=metrics)
        else:
            logger.debug("Database operation completed", extra=metrics)


async def execute_with_timeout(
    session: AsyncSession,
    operation: Callable[[], Awaitable[T]],
    timeout: float = 30.0,
    operation_name: str = "database_operation",
) -> T:
    """
    Execute a database operation with timeout.

    Args:
        session: Database session
        operation: Async operation to execute
        timeout: Timeout in seconds
        operation_name: Name for logging purposes

    Returns:
        Result of the operation

    Raises:
        DatabaseTimeoutError: If operation times out
        DatabaseError: If operation fails
    """
    try:
        return await asyncio.wait_for(operation(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(
            "Database operation timed out",
            extra={"operation": operation_name, "timeout": timeout},
        )
        # Try to rollback the session if possible
        try:
            await session.rollback()
        except Exception as rollback_error:
            logger.warning(
                "Failed to rollback session after timeout",
                extra={
                    "operation": operation_name,
                    "rollback_error": str(rollback_error),
                },
            )

        raise DatabaseTimeoutError(
            f"Operation '{operation_name}' timed out after {timeout} seconds"
        ) from None
    except Exception as e:
        logger.error(
            "Database operation failed",
            extra={
                "operation": operation_name,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise DatabaseError(f"Operation '{operation_name}' failed: {str(e)}") from e


class BatchOperationManager:
    """Manager for batch database operations to reduce round trips"""

    def __init__(self, session: AsyncSession, batch_size: int = 100):
        self.session = session
        self.batch_size = batch_size
        self.pending_operations: list[dict[str, Any]] = []

    def add_operation(self, operation_type: str, **kwargs):
        """Add an operation to the batch"""
        self.pending_operations.append({"type": operation_type, "data": kwargs})

    async def execute_batch(self) -> dict[str, int]:
        """
        Execute all pending operations in batches.

        Returns:
            Dictionary with operation counts
        """
        if not self.pending_operations:
            return {"total": 0}

        results = {"total": len(self.pending_operations)}
        operation_groups = {}

        # Group operations by type
        for op in self.pending_operations:
            op_type = op["type"]
            if op_type not in operation_groups:
                operation_groups[op_type] = []
            operation_groups[op_type].append(op["data"])

        # Execute each group in batches
        for op_type, operations in operation_groups.items():
            results[op_type] = len(operations)

            for i in range(0, len(operations), self.batch_size):
                batch = operations[i : i + self.batch_size]
                await self._execute_batch_by_type(op_type, batch)

        # Clear pending operations
        self.pending_operations.clear()

        return results

    async def _execute_batch_by_type(
        self, operation_type: str, batch: list[dict[str, Any]]
    ):
        """Execute a batch of operations of the same type"""
        try:
            if operation_type == "job_status_update":
                await self._batch_update_job_status(batch)
            elif operation_type == "job_progress_update":
                await self._batch_update_job_progress(batch)
            else:
                logger.warning(f"Unknown batch operation type: {operation_type}")

        except Exception as e:
            logger.error(
                "Batch operation failed",
                extra={
                    "operation_type": operation_type,
                    "batch_size": len(batch),
                    "error": str(e),
                },
            )
            raise

    async def _batch_update_job_status(self, batch: list[dict[str, Any]]):
        """Execute batch job status updates"""
        from sqlalchemy import update

        from infrastructure.models import Job

        for job_data in batch:
            await self.session.execute(
                update(Job)
                .where(Job.id == job_data["job_id"])
                .values(
                    status=job_data["status"],
                    updated_at=job_data.get("updated_at"),
                    worker_id=job_data.get("worker_id"),
                    error=job_data.get("error"),
                    progress=job_data.get("progress"),
                    artifact_url=job_data.get("artifact_url"),
                    completed_at=job_data.get("completed_at"),
                )
            )

        await self.session.commit()

    async def _batch_update_job_progress(self, batch: list[dict[str, Any]]):
        """Execute batch job progress updates"""
        from sqlalchemy import update

        from infrastructure.models import Job

        for job_data in batch:
            await self.session.execute(
                update(Job)
                .where(Job.id == job_data["job_id"])
                .values(
                    progress=job_data["progress"],
                    updated_at=job_data.get("updated_at"),
                    payload=job_data.get("payload"),
                )
            )

        await self.session.commit()


async def check_connection_health(session: AsyncSession) -> bool:
    """
    Check if database connection is healthy.

    Args:
        session: Database session to check

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.warning(
            "Database connection health check failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False
