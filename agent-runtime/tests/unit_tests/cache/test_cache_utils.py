"""Unit tests for CacheUtils (LRU + Redis two-level cache)."""
import asyncio
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


class TestCacheUtilsTTLRefresh:
    """Redis 命中时 should_refresh_ttl 续期行为测试。"""

    @pytest.mark.asyncio
    async def test_aget_redis_hit_refreshes_ttl(self, cache_utils, mock_async_redis):
        """aget Redis 命中且 should_refresh_ttl=True 时 expire 以 redis_ttl 续期。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}
        mock_async_redis.expire.assert_called_once_with(
            "agent_runtime:test:key1", 60
        )
        # 续期成功后内存条目必须记录刷新时刻（否则节流失效、多发 EXPIRE）
        assert (
            cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] > 0
        )

    @pytest.mark.asyncio
    async def test_aget_memory_hit_skips_expire(self, cache_utils, mock_async_redis):
        """内存命中时即使 should_refresh_ttl=True 也不发 expire（热路径零 Redis 开销）。"""
        await cache_utils.aput("key1", {"data": "v1"})
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}
        mock_async_redis.get.assert_not_called()
        mock_async_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_aget_expire_failure_returns_value(
        self, cache_utils, mock_async_redis
    ):
        """expire 抛异常时 aget 仍返回已取到的 value（续期失败不影响读取）。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        mock_async_redis.expire.side_effect = Exception("redis expire failed")
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}

    @pytest.mark.asyncio
    async def test_aget_deserialize_failure_returns_none(
        self, cache_utils, mock_async_redis
    ):
        """deserialize 失败必须落入外层 except 返回 None，且不污染内存层。

        钉死内层防御 try 只包 expire 不包 deserialize：若误包，损坏 bytes 会
        回填内存层，后续内存命中持续返回 bytes 且失去 MISS 自愈。
        """
        mock_async_redis.get.return_value = b"corrupted-pickle"
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result is None
        # 内存层未被污染：不得从内存拿到原始 bytes
        assert (
            cache_utils._get_from_memory_cache("agent_runtime:test:key1") is None  # pylint: disable=protected-access
        )

    @pytest.mark.asyncio
    async def test_memory_expiry_redis_hit_backfill(
        self, cache_utils, mock_async_redis
    ):
        """memory_ttl 过期 → Redis 命中 → expire 续期 → 回填内存 → 再次读取命中内存。"""
        await cache_utils.aput("key1", {"data": "v1"})
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v2"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        time.sleep(2.5)  # memory_ttl=2，等内存过期
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        # 取到的是 Redis 里的 v2，证明内存已过期并从 Redis 回填
        assert result == {"data": "v2"}
        mock_async_redis.expire.assert_called_once_with(
            "agent_runtime:test:key1", 60
        )
        # 回填后再次读取应命中内存，不再碰 Redis
        mock_async_redis.get.reset_mock()
        mock_async_redis.expire.reset_mock()
        result2 = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result2 == {"data": "v2"}
        mock_async_redis.get.assert_not_called()
        mock_async_redis.expire.assert_not_called()


class TestAgetWithSourceTTLRefresh:
    """aget_with_source 续期行为测试。"""

    @pytest.mark.asyncio
    async def test_redis_hit_refreshes_ttl(self, cache_utils, mock_async_redis):
        """should_refresh_ttl=True 时 Redis 命中以 redis_ttl 续期。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        value, source = await cache_utils.aget_with_source(
            "key1", should_refresh_ttl=True
        )
        assert value == {"data": "v1"}
        assert source == "redis"
        mock_async_redis.expire.assert_called_once_with(
            "agent_runtime:test:key1", 60
        )

    @pytest.mark.asyncio
    async def test_no_refresh_by_default(self, cache_utils, mock_async_redis):
        """默认不续期：不传参数时 Redis 命中不发 expire。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        value, source = await cache_utils.aget_with_source("key1")
        assert value == {"data": "v1"}
        assert source == "redis"
        mock_async_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_expire_failure_returns_value(self, cache_utils, mock_async_redis):
        """expire 抛异常时不影响 aget_with_source 返回值。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        mock_async_redis.expire.side_effect = Exception("redis expire failed")
        value, source = await cache_utils.aget_with_source(
            "key1", should_refresh_ttl=True
        )
        assert value == {"data": "v1"}
        assert source == "redis"


class TestCacheTTLConfigDefaults:
    """新增 TTL 配置字段默认值与下界校验。

    注意：open_utils 的队列在 import 时构造、settings 亦在 import 时实例化，
    config→队列的接线无法用单测覆盖，只能靠 review 把关。
    """

    @staticmethod
    def test_default_ttl_values(monkeypatch):
        from agent_runtime.common.config import CacheSettings

        for var in (
            "IR_CACHE_TTL_SECONDS",
            "WORKFLOW_CACHE_TTL_SECONDS",
            "AGENT_CACHE_TTL_SECONDS",
        ):
            monkeypatch.delenv(var, raising=False)
        cs = CacheSettings()
        assert cs.ir_cache_ttl_seconds == 24 * 60 * 60
        assert cs.workflow_cache_ttl_seconds == 24 * 60 * 60
        assert cs.agent_cache_ttl_seconds == 24 * 60 * 60

    @staticmethod
    def test_ttl_rejects_non_positive(monkeypatch):
        """TTL 配置为 0 时应校验失败，防止 set(ex=0) 写入即删的静默失效。"""
        from pydantic import ValidationError

        from agent_runtime.common.config import CacheSettings

        monkeypatch.setenv("WORKFLOW_CACHE_TTL_SECONDS", "0")
        with pytest.raises(ValidationError):
            CacheSettings()


class TestBackgroundTTLRefresh:
    """内存命中的节流后台续期测试（"有调用即保活"语义）。"""

    @pytest.mark.asyncio
    async def test_aput_marks_last_refresh(self, cache_utils, mock_async_redis):
        """aput 写入且 Redis set 成功后，内存条目记录 Redis 刷新时刻。"""
        await cache_utils.aput("key1", {"data": "v1"})
        assert (
            cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] > 0
        )

    @pytest.mark.asyncio
    async def test_memory_hit_triggers_background_refresh(
        self, cache_utils, mock_async_redis
    ):
        """距上次刷新超过节流间隔的内存命中，会后台 EXPIRE 续期且不阻塞返回。"""
        await cache_utils.aput("key1", {"data": "v1"})
        # 模拟上次 Redis 刷新发生在 400s 前（超过 300s 节流间隔）
        cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] = (
            time.time() - 400
        )
        mock_async_redis.expire.reset_mock()
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}
        await asyncio.sleep(0.05)  # 给后台任务执行机会
        mock_async_redis.expire.assert_called_once_with(
            "agent_runtime:test:key1", 60
        )

    @pytest.mark.asyncio
    async def test_memory_hit_throttled_within_interval(
        self, cache_utils, mock_async_redis
    ):
        """节流间隔内的重复内存命中不重复发起 EXPIRE。"""
        await cache_utils.aput("key1", {"data": "v1"})
        mock_async_redis.expire.reset_mock()
        # aput 刚标记 last_refresh=now，处于间隔内
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}
        await asyncio.sleep(0.05)
        mock_async_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_aget_with_source_memory_hit_triggers_background_refresh(
        self, cache_utils, mock_async_redis
    ):
        """aget_with_source 内存命中同样支持节流后台续期。"""
        await cache_utils.aput("key1", {"data": "v1"})
        cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] = (
            time.time() - 400
        )
        mock_async_redis.expire.reset_mock()
        value, source = await cache_utils.aget_with_source(
            "key1", should_refresh_ttl=True
        )
        assert value == {"data": "v1"}
        assert source == "memory"
        await asyncio.sleep(0.05)
        mock_async_redis.expire.assert_called_once_with(
            "agent_runtime:test:key1", 60
        )

    @pytest.mark.asyncio
    async def test_background_failure_rolls_back_marker(
        self, cache_utils, mock_async_redis
    ):
        """后台 EXPIRE 失败时回滚乐观标记，下次内存命中会重试。"""
        await cache_utils.aput("key1", {"data": "v1"})
        cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] = (
            time.time() - 400
        )
        mock_async_redis.expire.side_effect = Exception("redis down")
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}  # 读取不受后台失败影响
        await asyncio.sleep(0.05)
        assert (
            cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"]
            == -1.0
        )

    @pytest.mark.asyncio
    async def test_throttle_interval_shrinks_with_small_ttl(
        self, mock_redis, mock_async_redis
    ):
        """小 TTL 配置下节流窗口自动收紧为 TTL/2，续期不静默失效。"""
        from jiuwen.serve.controllers.execution.open_utils import CacheUtils

        cu = CacheUtils(
            capacity=3, should_serialize=True, cache_name="test_small",
            memory_ttl=2, redis_ttl=60,
        )
        cu._redis_cache = mock_redis  # pylint: disable=protected-access
        cu._async_redis_cache = mock_async_redis  # pylint: disable=protected-access
        await cu.aput("key1", {"data": "v1"})
        key = "agent_runtime:test_small:key1"

        # 距上次刷新 40s > 60/2=30 → 触发（若窗口仍是固定 300s 则不会触发）
        cu.memory_cache[key]["last_refresh"] = time.time() - 40
        mock_async_redis.expire.reset_mock()
        await cu.aget("key1", should_refresh_ttl=True)
        await asyncio.sleep(0.05)
        mock_async_redis.expire.assert_called_once_with(key, 60)

        # 距上次刷新 20s < 30 → 节流不触发
        cu.memory_cache[key]["last_refresh"] = time.time() - 20
        mock_async_redis.expire.reset_mock()
        await cu.aget("key1", should_refresh_ttl=True)
        await asyncio.sleep(0.05)
        mock_async_redis.expire.assert_not_called()


class TestCorruptedEntrySelfHealing:
    """损坏缓存条目与 Redis 条目丢失的自愈行为测试。"""

    @pytest.mark.asyncio
    async def test_corrupted_pickle_deleted_and_raised(
        self, cache_utils, mock_async_redis
    ):
        """aget_with_source 命中损坏 pickle 时：删除该 key、抛出原异常，且不续期。

        修复回归点：若先续期再 deserialize，损坏条目会被无限刷新而永不自愈。
        """
        from jiuwen.common.exception.base import JiuWenBaseException

        mock_async_redis.get.return_value = b"corrupted-pickle"
        with pytest.raises(JiuWenBaseException):
            await cache_utils.aget_with_source("key1", should_refresh_ttl=True)
        # 损坏条目被删除（下次读取 miss → 回源重建）
        mock_async_redis.delete.assert_called_once_with("agent_runtime:test:key1")
        # 损坏条目不得被续命
        mock_async_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_corrupted_pickle_aget_returns_none(
        self, cache_utils, mock_async_redis
    ):
        """aget 命中损坏 pickle 时返回 None（上层回源重建），且不续期。"""
        mock_async_redis.get.return_value = b"corrupted-pickle"
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result is None
        mock_async_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_expire_false_triggers_rewrite(
        self, cache_utils, mock_async_redis
    ):
        """后台 EXPIRE 返回 False（key 被外部删除）时，用内存值重写重建条目。

        修复回归点：expire 对不存在的 key 返回 False 而非抛异常，若不检查
        返回值，Redis 条目丢失后在内存存活期间永远无法重建。
        """
        await cache_utils.aput("key1", {"data": "v1"})
        cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] = (
            time.time() - 400
        )
        # expire 返回 False：模拟 key 已被外部删除/淘汰
        mock_async_redis.expire.return_value = False
        mock_async_redis.set.reset_mock()
        await cache_utils.aget("key1", should_refresh_ttl=True)
        await asyncio.sleep(0.05)
        # 验证用内存值整体重写（set 被再次调用，携带新 TTL）
        mock_async_redis.set.assert_called_once()
        call_args = mock_async_redis.set.call_args
        ex_val = call_args[1].get("ex") if call_args[1] else None
        assert ex_val == 60
        assert call_args[0][0] == "agent_runtime:test:key1"


class TestDirectExpireReturnValue:
    """Redis 命中直接续期路径检查 expire 布尔返回值的测试。"""

    @pytest.mark.asyncio
    async def test_aget_expire_false_not_marked(self, cache_utils, mock_async_redis):
        """GET 命中但 expire 返回 False（两命令间 key 被删）时不误标已刷新。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        mock_async_redis.expire.return_value = False
        result = await cache_utils.aget("key1", should_refresh_ttl=True)
        assert result == {"data": "v1"}  # 数据仍正确返回
        # 未标记 → 下次内存命中立即走后台续期（发现 False 后 aput 重写自愈）
        assert (
            cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] == -1.0
        )

    @pytest.mark.asyncio
    async def test_aget_with_source_expire_false_not_marked(
        self, cache_utils, mock_async_redis
    ):
        """aget_with_source 同款：expire False 不误标。"""
        mock_async_redis.get.return_value = pickle.dumps(
            {"data": "v1"}, protocol=pickle.HIGHEST_PROTOCOL
        )
        mock_async_redis.expire.return_value = False
        value, source = await cache_utils.aget_with_source(
            "key1", should_refresh_ttl=True
        )
        assert value == {"data": "v1"}
        assert source == "redis"
        assert (
            cache_utils.memory_cache["agent_runtime:test:key1"]["last_refresh"] == -1.0
        )


class TestSyncBuildWorkflowDrainsBackgroundTasks:
    """sync_build_workflow 临时事件循环的后台任务回收测试。"""

    @staticmethod
    def test_background_task_drained_and_loop_closed(mock_async_redis):
        """临时循环上创建的后台续期任务在返回前被执行，不随循环悬挂。

        修复回归点：sync_build_workflow 用 new_event_loop 包裹 build_workflow，
        若返回前不运行后台任务，任务会悬挂在已停止的循环上（且持引用阻止
        循环对象及其 fd 被 GC），重复同步构建持续累积。
        """
        from unittest.mock import patch as mock_patch

        from jiuwen.orchestration.flow import workflow as wf_mod
        from jiuwen.serve.controllers.execution.open_utils import CacheUtils

        cu = CacheUtils(
            capacity=3, should_serialize=True, cache_name="t_sync",
            memory_ttl=3600, redis_ttl=60,
        )
        cu._async_redis_cache = mock_async_redis  # pylint: disable=protected-access

        async def fake_build(data, **kwargs):
            await cu.aput("k", {"v": 1})
            # 模拟距上次刷新超节流窗口，使 aget 内存命中时创建后台续期任务
            cu.memory_cache["agent_runtime:t_sync:k"]["last_refresh"] = (
                time.time() - 400
            )
            value = await cu.aget("k", should_refresh_ttl=True)
            assert value == {"v": 1}
            return "BUILT"

        mock_async_redis.expire.reset_mock()
        with mock_patch.object(wf_mod, "build_workflow", fake_build):
            result = wf_mod.sync_build_workflow({"ir_path": "x"})
        assert result == "BUILT"
        # drain 生效：后台任务在临时循环上执行完毕（修复前任务悬挂、expire 不被调用）
        mock_async_redis.expire.assert_called_once_with(
            "agent_runtime:t_sync:k", 60
        )

    @staticmethod
    def test_drain_from_worker_thread(mock_async_redis):
        """非主线程（APS worker 场景）调用 drain 不因 get_event_loop 失败。

        修复回归点：drain 若用 asyncio.gather，会在无默认事件循环的
        工作线程触发 RuntimeError。
        """
        import threading

        from jiuwen.serve.controllers.execution.open_utils import (
            CacheUtils,
            drain_background_ttl_tasks,
        )

        cu = CacheUtils(
            capacity=3, should_serialize=True, cache_name="t_thread",
            memory_ttl=3600, redis_ttl=60,
        )
        cu._async_redis_cache = mock_async_redis  # pylint: disable=protected-access
        key = "agent_runtime:t_thread:k"
        result = {}

        def worker():
            async def fake_build():
                await cu.aput("k", {"v": 1})
                cu.memory_cache[key]["last_refresh"] = time.time() - 400
                return await cu.aget("k", should_refresh_ttl=True)

            loop = asyncio.new_event_loop()
            try:
                result["value"] = loop.run_until_complete(fake_build())
                result["drained"] = drain_background_ttl_tasks(loop)
            finally:
                loop.close()

        mock_async_redis.expire.reset_mock()
        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=10)
        assert result["value"] == {"v": 1}
        assert result["drained"] is True
        mock_async_redis.expire.assert_called_once_with(key, 60)

