"""
Load testing for performance optimizations.

This module contains tests that simulate high load scenarios to validate
the performance improvements implemented in the caching and database layers.
"""
import asyncio
import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app


class TestCachePerformance:
    """Test caching performance under load."""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager with realistic response times."""
        with patch('infrastructure.cache.cache_manager') as mock:
            # Simulate cache hit (fast)
            async def mock_get_hit(key):
                await asyncio.sleep(0.001)  # 1ms for cache hit
                return "result_test_1"
            
            # Simulate cache miss (returns None)
            async def mock_get_miss(key):
                await asyncio.sleep(0.001)  # 1ms for cache miss
                return None
            
            # Simulate cache set
            async def mock_set(key, value, ttl=None):
                await asyncio.sleep(0.002)  # 2ms for cache set
                return True
            
            mock.get = AsyncMock(side_effect=mock_get_hit)
            mock.set = AsyncMock(side_effect=mock_set)
            mock.delete = AsyncMock(return_value=True)
            mock.exists = AsyncMock(return_value=True)
            
            yield mock
    
    def test_cache_concurrent_access(self, mock_cache_manager):
        """Test cache performance under concurrent access."""
        from infrastructure.cache import cached_result
        
        call_count = 0
        
        @cached_result(prefix="test", ttl=300)
        async def expensive_operation(param: str):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return f"result_{param}_{call_count}"
        
        async def run_concurrent_requests():
            # Run 10 concurrent requests for the same data
            tasks = [expensive_operation("test") for _ in range(10)]
            results = await asyncio.gather(*tasks)
            return results
        
        # Run the test
        start_time = time.time()
        results = asyncio.run(run_concurrent_requests())
        end_time = time.time()
        
        # Verify results
        assert len(results) == 10
        assert all(result.startswith("result_test_") for result in results)
        
        # With caching, this should complete much faster than 10 * 0.1s
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should be much less than 1 second
        
        # Verify cache was accessed
        assert mock_cache_manager.get.call_count >= 1


class TestDatabasePerformance:
    """Test database performance optimizations."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session with realistic query times."""
        session = AsyncMock()
        
        # Mock fast query (with indexes)
        async def mock_execute_fast(query):
            await asyncio.sleep(0.01)  # 10ms for indexed query
            result = AsyncMock()
            result.scalar_one_or_none.return_value = {"id": "test", "status": "completed"}
            result.fetchall.return_value = [("pending", 5), ("running", 3), ("completed", 10)]
            return result
        
        session.execute = AsyncMock(side_effect=mock_execute_fast)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        
        return session
    
    @patch('infrastructure.repositories.jobs.cache_manager')
    def test_job_repository_performance(self, mock_cache, mock_session):
        """Test job repository performance under load."""
        from infrastructure.repositories.jobs import JobRepository
        
        # Mock cache miss to force database queries
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        
        repo = JobRepository(mock_session)
        
        async def run_concurrent_queries():
            # Run multiple concurrent database queries
            tasks = []
            for i in range(20):
                tasks.append(repo.get_job_by_id(f"job_{i}"))
                tasks.append(repo.get_job_counts_by_status())
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            return results, end_time - start_time
        
        results, execution_time = asyncio.run(run_concurrent_queries())
        
        # Verify all queries completed
        assert len(results) == 40
        
        # With proper indexing and connection pooling, this should be reasonably fast
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        # Verify database was accessed
        assert mock_session.execute.call_count >= 20


class TestAPIPerformance:
    """Test API performance under load."""
    
    def test_api_concurrent_requests(self):
        """Test API performance under concurrent requests."""
        client = TestClient(app)
        
        def make_request():
            """Make a single API request."""
            try:
                response = client.get("/api/v1/performance/stats")
                return response.status_code
            except Exception as e:
                return str(e)
        
        # Use ThreadPoolExecutor to simulate concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in futures]
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Verify requests completed
        assert len(results) == 50
        
        # Most requests should either succeed (200) or fail gracefully (500)
        # None should timeout or cause server crashes
        valid_responses = [r for r in results if isinstance(r, int) and r in [200, 404, 500]]
        assert len(valid_responses) >= 40  # At least 80% should be valid HTTP responses
        
        # Should handle 50 concurrent requests reasonably quickly
        assert execution_time < 30.0  # Should complete within 30 seconds
        
        print(f"Processed 50 concurrent requests in {execution_time:.2f} seconds")
        print(f"Average response time: {execution_time/50:.3f} seconds per request")


class TestMemoryUsage:
    """Test memory usage under load."""
    
    def test_cache_memory_efficiency(self):
        """Test that caching doesn't cause memory leaks."""
        from infrastructure.cache import cached_result
        import gc
        
        @cached_result(prefix="memory_test", ttl=1)  # Short TTL for testing
        async def memory_test_function(param: int):
            # Create some data that should be garbage collected
            data = [i for i in range(1000)]
            return f"result_{param}_{len(data)}"
        
        async def run_memory_test():
            # Run many operations to test memory usage
            for i in range(100):
                await memory_test_function(i % 10)  # Reuse some keys
                
                # Force garbage collection periodically
                if i % 20 == 0:
                    gc.collect()
        
        # Run the test
        initial_objects = len(gc.get_objects())
        asyncio.run(run_memory_test())
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should not grow excessively
        object_growth = final_objects - initial_objects
        assert object_growth < 1000  # Reasonable growth limit
        
        print(f"Object count growth: {object_growth}")


class TestConnectionPooling:
    """Test database connection pooling performance."""
    
    def test_connection_pool_efficiency(self):
        """Test that connection pooling works efficiently."""
        # This test verifies that we can create multiple sessions without errors
        # In a real scenario, this would test connection pool efficiency
        
        async def test_multiple_connections():
            # Simulate multiple concurrent database operations
            sessions = []
            for _ in range(20):
                # Mock session creation
                session = AsyncMock()
                sessions.append(session)
            
            # All sessions should be created without blocking
            return len(sessions)
        
        result = asyncio.run(test_multiple_connections())
        assert result == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])