"""
WebSocket Stress Testing Tool

This module provides comprehensive stress testing capabilities for WebSocket connections,
including concurrent connection testing, message throughput testing, and error scenario simulation.
"""

import argparse
import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Metrics for a single WebSocket connection."""
    connection_id: str
    connect_time: float = 0.0
    disconnect_time: float = 0.0
    messages_received: int = 0
    messages_sent: int = 0
    errors: list[str] = field(default_factory=list)
    latencies: list[float] = field(default_factory=list)
    connection_duration: float = 0.0
    successful: bool = False


@dataclass
class StressTestResults:
    """Results from a stress test run."""
    total_connections: int
    successful_connections: int
    failed_connections: int
    total_messages_sent: int
    total_messages_received: int
    total_errors: int
    test_duration: float
    average_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    throughput_messages_per_second: float
    connection_success_rate: float
    error_details: dict[str, int] = field(default_factory=dict)


class WebSocketStressTester:
    """Comprehensive WebSocket stress testing tool."""

    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.http_base_url = base_url.replace("ws://", "http://").replace("wss://", "https://")
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def create_test_job(self) -> str:
        """Create a test Monte Carlo job and return its ID."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        job_data = {
            "symbol": "AAPL",
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-12-31T23:59:59",
            "num_runs": 1000,
            "initial_capital": 10000.0,
            "strategy_params": {},
            "priority": "normal"
        }

        async with self.session.post(
            f"{self.http_base_url}/api/v1/monte-carlo/jobs",
            json=job_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["job_id"]
            else:
                raise RuntimeError(f"Failed to create test job: {response.status}")

    async def single_websocket_test(
        self,
        connection_id: str,
        job_id: str,
        duration_seconds: int = 30,
        message_interval: float = 1.0
    ) -> ConnectionMetrics:
        """Test a single WebSocket connection."""
        metrics = ConnectionMetrics(connection_id=connection_id)
        start_time = time.time()

        try:
            # Connect to WebSocket
            connect_start = time.time()
            uri = f"{self.base_url}/api/v1/monte-carlo/jobs/{job_id}/progress"

            async with websockets.connect(uri) as websocket:
                metrics.connect_time = time.time() - connect_start
                logger.info(f"Connection {connection_id} established in {metrics.connect_time:.3f}s")

                # Listen for messages with timeout
                end_time = start_time + duration_seconds

                while time.time() < end_time:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=min(message_interval, end_time - time.time())
                        )

                        receive_time = time.time()
                        metrics.messages_received += 1

                        # Parse message and calculate latency if possible
                        try:
                            data = json.loads(message)
                            if 'timestamp' in data:
                                msg_timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                                latency = receive_time - msg_timestamp.timestamp()
                                metrics.latencies.append(latency)
                        except (json.JSONDecodeError, ValueError, KeyError):
                            pass  # Ignore parsing errors for latency calculation

                    except asyncio.TimeoutError:
                        # No message received within timeout - this is normal
                        continue
                    except ConnectionClosed:
                        logger.info(f"Connection {connection_id} closed by server")
                        break
                    except Exception as e:
                        error_msg = f"Message receive error: {str(e)}"
                        metrics.errors.append(error_msg)
                        logger.warning(f"Connection {connection_id}: {error_msg}")

                metrics.successful = True

        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            metrics.errors.append(error_msg)
            logger.error(f"Connection {connection_id}: {error_msg}")

        finally:
            metrics.disconnect_time = time.time()
            metrics.connection_duration = metrics.disconnect_time - start_time

        return metrics

    async def concurrent_connections_test(
        self,
        num_connections: int,
        duration_seconds: int = 30,
        ramp_up_seconds: int = 5
    ) -> StressTestResults:
        """Test multiple concurrent WebSocket connections."""
        logger.info(f"Starting concurrent connections test: {num_connections} connections")

        # Create a test job
        job_id = await self.create_test_job()
        logger.info(f"Created test job: {job_id}")

        # Calculate ramp-up delay
        ramp_delay = ramp_up_seconds / num_connections if num_connections > 0 else 0

        # Start connections with ramp-up
        tasks = []
        start_time = time.time()

        for i in range(num_connections):
            connection_id = f"conn_{i:04d}"

            # Add ramp-up delay
            if i > 0:
                await asyncio.sleep(ramp_delay)

            task = asyncio.create_task(
                self.single_websocket_test(
                    connection_id=connection_id,
                    job_id=job_id,
                    duration_seconds=duration_seconds
                )
            )
            tasks.append(task)

        # Wait for all connections to complete
        logger.info(f"All {num_connections} connections started, waiting for completion...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        metrics_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error metrics for failed connections
                error_metrics = ConnectionMetrics(connection_id=f"conn_{i:04d}")
                error_metrics.errors.append(str(result))
                metrics_list.append(error_metrics)
            else:
                metrics_list.append(result)

        return self._calculate_stress_test_results(metrics_list, time.time() - start_time)

    async def message_throughput_test(
        self,
        num_connections: int = 10,
        messages_per_connection: int = 100,
        burst_mode: bool = False
    ) -> StressTestResults:
        """Test message throughput with multiple connections."""
        logger.info(f"Starting throughput test: {num_connections} connections, {messages_per_connection} messages each")

        # Create test jobs for each connection
        job_ids = []
        for _ in range(num_connections):
            job_id = await self.create_test_job()
            job_ids.append(job_id)

        # Start throughput test
        tasks = []
        start_time = time.time()

        for i, job_id in enumerate(job_ids):
            connection_id = f"throughput_conn_{i:04d}"
            task = asyncio.create_task(
                self._throughput_connection_test(
                    connection_id=connection_id,
                    job_id=job_id,
                    target_messages=messages_per_connection,
                    burst_mode=burst_mode
                )
            )
            tasks.append(task)

        # Wait for completion
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        metrics_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_metrics = ConnectionMetrics(connection_id=f"throughput_conn_{i:04d}")
                error_metrics.errors.append(str(result))
                metrics_list.append(error_metrics)
            else:
                metrics_list.append(result)

        return self._calculate_stress_test_results(metrics_list, time.time() - start_time)

    async def _throughput_connection_test(
        self,
        connection_id: str,
        job_id: str,
        target_messages: int,
        burst_mode: bool = False
    ) -> ConnectionMetrics:
        """Test throughput for a single connection."""
        metrics = ConnectionMetrics(connection_id=connection_id)
        start_time = time.time()

        try:
            uri = f"{self.base_url}/api/v1/monte-carlo/jobs/{job_id}/progress"

            async with websockets.connect(uri) as websocket:
                messages_received = 0
                timeout_seconds = 60  # Maximum time to wait for messages

                while messages_received < target_messages and (time.time() - start_time) < timeout_seconds:
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        messages_received += 1
                        metrics.messages_received += 1

                        # In burst mode, don't wait between messages
                        if not burst_mode:
                            await asyncio.sleep(0.01)  # Small delay for controlled throughput

                    except asyncio.TimeoutError:
                        continue
                    except ConnectionClosed:
                        break

                metrics.successful = True

        except Exception as e:
            metrics.errors.append(str(e))

        finally:
            metrics.connection_duration = time.time() - start_time

        return metrics

    async def error_scenario_test(self) -> dict[str, Any]:
        """Test various error scenarios."""
        logger.info("Starting error scenario tests")

        error_results = {}

        # Test 1: Invalid job ID
        try:
            invalid_job_id = "invalid-job-id-12345"
            uri = f"{self.base_url}/api/v1/monte-carlo/jobs/{invalid_job_id}/progress"

            async with websockets.connect(uri) as websocket:
                # Should receive an error message
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_results["invalid_job_id"] = {"success": True, "message": message}
        except Exception as e:
            error_results["invalid_job_id"] = {"success": False, "error": str(e)}

        # Test 2: Rapid connect/disconnect
        rapid_disconnect_errors = []
        for _i in range(10):
            try:
                job_id = await self.create_test_job()
                uri = f"{self.base_url}/api/v1/monte-carlo/jobs/{job_id}/progress"

                async with websockets.connect(uri) as websocket:
                    # Immediately disconnect
                    await websocket.close()

            except Exception as e:
                rapid_disconnect_errors.append(str(e))

        error_results["rapid_disconnect"] = {
            "total_attempts": 10,
            "errors": len(rapid_disconnect_errors),
            "error_details": rapid_disconnect_errors
        }

        # Test 3: Connection timeout
        try:
            # Try to connect to non-existent endpoint
            invalid_uri = f"{self.base_url}/api/v1/invalid/endpoint"
            await asyncio.wait_for(
                websockets.connect(invalid_uri),
                timeout=5.0
            )
            error_results["connection_timeout"] = {"success": False, "error": "Should have failed"}
        except Exception as e:
            error_results["connection_timeout"] = {"success": True, "error": str(e)}

        return error_results

    def _calculate_stress_test_results(
        self,
        metrics_list: list[ConnectionMetrics],
        total_duration: float
    ) -> StressTestResults:
        """Calculate comprehensive stress test results."""
        successful_connections = sum(1 for m in metrics_list if m.successful)
        failed_connections = len(metrics_list) - successful_connections

        total_messages_sent = sum(m.messages_sent for m in metrics_list)
        total_messages_received = sum(m.messages_received for m in metrics_list)
        total_errors = sum(len(m.errors) for m in metrics_list)

        # Calculate latency statistics
        all_latencies = []
        for metrics in metrics_list:
            all_latencies.extend(metrics.latencies)

        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            median_latency = statistics.median(all_latencies)
            p95_latency = statistics.quantiles(all_latencies, n=20)[18]  # 95th percentile
            p99_latency = statistics.quantiles(all_latencies, n=100)[98]  # 99th percentile
        else:
            avg_latency = median_latency = p95_latency = p99_latency = 0.0

        # Calculate throughput
        throughput = total_messages_received / total_duration if total_duration > 0 else 0.0

        # Calculate connection success rate
        success_rate = successful_connections / len(metrics_list) if metrics_list else 0.0

        # Collect error details
        error_details = {}
        for metrics in metrics_list:
            for error in metrics.errors:
                error_type = error.split(':')[0] if ':' in error else error
                error_details[error_type] = error_details.get(error_type, 0) + 1

        return StressTestResults(
            total_connections=len(metrics_list),
            successful_connections=successful_connections,
            failed_connections=failed_connections,
            total_messages_sent=total_messages_sent,
            total_messages_received=total_messages_received,
            total_errors=total_errors,
            test_duration=total_duration,
            average_latency=avg_latency,
            median_latency=median_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            throughput_messages_per_second=throughput,
            connection_success_rate=success_rate,
            error_details=error_details
        )

    def print_results(self, results: StressTestResults, test_name: str = "Stress Test"):
        """Print formatted stress test results."""
        print(f"\n{'='*60}")
        print(f"{test_name} Results")
        print(f"{'='*60}")
        print(f"Total Connections: {results.total_connections}")
        print(f"Successful Connections: {results.successful_connections}")
        print(f"Failed Connections: {results.failed_connections}")
        print(f"Connection Success Rate: {results.connection_success_rate:.2%}")
        print(f"Test Duration: {results.test_duration:.2f}s")
        print("\nMessage Statistics:")
        print(f"  Messages Sent: {results.total_messages_sent}")
        print(f"  Messages Received: {results.total_messages_received}")
        print(f"  Throughput: {results.throughput_messages_per_second:.2f} msg/s")
        print("\nLatency Statistics:")
        print(f"  Average: {results.average_latency*1000:.2f}ms")
        print(f"  Median: {results.median_latency*1000:.2f}ms")
        print(f"  95th Percentile: {results.p95_latency*1000:.2f}ms")
        print(f"  99th Percentile: {results.p99_latency*1000:.2f}ms")
        print(f"\nErrors: {results.total_errors}")
        if results.error_details:
            print("Error Details:")
            for error_type, count in results.error_details.items():
                print(f"  {error_type}: {count}")
        print(f"{'='*60}\n")


async def main():
    """Main function to run stress tests."""
    parser = argparse.ArgumentParser(description="WebSocket Stress Testing Tool")
    parser.add_argument("--url", default="ws://localhost:8000", help="WebSocket base URL")
    parser.add_argument("--connections", type=int, default=10, help="Number of concurrent connections")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--test-type", choices=["concurrent", "throughput", "errors", "all"],
                       default="all", help="Type of test to run")

    args = parser.parse_args()

    async with WebSocketStressTester(args.url) as tester:
        if args.test_type in ["concurrent", "all"]:
            logger.info("Running concurrent connections test...")
            results = await tester.concurrent_connections_test(
                num_connections=args.connections,
                duration_seconds=args.duration
            )
            tester.print_results(results, "Concurrent Connections Test")

        if args.test_type in ["throughput", "all"]:
            logger.info("Running throughput test...")
            results = await tester.message_throughput_test(
                num_connections=min(args.connections, 5),  # Limit for throughput test
                messages_per_connection=100
            )
            tester.print_results(results, "Message Throughput Test")

        if args.test_type in ["errors", "all"]:
            logger.info("Running error scenario tests...")
            error_results = await tester.error_scenario_test()
            print(f"\n{'='*60}")
            print("Error Scenario Test Results")
            print(f"{'='*60}")
            for scenario, result in error_results.items():
                print(f"{scenario}: {result}")
            print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
