"""
S3 adapter for artifact storage.

This module provides S3 storage functionality for Monte Carlo job artifacts,
including result files, charts, and reports with lifecycle management.
"""
import json
import logging
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, Optional, List, BinaryIO, Union
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class S3StorageAdapter:
    """S3 implementation for artifact storage"""
    
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        prefix: str = "monte-carlo-artifacts",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,  # For LocalStack testing
        lifecycle_days: int = 30,  # Days before artifacts are moved to IA
        expiration_days: int = 365  # Days before artifacts are deleted
    ):
        """
        Initialize S3 storage adapter.
        
        Args:
            bucket_name: S3 bucket name
            region_name: AWS region
            prefix: Key prefix for all artifacts
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
            endpoint_url: Custom endpoint URL (for testing with LocalStack)
            lifecycle_days: Days before moving to Infrequent Access
            expiration_days: Days before permanent deletion
        """
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.lifecycle_days = lifecycle_days
        self.expiration_days = expiration_days
        
        # Initialize S3 client
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
            
        self.s3_client = self.session.client("s3", **client_kwargs)
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="s3-adapter")
        
        logger.info(f"Initialized S3 adapter for bucket: {bucket_name}")

    async def upload_artifact(
        self,
        job_id: str,
        artifact_name: str,
        content: Union[bytes, str, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload an artifact to S3.
        
        Args:
            job_id: Job identifier
            artifact_name: Name of the artifact file
            content: File content (bytes, string, or file-like object)
            content_type: MIME type of the content
            metadata: Additional metadata to store with the object
            
        Returns:
            S3 URL of the uploaded artifact
        """
        try:
            # Generate S3 key
            timestamp = datetime.now(UTC).strftime("%Y/%m/%d")
            key = f"{self.prefix}/{timestamp}/{job_id}/{artifact_name}"
            
            # Prepare metadata
            upload_metadata = {
                "job-id": job_id,
                "upload-timestamp": datetime.now(UTC).isoformat(),
                "artifact-type": Path(artifact_name).suffix.lstrip(".") or "unknown"
            }
            if metadata:
                upload_metadata.update(metadata)
            
            # Convert content to bytes if needed
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            elif hasattr(content, 'read'):
                content_bytes = content.read()
            else:
                content_bytes = content
            
            # Upload to S3
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._upload_object_sync,
                key,
                content_bytes,
                content_type,
                upload_metadata
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
            
            logger.info(f"Uploaded artifact {artifact_name} for job {job_id} to {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload artifact {artifact_name} for job {job_id}: {str(e)}")
            raise

    async def download_artifact(
        self,
        job_id: str,
        artifact_name: str
    ) -> Optional[bytes]:
        """
        Download an artifact from S3.
        
        Args:
            job_id: Job identifier
            artifact_name: Name of the artifact file
            
        Returns:
            Artifact content as bytes, or None if not found
        """
        try:
            # Try to find the artifact (it could be in different date folders)
            key = await self._find_artifact_key(job_id, artifact_name)
            if not key:
                logger.warning(f"Artifact {artifact_name} not found for job {job_id}")
                return None
            
            # Download from S3
            content = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._download_object_sync,
                key
            )
            
            logger.info(f"Downloaded artifact {artifact_name} for job {job_id}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download artifact {artifact_name} for job {job_id}: {str(e)}")
            raise

    async def delete_artifact(
        self,
        job_id: str,
        artifact_name: str
    ) -> bool:
        """
        Delete an artifact from S3.
        
        Args:
            job_id: Job identifier
            artifact_name: Name of the artifact file
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # Find the artifact key
            key = await self._find_artifact_key(job_id, artifact_name)
            if not key:
                logger.warning(f"Artifact {artifact_name} not found for job {job_id}")
                return False
            
            # Delete from S3
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._delete_object_sync,
                key
            )
            
            logger.info(f"Deleted artifact {artifact_name} for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete artifact {artifact_name} for job {job_id}: {str(e)}")
            raise

    async def list_job_artifacts(
        self,
        job_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all artifacts for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            List of artifact information dictionaries
        """
        try:
            # List objects with job prefix
            prefix = f"{self.prefix}/"
            
            artifacts = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._list_objects_sync,
                prefix,
                job_id
            )
            
            logger.info(f"Found {len(artifacts)} artifacts for job {job_id}")
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to list artifacts for job {job_id}: {str(e)}")
            raise

    async def setup_lifecycle_policy(self) -> bool:
        """
        Set up S3 lifecycle policy for automatic artifact management.
        
        Returns:
            True if policy was set successfully
        """
        try:
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'MonteCarloArtifactLifecycle',
                        'Status': 'Enabled',
                        'Filter': {
                            'Prefix': f"{self.prefix}/"
                        },
                        'Transitions': [
                            {
                                'Days': self.lifecycle_days,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': self.lifecycle_days * 3,
                                'StorageClass': 'GLACIER'
                            }
                        ],
                        'Expiration': {
                            'Days': self.expiration_days
                        }
                    }
                ]
            }
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._put_lifecycle_configuration_sync,
                lifecycle_config
            )
            
            logger.info(f"Set up lifecycle policy for bucket {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up lifecycle policy: {str(e)}")
            return False

    def _upload_object_sync(
        self,
        key: str,
        content: bytes,
        content_type: str,
        metadata: Dict[str, str]
    ) -> None:
        """Synchronous S3 object upload"""
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=metadata
        )

    def _download_object_sync(self, key: str) -> bytes:
        """Synchronous S3 object download"""
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=key
        )
        return response['Body'].read()

    def _delete_object_sync(self, key: str) -> None:
        """Synchronous S3 object deletion"""
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=key
        )

    def _list_objects_sync(self, prefix: str, job_id: str) -> List[Dict[str, Any]]:
        """Synchronous S3 object listing"""
        artifacts = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                # Check if this object belongs to the job
                if f"/{job_id}/" in key:
                    artifact_name = Path(key).name
                    artifacts.append({
                        'name': artifact_name,
                        'key': key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
                    })
        
        return artifacts

    def _put_lifecycle_configuration_sync(self, lifecycle_config: Dict[str, Any]) -> None:
        """Synchronous lifecycle configuration setup"""
        self.s3_client.put_bucket_lifecycle_configuration(
            Bucket=self.bucket_name,
            LifecycleConfiguration=lifecycle_config
        )

    async def _find_artifact_key(self, job_id: str, artifact_name: str) -> Optional[str]:
        """Find the S3 key for an artifact by searching through date prefixes"""
        try:
            # Search in recent date folders (last 30 days)
            for days_back in range(30):
                date = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y/%m/%d")
                key = f"{self.prefix}/{date}/{job_id}/{artifact_name}"
                
                # Check if object exists
                exists = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._object_exists_sync,
                    key
                )
                
                if exists:
                    return key
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding artifact key: {str(e)}")
            return None

    def _object_exists_sync(self, key: str) -> bool:
        """Check if S3 object exists synchronously"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    async def cleanup(self) -> None:
        """Clean up resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        logger.info("S3 adapter cleanup completed")