"""
SQS implementation of the queue interface.

This module provides a concrete implementation of the queue interface using AWS SQS,
with support for dead letter queues, message attributes, monitoring, and visibility timeout heartbeat.
"""
import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional, List, Set
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import asyncio
from concurrent.futures import ThreadPoolExecutor

from domain.queue import (
    QueueInterface, Job, JobStatus, JobMetadata, QueueMetrics,
    MonteCarloJobPayload
)
from config.queue_config import SQSConfig
from infrastructure.security import CredentialManager

logger = logging.getLogger(__name__)


class SQSQueueAdapter(QueueInterface[MonteCarloJobPayload]):
    """SQS implementation of the queue interface"""
    
    def __init__(
        self,
        config: SQSConfig
    ):
        """
        Initialize SQS queue adapter with secure configuration.
        
        Args:
            config: SQS configuration with secure credential management
        """
        self.queue_url = config.queue_url
        self.dead_letter_queue_url = config.dead_letter_queue_url
        self.visibility_timeout = config.visibility_timeout
        self.message_retention_period = config.message_retention_period
        self.max_receive_count = config.max_receive_count
        
        # Validate credentials
        if not CredentialManager.validate_credentials(config.aws_credentials):
            raise ValueError("Invalid AWS credentials provided")
        
        # Initialize SQS client with secure configuration
        boto3_config = config.get_boto3_config()
        self.session = boto3.Session(**{k: v for k, v in boto3_config.items() 
                                      if k not in ("endpoint_url",)})
        
        client_kwargs = {}
        if "endpoint_url" in boto3_config:
            client_kwargs["endpoint_url"] = boto3_config["endpoint_url"]
            
        self.sqs_client = self.session.client("sqs", **client_kwargs)
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="sqs-adapter")
        
        # In-memory job tracking for status queries
        self._job_cache: Dict[str, Job[MonteCarloJobPayload]] = {}
        
        # Heartbeat tracking for visibility timeout extension
        self._active_heartbeats: Set[str] = set()
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("Initialized SQS adapter", extra={
            "queue_url": config.queue_url,
            "credential_info": config.aws_credentials.mask_sensitive_data()
        })
    
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
            
            # Start heartbeat for visibility timeout extension
            await self._start_heartbeat(job.metadata.job_id, message["ReceiptHandle"])
            
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
            
            # Stop heartbeat
            await self._stop_heartbeat(job_id)
            
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
                
                # Stop heartbeat
                await self._stop_heartbeat(job_id)
                
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
        """Get queue metrics including DLQ statistics"""
        try:
            loop = asyncio.get_event_loop()
            
            # Get main queue attributes
            main_attributes = await loop.run_in_executor(
                self.executor,
                self._get_queue_attributes_sync
            )
            
            # Get DLQ attributes if configured
            dlq_attributes = {}
            if self.dead_letter_queue_url:
                try:
                    dlq_attributes = await loop.run_in_executor(
                        self.executor,
                        self._get_dlq_attributes_sync
                    )
                except Exception as e:
                    logger.warning(f"Failed to get DLQ metrics: {e}")
            
            # Parse metrics
            pending_jobs = int(main_attributes.get("ApproximateNumberOfMessages", 0))
            processing_jobs = int(main_attributes.get("ApproximateNumberOfMessagesNotVisible", 0))
            dlq_messages = int(dlq_attributes.get("ApproximateNumberOfMessages", 0))
            
            return QueueMetrics(
                queue_name=self.queue_url.split("/")[-1],
                pending_jobs=pending_jobs,
                processing_jobs=processing_jobs,
                completed_jobs=0,  # SQS doesn't track completed jobs
                failed_jobs=dlq_messages,  # Messages in DLQ are failed jobs
                average_processing_time=0.0,  # Would need CloudWatch for this
                throughput_per_minute=0.0,  # Would need CloudWatch for this
                last_updated=datetime.now(UTC)
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue metrics: {str(e)}")
            return QueueMetrics(
                queue_name="unknown",
                pending_jobs=0,
                processing_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                average_processing_time=0.0,
                throughput_per_minute=0.0,
                last_updated=datetime.now(UTC)
            )
    
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
    
    def _get_dlq_attributes_sync(self) -> Dict[str, str]:
        """Get DLQ attributes synchronously"""
        if not self.dead_letter_queue_url:
            return {}
            
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.dead_letter_queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            return response.get('Attributes', {})
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to get DLQ attributes: {e}")
            return {}

    async def cleanup(self) -> None:
        """Cleanup resources"""
        # Stop all active heartbeats
        for job_id in list(self._active_heartbeats):
            await self._stop_heartbeat(job_id)
        
        self.executor.shutdown(wait=True)
        logger.info("SQS adapter cleanup completed")
    
    async def _start_heartbeat(self, job_id: str, receipt_handle: str) -> None:
        """Start heartbeat task to extend message visibility timeout"""
        if job_id in self._active_heartbeats:
            logger.warning(f"Heartbeat already active for job {job_id}")
            return
        
        self._active_heartbeats.add(job_id)
        
        async def heartbeat_loop():
            """Background task to extend visibility timeout every 15 seconds"""
            try:
                while job_id in self._active_heartbeats:
                    await asyncio.sleep(15)  # Wait 15 seconds
                    
                    if job_id not in self._active_heartbeats:
                        break
                    
                    try:
                        # Extend visibility timeout by the original timeout value
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            self.executor,
                            self._change_message_visibility_sync,
                            receipt_handle,
                            self.visibility_timeout
                        )
                        logger.debug(f"Extended visibility timeout for job {job_id}")
                    except Exception as e:
                        logger.error(f"Failed to extend visibility timeout for job {job_id}: {e}")
                        # Continue the loop - transient errors shouldn't stop heartbeat
                        
            except asyncio.CancelledError:
                logger.debug(f"Heartbeat cancelled for job {job_id}")
            except Exception as e:
                logger.error(f"Heartbeat error for job {job_id}: {e}")
            finally:
                self._active_heartbeats.discard(job_id)
                self._heartbeat_tasks.pop(job_id, None)
        
        # Start the heartbeat task
        task = asyncio.create_task(heartbeat_loop())
        self._heartbeat_tasks[job_id] = task
        
        logger.debug(f"Started heartbeat for job {job_id}")
    
    async def _stop_heartbeat(self, job_id: str) -> None:
        """Stop heartbeat task for a job"""
        if job_id not in self._active_heartbeats:
            return
        
        # Remove from active set
        self._active_heartbeats.discard(job_id)
        
        # Cancel the task if it exists
        task = self._heartbeat_tasks.pop(job_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.debug(f"Stopped heartbeat for job {job_id}")