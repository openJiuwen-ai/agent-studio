# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Tests for R07 fix: Agent instance cache isolation by conversation_id.

Covers fix R07: when AGENT_CACHE_ENABLE=true, Agent instances were cached
by ir_path only, causing cross-session state leakage. The fix changes the
cache key to f"{conversation_id}:{ir_path}" and adds empty-conversation_id
defense.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.controller.common.config import AgentConfig


def _make_agent_config(ir_path="agent/ir/test_agent.json", is_published=True):
    """Create a minimal AgentConfig for testing."""
    return AgentConfig(
        task_id="task-001",
        agent_id="agent-001",
        ir_path=ir_path,
        is_published=is_published,
    )


@pytest.fixture
def mock_caches():
    """Patch cache_agent_queue and cache_agent_config with AsyncMocks."""
    with patch(
        "jiuwen.multi_agent.core.member_instance_manager.cache_agent_queue"
    ) as mock_queue, patch(
        "jiuwen.multi_agent.core.member_instance_manager.cache_agent_config"
    ) as mock_config:
        mock_queue.aget = AsyncMock(return_value=None)
        mock_queue.aput = AsyncMock(return_value=None)
        mock_config.aget = AsyncMock(return_value=None)
        mock_config.aput = AsyncMock(return_value=None)
        yield mock_queue, mock_config


@pytest.fixture
def mock_timed_cache_op():
    """Patch timed_cache_op to pass through the coroutine without timing logic."""
    async def _passthrough(_label, coro, _key):
        return await coro

    with patch(
        "jiuwen.multi_agent.core.member_instance_manager.timed_cache_op",
        side_effect=_passthrough,
    ):
        yield


class TestR07CrossSessionIsolation:
    """R07: 不同会话的 Agent 实例缓存按 conversation_id 隔离。"""

    @pytest.mark.asyncio
    async def test_different_conversation_ids_use_different_cache_keys(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """两个不同 conversation_id 的 aput key 应该不同。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, mock_config = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        fake_agent_a = MagicMock(name="agent_a")
        fake_agent_b = MagicMock(name="agent_b")
        member_class = MagicMock(side_effect=[fake_agent_a, fake_agent_b])

        # 会话 A
        mgr_a = MemberInstanceManager(conversation_id="conv-A")
        mgr_a.register_member_type("member-1", member_class, config)
        await mgr_a._lazy_load_member("member-1")

        # 会话 B
        mgr_b = MemberInstanceManager(conversation_id="conv-B")
        mgr_b.register_member_type("member-1", member_class, config)
        await mgr_b._lazy_load_member("member-1")

        # 验证 aput 被调用了两次，且 key 不同
        assert mock_queue.aput.call_count == 2
        key_a = mock_queue.aput.call_args_list[0][0][0]
        key_b = mock_queue.aput.call_args_list[1][0][0]
        assert key_a == "conv-A:agent/ir/test_agent.json"
        assert key_b == "conv-B:agent/ir/test_agent.json"
        assert key_a != key_b

    @pytest.mark.asyncio
    async def test_different_conversation_ids_get_different_instances(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """两个不同 conversation_id 应该获得不同的 agent 实例。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, _ = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        fake_agent_a = MagicMock(name="agent_a")
        fake_agent_b = MagicMock(name="agent_b")
        member_class = MagicMock(side_effect=[fake_agent_a, fake_agent_b])

        # 会话 A
        mgr_a = MemberInstanceManager(conversation_id="conv-A")
        mgr_a.register_member_type("member-1", member_class, config)
        member_a = await mgr_a._lazy_load_member("member-1")

        # 会话 B
        mgr_b = MemberInstanceManager(conversation_id="conv-B")
        mgr_b.register_member_type("member-1", member_class, config)
        member_b = await mgr_b._lazy_load_member("member-1")

        # 验证实例不同
        assert member_a._agent is fake_agent_a  # pylint: disable=protected-access
        assert member_b._agent is fake_agent_b  # pylint: disable=protected-access
        assert member_a._agent is not member_b._agent  # pylint: disable=protected-access


class TestR07SameSessionReuse:
    """R07: 相同 conversation_id 跨轮复用 Agent 实例。"""

    @pytest.mark.asyncio
    async def test_same_conversation_id_hits_cache(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """相同 conversation_id 第二次调用应命中缓存，不新建实例。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, _ = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        cached_agent = MagicMock(name="cached_agent")
        member_class = MagicMock(return_value=MagicMock(name="should_not_be_called"))

        # 第一次调用：cache miss → 新建 + aput
        mgr = MemberInstanceManager(conversation_id="conv-X")
        mgr.register_member_type("member-1", member_class, config)
        await mgr._lazy_load_member("member-1")

        # 第二次调用：模拟 cache hit
        # 先清除 active_members 让它重新走 _lazy_load_member
        mgr._active_members.clear()
        mock_queue.aget.return_value = cached_agent
        member2 = await mgr._lazy_load_member("member-1")

        # 验证第二次返回的是缓存的实例
        assert member2._agent is cached_agent  # pylint: disable=protected-access
        # member_class 只应被调用一次（第一次 miss 时）
        assert member_class.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_key_contains_conversation_id(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """aget/aput 的 key 必须包含 conversation_id。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, _ = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        member_class = MagicMock(return_value=MagicMock())

        mgr = MemberInstanceManager(conversation_id="conv-key-test")
        mgr.register_member_type("member-1", member_class, config)
        await mgr._lazy_load_member("member-1")

        # 验证 aget 和 aput 的 key 都包含 conversation_id
        aget_key = mock_queue.aget.call_args[0][0]
        aput_key = mock_queue.aput.call_args[0][0]
        assert "conv-key-test" in aget_key
        assert "conv-key-test" in aput_key
        assert aget_key == aput_key


class TestR07EmptyConversationIdDefense:
    """R07: 空 conversation_id 时强制关闭缓存，避免退化为按 ir_path 共享。"""

    @pytest.mark.asyncio
    async def test_empty_conversation_id_disables_cache(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """conversation_id='' + AGENT_CACHE_ENABLE=true → 不调用缓存。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, mock_config = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config(is_published=True)
        member_class = MagicMock(return_value=MagicMock(name="agent"))

        mgr = MemberInstanceManager(conversation_id="")
        mgr.register_member_type("member-1", member_class, config)
        await mgr._lazy_load_member("member-1")

        # 验证缓存完全不被调用
        mock_queue.aget.assert_not_called()
        mock_queue.aput.assert_not_called()
        mock_config.aget.assert_not_called()
        mock_config.aput.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_conversation_id_still_creates_instance(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """空 conversation_id 时仍应正常创建实例。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, _ = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        fake_agent = MagicMock(name="agent")
        member_class = MagicMock(return_value=fake_agent)

        mgr = MemberInstanceManager(conversation_id="")
        mgr.register_member_type("member-1", member_class, config)
        member = await mgr._lazy_load_member("member-1")

        assert member._agent is fake_agent  # pylint: disable=protected-access
        assert member_class.call_count == 1


class TestR07CacheDisabled:
    """R07: AGENT_CACHE_ENABLE=false 时不走缓存。"""

    @pytest.mark.asyncio
    async def test_cache_disabled_no_cache_calls(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """AGENT_CACHE_ENABLE=false → 不调用缓存。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "false")
        mock_queue, mock_config = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        member_class = MagicMock(return_value=MagicMock())

        mgr = MemberInstanceManager(conversation_id="conv-1")
        mgr.register_member_type("member-1", member_class, config)
        await mgr._lazy_load_member("member-1")

        mock_queue.aget.assert_not_called()
        mock_queue.aput.assert_not_called()
        mock_config.aget.assert_not_called()
        mock_config.aput.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_disabled_creates_new_instance_each_time(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """AGENT_CACHE_ENABLE=false → 每次新建实例。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "false")
        mock_queue, _ = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        agent1 = MagicMock(name="agent1")
        agent2 = MagicMock(name="agent2")
        member_class = MagicMock(side_effect=[agent1, agent2])

        mgr = MemberInstanceManager(conversation_id="conv-1")
        mgr.register_member_type("member-1", member_class, config)
        member1 = await mgr._lazy_load_member("member-1")

        # 清除 active_members，再次加载
        mgr._active_members.clear()
        member2 = await mgr._lazy_load_member("member-1")

        assert member1._agent is agent1  # pylint: disable=protected-access
        assert member2._agent is agent2  # pylint: disable=protected-access
        assert member1._agent is not member2._agent  # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_unpublished_agent_skips_cache(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """is_published=False → 不走缓存。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, mock_config = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config(is_published=False)
        member_class = MagicMock(return_value=MagicMock())

        mgr = MemberInstanceManager(conversation_id="conv-1")
        mgr.register_member_type("member-1", member_class, config)
        await mgr._lazy_load_member("member-1")

        mock_queue.aget.assert_not_called()
        mock_queue.aput.assert_not_called()


class TestR07AgentConfigSingleton:
    """R07: AgentConfig 单例层跨会话共享。"""

    @pytest.mark.asyncio
    async def test_config_cached_once_shared_across_sessions(
        self, mock_caches, mock_timed_cache_op, monkeypatch
    ):
        """两个不同会话：AgentConfig 只 aput 一次，第二次 aget 命中。"""
        monkeypatch.setenv("AGENT_CACHE_ENABLE", "true")
        mock_queue, mock_config = mock_caches

        from jiuwen.multi_agent.core.member_instance_manager import (
            MemberInstanceManager,
        )

        config = _make_agent_config()
        member_class = MagicMock(return_value=MagicMock())

        # 会话 A：config cache miss → aput
        mgr_a = MemberInstanceManager(conversation_id="conv-A")
        mgr_a.register_member_type("member-1", member_class, config)
        await mgr_a._lazy_load_member("member-1")

        # 会话 B：config cache hit → 返回同一 config
        cached_config = mock_config.aget.return_value
        mock_config.aget.return_value = config  # 模拟 L2 命中
        mgr_b = MemberInstanceManager(conversation_id="conv-B")
        mgr_b.register_member_type("member-1", member_class, config)
        await mgr_b._lazy_load_member("member-1")

        # config 的 aput 只调用一次（会话 A 首次 miss+put）
        assert mock_config.aput.call_count == 1
        # config 的 aget 调用了两次（两个会话各一次）
        assert mock_config.aget.call_count == 2
