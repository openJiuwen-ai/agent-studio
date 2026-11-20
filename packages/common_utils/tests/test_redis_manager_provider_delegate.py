# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""RedisClientManager Phase 2 过渡委托单测：Provider 优先 / legacy 回退 / 双收口。

口径（设计文档 §十）：
  - 已装配 Provider：get_client / is_initialized / close 看到 Provider；
  - 未装配或适配层包未安装（builder 兼容）：回退 legacy，行为不变；
  - 同步客户端始终 legacy（适配层无同步面）。
"""

# pylint: disable=protected-access  # 白盒单测：直接访问/替换 _client 等内部成员

import asyncio
import sys

import pytest

from common_utils.redis_manager import (
    RedisClientManager,
    get_redis_client,
)


class _FakeSpiClient:
    """SPI 客户端替身：native_client() 返回预置原生视图（真 as_native_client 兼容）。"""

    def __init__(self, native):
        self._native = native

    def native_client(self):
        return self._native


class _FakeAsyncLegacyClient:
    """legacy 异步客户端替身：记录 aclose。"""

    def __init__(self):
        self.aclose_called = False

    async def aclose(self):
        self.aclose_called = True


class _FakeSyncLegacyClient:
    """legacy 同步客户端替身：记录 close。"""

    def __init__(self):
        self.close_called = False

    def close(self):
        self.close_called = True


@pytest.fixture
def provider_assembled(monkeypatch):
    """模拟「Provider 已装配」：accessor 三函数替换 + 返回预置原生视图。

    不触碰 accessor 真实全局状态（monkeypatch 自动恢复）。
    """
    from redis_spi import accessor

    native = object()
    provider_closed = []

    monkeypatch.setattr(accessor, "is_initialized", lambda: True)
    monkeypatch.setattr(accessor, "get_redis", lambda: _FakeSpiClient(native))

    async def fake_aclose():
        provider_closed.append(True)

    monkeypatch.setattr(accessor, "aclose", fake_aclose)
    return native, provider_closed


class TestProviderFirstDelegation:
    @staticmethod
    def test_get_client_returns_provider_view(provider_assembled, reset_common_utils_state):
        native, _ = provider_assembled
        assert RedisClientManager.get_instance().get_client() is native

    @staticmethod
    def test_module_function_delegates_too(provider_assembled, reset_common_utils_state):
        native, _ = provider_assembled
        assert get_redis_client() is native

    @staticmethod
    def test_is_initialized_true_via_provider(provider_assembled, reset_common_utils_state):
        # legacy _client 为 None，但 Provider 已装配 → 可用
        assert RedisClientManager.get_instance().is_initialized is True


class TestLegacyFallback:
    @staticmethod
    def test_get_client_falls_back_to_legacy(reset_common_utils_state):
        # Provider 未装配（真实 accessor._client 为 None，由 fixture 复位保证）
        fake = _FakeAsyncLegacyClient()
        inst = RedisClientManager.get_instance()
        inst._client = fake
        assert inst.get_client() is fake

    @staticmethod
    def test_uninitialized_raises_runtime_error(reset_common_utils_state):
        with pytest.raises(RuntimeError):
            RedisClientManager.get_instance().get_client()

    @staticmethod
    def test_package_missing_falls_back_to_legacy(reset_common_utils_state, monkeypatch):
        # builder 兼容分支：redis_spi 不可导入（sys.modules 置 None → ImportError）
        fake = _FakeAsyncLegacyClient()
        inst = RedisClientManager.get_instance()
        inst._client = fake
        monkeypatch.setitem(sys.modules, "redis_spi", None)
        assert inst.get_client() is fake
        assert inst.is_initialized is True

    @staticmethod
    def test_package_missing_uninitialized_is_false(reset_common_utils_state, monkeypatch):
        monkeypatch.setitem(sys.modules, "redis_native", None)
        inst = RedisClientManager.get_instance()
        assert inst.is_initialized is False
        with pytest.raises(RuntimeError):
            inst.get_client()


class TestClose:
    @staticmethod
    def test_close_closes_provider_and_legacy(provider_assembled, reset_common_utils_state):
        _, provider_closed = provider_assembled
        inst = RedisClientManager.get_instance()
        legacy_async = _FakeAsyncLegacyClient()
        legacy_sync = _FakeSyncLegacyClient()
        inst._client = legacy_async
        inst._sync_client = legacy_sync

        asyncio.run(inst.close())

        assert provider_closed == [True]
        assert legacy_async.aclose_called is True
        assert legacy_sync.close_called is True

    @staticmethod
    def test_close_without_provider_only_legacy(reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        legacy_async = _FakeAsyncLegacyClient()
        legacy_sync = _FakeSyncLegacyClient()
        inst._client = legacy_async
        inst._sync_client = legacy_sync

        asyncio.run(inst.close())

        assert legacy_async.aclose_called is True
        assert legacy_sync.close_called is True
