"""
Enhanced logging utilities for background tasks and WebSocket handlers.

This module provides specialized logging decorators and utilities for tracking
background tasks, WebSocket connections, and async operations with proper
error handling and structured logging.
"""

import asyncio
import contextvars
import functools
import logging
import time
import traceback
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, TypeVar

# Context variables for tracking background tasks
TASK_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "task_id", default="unknown"
)
WEBSOCKET_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "websocket_id", default="unknown"
)
JOB_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "job_id", default="unknown"
)

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


class BackgroundTaskFilter(logging.Filter):
    """Filter to add background task context to log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        # Add task context to log record
        record.task_id = TASK_ID.get("unknown")
        record.websocket_id = WEBSOCKET_ID.get("unknown")
        record.job_id = JOB_ID.get("unknown")
        return True


def log_background_task(
    task_name: str,
    include_args: bool = False,
    include_result: bool = False,
    log_level: int = logging.INFO,
):
    """
    Decorator for logging background tasks with comprehensive error handling.

    Args:
        task_name: Name of the task for logging
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        log_level: Logging level for success messages
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            task_id = f"{task_name}_{int(time.time() * 1000)}"
            token = TASK_ID.set(task_id)

            start_time = time.time()
            logger = logging.getLogger(func.__module__)

            # Log task start
            log_data = {
                "task_name": task_name,
                "task_id": task_id,
                "function": func.__name__,
                "module": func.__module__,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if include_args and (args or kwargs):
                log_data["args"] = {
                    "positional": [
                        str(arg)[:100] for arg in args
                    ],  # Truncate long args
                    "keyword": {k: str(v)[:100] for k, v in kwargs.items()},
                }

            logger.log(
                log_level, f"Background task started: {task_name}", extra=log_data
            )

            try:
                result = await func(*args, **kwargs)

                # Log successful completion
                duration = time.time() - start_time
                completion_data = {
                    **log_data,
                    "duration_seconds": round(duration, 3),
                    "status": "completed",
                }

                if include_result and result is not None:
                    completion_data["result"] = str(result)[
                        :200
                    ]  # Truncate long results

                logger.log(
                    log_level,
                    f"Background task completed: {task_name}",
                    extra=completion_data,
                )
                return result

            except asyncio.CancelledError:
                # Handle task cancellation
                duration = time.time() - start_time
                logger.warning(
                    f"Background task cancelled: {task_name}",
                    extra={
                        **log_data,
                        "duration_seconds": round(duration, 3),
                        "status": "cancelled",
                    },
                )
                raise

            except Exception as e:
                # Log error with full traceback
                duration = time.time() - start_time
                error_data = {
                    **log_data,
                    "duration_seconds": round(duration, 3),
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                }

                logger.error(f"Background task failed: {task_name}", extra=error_data)
                raise

            finally:
                TASK_ID.reset(token)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, use similar logging but without async
            task_id = f"{task_name}_{int(time.time() * 1000)}"
            token = TASK_ID.set(task_id)

            start_time = time.time()
            logger = logging.getLogger(func.__module__)

            log_data = {
                "task_name": task_name,
                "task_id": task_id,
                "function": func.__name__,
                "module": func.__module__,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if include_args and (args or kwargs):
                log_data["args"] = {
                    "positional": [str(arg)[:100] for arg in args],
                    "keyword": {k: str(v)[:100] for k, v in kwargs.items()},
                }

            logger.log(log_level, f"Task started: {task_name}", extra=log_data)

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                completion_data = {
                    **log_data,
                    "duration_seconds": round(duration, 3),
                    "status": "completed",
                }

                if include_result and result is not None:
                    completion_data["result"] = str(result)[:200]

                logger.log(
                    log_level, f"Task completed: {task_name}", extra=completion_data
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                error_data = {
                    **log_data,
                    "duration_seconds": round(duration, 3),
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                }

                logger.error(f"Task failed: {task_name}", extra=error_data)
                raise

            finally:
                TASK_ID.reset(token)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_websocket_connection(connection_name: str):
    """
    Decorator for logging WebSocket connection lifecycle.

    Args:
        connection_name: Name of the WebSocket connection for logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            websocket_id = f"{connection_name}_{int(time.time() * 1000)}"
            ws_token = WEBSOCKET_ID.set(websocket_id)

            logger = logging.getLogger(func.__module__)
            start_time = time.time()

            # Extract job_id if available from kwargs
            job_id = kwargs.get("job_id", "unknown")
            job_token = JOB_ID.set(job_id)

            log_data = {
                "connection_name": connection_name,
                "websocket_id": websocket_id,
                "job_id": job_id,
                "function": func.__name__,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info(
                f"WebSocket connection started: {connection_name}", extra=log_data
            )

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time
                logger.info(
                    f"WebSocket connection completed: {connection_name}",
                    extra={
                        **log_data,
                        "duration_seconds": round(duration, 3),
                        "status": "completed",
                    },
                )
                return result

            except asyncio.CancelledError:
                duration = time.time() - start_time
                logger.warning(
                    f"WebSocket connection cancelled: {connection_name}",
                    extra={
                        **log_data,
                        "duration_seconds": round(duration, 3),
                        "status": "cancelled",
                    },
                )
                raise

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"WebSocket connection failed: {connection_name}",
                    extra={
                        **log_data,
                        "duration_seconds": round(duration, 3),
                        "status": "failed",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc(),
                    },
                )
                raise

            finally:
                WEBSOCKET_ID.reset(ws_token)
                JOB_ID.reset(job_token)

        return wrapper

    return decorator


@asynccontextmanager
async def log_async_operation(
    operation_name: str,
    logger_name: str | None = None,
    extra_context: dict[str, Any] | None = None,
):
    """
    Context manager for logging async operations with timing and error handling.

    Args:
        operation_name: Name of the operation
        logger_name: Logger name (defaults to caller's module)
        extra_context: Additional context to include in logs
    """
    if logger_name is None:
        import inspect

        frame = inspect.currentframe().f_back
        logger_name = frame.f_globals.get("__name__", "unknown")

    logger = logging.getLogger(logger_name)
    start_time = time.time()
    operation_id = f"{operation_name}_{int(time.time() * 1000)}"

    log_data = {
        "operation_name": operation_name,
        "operation_id": operation_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if extra_context:
        log_data.update(extra_context)

    logger.info(f"Async operation started: {operation_name}", extra=log_data)

    try:
        yield operation_id

        duration = time.time() - start_time
        logger.info(
            f"Async operation completed: {operation_name}",
            extra={
                **log_data,
                "duration_seconds": round(duration, 3),
                "status": "completed",
            },
        )

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Async operation failed: {operation_name}",
            extra={
                **log_data,
                "duration_seconds": round(duration, 3),
                "status": "failed",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def setup_background_task_logging():
    """
    Setup enhanced logging for background tasks.

    This should be called during application startup to add the
    BackgroundTaskFilter to the root logger.
    """
    root_logger = logging.getLogger()

    # Check if filter is already added
    for handler in root_logger.handlers:
        for filter_obj in handler.filters:
            if isinstance(filter_obj, BackgroundTaskFilter):
                return  # Already setup

    # Add the filter to all existing handlers
    task_filter = BackgroundTaskFilter()
    for handler in root_logger.handlers:
        handler.addFilter(task_filter)

    logger.info("Background task logging setup completed")


def create_safe_background_task(
    coro, name: str | None = None, logger_name: str | None = None
) -> asyncio.Task:
    """
    Create a background task with comprehensive error handling and logging.

    Args:
        coro: Coroutine to run as background task
        name: Optional name for the task
        logger_name: Logger name for error reporting

    Returns:
        asyncio.Task with error handling
    """
    if logger_name is None:
        import inspect

        frame = inspect.currentframe().f_back
        logger_name = frame.f_globals.get("__name__", "background_task")

    task_logger = logging.getLogger(logger_name)

    async def safe_wrapper():
        try:
            return await coro
        except asyncio.CancelledError:
            task_logger.info(f"Background task cancelled: {name or 'unnamed'}")
            raise
        except Exception as e:
            task_logger.error(
                f"Background task failed: {name or 'unnamed'}",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            # Don't re-raise to prevent task from dying silently

    task = asyncio.create_task(safe_wrapper())
    if name:
        task.set_name(name)

    return task
