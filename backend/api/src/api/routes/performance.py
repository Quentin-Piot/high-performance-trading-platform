"""
Performance monitoring API endpoints.
This module provides endpoints for monitoring database performance,
cache statistics, and system metrics.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_pool_status, get_session
from infrastructure.db_indexes import IndexManager, analyze_database_performance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/performance", tags=["performance"])
class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics"""
    connection_pool: dict[str, Any]
    table_statistics: dict[str, Any]
    slow_queries: list[dict[str, Any]]
    index_usage: list[dict[str, Any]]
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
    session: AsyncSession = Depends(get_session),
) -> DatabaseStatsResponse:
    """
    Get comprehensive database performance metrics.
    Returns:
        Database performance statistics including connection pool,
        table statistics, slow queries, and index usage
    """
    try:
        pool_status = await get_pool_status()
        performance_data = await analyze_database_performance(session)
        return DatabaseStatsResponse(
            connection_pool=pool_status,
            table_statistics=performance_data.get("table_statistics", {}),
            slow_queries=performance_data.get("slow_queries", []),
            index_usage=performance_data.get("index_usage", []),
        )
    except Exception as e:
        logger.error(
            "Failed to get database performance metrics", extra={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database performance metrics",
        ) from e
@router.get("/cache", response_model=CacheStatsResponse)
async def get_cache_performance() -> CacheStatsResponse:
    """
    Get cache performance metrics.
    Returns:
        Cache statistics (disabled - no cache system)
    """
    return CacheStatsResponse(
        enabled=False,
        connected_clients=0,
        used_memory=0,
        used_memory_human="0B",
        keyspace_hits=0,
        keyspace_misses=0,
        total_commands_processed=0,
        uptime_in_seconds=0,
        hit_ratio=0.0,
    )
@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    session: AsyncSession = Depends(get_session),
) -> PerformanceMetricsResponse:
    """
    Get comprehensive performance metrics for database and cache.
    Returns:
        Complete performance metrics including database and cache statistics
    """
    try:
        import asyncio
        from datetime import datetime
        db_task = get_database_performance(session)
        cache_task = get_cache_performance()
        db_stats, cache_stats = await asyncio.gather(db_task, cache_task)
        return PerformanceMetricsResponse(
            database=db_stats,
            cache=cache_stats,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error("Failed to get performance metrics", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics",
        ) from e
@router.post("/database/optimize/{table_name}")
async def optimize_table(
    table_name: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    """
    Optimize a specific database table.
    Args:
        table_name: Name of the table to optimize
    Returns:
        Optimization results
    """
    try:
        allowed_tables = ["jobs", "users"]
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table '{table_name}' is not allowed for optimization",
            )
        index_manager = IndexManager(session)
        result = await index_manager.optimize_table(table_name)
        logger.info(
            "Table optimization completed",
            extra={"table_name": table_name, "success": result.get("success", False)},
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to optimize table",
            extra={"table_name": table_name, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize table '{table_name}'",
        ) from e
@router.post("/database/create-indexes")
async def create_performance_indexes(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
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
        logger.info(
            "Performance indexes creation completed",
            extra={
                "success_count": success_count,
                "total_count": total_count,
                "results": results,
            },
        )
        return {
            "success": True,
            "message": f"Created {success_count}/{total_count} indexes successfully",
            "results": results,
        }
    except Exception as e:
        logger.error("Failed to create performance indexes", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create performance indexes",
        ) from e
@router.delete("/cache/clear")
async def clear_cache() -> dict[str, Any]:
    """
    Clear all cache entries.
    Returns:
        Cache clearing results (disabled - no cache system)
    """
    return {"success": False, "message": "Cache system is disabled"}
@router.delete("/cache/pattern/{pattern}")
async def clear_cache_pattern(pattern: str) -> dict[str, Any]:
    """
    Clear cache entries matching a pattern.
    Args:
        pattern: Redis pattern to match (e.g., "job:*", "user:*")
    Returns:
        Cache clearing results (disabled - no cache system)
    """
    return {"success": False, "message": "Cache system is disabled", "pattern": pattern}
