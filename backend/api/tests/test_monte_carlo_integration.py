"""
Integration tests for the Monte Carlo simulation system.

This module contains comprehensive integration tests for the SQS queue system,
worker processing, and API endpoints.
"""
import asyncio
import json
import os
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

import boto3
from moto import mock_sqs
from fastapi.testclient import TestClient

from src.domain.queue import JobStatus, JobPriority, MonteCarloJobPayload
from src.infrastructure.queue.sqs_adapter import SQSQueueAdapter
from src.infrastructure.monitoring.metrics import MonitoringService
from src.services.job_manager import MonteCarloJobManager
from src.workers.monte_carlo_worker import MonteCarloWorker, MonteCarloJobProcessor
from src.config import get_testing_config
from src.api.routes.monte_carlo import router


class TestMonteCarloIntegration:
    """Integration tests for Monte Carlo simulation system"""
    
    @pytest.fixture
    def config(self):
        """Get testing configuration"""
        return get_testing_config()
    
    @pytest.fixture
    def mock_sqs_setup(self, config):
        """Set up mock SQS environment"""
        with mock_sqs():
            # Create SQS client
            sqs = boto3.client(
                'sqs',
                region_name=config.sqs.region_name,
                endpoint_url=config.sqs.endpoint_url,
                aws_access_key_id='testing',
                aws_secret_access_key='testing'
            )
            
            # Create main queue
            queue_response = sqs.create_queue(
                QueueName='test-monte-carlo-jobs',
                Attributes={
                    'VisibilityTimeout': str(config.sqs.visibility_timeout),
                    'MessageRetentionPeriod': str(config.sqs.message_retention_period)
                }
            )
            
            # Create dead letter queue
            dlq_response = sqs.create_queue(
                QueueName='test-monte-carlo-jobs-dlq',
                Attributes={
                    'MessageRetentionPeriod': str(config.sqs.message_retention_period)
                }
            )
            
            # Update config with actual URLs
            config.sqs.queue_url = queue_response['QueueUrl']
            config.sqs.dead_letter_queue_url = dlq_response['QueueUrl']
            
            yield sqs, config
    
    @pytest.fixture
    def queue_adapter(self, mock_sqs_setup):
        """Create SQS queue adapter"""
        sqs, config = mock_sqs_setup
        return SQSQueueAdapter(config.sqs)
    
    @pytest.fixture
    def monitoring_service(self):
        """Create monitoring service"""
        return MonitoringService()
    
    @pytest.fixture
    def job_manager(self, queue_adapter, monitoring_service):
        """Create job manager"""
        return MonteCarloJobManager(queue_adapter, monitoring_service)
    
    @pytest.fixture
    def job_processor(self, monitoring_service):
        """Create job processor with mocked backtest service"""
        processor = MonteCarloJobProcessor(monitoring_service)
        
        # Mock the backtest service
        async def mock_run_monte_carlo(payload, progress_callback=None):
            """Mock Monte Carlo simulation"""
            total_runs = payload.num_runs
            
            for i in range(total_runs):
                if progress_callback:
                    await progress_callback(i / total_runs, f"Run {i+1}/{total_runs}")
                await asyncio.sleep(0.01)  # Simulate work
            
            return {
                "total_runs": total_runs,
                "successful_runs": total_runs,
                "average_return": 0.08,
                "volatility": 0.15,
                "sharpe_ratio": 0.53,
                "max_drawdown": -0.12,
                "final_portfolio_values": [100000 + i * 1000 for i in range(total_runs)]
            }
        
        processor._run_monte_carlo_simulation = mock_run_monte_carlo
        return processor
    
    @pytest.fixture
    def worker(self, queue_adapter, job_processor, config):
        """Create Monte Carlo worker"""
        return MonteCarloWorker(
            queue=queue_adapter,
            processor=job_processor,
            config=config.worker
        )
    
    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client"""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_end_to_end_single_job(self, job_manager, worker, config):
        """Test complete end-to-end flow for a single job"""
        # Create test payload
        payload = MonteCarloJobPayload(
            symbol="AAPL",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            num_runs=10,
            initial_capital=100000.0,
            strategy_params={"strategy": "buy_and_hold"}
        )
        
        # Submit job
        job_id = await job_manager.submit_job(
            payload=payload,
            priority=JobPriority.HIGH,
            timeout_seconds=300
        )
        
        assert job_id is not None
        
        # Start worker in background
        worker_task = asyncio.create_task(worker.start())
        
        try:
            # Wait for job completion
            job = await job_manager.wait_for_completion(job_id, timeout_seconds=30)
            
            assert job is not None
            assert job.status == JobStatus.COMPLETED
            assert job.result is not None
            assert job.result["total_runs"] == 10
            assert job.result["successful_runs"] == 10
            assert "average_return" in job.result
            
        finally:
            # Stop worker
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_bulk_job_submission(self, job_manager, worker, config):
        """Test bulk job submission and processing"""
        # Create multiple test payloads
        payloads = []
        for i in range(5):
            payload = MonteCarloJobPayload(
                symbol=f"STOCK{i}",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                num_runs=5,
                initial_capital=100000.0,
                strategy_params={"strategy": "test", "param": i}
            )
            payloads.append(payload)
        
        # Submit bulk jobs
        job_ids = await job_manager.submit_bulk_jobs(
            payloads=payloads,
            priorities=[JobPriority.MEDIUM] * 5,
            batch_name="test_batch"
        )
        
        assert len(job_ids) == 5
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        try:
            # Wait for all jobs to complete
            completed_jobs = []
            for job_id in job_ids:
                job = await job_manager.wait_for_completion(job_id, timeout_seconds=60)
                completed_jobs.append(job)
            
            # Verify all jobs completed successfully
            for job in completed_jobs:
                assert job.status == JobStatus.COMPLETED
                assert job.result is not None
                assert job.result["total_runs"] == 5
            
        finally:
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_job_cancellation(self, job_manager, worker, config):
        """Test job cancellation functionality"""
        # Create long-running job
        payload = MonteCarloJobPayload(
            symbol="AAPL",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            num_runs=1000,  # Large number to ensure it runs long enough
            initial_capital=100000.0,
            strategy_params={"strategy": "test"}
        )
        
        # Submit job
        job_id = await job_manager.submit_job(payload=payload)
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        try:
            # Wait a bit for job to start
            await asyncio.sleep(1)
            
            # Cancel job
            success = await job_manager.cancel_job(job_id)
            assert success
            
            # Verify job is cancelled
            await asyncio.sleep(2)
            job = await job_manager.get_job_status(job_id)
            assert job.status in [JobStatus.CANCELLED, JobStatus.FAILED]
            
        finally:
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_job_progress_tracking(self, job_manager, worker, config):
        """Test job progress tracking"""
        # Create test payload
        payload = MonteCarloJobPayload(
            symbol="AAPL",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            num_runs=20,
            initial_capital=100000.0,
            strategy_params={"strategy": "test"}
        )
        
        # Submit job
        job_id = await job_manager.submit_job(payload=payload)
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        try:
            # Monitor progress
            progress_updates = []
            for _ in range(10):  # Check progress 10 times
                await asyncio.sleep(0.5)
                progress = await job_manager.get_job_progress(job_id)
                if progress:
                    progress_updates.append(progress.get("progress", 0))
                
                # Break if job completed
                job = await job_manager.get_job_status(job_id)
                if job and job.status == JobStatus.COMPLETED:
                    break
            
            # Verify progress was tracked
            assert len(progress_updates) > 0
            # Progress should generally increase (allowing for some variance)
            if len(progress_updates) > 1:
                assert max(progress_updates) > min(progress_updates)
            
        finally:
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_queue_metrics(self, job_manager, queue_adapter):
        """Test queue metrics collection"""
        # Submit some jobs
        payloads = [
            MonteCarloJobPayload(
                symbol=f"TEST{i}",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                num_runs=5,
                initial_capital=100000.0,
                strategy_params={}
            )
            for i in range(3)
        ]
        
        job_ids = []
        for payload in payloads:
            job_id = await job_manager.submit_job(payload=payload)
            job_ids.append(job_id)
        
        # Get metrics
        metrics = await job_manager.get_queue_metrics()
        
        assert metrics.total_jobs >= 3
        assert metrics.pending_jobs >= 3
        assert metrics.queue_depth >= 3
    
    def test_api_job_submission(self, test_client):
        """Test API endpoint for job submission"""
        job_data = {
            "symbol": "AAPL",
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-12-31T00:00:00",
            "num_runs": 10,
            "initial_capital": 100000.0,
            "strategy_params": {"strategy": "test"},
            "priority": "medium"
        }
        
        with patch('src.api.routes.monte_carlo.get_job_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.submit_job.return_value = "test-job-id"
            mock_get_manager.return_value = mock_manager
            
            response = test_client.post("/monte-carlo/jobs", json=job_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["job_id"] == "test-job-id"
            assert data["status"] == "pending"
    
    def test_api_bulk_job_submission(self, test_client):
        """Test API endpoint for bulk job submission"""
        bulk_data = {
            "batch_name": "test_batch",
            "jobs": [
                {
                    "symbol": f"STOCK{i}",
                    "start_date": "2023-01-01T00:00:00",
                    "end_date": "2023-12-31T00:00:00",
                    "num_runs": 5,
                    "initial_capital": 100000.0,
                    "strategy_params": {},
                    "priority": "medium"
                }
                for i in range(3)
            ]
        }
        
        with patch('src.api.routes.monte_carlo.get_job_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.submit_bulk_jobs.return_value = ["job1", "job2", "job3"]
            mock_get_manager.return_value = mock_manager
            
            response = test_client.post("/monte-carlo/jobs/bulk", json=bulk_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["total_jobs"] == 3
            assert data["successful_submissions"] == 3
            assert len(data["jobs"]) == 3
    
    def test_api_job_status(self, test_client):
        """Test API endpoint for job status"""
        with patch('src.api.routes.monte_carlo.get_job_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_job = Mock()
            mock_job.id = "test-job-id"
            mock_job.status = JobStatus.COMPLETED
            mock_job.created_at = datetime.utcnow()
            mock_job.updated_at = datetime.utcnow()
            mock_job.result = {"total_runs": 10}
            mock_job.error_message = None
            mock_job.metadata.progress = 1.0
            mock_job.metadata.to_dict.return_value = {"progress": 1.0}
            
            mock_manager.get_job_status.return_value = mock_job
            mock_get_manager.return_value = mock_manager
            
            response = test_client.get("/monte-carlo/jobs/test-job-id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-id"
            assert data["status"] == "completed"
            assert data["result"]["total_runs"] == 10
    
    def test_api_job_cancellation(self, test_client):
        """Test API endpoint for job cancellation"""
        with patch('src.api.routes.monte_carlo.get_job_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.cancel_job.return_value = True
            mock_get_manager.return_value = mock_manager
            
            response = test_client.delete("/monte-carlo/jobs/test-job-id")
            
            assert response.status_code == 204
    
    def test_api_queue_metrics(self, test_client):
        """Test API endpoint for queue metrics"""
        with patch('src.api.routes.monte_carlo.get_job_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_metrics = Mock()
            mock_metrics.total_jobs = 100
            mock_metrics.pending_jobs = 10
            mock_metrics.running_jobs = 5
            mock_metrics.completed_jobs = 80
            mock_metrics.failed_jobs = 5
            mock_metrics.average_processing_time = 120.5
            mock_metrics.queue_depth = 15
            mock_metrics.worker_count = 3
            
            mock_manager.get_queue_metrics.return_value = mock_metrics
            mock_get_manager.return_value = mock_manager
            
            response = test_client.get("/monte-carlo/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_jobs"] == 100
            assert data["pending_jobs"] == 10
            assert data["running_jobs"] == 5
            assert data["completed_jobs"] == 80
            assert data["failed_jobs"] == 5
    
    @pytest.mark.asyncio
    async def test_error_handling(self, job_manager, worker, config):
        """Test error handling in the system"""
        # Create invalid payload (this would need to be implemented based on validation rules)
        payload = MonteCarloJobPayload(
            symbol="INVALID",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            num_runs=0,  # Invalid: should be > 0
            initial_capital=100000.0,
            strategy_params={}
        )
        
        # This should raise an error during validation
        with pytest.raises(Exception):
            await job_manager.submit_job(payload=payload)
    
    @pytest.mark.asyncio
    async def test_worker_health_checks(self, worker):
        """Test worker health check functionality"""
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        try:
            # Wait for worker to start
            await asyncio.sleep(1)
            
            # Check worker health
            health = await worker.health_check()
            assert health["status"] == "healthy"
            assert "uptime" in health
            assert "processed_jobs" in health
            
        finally:
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])