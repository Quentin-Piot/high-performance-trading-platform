"""
Performance monitoring API endpoints.

This module provides endpoints for monitoring database performance,
cache statistics, and system metrics.
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from infrastructure.db import get_session, get_pool_status
from infrastructure.db_indexes import IndexManager, analyze_database_performance
from infrastructure.cache import cache_manager
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics"""
    connection_pool: Dict[str, Any]
    table_statistics: Dict[str, Any]
    slow_queries: List[Dict[str, Any]]
    index_usage: List[Dict[str, Any]]


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics"""
    enabled: bool
    connected_clients: int = 0
    used_memory: int = 0
    used_memory_human: str = "0B"
    keyspace_hits: int = 0
    keyspace_misses: int = 0
    total_commands_processed: int = 0
    uptime_in_seconds: int = 0
    hit_ratio: float = 0.0


class PerformanceMetricsResponse(BaseModel):
    """Response model for comprehensive performance metrics"""
    database: DatabaseStatsResponse
    cache: CacheStatsResponse
    timestamp: str


@router.get("/database", response_model=DatabaseStatsResponse)
async def get_database_performance(
    session: AsyncSession = Depends(get_session)
) -> DatabaseStatsResponse:
    """
    Get comprehensive database performance metrics.
    
    Returns:
        Database performance statistics including connection pool,
        table statistics, slow queries, and index usage
    """
    try:
        # Get connection pool status
        pool_status = await get_pool_status()
        
        # Get comprehensive database analysis
        performance_data = await analyze_database_performance(session)
        
        return DatabaseStatsResponse(
            connection_pool=pool_status,
            table_statistics=performance_data.get("table_statistics", {}),
            slow_queries=performance_data.get("slow_queries", []),
            index_usage=performance_data.get("index_usage", [])
        )
        
    except Exception as e:
        logger.error("Failed to get database performance metrics", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database performance metrics"
        )


@router.get("/cache", response_model=CacheStatsResponse)
async def get_cache_performance() -> CacheStatsResponse:
    """
    Get cache performance metrics.
    
    Returns:
        Cache statistics including hit ratio, memory usage, and connection info
    """
    try:
        stats = await cache_manager.get_stats()
        
        # Calculate hit ratio
        hits = stats.get("keyspace_hits", 0)
        misses = stats.get("keyspace_misses", 0)
        total_requests = hits + misses
        hit_ratio = (hits / total_requests) if total_requests > 0 else 0.0
        
        return CacheStatsResponse(
            enabled=stats.get("enabled", False),
            connected_clients=stats.get("connected_clients", 0),
            used_memory=stats.get("used_memory", 0),
            used_memory_human=stats.get("used_memory_human", "0B"),
            keyspace_hits=hits,
            keyspace_misses=misses,
            total_commands_processed=stats.get("total_commands_processed", 0),
            uptime_in_seconds=stats.get("uptime_in_seconds", 0),
            hit_ratio=hit_ratio
        )
        
    except Exception as e:
        logger.error("Failed to get cache performance metrics", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache performance metrics"
        )


@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    session: AsyncSession = Depends(get_session)
) -> PerformanceMetricsResponse:
    """
    Get comprehensive performance metrics for database and cache.
    
    Returns:
        Complete performance metrics including database and cache statistics
    """
    try:
        from datetime import datetime
        
        # Get database and cache metrics concurrently
        import asyncio
        
        db_task = get_database_performance(session)
        cache_task = get_cache_performance()
        
        db_stats, cache_stats = await asyncio.gather(db_task, cache_task)
        
        return PerformanceMetricsResponse(
            database=db_stats,
            cache=cache_stats,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("Failed to get performance metrics", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.post("/database/optimize/{table_name}")
async def optimize_table(
    table_name: str,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Optimize a specific database table.
    
    Args:
        table_name: Name of the table to optimize
        
    Returns:
        Optimization results
    """
    try:
        # Validate table name to prevent SQL injection
        allowed_tables = ["jobs", "users"]
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table '{table_name}' is not allowed for optimization"
            )
        
        index_manager = IndexManager(session)
        result = await index_manager.optimize_table(table_name)
        
        logger.info("Table optimization completed", extra={
            "table_name": table_name,
            "success": result.get("success", False)
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to optimize table", extra={
            "table_name": table_name,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize table '{table_name}'"
        )


@router.post("/database/create-indexes")
async def create_performance_indexes(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Create performance-optimized database indexes.
    
    Returns:
        Index creation results
    """
    try:
        index_manager = IndexManager(session)
        results = await index_manager.create_performance_indexes()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info("Performance indexes creation completed", extra={
            "success_count": success_count,
            "total_count": total_count,
            "results": results
        })
        
        return {
            "success": True,
            "message": f"Created {success_count}/{total_count} indexes successfully",
            "results": results
        }
        
    except Exception as e:
        logger.error("Failed to create performance indexes", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create performance indexes"
        )


@router.delete("/cache/clear")
async def clear_cache() -> Dict[str, Any]:
    """
    Clear all cache entries.
    
    Returns:
        Cache clearing results
    """
    try:
        if not cache_manager.enabled:
            return {
                "success": False,
                "message": "Cache is not enabled"
            }
        
        # Clear all cache entries
        cleared_count = await cache_manager.delete_pattern("*")
        
        logger.info("Cache cleared", extra={
            "cleared_count": cleared_count
        })
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cache entries",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error("Failed to clear cache", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.delete("/cache/pattern/{pattern}")
async def clear_cache_pattern(pattern: str) -> Dict[str, Any]:
    """
    Clear cache entries matching a pattern.
    
    Args:
        pattern: Redis pattern to match (e.g., "job:*", "user:*")
        
    Returns:
        Cache clearing results
    """
    try:
        if not cache_manager.enabled:
            return {
                "success": False,
                "message": "Cache is not enabled"
            }
        
        # Clear cache entries matching pattern
        cleared_count = await cache_manager.delete_pattern(pattern)
        
        logger.info("Cache pattern cleared", extra={
            "pattern": pattern,
            "cleared_count": cleared_count
        })
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cache entries matching pattern '{pattern}'",
            "pattern": pattern,
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error("Failed to clear cache pattern", extra={
            "pattern": pattern,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache pattern '{pattern}'"
        )