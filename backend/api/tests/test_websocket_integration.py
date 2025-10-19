import asyncio
import logging
import pytest
from tests.stress.websocket_stress_test import WebSocketStressTester

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_single_websocket_connection():
    tester = WebSocketStressTester()
    async with tester:
        try:
            job_id = await tester.create_test_job()
            metrics = await tester.single_websocket_test("test_conn", job_id, duration_seconds=20)
            assert metrics.successful
            assert metrics.messages_received > 0
        except Exception as e:
            logger.error(f"Test failed: {e}")
            pytest.fail(f"Test failed with exception: {e}")