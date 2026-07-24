"""Unit tests for CacheUtils (LRU + Redis two-level cache)."""
import pickle
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# We must patch the *source* modules before open_utils is ever imported,
# because open_utils creates module-level CacheUtils instances at import time.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_redis_modules():
    """Patch the Redis client factory at the open_utils import site so that
    importing open_utils (and any lazy ``get_redis_client()`` call) does not
    attempt a real Redis connection.

    The vendored ``open_utils`` now obtains both sync and async Redis clients
    through the single ``get_redis_client`` helper (imported from
    ``common_utils.redis_manager``); the old separate
    ``get_redis_instance`` / ``get_async_redis_instance`` symbols no longer
    exist. Individual tests still override ``CacheUtils._redis_cache`` /
    ``_async_redis_cache`` directly via the ``cache_utils`` fixture, so the
    return value here only needs to be a benign mock.
    """
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1

    mock_async_redis = AsyncMock()
    mock_async_redis.get.return_value = None
    mock_async_redis.set.return_value = True
    mock_async_redis.delete.return_value = 1

    with patch(
        "jiuwen.serve.controllers.execution.open_utils.get_redis_client",
        return_value=mock_async_redis,
    ):
        yield mock_redis, mock_async_redis


@pytest.fixture
def mock_redis(_patch_redis_modules):
    """Sync Redis mock (extracted from autouse fixture)."""
    return _patch_redis_modules[0]


@pytest.fixture
def mock_async_redis(_patch_redis_modules):
    """Async Redis mock (extracted from autouse fixture)."""
    return _patch_redis_modules[1]


@pytest.fixture
def cache_utils(mock_redis, mock_async_redis):
    """CacheUtils instance with mocked Redis backends."""
    from jiuwen.serve.controllers.execution.open_utils import CacheUtils

    cu = CacheUtils(
        capacity=3,
        should_serialize=True,
        cache_name="test",
        memory_ttl=2,
        redis_ttl=60,
    )
    cu._redis_cache = mock_redis  # pylint: disable=protected-access
    cu._async_redis_cache = mock_async_redis  # pylint: disable=protected-access
    return cu


class TestCacheUtilsPutGet:
    """Basic put/get cycle tests."""

    @staticmethod
    def test_put_then_get_memory_hit(cache_utils, mock_redis):
        """After put, get returns from memory (L1) without touching Redis."""
        cache_utils.put("key1", {"data": "value1"})
        mock_redis.get.reset_mock()

        result = cache_utils.get("key1")
        assert result == {"data": "value1"}
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_aput_then_aget_memory_hit(self, cache_utils, mock_async_redis):
        """Async put/get returns from memory (L1) without touching async Redis."""
        await cache_utils.aput("key1", {"data": "value1"})
        mock_async_redis.get.reset_mock()

        result = await cache_utils.aget("key1")
        assert result == {"data": "value1"}
        mock_async_redis.get.assert_not_called()

    @staticmethod
    def test_get_miss_memory_hit_redis(cache_utils, mock_redis):
        """When memory misses but Redis hits, data is returned and backfilled to memory."""
        cache_utils.put("key1", {"data": "value1"})
        # Simulate memory eviction by clearing the LRU
        cache_utils.memory_cache.clear()
        mock_redis.get.return_value = pickle.dumps(
            {"data": "value1"}, protocol=pickle.HIGHEST_PROTOCOL
        )

        result = cache_utils.get("key1")
        assert result == {"data": "value1"}

    @staticmethod
    def test_get_miss_both(cache_utils, mock_redis):
        """When both memory and Redis miss, returns None."""
        result = cache_utils.get("nonexistent")
        assert result is None


class TestCacheUtilsLRUEviction:
    """LRU capacity and eviction tests."""

    @staticmethod
    def test_lru_eviction(cache_utils):
        """When capacity is exceeded, the least-recently-used item is evicted from memory."""
        cache_utils.put("key1", "val1")
        cache_utils.put("key2", "val2")
        cache_utils.put("key3", "val3")
        # capacity=3, adding a 4th evicts key1
        cache_utils.put("key4", "val4")
        assert cache_utils.memory_cache.get("ei:engine:test:key1") is None
        # But key1 is still in Redis
        assert cache_utils.redis_cache.set.call_count == 4


class TestCacheUtilsTTL:
    """TTL expiration tests."""

    @staticmethod
    def test_memory_ttl_expiration(cache_utils, mock_redis):
        """Memory cache entries expire after memory_ttl seconds."""
        cache_utils.put("key1", "val1")
        # Wait for TTL to expire (memory_ttl=2s)
        time.sleep(2.5)
        mock_redis.get.return_value = None  # Redis also expired
        result = cache_utils.get("key1")
        assert result is None


class TestCacheUtilsPop:
    """Pop (delete) tests."""

    @staticmethod
    def test_pop_removes_from_both_layers(cache_utils, mock_redis):
        cache_utils.put("key1", "val1")
        # Redis mock.get must return a truthy value so pop() calls delete
        mock_redis.get.return_value = b"serialized"
        cache_utils.pop("key1")
        assert cache_utils.memory_cache.get("ei:engine:test:key1") is None
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_apop_removes_from_both_layers(self, cache_utils, mock_async_redis):
        await cache_utils.aput("key1", "val1")
        # Async Redis mock.get must return a truthy value so apop() calls delete
        mock_async_redis.get.return_value = b"serialized"
        await cache_utils.apop("key1")
        assert cache_utils.memory_cache.get("ei:engine:test:key1") is None
        mock_async_redis.delete.assert_called()


class TestCacheUtilsRedisDegradation:
    """Redis failure graceful degradation tests."""

    @staticmethod
    def test_get_degrades_to_memory_only_on_redis_error(cache_utils, mock_redis):
        """When Redis raises an exception, get still returns from memory."""
        cache_utils.put("key1", "val1")
        # Clear memory to force Redis lookup
        cache_utils.memory_cache.clear()
        mock_redis.get.side_effect = Exception("Redis connection refused")
        result = cache_utils.get("key1")
        # Should return None gracefully (no crash), since memory was cleared and Redis failed
        assert result is None

    @staticmethod
    def test_put_does_not_crash_on_redis_error(cache_utils, mock_redis):
        """When Redis raises on set, put still writes to memory."""
        mock_redis.set.side_effect = Exception("Redis connection refused")
        cache_utils.put("key1", "val1")
        # Memory should still have it
        result = cache_utils.get("key1")
        assert result == "val1"


class TestCacheUtilsKeyFormat:
    """Redis key format tests."""

    @staticmethod
    def test_redis_key_format(cache_utils, mock_redis):
        """Keys are prefixed with agent_runtime:{cache_name}:."""
        cache_utils.put("mykey", "val")
        call_args = mock_redis.set.call_args
        actual_key = call_args[0][0]
        assert actual_key == "agent_runtime:test:mykey"


class TestCacheUtilsTTLOverride:
    """CacheUtils aput/put ttl parameter override tests."""

    @pytest.mark.asyncio
    async def test_aput_ttl_override(self, cache_utils, mock_async_redis):
        """aput(ttl=600) passes ex=600 to Redis instead of default redis_ttl."""
        await cache_utils.aput("key1", {"data": "v1"}, ttl=600)
        call_args = mock_async_redis.set.call_args
        # The key arg: check that ex kwarg or 3rd positional arg is 600
        ex_val = call_args[1].get("ex") if call_args[1] else None
        if ex_val is None and len(call_args[0]) > 2:
            ex_val = call_args[0][2]
        assert ex_val == 600

    @pytest.mark.asyncio
    async def test_aput_ttl_minus_one_no_expiry(self, cache_utils, mock_async_redis):
        """aput(ttl=-1) means no expiry: Redis SET is called with ex=None."""
        await cache_utils.aput("key1", {"data": "v1"}, ttl=-1)
        call_args = mock_async_redis.set.call_args
        ex_val = call_args[1].get("ex") if call_args[1] else "NOT_FOUND"
        if ex_val == "NOT_FOUND" and len(call_args[0]) > 2:
            ex_val = call_args[0][2]
        assert ex_val is None

    @pytest.mark.asyncio
    async def test_aput_ttl_none_uses_default(self, cache_utils, mock_async_redis):
        """aput(ttl=None) or aput() uses self.redis_ttl as ex."""
        await cache_utils.aput("key1", {"data": "v1"})
        call_args = mock_async_redis.set.call_args
        ex_val = call_args[1].get("ex") if call_args[1] else None
        if ex_val is None and len(call_args[0]) > 2:
            ex_val = call_args[0][2]
        # redis_ttl=60 for this fixture (see cache_utils fixture: memory_ttl=2, redis_ttl=60)
        assert ex_val == 60

    @staticmethod
    def test_put_ttl_override(mock_redis, cache_utils):
        """put(ttl=600) passes ex=600 to Redis."""
        cache_utils.put("key1", {"data": "v1"}, ttl=600)
        call_args = mock_redis.set.call_args
        ex_val = call_args[1].get("ex") if call_args[1] else None
        if ex_val is None and len(call_args[0]) > 2:
            ex_val = call_args[0][2]
        assert ex_val == 600

    @staticmethod
    def test_put_ttl_minus_one_no_expiry(mock_redis, cache_utils):
        """put(ttl=-1) means no expiry: Redis SET is called with ex=None."""
        cache_utils.put("key1", {"data": "v1"}, ttl=-1)
        call_args = mock_redis.set.call_args
        ex_val = call_args[1].get("ex") if call_args[1] else "NOT_FOUND"
        if ex_val == "NOT_FOUND" and len(call_args[0]) > 2:
            ex_val = call_args[0][2]
        assert ex_val is None

