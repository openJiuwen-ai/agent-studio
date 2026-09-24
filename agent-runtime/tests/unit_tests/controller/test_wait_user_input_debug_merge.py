# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""Tests for WaitUserInput 调试记录合并修复。

多智能体「等待输入」(action_after_completion=WaitUserInput) 场景下，调试记录
本应合并为一条，却每轮新建一条。根因是 manager 端合并依赖两个 SSE 事件：
第一轮 workflow_blocked（缓存 executionId）、第二轮 workflow_resume（取回缓存并
合并）。WaitUserInput 链路两者都缺失，本文件的两个修复分别补齐：

- 修复1 (control_mode._handle_workflow_completion): WAITING_USER_INPUT 分支补发
  workflow_blocked，与 questioner 中断链路同构。
- 修复2 (control_agent.select_agent/execute): 恢复被中断 agent 时补发
  workflow_resume。
"""
# pylint: disable=protected-access
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from jiuwen.controller.agent.control_mode.control_mode import ControllerMode
from jiuwen.controller.common.enum import ActionAfterCompletionType, WorkflowType
from jiuwen.multi_agent.agent_group.hierarchical_group.control_agent import (
    HierarchicalControlAgent,
)
from jiuwen.multi_agent.core.member import MemberMessageType
from jiuwen.orchestration.flow.stream.base import StreamCode


class TestWaitingUserInputEmitsBlocked:
    """修复1 — WAITING_USER_INPUT 完成分支补发 workflow_blocked。"""

    @staticmethod
    def _make_mode(action_after_completion):
        """构造仅含被测分支所需依赖的 ControllerMode，绕过 __init__。"""
        mode = ControllerMode.__new__(ControllerMode)
        mode.task_id = "task-xyz"
        mode.terminate = False
        mode.task_end = False

        # context_manager.get_workflow_context_by_name_and_type -> workflow_context
        # current_node_info 模拟工作流跑完后的末节点（真实场景为结束节点）
        current_node = SimpleNamespace(
            node_id="node_end",
            node_name="结束",
            node_type="jiuwen.end",
            execution_id="exec-1",
            workflow_id="wf-1",
            workflow_name="唐诗生成工作流",
        )
        workflow_context = MagicMock()
        workflow_context.action_after_completion = action_after_completion
        workflow_context.workflow_name = "唐诗生成工作流"
        workflow_context.current_node_info = current_node

        ctx_mgr = MagicMock()
        ctx_mgr.get_workflow_context_by_name_and_type.return_value = workflow_context
        ctx_mgr.controller_context.processed_workflow_names = []
        ctx_mgr.is_end_workflow_completed.return_value = False
        ctx_mgr.get_end_workflow_contexts.return_value = None
        mode.context_manager = ctx_mgr

        mode.task_planner = MagicMock()
        return mode

    @staticmethod
    def _completion_message():
        msg = MagicMock()
        msg.message_type = "WORKFLOW_COMPLETION"
        msg.content = {
            "workflow_name": "唐诗生成工作流",
            "workflow_type": WorkflowType.GENERAL,
        }
        return msg

    def test_wait_user_input_yields_workflow_blocked(self):
        """WaitUserInput：应 yield 一个 code=WORKFLOW_BLOCKED_MESSAGE 的 StreamData。"""
        mode = self._make_mode(ActionAfterCompletionType.WAITING_USER_INPUT)
        chunks = list(
            mode._handle_workflow_completion(
                self._completion_message(), "task_workflow_1", "唐诗"
            )
        )
        blocked = [
            c for c in chunks
            if getattr(c, "code", None) == StreamCode.WORKFLOW_BLOCKED_MESSAGE.value
        ]
        assert len(blocked) == 1
        assert blocked[0].execution_id == "task-xyz"
        # manager 端 blockHandler 消费该事件缓存 executionId；data 为跳转调试数据
        assert blocked[0].data["query"] == "唐诗"
        assert blocked[0].data["workflow_name"] == "唐诗生成工作流"
        # terminate 仍被置位（保持原有「等待输入」行为）
        assert mode.terminate is True

    def test_continue_action_does_not_emit_blocked(self):
        """非 WaitUserInput（CONTINUE）：不应补发 workflow_blocked，避免误标 block。"""
        mode = self._make_mode(ActionAfterCompletionType.CONTINUE)
        chunks = list(
            mode._handle_workflow_completion(
                self._completion_message(), "task_workflow_1", "唐诗"
            )
        )
        blocked = [
            c for c in chunks
            if getattr(c, "code", None) == StreamCode.WORKFLOW_BLOCKED_MESSAGE.value
        ]
        assert blocked == []
        assert mode.terminate is False


class TestResumeInterruptedAgentEmitsWorkflowResume:
    """修复2 — 恢复被中断 agent 时补发 workflow_resume。"""

    @staticmethod
    def _make_agent():
        agent = HierarchicalControlAgent.__new__(HierarchicalControlAgent)
        agent.current_agent_calls_count = 0
        agent.call_agent_history = []
        agent.interrupted_agents = []
        agent.agents = {"agent-1", "main-agent-id"}
        agent._resumed_from_interrupt = False
        agent.config = MagicMock()
        agent.config.main_agent.metadata.id = "main-agent-id"
        return agent

    @pytest.mark.asyncio
    async def test_select_interrupted_agent_sets_resume_flag(self):
        """存在被中断 agent 时，select_agent 返回它并置位 _resumed_from_interrupt。"""
        agent = self._make_agent()
        agent.interrupted_agents = ["agent-1"]

        selected = await agent.select_agent({"inputs": "宋词"})

        assert selected == "agent-1"
        assert agent._resumed_from_interrupt is True
        assert agent.interrupted_agents == []  # LIFO pop 已消费

    @pytest.mark.asyncio
    async def test_select_main_agent_does_not_set_resume_flag(self):
        """无中断 agent（首轮）：走 main agent，不置 resume 标记，避免误发 resume。"""
        agent = self._make_agent()

        selected = await agent.select_agent({"inputs": "唐诗"})

        assert selected == "main-agent-id"
        assert agent._resumed_from_interrupt is False

    @pytest.mark.asyncio
    async def test_handoff_takes_priority_over_resume_flag(self):
        """handoff 上下文优先级最高：即便有中断 agent 也走 handoff，不误置 resume。"""
        agent = self._make_agent()
        agent.interrupted_agents = ["agent-1"]
        inputs = {"inputs": "x", "handoff_context": {"to_agent": "main-agent-id"}}

        selected = await agent.select_agent(inputs)

        assert selected == "main-agent-id"
        assert agent._resumed_from_interrupt is False

    @staticmethod
    def test_resume_message_is_stream_workflow_resume():
        """补发的 resume 消息应为 STREAM 类型、code=WORKFLOW_RESUME_MESSAGE。"""
        msg = HierarchicalControlAgent._create_workflow_resume_message("agent-1")

        assert msg.type == MemberMessageType.STREAM
        assert msg.data.code == StreamCode.WORKFLOW_RESUME_MESSAGE.value
        assert msg.data.data["agent_id"] == "agent-1"
