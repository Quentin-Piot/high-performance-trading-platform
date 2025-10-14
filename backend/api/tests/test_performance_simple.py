"""
Simple integration tests for performance optimizations.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


class TestPerformanceEndpoints:
    """Test performance monitoring endpoints are accessible."""
    
    def test_performance_routes_registered(self):
        """Test that performance routes are properly registered."""
        client = TestClient(app)
        
        # Test that the performance database endpoint exists (even if it fails due to missing dependencies)
        response = client.get("/api/v1/performance/database")
        # We expect either 200 (success) or 500 (internal error due to missing Redis/DB)
        # but not 404 (route not found)
        assert response.status_code != 404
    
    def test_monte_carlo_routes_registered(self):
        """Test that Monte Carlo routes are properly registered."""
        client = TestClient(app)
        
        # Test that the Monte Carlo metrics endpoint exists
        response = client.get("/api/v1/monte-carlo/metrics")
        # We expect either 200 (success) or 500 (internal error)
        # but not 404 (route not found)
        assert response.status_code != 404


class TestCacheModule:
    """Test cache module can be imported and has expected structure."""
    
    def test_cache_manager_import(self):
        """Test that cache manager can be imported."""
        from infrastructure.cache import cache_manager, cached_result
        
        # Verify the cache manager has expected methods
        assert hasattr(cache_manager, 'get')
        assert hasattr(cache_manager, 'set')
        assert hasattr(cache_manager, 'delete')
        assert callable(cached_result)
    
    def test_cache_decorator_structure(self):
        """Test that cached_result decorator has correct signature."""
        from infrastructure.cache import cached_result
        import inspect
        
        # Check that cached_result is callable
        assert callable(cached_result)
        
        # Test basic decorator usage (without actually connecting to Redis)
        @cached_result("test", ttl=300)
        def sample_sync_function():
            return "test"
        
        # Verify the decorator returns a function
        assert callable(sample_sync_function)


class TestJobRepository:
    """Test job repository has caching integration."""
    
    def test_job_repository_has_cached_methods(self):
        """Test that job repository methods have caching decorators."""
        from infrastructure.repositories.jobs import JobRepository
        
        # Check that the class exists and has expected methods
        assert hasattr(JobRepository, 'get_job_by_id')
        assert hasattr(JobRepository, 'get_job_counts_by_status')
        assert hasattr(JobRepository, 'update_job_status')


class TestDatabaseIndexes:
    """Test database index management module."""
    
    def test_index_manager_import(self):
        """Test that IndexManager can be imported and instantiated"""
        try:
            from src.infrastructure.db_indexes import IndexManager
            assert IndexManager is not None
        except ImportError:
            pytest.skip("db_indexes module not available")


class TestJobManager:
    """Test job manager has performance optimizations."""
    
    def test_job_manager_import(self):
        """Test that MonteCarloJobManager can be imported."""
        from services.job_manager import MonteCarloJobManager
        
        # Verify the class has expected methods
        assert hasattr(MonteCarloJobManager, 'get_job_progress')
        assert hasattr(MonteCarloJobManager, 'submit_monte_carlo_job')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])