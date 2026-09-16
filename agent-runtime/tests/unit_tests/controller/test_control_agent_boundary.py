# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 单元测试需直接验证内部方法 _select_agent_with_cycle_check 行为
"""Tests for control_agent.py — max_agent_calls 边界判断 (>= 语义, 对齐 lumina-engine upstream)。

修复前(2fe87a96): current_agent_calls_count > max_agent_calls 才进入循环检测
修复后(af74e40):   current_agent_calls_count >= max_agent_calls 进入循环检测
即 "恰好达到最大次数" 时触发 _detect_cycle()：检测到循环 → 返回 (main_agent, True)
走默认工作流；未检测到循环 → 返回 (None, False) 正常结束，不报错。
"""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_COMMON_UTILS = os.path.join(_REPO_ROOT, "packages", "common_utils")
if os.path.isdir(_COMMON_UTILS) and _COMMON_UTILS not in sys.path:
    sys.path.insert(0, _COMMON_UTILS)

from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.multi_agent.agent_group.hierarchical_group.control_agent import (
    HierarchicalControlAgent,
)


def _make_agent(max_agent_calls=5):
    """创建 HierarchicalControlAgent 实例，绕过构造器外部依赖。"""
    obj = HierarchicalControlAgent.__new__(HierarchicalControlAgent)
    obj.current_agent_calls_count = 0
    obj.call_agent_history = []
    # mock config
    obj.config = MagicMock()
    obj.config.max_agent_calls = max_agent_calls
    obj.config.main_agent = MagicMock()
    obj.config.main_agent.metadata.id = "main-agent-id"
    return obj


class TestSelectAgentWithCycleCheckBoundary:
    """_select_agent_with_cycle_check — >= 边界判断。"""

    @pytest.mark.asyncio
    async def test_count_equal_max_without_cycle_returns_none(self):
        """执行次数恰好等于最大调用次数且无循环时，返回 (None, False) 正常结束。"""
        agent = _make_agent(max_agent_calls=5)
        agent.current_agent_calls_count = 5  # 恰好等于 max

        # mock select_agent 确保循环检测分支下不被调用
        agent.select_agent = AsyncMock(return_value="agent-1")
        # mock _detect_cycle 返回 False（无循环 → 正常结束）
        agent._detect_cycle = MagicMock(return_value=False)

        result_agent_id, has_cycle = await agent._select_agent_with_cycle_check({})

        # count >= max → 进入循环检测，_detect_cycle 返回 False → 返回 (None, False)
        assert result_agent_id is None
        assert has_cycle is False
        agent.select_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_count_equal_max_with_cycle_returns_main(self):
        """执行次数恰好等于最大调用次数且检测到循环时，返回 (main_agent, True) 走默认工作流。"""
        agent = _make_agent(max_agent_calls=5)
        agent.current_agent_calls_count = 5  # 恰好等于 max
        agent.call_agent_history = ["agent-a", "agent-b", "agent-a", "agent-b"]

        agent.select_agent = AsyncMock(return_value="agent-1")
        agent._detect_cycle = MagicMock(return_value=True)

        result_agent_id, has_cycle = await agent._select_agent_with_cycle_check({})

        assert result_agent_id == "main-agent-id"
        assert has_cycle is True
        agent.select_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_count_greater_than_max_triggers_cycle_check(self):
        """执行次数超过最大调用次数时，应进入循环检测分支。"""
        agent = _make_agent(max_agent_calls=5)
        agent.current_agent_calls_count = 6  # 超过 max

        agent.select_agent = AsyncMock(return_value="agent-1")
        agent._detect_cycle = MagicMock(return_value=False)

        result_agent_id, has_cycle = await agent._select_agent_with_cycle_check({})

        # count > max → 进入循环检测，_detect_cycle 返回 False → 返回 (None, False)
        assert result_agent_id is None
        assert has_cycle is False
        agent.select_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_count_greater_than_max_with_cycle_detected(self):
        """执行次数超过最大且检测到循环时，应返回 main_agent 并标记循环。"""
        agent = _make_agent(max_agent_calls=3)
        agent.current_agent_calls_count = 4  # 超过 max
        agent.call_agent_history = ["agent-a", "agent-b", "agent-a", "agent-b"]

        agent.select_agent = AsyncMock(return_value="agent-1")
        agent._detect_cycle = MagicMock(return_value=True)

        result_agent_id, has_cycle = await agent._select_agent_with_cycle_check({})

        assert result_agent_id == "main-agent-id"
        assert has_cycle is True
        agent.select_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_count_less_than_max_normal_flow(self):
        """执行次数小于最大调用次数时，应正常调用 select_agent。"""
        agent = _make_agent(max_agent_calls=10)
        agent.current_agent_calls_count = 3

        agent.select_agent = AsyncMock(return_value="agent-2")
        agent._detect_cycle = MagicMock(return_value=False)

        result_agent_id, has_cycle = await agent._select_agent_with_cycle_check({})

        assert result_agent_id == "agent-2"
        assert has_cycle is False
        agent.select_agent.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_equal_max_with_zero_max(self):
        """边界: max_agent_calls=0, count=0 → 恰好相等进入循环检测分支。"""
        agent = _make_agent(max_agent_calls=0)
        agent.current_agent_calls_count = 0

        agent.select_agent = AsyncMock(return_value="agent-x")
        agent._detect_cycle = MagicMock(return_value=False)

        result_agent_id, has_cycle = await agent._select_agent_with_cycle_check({})

        # count >= max(0) → 进入循环检测，无循环 → 返回 (None, False)
        assert result_agent_id is None
        assert has_cycle is False
