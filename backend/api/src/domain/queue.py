"""
Domain interfaces for queue systems and job management.

This module defines abstract interfaces for queue operations, job management,
and worker systems to enable a decoupled, scalable architecture.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Generic, TypeVar
import uuid

# Type variables for generic interfaces
T = TypeVar('T')
R = TypeVar('R')


class JobStatus(Enum):
    """Status of a job in the queue system"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobPriority(Enum):
    """Priority levels for jobs"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class JobMetadata:
    """Metadata for job tracking and monitoring"""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: Optional[int] = None
    tags: Dict[str, str] = field(default_factory=dict)
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class Job(Generic[T]):
    """Generic job representation"""
    payload: T
    metadata: JobMetadata
    status: JobStatus = JobStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0
    
    def update_status(self, status: JobStatus, error: Optional[str] = None) -> None:
        """Update job status and timestamp"""
        self.status = status
        self.error = error
        self.metadata.updated_at = datetime.now(UTC)
    
    def increment_retry(self) -> bool:
        """Increment retry count and return True if retries available"""
        self.metadata.retry_count += 1
        return self.metadata.retry_count <= self.metadata.max_retries


@dataclass
class MonteCarloJobPayload:
    """Payload for Monte Carlo simulation jobs"""
    csv_data: bytes
    filename: str
    strategy_name: str
    strategy_params: Dict[str, Any]
    runs: int
    method: str = "bootstrap"
    method_params: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    include_equity_envelope: bool = True
    parallel_workers: int = 1


@dataclass
class QueueMetrics:
    """Metrics for queue monitoring"""
    queue_name: str
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time: float
    throughput_per_minute: float
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


class QueueInterface(ABC, Generic[T]):
    """Abstract interface for queue operations"""
    
    @abstractmethod
    async def enqueue(self, job: Job[T]) -> str:
        """
        Enqueue a job and return job ID.
        
        Args:
            job: Job to enqueue
            
        Returns:
            Job ID for tracking
        """
        pass
    
    @abstractmethod
    async def dequeue(self, timeout_seconds: Optional[int] = None) -> Optional[Job[T]]:
        """
        Dequeue a job for processing.
        
        Args:
            timeout_seconds: Maximum time to wait for a job
            
        Returns:
            Job to process or None if timeout
        """
        pass
    
    @abstractmethod
    async def acknowledge(self, job_id: str) -> bool:
        """
        Acknowledge successful job completion.
        
        Args:
            job_id: ID of completed job
            
        Returns:
            True if acknowledged successfully
        """
        pass
    
    @abstractmethod
    async def reject(self, job_id: str, requeue: bool = True) -> bool:
        """
        Reject a job (failed processing).
        
        Args:
            job_id: ID of failed job
            requeue: Whether to requeue for retry
            
        Returns:
            True if rejected successfully
        """
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> Optional[Job[T]]:
        """
        Get current status of a job.
        
        Args:
            job_id: Job ID to query
            
        Returns:
            Job with current status or None if not found
        """
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> QueueMetrics:
        """
        Get queue metrics for monitoring.
        
        Returns:
            Current queue metrics
        """
        pass


class JobProcessorInterface(ABC, Generic[T, R]):
    """Abstract interface for job processors"""
    
    @abstractmethod
    async def process(self, job: Job[T]) -> R:
        """
        Process a job and return result.
        
        Args:
            job: Job to process
            
        Returns:
            Processing result
            
        Raises:
            Exception: If processing fails
        """
        pass
    
    @abstractmethod
    def get_processor_id(self) -> str:
        """Get unique processor identifier"""
        pass


class ProgressCallbackInterface(ABC):
    """Abstract interface for progress reporting"""
    
    @abstractmethod
    async def report_progress(self, job_id: str, progress: float, message: Optional[str] = None) -> None:
        """
        Report job progress.
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0.0 to 1.0)
            message: Optional progress message
        """
        pass
    
    @abstractmethod
    async def report_completion(self, job_id: str, result: Any) -> None:
        """
        Report job completion.
        
        Args:
            job_id: Job ID
            result: Job result
        """
        pass
    
    @abstractmethod
    async def report_error(self, job_id: str, error: str) -> None:
        """
        Report job error.
        
        Args:
            job_id: Job ID
            error: Error message
        """
        pass


class WorkerInterface(ABC):
    """Abstract interface for worker processes"""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the worker process"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the worker process gracefully"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if worker is healthy"""
        pass
    
    @abstractmethod
    def get_worker_id(self) -> str:
        """Get unique worker identifier"""
        pass


class JobManagerInterface(ABC):
    """Abstract interface for job management"""
    
    @abstractmethod
    async def submit_job(self, payload: Any, metadata: Optional[JobMetadata] = None) -> str:
        """
        Submit a new job.
        
        Args:
            payload: Job payload
            metadata: Optional job metadata
            
        Returns:
            Job ID
        """
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job or None if not found
        """
        pass
    
    @abstractmethod
    async def list_jobs(
        self, 
        status: Optional[JobStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """
        List jobs with optional filtering.
        
        Args:
            status: Filter by status
            user_id: Filter by user
            limit: Maximum number of jobs
            offset: Pagination offset
            
        Returns:
            List of jobs
        """
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        pass


class MonitoringInterface(ABC):
    """Abstract interface for system monitoring"""
    
    @abstractmethod
    async def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value"""
        pass
    
    @abstractmethod
    async def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    async def record_timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric"""
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        pass