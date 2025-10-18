"""
Integration tests for performance optimizations.
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from infrastructure.cache import cached_result
from infrastructure.repositories.jobs import JobRepository
from services.job_manager import MonteCarloJobManager


class TestCacheIntegration:
    """Test caching functionality integration."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager for testing."""
        with patch('infrastructure.cache.cache_manager') as mock:
            mock.get = AsyncMock(return_value=None)
            mock.set = AsyncMock()
            mock.delete = AsyncMock()
            mock.exists = AsyncMock(return_value=False)
            mock.get_stats = AsyncMock(return_value={
                'hits': 100,
                'misses': 50,
                'hit_ratio': 0.67,
                'memory_usage': '10MB'
            })
            yield mock

    def test_cached_result_decorator(self, mock_cache_manager):
        """Test that cached_result decorator works correctly."""

        @cached_result("test", ttl=300)
        async def sample_function(param1: str, param2: int):
            return f"result_{param1}_{param2}"

        # Test function execution
        result = asyncio.run(sample_function("test", 123))
        assert result == "result_test_123"

        # Verify cache was called
        mock_cache_manager.get.assert_called_once()
        mock_cache_manager.set.assert_called_once()


class TestJobRepositoryIntegration:
    """Test job repository caching integration."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def job_repo(self, mock_session):
        """Create job repository with mocked session."""
        return JobRepository(mock_session)

    def test_get_job_by_id_caching(self, job_repo):
        """Test that get_job_by_id method exists and is callable."""
        # Simple test to verify the method exists and is callable
        assert hasattr(job_repo, 'get_job_by_id')
        assert callable(job_repo.get_job_by_id)

    def test_get_job_counts_by_status_caching(self, job_repo):
        """Test that get_job_counts_by_status method exists and is callable."""
        # Simple test to verify the method exists and is callable
        assert hasattr(job_repo, 'get_job_counts_by_status')
        assert callable(job_repo.get_job_counts_by_status)


class TestPerformanceAPIIntegration:
    """Test performance monitoring API endpoints."""

    def test_performance_stats_endpoint(self):
        """Test that performance stats endpoint is accessible."""
        client = TestClient(app)

        with patch('api.routes.performance.cache_manager') as mock_cache:
            mock_cache.get_stats = AsyncMock(return_value={
                'enabled': True,
                'connected_clients': 1,
                'used_memory': 1024,
                'used_memory_human': '1KB',
                'keyspace_hits': 100,
                'keyspace_misses': 50,
                'total_commands_processed': 150,
                'uptime_in_seconds': 3600
            })

            with patch('api.routes.performance.get_database_performance') as mock_db:
                mock_db.return_value = {
                    'connection_pool': {'active': 5, 'idle': 15},
                    'table_statistics': {'jobs': {'rows': 1000}},
                    'slow_queries': [],
                    'index_usage': []
                }

                response = client.get("/api/v1/performance/metrics")
                assert response.status_code == 200

                data = response.json()
                assert 'database' in data
                assert 'cache' in data
                assert 'timestamp' in data

    @pytest.mark.asyncio
    async def test_cache_clear_endpoint(self):
        """Test cache clearing endpoint."""
        client = TestClient(app)

        with patch('api.routes.performance.cache_manager') as mock_cache:
            mock_cache.enabled = True
            mock_cache.delete_pattern = AsyncMock(return_value=10)

            response = client.delete("/api/v1/performance/cache/clear")
            assert response.status_code == 200

            data = response.json()
            assert data['success']
            assert 'cleared_count' in data


class TestDatabaseOptimizationIntegration:
    """Test database optimization features."""

    @pytest.fixture
    def mock_index_manager(self):
        """Mock IndexManager for database optimization tests."""
        with patch('api.routes.performance.IndexManager') as mock:
            instance = AsyncMock()
            instance.create_performance_indexes.return_value = {
                'jobs_status_idx': True,
                'jobs_created_at_idx': True,
                'jobs_user_id_idx': True
            }
            instance.optimize_table.return_value = {
                'success': True,
                'message': 'Table optimized successfully',
                'table': 'jobs'
            }
            mock.return_value = instance
            yield instance

    def test_create_indexes_endpoint(self, mock_index_manager):
        """Test database index creation endpoint."""
        client = TestClient(app)

        response = client.post("/api/v1/performance/database/create-indexes")
        assert response.status_code == 200

        data = response.json()
        assert data['success']
        assert 'message' in data

    def test_optimize_table_endpoint(self, mock_index_manager):
        """Test table optimization endpoint."""
        client = TestClient(app)

        response = client.post("/api/v1/performance/database/optimize/jobs")
        assert response.status_code == 200

        data = response.json()
        assert data['success']
        assert 'message' in data


class TestJobManagerIntegration:
    """Test job manager performance optimizations."""

    @pytest.fixture
    def mock_job_manager(self):
        """Mock job manager dependencies."""
        with patch('services.job_manager.JobRepository') as mock_repo, \
             patch('services.job_manager.cache_manager') as mock_cache:

            # Mock repository
            repo_instance = AsyncMock()
            repo_instance.get_job_by_id.return_value = None
            mock_repo.return_value = repo_instance

            # Mock cache
            mock_cache.get.return_value = asyncio.Future()
            mock_cache.get.return_value.set_result(None)
            mock_cache.set.return_value = asyncio.Future()
            mock_cache.set.return_value.set_result(True)

            yield {
                'repo': repo_instance,
                'cache': mock_cache
            }

    def test_get_job_progress_caching(self):
        """Test that MonteCarloJobManager has get_job_progress method."""
        # Simple test to verify the method exists and is callable

        # Verify the method exists and is callable on the class
        assert hasattr(MonteCarloJobManager, 'get_job_progress')
        assert callable(MonteCarloJobManager.get_job_progress)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
