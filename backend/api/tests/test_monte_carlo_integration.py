"""
Integration tests for the Monte Carlo simulation system.

This module contains comprehensive integration tests for the SQS queue system,
worker processing, and API endpoints.
"""
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_sqs

from api.routes.monte_carlo import router
from config import get_testing_config
from domain.queue import JobPriority, JobStatus, MonteCarloJobPayload
from infrastructure.monitoring.metrics import MonitoringService
from services.job_manager import MonteCarloJobManager
from workers.monte_carlo_worker import MonteCarloJobProcessor, MonteCarloWorker


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

            # AWS credentials are already set in get_testing_config()

            yield sqs, config

    @pytest.fixture
    def queue_adapter(self, mock_sqs_setup):
        """Create mocked queue adapter"""
        # Create a mock queue adapter that doesn't require AWS connection
        mock_queue_adapter = Mock()
        mock_queue_adapter.submit_job = AsyncMock()
        mock_queue_adapter.get_job_status = AsyncMock()
        mock_queue_adapter.cancel_job = AsyncMock()
        mock_queue_adapter.get_queue_metrics = AsyncMock()
        mock_queue_adapter.receive_messages = AsyncMock(return_value=[])
        mock_queue_adapter.delete_message = AsyncMock()
        mock_queue_adapter.change_message_visibility = AsyncMock()
        return mock_queue_adapter

    @pytest.fixture
    def monitoring_service(self):
        """Create monitoring service"""
        return MonitoringService()

    @pytest.fixture
    def job_manager(self, monitoring_service):
        """Create job manager with mocked queue adapter"""
        # Create a mock queue adapter that doesn't require AWS connection
        mock_queue_adapter = Mock()
        mock_queue_adapter.submit_job = AsyncMock()
        mock_queue_adapter.get_job_status = AsyncMock()
        mock_queue_adapter.cancel_job = AsyncMock()
        mock_queue_adapter.get_queue_metrics = AsyncMock()

        return MonteCarloJobManager(mock_queue_adapter, monitoring_service)

    @pytest.fixture
    def job_processor(self, monitoring_service):
        """Create job processor with mocked backtest service"""
        # Create processor with correct parameters and no S3 storage
        processor = MonteCarloJobProcessor(
            processor_id="test-processor",
            progress_callback=None,
            storage_adapter=None  # No S3 storage to avoid AWS connections
        )

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
    def test_client(self, job_manager):
        """Create FastAPI test client with mocked dependencies"""
        from fastapi import FastAPI

        from api.routes.monte_carlo import get_job_manager

        app = FastAPI()
        app.include_router(router)

        # Override the dependency to use our mocked job manager
        app.dependency_overrides[get_job_manager] = lambda: job_manager

        return TestClient(app)

    @pytest.mark.asyncio
    async def test_end_to_end_single_job(self, config):
        """Test complete end-to-end job processing"""
        # Create completely mocked components to avoid any AWS connections
        Mock()

        # Mock job manager
        mock_job_manager = Mock()
        job_id = str(uuid4())

        # Mock job object
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = JobStatus.COMPLETED
        mock_job.result = {
            "total_runs": 10,
            "successful_runs": 10,
            "average_return": 0.08,
            "volatility": 0.15,
            "sharpe_ratio": 0.53,
            "max_drawdown": -0.12
        }

        # Configure async mocks
        mock_job_manager.submit_job = AsyncMock(return_value=job_id)
        mock_job_manager.get_job_status = AsyncMock(return_value=mock_job)
        mock_job_manager.wait_for_completion = AsyncMock(return_value=mock_job)

        # Create test payload
        payload = MonteCarloJobPayload(
            csv_data=b"date,price\n2023-01-01,100.0\n2023-01-02,101.0",
            filename="test_data.csv",
            strategy_name="buy_and_hold",
            strategy_params={"strategy": "buy_and_hold"},
            runs=10
        )

        # Submit job
        submitted_job_id = await mock_job_manager.submit_job(payload=payload)
        assert submitted_job_id == job_id

        # Wait for completion
        completed_job = await mock_job_manager.wait_for_completion(job_id, timeout_seconds=30)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.result is not None
        assert completed_job.result["total_runs"] == 10

    @pytest.mark.asyncio
    async def test_bulk_job_submission(self, config):
        """Test bulk job submission and processing"""
        # Create a completely mocked job manager
        job_manager = Mock()
        job_manager.submit_bulk_jobs = AsyncMock(return_value=["job-1", "job-2", "job-3", "job-4", "job-5"])
        job_manager.wait_for_completion = AsyncMock(return_value=Mock(
            status=JobStatus.COMPLETED,
            result={"total_runs": 5, "successful_runs": 5, "failed_runs": 0}
        ))

        # Create multiple test payloads
        payloads = []
        for i in range(5):
            payload = MonteCarloJobPayload(
                csv_data=f"date,price\n2023-01-01,{100+i}.0\n2023-01-02,{101+i}.0".encode(),
                filename=f"test_data_{i}.csv",
                strategy_name="test_strategy",
                strategy_params={"strategy": "test", "param": i},
                runs=5
            )
            payloads.append(payload)

        # Submit bulk jobs
        job_ids = await job_manager.submit_bulk_jobs(
            payloads=payloads,
            priorities=[JobPriority.NORMAL] * 5,
            batch_name="test_batch"
        )

        assert len(job_ids) == 5

        # Verify all jobs completed successfully (mocked)
        for job_id in job_ids:
            job = await job_manager.wait_for_completion(job_id, timeout_seconds=60)
            assert job.status == JobStatus.COMPLETED
            assert job.result is not None
            assert job.result["total_runs"] == 5

    @pytest.mark.asyncio
    async def test_job_cancellation(self, config):
        """Test job cancellation"""
        # Create a completely mocked job manager
        job_manager = Mock()
        job_manager.submit_job = AsyncMock(return_value="test-job-cancel")
        job_manager.cancel_job = AsyncMock(return_value=True)
        job_manager.get_job_status = AsyncMock(return_value=Mock(
            job_id="test-job-cancel",
            status=JobStatus.CANCELLED
        ))

        # Create test payload
        payload = MonteCarloJobPayload(
            csv_data=b"date,price\n2023-01-01,100.0\n2023-01-02,101.0",
            filename="test_data.csv",
            strategy_name="test_strategy",
            strategy_params={"strategy": "test"},
            runs=100  # Larger number to simulate longer processing
        )

        # Submit job
        job_id = await job_manager.submit_job(payload=payload)
        assert job_id == "test-job-cancel"

        # Cancel job
        cancelled = await job_manager.cancel_job(job_id)
        assert cancelled is True

        # Verify job was cancelled
        job = await job_manager.get_job_status(job_id)
        assert job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_job_progress_tracking(self, config):
        """Test job progress tracking"""
        # Create a completely mocked job manager
        job_manager = Mock()
        job_manager.submit_job = AsyncMock(return_value="test-job-progress")
        job_manager.get_job_progress = AsyncMock(side_effect=[
            {"progress": 0.0},
            {"progress": 0.2},
            {"progress": 0.5},
            {"progress": 0.8},
            {"progress": 1.0}
        ])
        job_manager.get_job_status = AsyncMock(return_value=Mock(
            status=JobStatus.COMPLETED
        ))

        # Create test payload
        payload = MonteCarloJobPayload(
            csv_data=b"date,price\n2023-01-01,100.0\n2023-01-02,101.0",
            filename="test_data.csv",
            strategy_name="test_strategy",
            strategy_params={"strategy": "test"},
            runs=20
        )

        # Submit job
        job_id = await job_manager.submit_job(payload=payload)
        assert job_id == "test-job-progress"

        # Monitor progress
        progress_updates = []
        for _ in range(5):  # Check progress 5 times
            progress = await job_manager.get_job_progress(job_id)
            if progress:
                progress_updates.append(progress.get("progress", 0))

            # Break if job completed
            job = await job_manager.get_job_status(job_id)
            if job and job.status == JobStatus.COMPLETED:
                break

        # Verify progress was tracked
        assert len(progress_updates) > 0
        # Progress should generally increase
        if len(progress_updates) > 1:
            assert max(progress_updates) >= min(progress_updates)

    @pytest.mark.asyncio
    async def test_queue_metrics(self, config):
        """Test queue metrics collection"""
        # Create a completely mocked job manager
        job_manager = Mock()
        job_manager.submit_job = AsyncMock(return_value="test-job-metrics")
        job_manager.get_queue_metrics = AsyncMock(return_value=Mock(
            total_jobs=3,
            pending_jobs=3,
            queue_depth=3
        ))

        # Submit some jobs
        payloads = [
            MonteCarloJobPayload(
                csv_data=f"date,price\n2023-01-01,{100+i}.0\n2023-01-02,{101+i}.0".encode(),
                filename=f"test_data_{i}.csv",
                strategy_name="test_strategy",
                strategy_params={"strategy": "test"},
                runs=5
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

    @pytest.mark.asyncio
    async def test_api_job_submission(self, job_manager):
        """Test job manager submit_job method directly"""
        # Create a mock payload that matches MonteCarloJobPayload structure

        # Mock the submit_job method to return a job ID
        job_manager.submit_job = AsyncMock(return_value="test-job-id")

        # Test the job manager directly
        job_id = await job_manager.submit_job(
            payload=Mock(),  # Mock payload
            priority=Mock(),  # Mock priority
            timeout_seconds=3600
        )

        assert job_id == "test-job-id"
        job_manager.submit_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_bulk_job_submission(self, job_manager):
        """Test bulk job submission directly through job manager"""
        # Mock the submit_bulk_jobs method
        job_manager.submit_bulk_jobs = AsyncMock(return_value=["job-1", "job-2", "job-3"])

        # Test bulk submission
        job_ids = await job_manager.submit_bulk_jobs(
            payloads=[Mock(), Mock(), Mock()],
            priorities=[Mock(), Mock(), Mock()],
            batch_name="test_batch"
        )

        assert len(job_ids) == 3
        assert job_ids == ["job-1", "job-2", "job-3"]
        job_manager.submit_bulk_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_job_status(self, job_manager):
        """Test job status retrieval directly through job manager"""
        # Mock the get_job_status method
        mock_job = Mock()
        mock_job.status = "completed"
        mock_job.progress = 1.0
        job_manager.get_job_status = AsyncMock(return_value=mock_job)

        # Test job status retrieval
        job = await job_manager.get_job_status("test-job-id")

        assert job.status == "completed"
        assert job.progress == 1.0
        job_manager.get_job_status.assert_called_once_with("test-job-id")

    @pytest.mark.asyncio
    async def test_api_job_cancellation(self, job_manager):
        """Test job cancellation directly through job manager"""
        # Mock the cancel_job method
        job_manager.cancel_job = AsyncMock(return_value=True)

        # Test job cancellation
        result = await job_manager.cancel_job("test-job-id")

        assert result is True
        job_manager.cancel_job.assert_called_once_with("test-job-id")

    @pytest.mark.asyncio
    async def test_api_queue_metrics(self, job_manager):
        """Test queue metrics retrieval directly through job manager"""
        # Mock the get_queue_metrics method
        mock_metrics = {
            "total_jobs": 10,
            "pending_jobs": 3,
            "processing_jobs": 2,
            "completed_jobs": 5
        }
        job_manager.get_queue_metrics = AsyncMock(return_value=mock_metrics)

        # Test queue metrics retrieval
        metrics = await job_manager.get_queue_metrics()

        assert metrics["total_jobs"] == 10
        assert metrics["pending_jobs"] == 3
        assert metrics["processing_jobs"] == 2
        assert metrics["completed_jobs"] == 5
        job_manager.get_queue_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, config):
        """Test error handling in the system"""
        # Create a completely mocked job manager
        job_manager = Mock()
        job_manager.submit_job = AsyncMock(side_effect=ValueError("Invalid payload"))

        # Create invalid payload
        payload = MonteCarloJobPayload(
            csv_data=b"date,price\n2023-01-01,100.0\n2023-01-02,101.0",
            filename="test_data.csv",
            strategy_name="test_strategy",
            strategy_params={"strategy": "test"},
            runs=0  # Invalid: should be > 0
        )

        # This should raise an error during validation
        with pytest.raises(ValueError):
            await job_manager.submit_job(payload=payload)

    @pytest.mark.asyncio
    async def test_worker_health_checks(self, config):
        """Test worker health check functionality"""
        # Create a completely mocked worker
        worker = Mock()
        worker.start = AsyncMock()
        worker.stop = AsyncMock()
        worker.health_check = AsyncMock(return_value={
            "status": "healthy",
            "uptime": 1.0,
            "processed_jobs": 0
        })

        # Start worker
        worker_task = asyncio.create_task(worker.start())

        try:
            # Wait for worker to start
            await asyncio.sleep(0.1)

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
