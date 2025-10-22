"""
Database index optimization utilities.

This module provides utilities for creating and managing database indexes
to improve query performance for the trading platform.
"""
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class IndexManager:
    """Manages database indexes for performance optimization"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_performance_indexes(self) -> dict[str, bool]:
        """
        Create performance-optimized indexes for frequently queried columns.

        Returns:
            Dictionary mapping index name to creation success status
        """
        results = {}

        # Job table indexes for common query patterns
        job_indexes = [
            {
                "name": "idx_jobs_status_created_at",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status_created_at
                    ON jobs (status, created_at DESC)
                """,
                "description": "Composite index for status filtering with time ordering"
            },
            {
                "name": "idx_jobs_worker_status",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_worker_status
                    ON jobs (worker_id, status) WHERE worker_id IS NOT NULL
                """,
                "description": "Partial index for worker-specific job queries"
            },
            {
                "name": "idx_jobs_priority_created_at",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_priority_created_at
                    ON jobs (priority, created_at) WHERE status IN ('pending', 'retry')
                """,
                "description": "Partial index for job queue ordering"
            },
            {
                "name": "idx_jobs_dedup_key_hash",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_dedup_key_hash
                    ON jobs USING hash (dedup_key) WHERE dedup_key IS NOT NULL
                """,
                "description": "Hash index for fast deduplication lookups"
            },
            {
                "name": "idx_jobs_updated_at_status",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_updated_at_status
                    ON jobs (updated_at DESC, status) WHERE status IN ('processing', 'completed', 'failed')
                """,
                "description": "Index for monitoring and cleanup queries"
            },
            {
                "name": "idx_jobs_progress_processing",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_progress_processing
                    ON jobs (progress, updated_at DESC) WHERE status = 'processing'
                """,
                "description": "Partial index for progress monitoring of processing jobs"
            }
        ]

        # User table indexes (if exists)
        user_indexes = [
            {
                "name": "idx_users_email_lower",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower
                    ON users (LOWER(email))
                """,
                "description": "Case-insensitive email lookup index"
            },
            {
                "name": "idx_users_created_at",
                "sql": """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at
                    ON users (created_at DESC)
                """,
                "description": "Index for user registration analytics"
            }
        ]

        all_indexes = job_indexes + user_indexes

        for index_config in all_indexes:
            try:
                await self.session.execute(text(index_config["sql"]))
                await self.session.commit()

                results[index_config["name"]] = True
                logger.info("Created database index", extra={
                    "index_name": index_config["name"],
                    "description": index_config["description"]
                })

            except Exception as e:
                await self.session.rollback()
                results[index_config["name"]] = False
                logger.error("Failed to create database index", extra={
                    "index_name": index_config["name"],
                    "error": str(e)
                })

        return results

    async def analyze_table_statistics(self, table_name: str) -> dict[str, Any]:
        """
        Analyze table statistics for query optimization.

        Args:
            table_name: Name of the table to analyze

        Returns:
            Dictionary containing table statistics
        """
        try:
            # Update table statistics
            await self.session.execute(text(f"ANALYZE {table_name}"))

            # Get table size and row count
            # Get column statistics from pg_stats
            stats_query = text(f"""
                SELECT
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats
                WHERE tablename = '{table_name}'
                ORDER BY attname
            """)

            result = await self.session.execute(stats_query)
            stats = result.fetchall()

            # Get table size information
            # Use direct table name interpolation for PostgreSQL functions
            size_query = text(f"""
                SELECT
                    pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                    pg_size_pretty(pg_relation_size('{table_name}')) as table_size
            """)

            # Get row count with a separate, safer query
            count_query = text(f"""
                SELECT count(*) as row_count
                FROM {table_name}
            """)

            size_result = await self.session.execute(size_query)
            count_result = await self.session.execute(count_query)
            size_info = size_result.fetchone()
            count_info = count_result.fetchone()

            return {
                "table_name": table_name,
                "total_size": size_info.total_size if size_info else "Unknown",
                "table_size": size_info.table_size if size_info else "Unknown",
                "row_count": count_info.row_count if count_info else 0,
                "column_stats": [
                    {
                        "column": stat.attname,
                        "n_distinct": stat.n_distinct,
                        "correlation": stat.correlation
                    }
                    for stat in stats
                ]
            }

        except Exception as e:
            logger.error("Failed to analyze table statistics", extra={
                "table_name": table_name,
                "error": str(e)
            })
            return {"error": str(e)}

    async def get_slow_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get slow queries from pg_stat_statements (if available).

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of slow query information
        """
        try:
            # Check if pg_stat_statements extension is available
            check_extension = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                )
            """)

            result = await self.session.execute(check_extension)
            has_extension = result.scalar()

            if not has_extension:
                logger.warning("pg_stat_statements extension not available")
                return []

            # Get slow queries
            slow_queries = text("""
                SELECT
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                ORDER BY total_time DESC
                LIMIT :limit
            """)

            result = await self.session.execute(slow_queries, {"limit": limit})
            queries = result.fetchall()

            return [
                {
                    "query": query.query,
                    "calls": query.calls,
                    "total_time_ms": float(query.total_time),
                    "mean_time_ms": float(query.mean_time),
                    "rows": query.rows,
                    "cache_hit_percent": float(query.hit_percent) if query.hit_percent else 0.0
                }
                for query in queries
            ]

        except Exception as e:
            logger.error("Failed to get slow queries", extra={
                "error": str(e)
            })
            return []

    async def optimize_table(self, table_name: str) -> dict[str, Any]:
        """
        Optimize a table by running VACUUM and ANALYZE.

        Args:
            table_name: Name of the table to optimize

        Returns:
            Dictionary containing optimization results
        """
        try:
            # Run VACUUM ANALYZE for the table
            vacuum_query = text(f"VACUUM ANALYZE {table_name}")
            await self.session.execute(vacuum_query)

            logger.info("Optimized table", extra={
                "table_name": table_name,
                "operation": "VACUUM ANALYZE"
            })

            # Get updated statistics
            stats = await self.analyze_table_statistics(table_name)

            return {
                "success": True,
                "table_name": table_name,
                "operation": "VACUUM ANALYZE",
                "statistics": stats
            }

        except Exception as e:
            logger.error("Failed to optimize table", extra={
                "table_name": table_name,
                "error": str(e)
            })
            return {
                "success": False,
                "table_name": table_name,
                "error": str(e)
            }

    async def get_index_usage_stats(self) -> list[dict[str, Any]]:
        """
        Get index usage statistics.

        Returns:
            List of index usage statistics
        """
        try:
            query = text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC;
            """)

            result = await self.session.execute(query)
            stats = []

            for row in result:
                stats.append({
                    "schema": row.schemaname,
                    "table": row.tablename,
                    "index": row.indexname,
                    "tuples_read": row.idx_tup_read,
                    "tuples_fetched": row.idx_tup_fetch,
                    "scans": row.idx_scan
                })

            logger.info("Retrieved index usage statistics", extra={
                "index_count": len(stats)
            })

            return stats

        except Exception as e:
            logger.error("Failed to get index usage statistics", extra={
                "error": str(e)
            })
            return []

async def create_optimized_indexes(session: AsyncSession) -> dict[str, bool]:
    """
    Convenience function to create all performance indexes.

    Args:
        session: Database session

    Returns:
        Dictionary mapping index name to creation success status
    """
    index_manager = IndexManager(session)
    return await index_manager.create_performance_indexes()

async def analyze_database_performance(session: AsyncSession) -> dict[str, Any]:
    """
    Analyze comprehensive database performance metrics.

    Args:
        session: Database session

    Returns:
        Dictionary containing performance analysis results
    """
    try:
        index_manager = IndexManager(session)

        # Get table statistics for main tables
        table_stats = {}
        # Updated to match actual database tables
        main_tables = ["jobs", "users", "backtests", "strategies", "alembic_version"]

        for table_name in main_tables:
            try:
                stats = await index_manager.analyze_table_statistics(table_name)
                table_stats[table_name] = stats
            except Exception as e:
                logger.warning(f"Failed to analyze table {table_name}", extra={
                    "table_name": table_name,
                    "error": str(e)
                })
                table_stats[table_name] = {"error": str(e)}

        # Get slow queries
        slow_queries = await index_manager.get_slow_queries()

        # Get index usage statistics
        index_usage = await index_manager.get_index_usage_stats()

        return {
            "table_statistics": table_stats,
            "slow_queries": slow_queries,
            "index_usage": index_usage
        }

    except Exception as e:
        logger.error("Failed to analyze database performance", extra={
            "error": str(e)
        })
        return {
            "table_statistics": {},
            "slow_queries": [],
            "index_usage": []
        }
