"""
Monitoring and metrics implementation for the queue system.

This module provides monitoring capabilities including metrics collection,
health checks, and performance tracking for the Monte Carlo job processing system.
"""
import logging
import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
import threading
from contextlib import asynccontextmanager

from domain.queue import MonitoringInterface

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: str  # "healthy", "unhealthy", "warning"
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores metrics in memory"""
    
    def __init__(self, max_points_per_metric: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_points_per_metric: Maximum number of points to keep per metric
        """
        self.max_points_per_metric = max_points_per_metric
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self._counters: Dict[str, float] = defaultdict(float)
        self._lock = threading.RLock()
        
        logger.info("Initialized metrics collector")
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value"""
        with self._lock:
            metric_key = self._create_metric_key(name, tags or {})
            point = MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.now(UTC),
                tags=tags or {}
            )
            self._metrics[metric_key].append(point)
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        """Increment a counter metric"""
        with self._lock:
            counter_key = self._create_metric_key(name, tags or {})
            self._counters[counter_key] += value
            
            # Also record as a metric point
            self.record_metric(name, self._counters[counter_key], tags)
    
    def record_timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric"""
        self.record_metric(f"{name}.duration_ms", duration_ms, tags)
    
    def get_metric_points(self, name: str, tags: Optional[Dict[str, str]] = None) -> List[MetricPoint]:
        """Get metric points for a specific metric"""
        with self._lock:
            metric_key = self._create_metric_key(name, tags or {})
            return list(self._metrics.get(metric_key, []))
    
    def get_counter_value(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value"""
        with self._lock:
            counter_key = self._create_metric_key(name, tags or {})
            return self._counters.get(counter_key, 0.0)
    
    def get_all_metrics(self) -> Dict[str, List[MetricPoint]]:
        """Get all collected metrics"""
        with self._lock:
            return {key: list(points) for key, points in self._metrics.items()}
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
    
    def _create_metric_key(self, name: str, tags: Dict[str, str]) -> str:
        """Create a unique key for a metric with tags"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


class HealthChecker:
    """Performs health checks on system components"""
    
    def __init__(self):
        """Initialize health checker"""
        self._health_checks: Dict[str, Callable] = {}
        self._last_results: Dict[str, HealthCheck] = {}
        self._lock = threading.RLock()
        
        logger.info("Initialized health checker")
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function.
        
        Args:
            name: Name of the health check
            check_func: Function that returns (status, message, details)
        """
        with self._lock:
            self._health_checks[name] = check_func
            logger.info(f"Registered health check: {name}")
    
    async def run_health_check(self, name: str) -> HealthCheck:
        """Run a specific health check"""
        if name not in self._health_checks:
            return HealthCheck(
                name=name,
                status="unhealthy",
                message=f"Health check '{name}' not found",
                timestamp=datetime.now(UTC)
            )
        
        try:
            check_func = self._health_checks[name]
            
            # Run health check (support both sync and async functions)
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            # Parse result
            if isinstance(result, tuple):
                if len(result) == 2:
                    status, message = result
                    details = {}
                elif len(result) == 3:
                    status, message, details = result
                else:
                    raise ValueError("Health check must return (status, message) or (status, message, details)")
            else:
                status = "healthy" if result else "unhealthy"
                message = f"Health check {name} returned {result}"
                details = {}
            
            health_check = HealthCheck(
                name=name,
                status=status,
                message=message,
                timestamp=datetime.now(UTC),
                details=details
            )
            
            with self._lock:
                self._last_results[name] = health_check
            
            return health_check
            
        except Exception as e:
            error_check = HealthCheck(
                name=name,
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(UTC),
                details={"error": str(e)}
            )
            
            with self._lock:
                self._last_results[name] = error_check
            
            logger.error(f"Health check '{name}' failed: {str(e)}")
            return error_check
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        results = {}
        
        for name in self._health_checks:
            results[name] = await self.run_health_check(name)
        
        return results
    
    def get_last_result(self, name: str) -> Optional[HealthCheck]:
        """Get the last result for a health check"""
        with self._lock:
            return self._last_results.get(name)
    
    def get_all_last_results(self) -> Dict[str, HealthCheck]:
        """Get all last health check results"""
        with self._lock:
            return self._last_results.copy()


class PerformanceTracker:
    """Tracks performance metrics and statistics"""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize performance tracker.
        
        Args:
            window_size: Size of the sliding window for calculations
        """
        self.window_size = window_size
        self._timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._lock = threading.RLock()
        
        logger.info("Initialized performance tracker")
    
    @asynccontextmanager
    async def track_timing(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for tracking operation timing"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_timing(operation_name, duration_ms, tags)
    
    def record_timing(self, operation_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing for an operation"""
        with self._lock:
            key = self._create_key(operation_name, tags or {})
            self._timings[key].append(duration_ms)
    
    def get_statistics(self, operation_name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get statistics for an operation"""
        with self._lock:
            key = self._create_key(operation_name, tags or {})
            timings = list(self._timings.get(key, []))
            
            if not timings:
                return {
                    "count": 0,
                    "avg_ms": 0.0,
                    "min_ms": 0.0,
                    "max_ms": 0.0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0
                }
            
            timings.sort()
            count = len(timings)
            
            return {
                "count": count,
                "avg_ms": sum(timings) / count,
                "min_ms": timings[0],
                "max_ms": timings[-1],
                "p50_ms": timings[int(count * 0.5)],
                "p95_ms": timings[int(count * 0.95)],
                "p99_ms": timings[int(count * 0.99)]
            }
    
    def _create_key(self, operation_name: str, tags: Dict[str, str]) -> str:
        """Create a unique key for an operation with tags"""
        if not tags:
            return operation_name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{operation_name}[{tag_str}]"


class MonitoringService(MonitoringInterface):
    """Main monitoring service that coordinates all monitoring components"""
    
    def __init__(self):
        """Initialize monitoring service"""
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.performance_tracker = PerformanceTracker()
        
        # Register default health checks
        self._register_default_health_checks()
        
        logger.info("Initialized monitoring service")
    
    async def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value"""
        self.metrics_collector.record_metric(name, value, tags)
    
    async def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        self.metrics_collector.increment_counter(name, tags)
    
    async def record_timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric"""
        self.metrics_collector.record_timing(name, duration_ms, tags)
        self.performance_tracker.record_timing(name, duration_ms, tags)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        health_results = await self.health_checker.run_all_health_checks()
        
        # Determine overall status
        overall_status = "healthy"
        unhealthy_count = 0
        warning_count = 0
        
        for check in health_results.values():
            if check.status == "unhealthy":
                unhealthy_count += 1
                overall_status = "unhealthy"
            elif check.status == "warning":
                warning_count += 1
                if overall_status == "healthy":
                    overall_status = "warning"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": {
                name: {
                    "status": check.status,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details
                }
                for name, check in health_results.items()
            },
            "summary": {
                "total_checks": len(health_results),
                "healthy_checks": len(health_results) - unhealthy_count - warning_count,
                "warning_checks": warning_count,
                "unhealthy_checks": unhealthy_count
            }
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        all_metrics = self.metrics_collector.get_all_metrics()
        
        summary = {
            "total_metrics": len(all_metrics),
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": {}
        }
        
        for metric_key, points in all_metrics.items():
            if points:
                values = [p.value for p in points]
                summary["metrics"][metric_key] = {
                    "count": len(values),
                    "latest_value": values[-1],
                    "avg_value": sum(values) / len(values),
                    "min_value": min(values),
                    "max_value": max(values),
                    "latest_timestamp": points[-1].timestamp.isoformat()
                }
        
        return summary
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance statistics summary"""
        # This would collect performance stats from the performance tracker
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "operations": {}
        }
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a custom health check"""
        self.health_checker.register_health_check(name, check_func)
    
    @asynccontextmanager
    async def track_operation(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for tracking operation performance"""
        async with self.performance_tracker.track_timing(operation_name, tags):
            yield
    
    def _register_default_health_checks(self) -> None:
        """Register default system health checks"""
        
        def memory_check():
            """Check memory usage"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    return "unhealthy", f"High memory usage: {memory.percent:.1f}%", {"memory_percent": memory.percent}
                elif memory.percent > 80:
                    return "warning", f"Elevated memory usage: {memory.percent:.1f}%", {"memory_percent": memory.percent}
                else:
                    return "healthy", f"Memory usage: {memory.percent:.1f}%", {"memory_percent": memory.percent}
            except ImportError:
                return "warning", "psutil not available for memory monitoring", {}
            except Exception as e:
                return "unhealthy", f"Memory check failed: {str(e)}", {"error": str(e)}
        
        def disk_check():
            """Check disk usage"""
            try:
                import psutil
                disk = psutil.disk_usage('/')
                percent = (disk.used / disk.total) * 100
                if percent > 90:
                    return "unhealthy", f"High disk usage: {percent:.1f}%", {"disk_percent": percent}
                elif percent > 80:
                    return "warning", f"Elevated disk usage: {percent:.1f}%", {"disk_percent": percent}
                else:
                    return "healthy", f"Disk usage: {percent:.1f}%", {"disk_percent": percent}
            except ImportError:
                return "warning", "psutil not available for disk monitoring", {}
            except Exception as e:
                return "unhealthy", f"Disk check failed: {str(e)}", {"error": str(e)}
        
        self.health_checker.register_health_check("memory", memory_check)
        self.health_checker.register_health_check("disk", disk_check)


# Global monitoring service instance
monitoring_service = MonitoringService()