# Stress Testing Tools

This directory contains comprehensive stress testing tools for the high-performance trading platform's Monte Carlo simulation system.

## Overview

The stress testing suite includes tools for testing various aspects of the system under load:

1. **WebSocket Stress Testing** - Tests WebSocket connections, message throughput, and real-time communication
2. **Concurrent Job Stress Testing** - Tests job submission, processing, and queue management under concurrent load

## Tools

### 1. WebSocket Stress Test (`websocket_stress_test.py`)

Tests WebSocket connections for real-time progress updates and handles various stress scenarios.

#### Features:
- **Concurrent Connections**: Test multiple simultaneous WebSocket connections
- **Message Throughput**: Measure message processing rates and latencies
- **Error Scenarios**: Test error handling and recovery mechanisms
- **Latency Analysis**: Detailed latency statistics (average, median, 95th, 99th percentiles)

#### Usage:

```bash
# Basic concurrent connections test (10 connections for 30 seconds)
python websocket_stress_test.py --connections 10 --duration 30

# Throughput test
python websocket_stress_test.py --test-type throughput --connections 5

# Error scenario testing
python websocket_stress_test.py --test-type errors

# All tests with custom URL
python websocket_stress_test.py --url ws://localhost:8000 --test-type all
```

#### Parameters:
- `--url`: WebSocket base URL (default: `ws://localhost:8000`)
- `--connections`: Number of concurrent connections (default: 10)
- `--duration`: Test duration in seconds (default: 30)
- `--test-type`: Type of test (`concurrent`, `throughput`, `errors`, `all`)

#### Metrics Collected:
- Connection success rate
- Message throughput (messages/second)
- Latency statistics (ms)
- Error counts and types
- Connection duration

### 2. Concurrent Job Stress Test (`concurrent_job_stress_test.py`)

Tests the job submission and processing pipeline under concurrent load.

#### Features:
- **Concurrent Job Submission**: Submit multiple jobs simultaneously in batches
- **End-to-End Processing**: Track jobs from submission to completion
- **Queue Monitoring**: Monitor queue depth and processing patterns
- **Processing Time Analysis**: Detailed processing time statistics
- **Throughput Measurement**: Job submission and completion rates

#### Usage:

```bash
# Basic end-to-end test (20 jobs in batches of 5)
python concurrent_job_stress_test.py --jobs 20 --batch-size 5

# Submission-only test
python concurrent_job_stress_test.py --test-type submission --jobs 50

# Extended processing test with longer timeout
python concurrent_job_stress_test.py --jobs 30 --timeout 900

# All tests with custom URL
python concurrent_job_stress_test.py --url http://localhost:8000 --test-type all
```

#### Parameters:
- `--url`: API base URL (default: `http://localhost:8000`)
- `--jobs`: Number of jobs to submit (default: 20)
- `--batch-size`: Submission batch size (default: 5)
- `--timeout`: Job tracking timeout in seconds (default: 600)
- `--test-type`: Type of test (`submission`, `end-to-end`, `all`)

#### Metrics Collected:
- Job submission success rate
- Job completion success rate
- Submission and completion throughput
- Processing time statistics
- Queue depth over time
- Error analysis

## Prerequisites

### Dependencies

Install required dependencies:

```bash
pip install aiohttp websockets
```

### System Requirements

1. **Running Backend**: Ensure the trading platform backend is running
2. **Database**: Database should be accessible and properly configured
3. **Queue System**: SQS or local queue system should be operational
4. **Redis** (optional): For WebSocket pub/sub functionality

### Environment Setup

Make sure the following are configured:

```bash
# Environment variables
export ENVIRONMENT=development
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Start the backend
cd backend/api
poetry run python scripts/bootstrap.py
```

## Running Stress Tests

### Quick Start

1. **Start the backend system**:
   ```bash
   cd backend/api
   ENVIRONMENT=development RUN_WORKER=true poetry run python scripts/bootstrap.py
   ```

2. **Run WebSocket stress test**:
   ```bash
   cd tests/stress
   python websocket_stress_test.py --connections 5 --duration 60
   ```

3. **Run concurrent job stress test**:
   ```bash
   python concurrent_job_stress_test.py --jobs 10 --batch-size 3
   ```

### Comprehensive Testing

For thorough system testing, run both tools with increasing load:

```bash
# Light load
python websocket_stress_test.py --connections 5 --duration 30
python concurrent_job_stress_test.py --jobs 10 --batch-size 2

# Medium load
python websocket_stress_test.py --connections 15 --duration 60
python concurrent_job_stress_test.py --jobs 25 --batch-size 5

# Heavy load (monitor system resources)
python websocket_stress_test.py --connections 30 --duration 120
python concurrent_job_stress_test.py --jobs 50 --batch-size 10
```

## Interpreting Results

### WebSocket Test Results

- **Connection Success Rate**: Should be close to 100% under normal load
- **Message Throughput**: Depends on job processing speed and Redis performance
- **Latency**: 
  - < 100ms: Excellent
  - 100-500ms: Good
  - > 500ms: May indicate performance issues
- **Errors**: Should be minimal; investigate specific error types

### Job Processing Test Results

- **Submission Success Rate**: Should be 100% for valid requests
- **Completion Success Rate**: Depends on job complexity and system resources
- **Processing Time**: Varies by job parameters (num_runs, date range)
- **Throughput**: 
  - Submission: Should handle 10+ jobs/second
  - Completion: Depends on worker capacity and job complexity
- **Queue Depth**: Monitor for queue buildup indicating bottlenecks

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Ensure backend is running on correct port
   - Check firewall settings
   - Verify URL format

2. **High Error Rates**:
   - Check system resources (CPU, memory)
   - Verify database connectivity
   - Check queue system status

3. **Poor Performance**:
   - Monitor system resources during tests
   - Check database query performance
   - Verify Redis connectivity for WebSocket tests

4. **Timeouts**:
   - Increase timeout values for complex jobs
   - Check worker capacity and scaling
   - Monitor queue processing rates

### Monitoring During Tests

Monitor these system metrics during stress tests:

- **CPU Usage**: Should not consistently exceed 80%
- **Memory Usage**: Watch for memory leaks
- **Database Connections**: Monitor connection pool usage
- **Queue Depth**: Should not grow indefinitely
- **Network I/O**: Monitor for bandwidth limitations

## Best Practices

1. **Start Small**: Begin with low load and gradually increase
2. **Monitor Resources**: Keep an eye on system resources during tests
3. **Baseline Testing**: Establish baseline performance before making changes
4. **Isolated Testing**: Test individual components before full system tests
5. **Realistic Data**: Use realistic job parameters and data sizes
6. **Cleanup**: Clean up test data after stress testing

## Integration with CI/CD

These tools can be integrated into CI/CD pipelines for automated performance testing:

```bash
# Example CI script
#!/bin/bash
set -e

# Start backend in background
./start_backend.sh &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 30

# Run stress tests
python tests/stress/websocket_stress_test.py --connections 5 --duration 30
python tests/stress/concurrent_job_stress_test.py --jobs 10 --batch-size 2

# Cleanup
kill $BACKEND_PID
```

## Contributing

When adding new stress tests:

1. Follow the existing patterns for metrics collection
2. Include comprehensive error handling
3. Add appropriate logging
4. Document new test parameters and metrics
5. Update this README with new test descriptions