"""
Redis caching layer for improved performance.

This module provides caching utilities for frequently accessed data,
with support for TTL, serialization, and cache invalidation patterns.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
import redis.asyncio as redis
from redis.asyncio import Redis
import pickle
import hashlib

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheManager:
    """Redis-based cache manager with performance optimizations"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.redis_url
        self.enabled = settings.cache_enabled
        self.default_ttl = settings.cache_ttl
        self._redis: Optional[Redis] = None
        
        if not self.enabled:
            logger.info("Caching is disabled")
    
    async def connect(self) -> None:
        """Connect to Redis"""
        if not self.enabled:
            return
            
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("Connected to Redis cache", extra={
                "redis_url": self.redis_url.split('@')[0] + '@[REDACTED]' if '@' in self.redis_url else self.redis_url
            })
            
        except Exception as e:
            logger.error("Failed to connect to Redis", extra={
                "error": str(e),
                "redis_url": self.redis_url.split('@')[0] + '@[REDACTED]' if '@' in self.redis_url else self.redis_url
            })
            self.enabled = False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis cache")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and available"""
        return self.enabled and self._redis is not None
    
    def _generate_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """Generate cache key with consistent hashing"""
        key_parts = [prefix, identifier]
        
        # Add sorted kwargs for consistent key generation
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_suffix = hashlib.md5(
                json.dumps(sorted_kwargs, sort_keys=True).encode()
            ).hexdigest()[:8]
            key_parts.append(key_suffix)
        
        return ":".join(key_parts)
    
    def _serialize(self, data: Any) -> bytes:
        """Serialize data for storage"""
        try:
            # Try JSON first for simple types
            if isinstance(data, (dict, list, str, int, float, bool)) or data is None:
                return json.dumps(data).encode('utf-8')
        except (TypeError, ValueError):
            pass
        
        # Fall back to pickle for complex objects
        return pickle.dumps(data)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data from storage"""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self._redis:
            return None
        
        try:
            data = await self._redis.get(key)
            if data is None:
                return None
            
            return self._deserialize(data)
            
        except Exception as e:
            logger.warning("Cache get failed", extra={
                "key": key,
                "error": str(e)
            })
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (defaults to default_ttl)
            nx: Only set if key doesn't exist
            
        Returns:
            True if set successfully
        """
        if not self.enabled or not self._redis:
            return False
        
        try:
            serialized_data = self._serialize(value)
            ttl = ttl or self.default_ttl
            
            result = await self._redis.set(
                key, 
                serialized_data, 
                ex=ttl,
                nx=nx
            )
            
            return bool(result)
            
        except Exception as e:
            logger.warning("Cache set failed", extra={
                "key": key,
                "ttl": ttl,
                "error": str(e)
            })
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self._redis:
            return False
        
        try:
            result = await self._redis.delete(key)
            return result > 0
            
        except Exception as e:
            logger.warning("Cache delete failed", extra={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled or not self._redis:
            return 0
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                result = await self._redis.delete(*keys)
                logger.info("Deleted keys by pattern", extra={
                    "pattern": pattern,
                    "count": result
                })
                return result
            return 0
            
        except Exception as e:
            logger.warning("Cache pattern delete failed", extra={
                "pattern": pattern,
                "error": str(e)
            })
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self._redis:
            return False
        
        try:
            result = await self._redis.exists(key)
            return result > 0
            
        except Exception as e:
            logger.warning("Cache exists check failed", extra={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key (-1 if no expiry, -2 if key doesn't exist)"""
        if not self.enabled or not self._redis:
            return -2
        
        try:
            return await self._redis.ttl(key)
            
        except Exception as e:
            logger.warning("Cache TTL check failed", extra={
                "key": key,
                "error": str(e)
            })
            return -2
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment counter in cache"""
        if not self.enabled or not self._redis:
            return 0
        
        try:
            result = await self._redis.incr(key, amount)
            
            # Set TTL if this is a new key
            if result == amount and ttl:
                await self._redis.expire(key, ttl)
            
            return result
            
        except Exception as e:
            logger.warning("Cache increment failed", extra={
                "key": key,
                "amount": amount,
                "error": str(e)
            })
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self._redis:
            return {
                "enabled": False,
                "connected": False
            }
        
        try:
            info = await self._redis.info()
            return {
                "enabled": True,
                "connected": True,
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            }
        except Exception as e:
            logger.error("Failed to get cache stats", extra={"error": str(e)})
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }
    
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish a message to a Redis channel.
        
        Args:
            channel: Channel name
            message: Message to publish (will be JSON serialized)
            
        Returns:
            Number of subscribers that received the message
        """
        if not self.enabled or not self._redis:
            return 0
            
        try:
            serialized_message = json.dumps(message) if not isinstance(message, str) else message
            return await self._redis.publish(channel, serialized_message)
        except Exception as e:
            logger.error("Failed to publish message", extra={
                "channel": channel,
                "error": str(e)
            })
            return 0
    
    async def subscribe(self, *channels: str):
        """
        Subscribe to Redis channels and return an async iterator.
        
        Args:
            channels: Channel names to subscribe to
            
        Yields:
            Dict with 'channel' and 'data' keys for each message
        """
        if not self.enabled or not self._redis:
            logger.warning("Redis not available for pub/sub subscription")
            # Return empty async generator
            return
            yield  # This makes it an async generator but never yields anything
            
        pubsub = None
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(*channels)
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Try to parse as JSON, fallback to string
                        data = json.loads(message['data'])
                    except (json.JSONDecodeError, TypeError):
                        data = message['data']
                    
                    yield {
                        'channel': message['channel'],
                        'data': data
                    }
        except Exception as e:
            logger.error("Failed to subscribe to channels", extra={
                "channels": channels,
                "error": str(e)
            })
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(*channels)
                    await pubsub.close()
                except Exception:
                    pass


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
async def get_cached(key: str) -> Optional[Any]:
    """Get value from cache"""
    return await cache_manager.get(key)


async def set_cached(
    key: str, 
    value: Any, 
    ttl: Optional[int] = None
) -> bool:
    """Set value in cache"""
    return await cache_manager.set(key, value, ttl)


async def delete_cached(key: str) -> bool:
    """Delete key from cache"""
    return await cache_manager.delete(key)


async def cache_key(prefix: str, identifier: str, **kwargs) -> str:
    """Generate cache key"""
    return cache_manager._generate_key(prefix, identifier, **kwargs)


# Cache decorators for common patterns
def cached_result(prefix: str, ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = {
                "args": str(args),
                "kwargs": sorted(kwargs.items()) if kwargs else []
            }
            cache_key = cache_manager._generate_key(
                prefix, 
                func.__name__, 
                **key_data
            )
            
            # Try to get from cache first
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug("Cache hit", extra={
                    "function": func.__name__,
                    "cache_key": cache_key
                })
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            
            logger.debug("Cache miss - stored result", extra={
                "function": func.__name__,
                "cache_key": cache_key
            })
            
            return result
        return wrapper
    return decorator