"""
SQS implementation of the queue interface.

This module provides a concrete implementation of the queue interface using AWS SQS,
with support for dead letter queues, message attributes, and monitoring.
"""
import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.domain.queue import (
    QueueInterface, Job, JobStatus, JobMetadata, QueueMetrics,
    MonteCarloJobPayload
)

logger = logging.getLogger(__name__)


class SQSQueueAdapter(QueueInterface[MonteCarloJobPayload]):
    """SQS implementation of the queue interface"""
    
    def __init__(
        self,
        queue_url: str,
        region_name: str = "us-east-1",
        dead_letter_queue_url: Optional[str] = None,
        visibility_timeout: int = 300,
        message_retention_period: int = 1209600,  # 14 days
        max_receive_count: int = 3,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None  # For LocalStack testing
    ):
        """
        Initialize SQS queue adapter.
        
        Args:
            queue_url: SQS queue URL
            region_name: AWS region
            dead_letter_queue_url: Dead letter queue URL
            visibility_timeout: Message visibility timeout in seconds
            message_retention_period: Message retention period in seconds
            max_receive_count: Maximum receive count before moving to DLQ
            aws_access_key_id: AWS access key (optional, uses default credentials if not provided)
            aws_secret_access_key: AWS secret key (optional)
            endpoint_url: Custom endpoint URL (for testing with LocalStack)
        """
        self.queue_url = queue_url
        self.dead_letter_queue_url = dead_letter_queue_url
        self.visibility_timeout = visibility_timeout
        self.message_retention_period = message_retention_period
        self.max_receive_count = max_receive_count
        
        # Initialize SQS client
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key
            })
        
        self.session = boto3.Session(**session_kwargs)
        client_kwargs = {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
            
        self.sqs_client = self.session.client("sqs", **client_kwargs)
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="sqs-adapter")
        
        # In-memory job tracking for status queries
        self._job_cache: Dict[str, Job[MonteCarloJobPayload]] = {}
        
        logger.info(f"Initialized SQS adapter for queue: {queue_url}")
    
    async def enqueue(self, job: Job[MonteCarloJobPayload]) -> str:
        """Enqueue a Monte Carlo job to SQS"""
        try:
            # Serialize job payload
            message_body = self._serialize_job(job)
            
            # Prepare message attributes
            message_attributes = self._create_message_attributes(job)
            
            # Send message to SQS
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._send_message_sync,
                message_body,
                message_attributes,
                job.metadata.job_id
            )
            
            # Update job status
            job.update_status(JobStatus.QUEUED)
            self._job_cache[job.metadata.job_id] = job
            
            logger.info(f"Enqueued job {job.metadata.job_id} to SQS")
            return job.metadata.job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {job.metadata.job_id}: {str(e)}")
            job.update_status(JobStatus.FAILED, str(e))
            raise
    
    async def dequeue(self, timeout_seconds: Optional[int] = None) -> Optional[Job[MonteCarloJobPayload]]:
        """Dequeue a job from SQS"""
        try:
            wait_time = min(timeout_seconds or 20, 20)  # SQS max long polling is 20s
            
            loop = asyncio.get_event_loop()
            messages = await loop.run_in_executor(
                self.executor,
                self._receive_messages_sync,
                wait_time
            )
            
            if not messages:
                return None
            
            message = messages[0]  # Process one message at a time
            
            # Deserialize job
            job = self._deserialize_job(message["Body"])
            job.update_status(JobStatus.PROCESSING)
            
            # Store receipt handle for acknowledgment
            job.metadata.tags["receipt_handle"] = message["ReceiptHandle"]
            job.metadata.tags["message_id"] = message["MessageId"]
            
            # Update cache
            self._job_cache[job.metadata.job_id] = job
            
            logger.info(f"Dequeued job {job.metadata.job_id} from SQS")
            return job
            
        except Exception as e:
            logger.error(f"Failed to dequeue job: {str(e)}")
            return None
    
    async def acknowledge(self, job_id: str) -> bool:
        """Acknowledge successful job completion"""
        try:
            job = self._job_cache.get(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found in cache for acknowledgment")
                return False
            
            receipt_handle = job.metadata.tags.get("receipt_handle")
            if not receipt_handle:
                logger.warning(f"No receipt handle found for job {job_id}")
                return False
            
            # Delete message from SQS
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._delete_message_sync,
                receipt_handle
            )
            
            # Update job status
            job.update_status(JobStatus.COMPLETED)
            
            logger.info(f"Acknowledged job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge job {job_id}: {str(e)}")
            return False
    
    async def reject(self, job_id: str, requeue: bool = True) -> bool:
        """Reject a job (failed processing)"""
        try:
            job = self._job_cache.get(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found in cache for rejection")
                return False
            
            receipt_handle = job.metadata.tags.get("receipt_handle")
            if not receipt_handle:
                logger.warning(f"No receipt handle found for job {job_id}")
                return False
            
            if requeue and job.increment_retry():
                # Change message visibility to make it available for retry
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self._change_message_visibility_sync,
                    receipt_handle,
                    0  # Make immediately available
                )
                job.update_status(JobStatus.RETRY)
                logger.info(f"Requeued job {job_id} for retry (attempt {job.metadata.retry_count})")
            else:
                # Delete message (will go to DLQ if configured)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self._delete_message_sync,
                    receipt_handle
                )
                job.update_status(JobStatus.FAILED)
                logger.info(f"Rejected job {job_id} (max retries exceeded)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject job {job_id}: {str(e)}")
            return False
    
    async def get_job_status(self, job_id: str) -> Optional[Job[MonteCarloJobPayload]]:
        """Get current status of a job"""
        return self._job_cache.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        try:
            job = self._job_cache.get(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found for cancellation")
                return False
            
            if job.status in [JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED]:
                logger.warning(f"Cannot cancel job {job_id} in status {job.status}")
                return False
            
            job.update_status(JobStatus.CANCELLED)
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            return False
    
    async def get_metrics(self) -> QueueMetrics:
        """Get queue metrics from SQS"""
        try:
            loop = asyncio.get_event_loop()
            attributes = await loop.run_in_executor(
                self.executor,
                self._get_queue_attributes_sync
            )
            
            # Calculate metrics from cache and SQS attributes
            pending_jobs = int(attributes.get("ApproximateNumberOfMessages", 0))
            processing_jobs = len([j for j in self._job_cache.values() if j.status == JobStatus.PROCESSING])
            completed_jobs = len([j for j in self._job_cache.values() if j.status == JobStatus.COMPLETED])
            failed_jobs = len([j for j in self._job_cache.values() if j.status == JobStatus.FAILED])
            
            return QueueMetrics(
                queue_name=self.queue_url.split("/")[-1],
                pending_jobs=pending_jobs,
                processing_jobs=processing_jobs,
                completed_jobs=completed_jobs,
                failed_jobs=failed_jobs,
                average_processing_time=0.0,  # Would need additional tracking
                throughput_per_minute=0.0,    # Would need additional tracking
                last_updated=datetime.now(UTC)
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue metrics: {str(e)}")
            raise
    
    def _serialize_job(self, job: Job[MonteCarloJobPayload]) -> str:
        """Serialize job to JSON string"""
        job_dict = {
            "job_id": job.metadata.job_id,
            "payload": {
                "csv_data": job.payload.csv_data.hex(),  # Convert bytes to hex string
                "filename": job.payload.filename,
                "strategy_name": job.payload.strategy_name,
                "strategy_params": job.payload.strategy_params,
                "runs": job.payload.runs,
                "method": job.payload.method,
                "method_params": job.payload.method_params,
                "seed": job.payload.seed,
                "include_equity_envelope": job.payload.include_equity_envelope
            },
            "metadata": {
                "created_at": job.metadata.created_at.isoformat(),
                "updated_at": job.metadata.updated_at.isoformat(),
                "priority": job.metadata.priority.value,
                "max_retries": job.metadata.max_retries,
                "retry_count": job.metadata.retry_count,
                "timeout_seconds": job.metadata.timeout_seconds,
                "tags": job.metadata.tags,
                "user_id": job.metadata.user_id,
                "correlation_id": job.metadata.correlation_id
            },
            "status": job.status.value,
            "progress": job.progress
        }
        return json.dumps(job_dict)
    
    def _deserialize_job(self, message_body: str) -> Job[MonteCarloJobPayload]:
        """Deserialize job from JSON string"""
        job_dict = json.loads(message_body)
        
        # Reconstruct payload
        payload_dict = job_dict["payload"]
        payload = MonteCarloJobPayload(
            csv_data=bytes.fromhex(payload_dict["csv_data"]),
            filename=payload_dict["filename"],
            strategy_name=payload_dict["strategy_name"],
            strategy_params=payload_dict["strategy_params"],
            runs=payload_dict["runs"],
            method=payload_dict["method"],
            method_params=payload_dict["method_params"],
            seed=payload_dict["seed"],
            include_equity_envelope=payload_dict["include_equity_envelope"]
        )
        
        # Reconstruct metadata
        metadata_dict = job_dict["metadata"]
        metadata = JobMetadata(
            job_id=job_dict["job_id"],
            created_at=datetime.fromisoformat(metadata_dict["created_at"]),
            updated_at=datetime.fromisoformat(metadata_dict["updated_at"]),
            priority=JobPriority(metadata_dict["priority"]),
            max_retries=metadata_dict["max_retries"],
            retry_count=metadata_dict["retry_count"],
            timeout_seconds=metadata_dict["timeout_seconds"],
            tags=metadata_dict["tags"],
            user_id=metadata_dict["user_id"],
            correlation_id=metadata_dict["correlation_id"]
        )
        
        return Job(
            payload=payload,
            metadata=metadata,
            status=JobStatus(job_dict["status"]),
            progress=job_dict["progress"]
        )
    
    def _create_message_attributes(self, job: Job[MonteCarloJobPayload]) -> Dict[str, Any]:
        """Create SQS message attributes from job metadata"""
        attributes = {
            "JobId": {"StringValue": job.metadata.job_id, "DataType": "String"},
            "Priority": {"StringValue": str(job.metadata.priority.value), "DataType": "Number"},
            "Runs": {"StringValue": str(job.payload.runs), "DataType": "Number"},
            "Strategy": {"StringValue": job.payload.strategy_name, "DataType": "String"},
            "Method": {"StringValue": job.payload.method, "DataType": "String"}
        }
        
        if job.metadata.user_id:
            attributes["UserId"] = {"StringValue": job.metadata.user_id, "DataType": "String"}
        
        if job.metadata.correlation_id:
            attributes["CorrelationId"] = {"StringValue": job.metadata.correlation_id, "DataType": "String"}
        
        return attributes
    
    # Synchronous methods for thread pool execution
    
    def _send_message_sync(self, message_body: str, message_attributes: Dict[str, Any], deduplication_id: str) -> Dict[str, Any]:
        """Send message to SQS (synchronous)"""
        params = {
            "QueueUrl": self.queue_url,
            "MessageBody": message_body,
            "MessageAttributes": message_attributes
        }
        
        # Add deduplication ID for FIFO queues
        if self.queue_url.endswith(".fifo"):
            params["MessageDeduplicationId"] = deduplication_id
            params["MessageGroupId"] = "monte-carlo-jobs"
        
        return self.sqs_client.send_message(**params)
    
    def _receive_messages_sync(self, wait_time: int) -> List[Dict[str, Any]]:
        """Receive messages from SQS (synchronous)"""
        response = self.sqs_client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=wait_time,
            MessageAttributeNames=["All"],
            AttributeNames=["All"]
        )
        return response.get("Messages", [])
    
    def _delete_message_sync(self, receipt_handle: str) -> None:
        """Delete message from SQS (synchronous)"""
        self.sqs_client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )
    
    def _change_message_visibility_sync(self, receipt_handle: str, visibility_timeout: int) -> None:
        """Change message visibility timeout (synchronous)"""
        self.sqs_client.change_message_visibility(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=visibility_timeout
        )
    
    def _get_queue_attributes_sync(self) -> Dict[str, str]:
        """Get queue attributes (synchronous)"""
        response = self.sqs_client.get_queue_attributes(
            QueueUrl=self.queue_url,
            AttributeNames=["All"]
        )
        return response.get("Attributes", {})
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.executor.shutdown(wait=True)
        logger.info("SQS adapter cleanup completed")