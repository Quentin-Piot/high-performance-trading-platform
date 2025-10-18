"""
Enhanced Redis pub/sub utilities with automatic reconnection, connection pooling,
health monitoring, message ordering, and duplicate detection.

This module provides robust Redis pub/sub functionality with:
- Automatic reconnection on connection failures
- Connection pooling for better resource management
- Health monitoring and metrics
- Message ordering guarantees
- Duplicate message detection
- Graceful error handling and recovery
"""
import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class PubSubMessage:
    """Enhanced message structure with ordering and deduplication support"""
    channel: str
    data: Any
    message_id: str
    timestamp: float
    sequence_number: int | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            'channel': self.channel,
            'data': self.data,
            'message_id': self.message_id,
            'timestamp': self.timestamp,
            'sequence_number': self.sequence_number,
            'retry_count': self.retry_count
        }

@dataclass
class PubSubMetrics:
    """Metrics for Redis pub/sub operations"""
    messages_published: int = 0
    messages_received: int = 0
    messages_duplicated: int = 0
    messages_out_of_order: int = 0
    connection_failures: int = 0
    reconnection_attempts: int = 0
    successful_reconnections: int = 0
    average_publish_latency: float = 0.0
    average_receive_latency: float = 0.0
    active_subscriptions: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'messages_published': self.messages_published,
            'messages_received': self.messages_received,
            'messages_duplicated': self.messages_duplicated,
            'messages_out_of_order': self.messages_out_of_order,
            'connection_failures': self.connection_failures,
            'reconnection_attempts': self.reconnection_attempts,
            'successful_reconnections': self.successful_reconnections,
            'average_publish_latency': self.average_publish_latency,
            'average_receive_latency': self.average_receive_latency,
            'active_subscriptions': self.active_subscriptions
        }

class MessageOrderingManager:
    """Manages message ordering and duplicate detection"""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.channel_sequences: dict[str, int] = defaultdict(int)
        self.message_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.pending_messages: dict[str, dict[int, PubSubMessage]] = defaultdict(dict)

    def get_next_sequence(self, channel: str) -> int:
        """Get next sequence number for a channel"""
        self.channel_sequences[channel] += 1
        return self.channel_sequences[channel]

    def is_duplicate(self, message: PubSubMessage) -> bool:
        """Check if message is a duplicate"""
        channel_history = self.message_history[message.channel]
        return message.message_id in [msg.message_id for msg in channel_history]

    def add_message(self, message: PubSubMessage) -> bool:
        """Add message to history and check for duplicates"""
        if self.is_duplicate(message):
            return False

        self.message_history[message.channel].append(message)
        return True

    def process_ordered_message(self, message: PubSubMessage) -> list[PubSubMessage]:
        """Process message with ordering guarantees"""
        if message.sequence_number is None:
            # No ordering required
            if self.add_message(message):
                return [message]
            return []

        channel = message.channel
        expected_seq = self.channel_sequences.get(channel, 0) + 1

        if message.sequence_number == expected_seq:
            # Message is in order
            if self.add_message(message):
                self.channel_sequences[channel] = message.sequence_number
                result = [message]

                # Check for pending messages that can now be processed
                pending = self.pending_messages[channel]
                next_seq = message.sequence_number + 1

                while next_seq in pending:
                    next_message = pending.pop(next_seq)
                    if self.add_message(next_message):
                        result.append(next_message)
                        self.channel_sequences[channel] = next_seq
                    next_seq += 1

                return result
            return []

        elif message.sequence_number > expected_seq:
            # Message is out of order, store for later
            if not self.is_duplicate(message):
                self.pending_messages[channel][message.sequence_number] = message
            return []

        else:
            # Message is old or duplicate
            return []

class EnhancedRedisPubSub:
    """Enhanced Redis pub/sub with automatic reconnection and advanced features"""

    def __init__(
        self,
        redis_url: str | None = None,
        max_connections: int = 10,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
        reconnect_backoff: float = 2.0,
        max_reconnect_attempts: int = -1,  # -1 for infinite
        message_ordering: bool = True,
        duplicate_detection: bool = True,
        health_check_interval: float = 30.0
    ):
        """
        Initialize enhanced Redis pub/sub manager.

        Args:
            redis_url: Redis connection URL
            max_connections: Maximum connections in pool
            reconnect_delay: Initial reconnection delay in seconds
            max_reconnect_delay: Maximum reconnection delay in seconds
            reconnect_backoff: Backoff multiplier for reconnection delays
            max_reconnect_attempts: Maximum reconnection attempts (-1 for infinite)
            message_ordering: Enable message ordering guarantees
            duplicate_detection: Enable duplicate message detection
            health_check_interval: Health check interval in seconds
        """
        self.redis_url = redis_url or settings.redis_url
        self.max_connections = max_connections
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.reconnect_backoff = reconnect_backoff
        self.max_reconnect_attempts = max_reconnect_attempts
        self.message_ordering = message_ordering
        self.duplicate_detection = duplicate_detection
        self.health_check_interval = health_check_interval

        # Connection management
        self._connection_pool: ConnectionPool | None = None
        self._redis: Redis | None = None
        self._pubsub_connections: dict[str, Redis] = {}
        self._active_subscriptions: dict[str, set[str]] = defaultdict(set)

        # Reconnection state
        self._reconnect_tasks: dict[str, asyncio.Task] = {}
        self._connection_healthy: dict[str, bool] = defaultdict(lambda: True)

        # Message management
        self._ordering_manager = MessageOrderingManager() if message_ordering else None
        self._message_callbacks: dict[str, list[Callable]] = defaultdict(list)

        # Metrics and monitoring
        self.metrics = PubSubMetrics()
        self._health_check_task: asyncio.Task | None = None
        self._last_health_check = time.time()

        # Shutdown flag
        self._shutdown = False

    async def initialize(self) -> None:
        """Initialize the Redis pub/sub manager"""
        try:
            # Create connection pool
            self._connection_pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Create main Redis connection
            self._redis = Redis(connection_pool=self._connection_pool)

            # Test connection
            await self._redis.ping()

            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info("Enhanced Redis pub/sub initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis pub/sub: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the Redis pub/sub manager"""
        self._shutdown = True

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Cancel reconnection tasks
        for task in self._reconnect_tasks.values():
            task.cancel()

        # Close all pub/sub connections
        for connection in self._pubsub_connections.values():
            try:
                await connection.close()
            except Exception:
                pass

        # Close main connection
        if self._redis:
            await self._redis.close()

        # Close connection pool
        if self._connection_pool:
            await self._connection_pool.disconnect()

        logger.info("Enhanced Redis pub/sub shutdown completed")

    async def _health_check_loop(self) -> None:
        """Periodic health check for connections"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _perform_health_check(self) -> None:
        """Perform health check on all connections"""
        self._last_health_check = time.time()

        # Check main connection
        if self._redis:
            try:
                await self._redis.ping()
                self._connection_healthy['main'] = True
            except Exception:
                self._connection_healthy['main'] = False
                logger.warning("Main Redis connection unhealthy")

        # Check pub/sub connections
        for conn_id, connection in self._pubsub_connections.items():
            try:
                await connection.ping()
                self._connection_healthy[conn_id] = True
            except Exception:
                self._connection_healthy[conn_id] = False
                logger.warning(f"Redis pub/sub connection {conn_id} unhealthy")

                # Trigger reconnection if not already in progress
                if conn_id not in self._reconnect_tasks:
                    self._reconnect_tasks[conn_id] = asyncio.create_task(
                        self._reconnect_pubsub(conn_id)
                    )

    async def _reconnect_pubsub(self, connection_id: str) -> None:
        """Reconnect a pub/sub connection with exponential backoff"""
        attempt = 0
        delay = self.reconnect_delay

        while not self._shutdown and (self.max_reconnect_attempts == -1 or attempt < self.max_reconnect_attempts):
            try:
                attempt += 1
                self.metrics.reconnection_attempts += 1

                logger.info(f"Attempting to reconnect pub/sub connection {connection_id} (attempt {attempt})")

                # Close existing connection
                if connection_id in self._pubsub_connections:
                    try:
                        await self._pubsub_connections[connection_id].close()
                    except Exception:
                        pass

                # Create new connection
                new_connection = Redis(connection_pool=self._connection_pool)
                await new_connection.ping()

                # Resubscribe to channels
                channels = self._active_subscriptions.get(connection_id, set())
                if channels:
                    pubsub = new_connection.pubsub()
                    await pubsub.subscribe(*channels)
                    self._pubsub_connections[connection_id] = new_connection

                self._connection_healthy[connection_id] = True
                self.metrics.successful_reconnections += 1

                logger.info(f"Successfully reconnected pub/sub connection {connection_id}")
                break

            except Exception as e:
                self.metrics.connection_failures += 1
                logger.warning(f"Reconnection attempt {attempt} failed for {connection_id}: {e}")

                if not self._shutdown:
                    await asyncio.sleep(delay)
                    delay = min(delay * self.reconnect_backoff, self.max_reconnect_delay)

        # Clean up reconnection task
        if connection_id in self._reconnect_tasks:
            del self._reconnect_tasks[connection_id]

    async def publish(
        self,
        channel: str,
        message: Any,
        ensure_delivery: bool = False,
        timeout: float = 5.0
    ) -> bool:
        """
        Publish a message to a Redis channel with enhanced features.

        Args:
            channel: Channel name
            message: Message to publish
            ensure_delivery: Whether to ensure message delivery
            timeout: Publish timeout in seconds

        Returns:
            True if message was published successfully
        """
        if not self._redis or self._shutdown:
            return False

        start_time = time.time()

        try:
            # Create enhanced message
            enhanced_message = PubSubMessage(
                channel=channel,
                data=message,
                message_id=str(uuid.uuid4()),
                timestamp=time.time(),
                sequence_number=self._ordering_manager.get_next_sequence(channel) if self._ordering_manager else None
            )

            # Serialize message
            serialized_message = json.dumps(enhanced_message.to_dict())

            # Publish with timeout
            subscribers = await asyncio.wait_for(
                self._redis.publish(channel, serialized_message),
                timeout=timeout
            )

            # Update metrics
            self.metrics.messages_published += 1
            publish_latency = time.time() - start_time
            self.metrics.average_publish_latency = (
                (self.metrics.average_publish_latency * (self.metrics.messages_published - 1) + publish_latency) /
                self.metrics.messages_published
            )

            if ensure_delivery and subscribers == 0:
                logger.warning(f"No subscribers for channel {channel}")
                return False

            logger.debug(f"Published message to {channel} ({subscribers} subscribers)")
            return True

        except asyncio.TimeoutError:
            logger.error(f"Publish timeout for channel {channel}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            self.metrics.connection_failures += 1
            return False

    @asynccontextmanager
    async def subscribe(
        self,
        *channels: str,
        connection_id: str | None = None,
        auto_reconnect: bool = True
    ) -> AsyncGenerator[AsyncGenerator[PubSubMessage, None], None]:
        """
        Subscribe to Redis channels with enhanced features.

        Args:
            channels: Channel names to subscribe to
            connection_id: Optional connection identifier
            auto_reconnect: Whether to automatically reconnect on failures

        Yields:
            Async generator of enhanced messages
        """
        if not self._redis or self._shutdown:
            return

        conn_id = connection_id or f"sub_{uuid.uuid4().hex[:8]}"
        pubsub = None

        try:
            # Create dedicated connection for subscription
            connection = Redis(connection_pool=self._connection_pool)
            pubsub = connection.pubsub()

            # Subscribe to channels
            await pubsub.subscribe(*channels)
            self._pubsub_connections[conn_id] = connection
            self._active_subscriptions[conn_id].update(channels)
            self.metrics.active_subscriptions += 1

            logger.info(f"Subscribed to channels {channels} with connection {conn_id}")

            async def message_generator():
                """Generate enhanced messages from subscription"""
                try:
                    async for raw_message in pubsub.listen():
                        if raw_message['type'] == 'message':
                            try:
                                # Parse enhanced message
                                message_data = json.loads(raw_message['data'])
                                message = PubSubMessage(**message_data)

                                # Process with ordering manager if enabled
                                if self._ordering_manager:
                                    ordered_messages = self._ordering_manager.process_ordered_message(message)
                                    for ordered_message in ordered_messages:
                                        self.metrics.messages_received += 1
                                        yield ordered_message
                                else:
                                    # Simple duplicate detection
                                    if not self.duplicate_detection or self._ordering_manager.add_message(message):
                                        self.metrics.messages_received += 1
                                        yield message
                                    else:
                                        self.metrics.messages_duplicated += 1

                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning(f"Failed to parse message from {raw_message['channel']}: {e}")
                                # Fallback to simple message
                                simple_message = PubSubMessage(
                                    channel=raw_message['channel'],
                                    data=raw_message['data'],
                                    message_id=str(uuid.uuid4()),
                                    timestamp=time.time()
                                )
                                self.metrics.messages_received += 1
                                yield simple_message

                except Exception as e:
                    logger.error(f"Subscription error for connection {conn_id}: {e}")
                    if auto_reconnect and not self._shutdown:
                        # Trigger reconnection
                        if conn_id not in self._reconnect_tasks:
                            self._reconnect_tasks[conn_id] = asyncio.create_task(
                                self._reconnect_pubsub(conn_id)
                            )

            yield message_generator()

        except Exception as e:
            logger.error(f"Failed to create subscription {conn_id}: {e}")
            self.metrics.connection_failures += 1
            raise
        finally:
            # Cleanup
            if pubsub:
                try:
                    await pubsub.unsubscribe(*channels)
                    await pubsub.close()
                except Exception:
                    pass

            if conn_id in self._pubsub_connections:
                try:
                    await self._pubsub_connections[conn_id].close()
                    del self._pubsub_connections[conn_id]
                except Exception:
                    pass

            if conn_id in self._active_subscriptions:
                del self._active_subscriptions[conn_id]

            self.metrics.active_subscriptions = max(0, self.metrics.active_subscriptions - 1)
            logger.info(f"Unsubscribed from channels {channels} (connection {conn_id})")

    def get_metrics(self) -> dict[str, Any]:
        """Get current pub/sub metrics"""
        return self.metrics.to_dict()

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of all connections"""
        return {
            'healthy_connections': sum(1 for healthy in self._connection_healthy.values() if healthy),
            'total_connections': len(self._connection_healthy),
            'connection_details': dict(self._connection_healthy),
            'active_subscriptions': len(self._active_subscriptions),
            'last_health_check': self._last_health_check,
            'reconnection_tasks': len(self._reconnect_tasks)
        }

# Global enhanced pub/sub manager instance
enhanced_pubsub = EnhancedRedisPubSub()
