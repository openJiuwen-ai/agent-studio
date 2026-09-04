# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
AgentGroupState.save_agent_group_state 单元测试

验证保存状态时 current_agent_calls_count 被正确持久化,
避免中断恢复后计数器归零导致 max_agent_calls 上限保护失效。
"""

# pylint: disable=no-self-use

from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.multi_agent.agent_group.group_state import AgentGroupState


class TestSaveAgentGroupState:
    """验证 save_agent_group_state 正确保存各字段。"""

    @pytest.mark.asyncio
    async def test_current_agent_calls_count_is_saved(self):
        """save 后 current_agent_calls_count 应等于 control_agent 的值。"""
        state = AgentGroupState()
        runner = MagicMock()
        runner.get_state = AsyncMock(return_value=None)
        control_agent = MagicMock()
        control_agent.interrupted_agents = ["agent-1"]
        control_agent.current_agent_calls_count = 5

        await state.save_agent_group_state(runner, control_agent)

        assert state.current_agent_calls_count == 5

    @pytest.mark.asyncio
    async def test_current_agent_calls_count_zero_when_not_set(self):
        """control_agent 的 current_agent_calls_count 为 0 时也应正确保存。"""
        state = AgentGroupState()
        runner = MagicMock()
        runner.get_state = AsyncMock(return_value=None)
        control_agent = MagicMock()
        control_agent.interrupted_agents = []
        control_agent.current_agent_calls_count = 0

        await state.save_agent_group_state(runner, control_agent)

        assert state.current_agent_calls_count == 0

    @pytest.mark.asyncio
    async def test_interrupted_agents_are_copied(self):
        """interrupted_agents 应为 control_agent 的副本,而非引用。"""
        state = AgentGroupState()
        runner = MagicMock()
        runner.get_state = AsyncMock(return_value=None)
        control_agent = MagicMock()
        control_agent.interrupted_agents = ["agent-1", "agent-2"]
        control_agent.current_agent_calls_count = 3

        await state.save_agent_group_state(runner, control_agent)

        assert state.interrupted_agents == ["agent-1", "agent-2"]
        assert state.interrupted_agents is not control_agent.interrupted_agents
