# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""链级 trace 输入/输出采集回归测试。

背景：``astream(self, inputs, ...)`` 的 ``inputs`` 是显式形参，服务层按位置传入
``req.query``；若仅依赖 ``kwargs`` 传递，``_setup_trace_manager`` 里
``kwargs.get("inputs")`` 恒为 None，导致 OTel 链级 span 的
``OJ_WORKFLOW_INPUTS`` 永远缺失。同理 Controller/default 模式此前硬编码
``on_chain_end(None)``，链级输出也永远为空。

本文件锁定修复后的行为：
1. ``inputs`` 显式透传至 ``on_chain_start``，且不污染下游 ``kwargs``；
2. Controller / default 分支用 ``_collect_chain_output()`` 采集最终输出；
3. ReAct / ToolUse 分支仍以 ``self.result`` 上报，行为不变；
4. 采集失败/上下文无结果时上报 None 且不影响业务流程。
"""
# pylint: disable=protected-access
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
for _pkg in ("common_utils", "storage", "model_service"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.append(_pkg_path)

from jiuwen.controller.agent import agent as agent_module
from jiuwen.controller.agent.agent import Agent
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import RetCode


def _make_agent(result=None):
    """构造不触发真实模型/网络的最小 Agent 实例。"""
    agent = Agent.__new__(Agent)
    agent.result = result
    agent.context_manager = MagicMock()
    agent.control_mode = MagicMock()
    # 非 Controller / 非 ReAct，避免 prepare_execution 走额外分支
    agent.control_mode.plan_config.plan_mode = "PlanExecute"
    return agent


def _make_trace_manager():
    trace_manager = MagicMock()
    trace_manager.on_chain_start = AsyncMock()
    trace_manager.on_chain_end = AsyncMock()
    trace_manager.on_chain_error = AsyncMock()
    return trace_manager


async def _source(items):
    for item in items:
        yield item


async def _collect_stream(agen):
    return [item async for item in agen]


@pytest.mark.asyncio
async def test_astream_passes_real_inputs_to_on_chain_start():
    """astream("hello") 必须把真实输入透传给 on_chain_start，而非 None。"""
    agent = _make_agent()
    agent._initialize_chat_history = MagicMock()
    agent.get_tools = AsyncMock(return_value=([], [], []))
    agent._inject_skills_if_needed = AsyncMock(
        return_value=([], MagicMock(prompt_suffix=""))
    )
    agent._build_stream_params = MagicMock(return_value={})
    agent._patch_system_prompt = MagicMock(return_value="origin-prompt")
    agent._restore_system_prompt = MagicMock()

    async def _empty_mode(stream_params, trace_manager):
        if False:  # pragma: no cover - 保证是异步生成器
            yield None

    agent._execute_stream_by_mode = _empty_mode

    trace_manager = _make_trace_manager()
    runtime_context = SimpleNamespace(
        agent_workflow_context={WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY: {}}
    )

    with patch.object(
        agent_module.TraceManager, "generate_manager", return_value=trace_manager
    ) as generate_manager, patch.object(
        agent_module, "get_instance_info", return_value={}
    ), patch.object(agent_module, "get_agent_identity", return_value=None):
        items = await _collect_stream(
            agent.astream("hello", runtime_context=runtime_context)
        )

    assert items == []
    trace_manager.on_chain_start.assert_awaited_once_with("hello")
    first_arg = trace_manager.on_chain_start.await_args.args[0]
    assert first_arg == "hello" and first_arg is not None
    generate_manager.assert_called_once()

    # 下游 kwargs 不应被注入 "inputs"（避免污染共享参数）
    passed_kwargs = agent.get_tools.call_args.args[1]
    assert "inputs" not in passed_kwargs
    # 仅保留调用方显式传入的 runtime_context（trace_handlers/session 已被 pop）
    assert set(passed_kwargs) == {"runtime_context"}


@pytest.mark.asyncio
async def test_controller_mode_reports_final_output():
    """Controller 分支：on_chain_end 收到上下文最终结果的 content。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.return_value = SimpleNamespace(
        role="assistant", content="controller-final-answer"
    )
    trace_manager = _make_trace_manager()

    items = await _collect_stream(
        agent._handle_controller_mode_stream(_source([{"chunk": 1}]), trace_manager)
    )

    assert items == [{"chunk": 1}]
    trace_manager.on_chain_end.assert_awaited_once_with("controller-final-answer")


@pytest.mark.asyncio
async def test_default_mode_reports_final_output():
    """default 分支：on_chain_end 收到上下文最终结果的 content。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.return_value = SimpleNamespace(
        role="assistant", content="default-final-answer"
    )
    trace_manager = _make_trace_manager()

    items = await _collect_stream(
        agent._handle_default_mode_stream(_source([{"chunk": 2}]), trace_manager)
    )

    assert items == [{"chunk": 2}]
    trace_manager.on_chain_end.assert_awaited_once_with("default-final-answer")


@pytest.mark.asyncio
async def test_react_result_unchanged():
    """ReAct 回归：self.result 仍原样上报给 on_chain_end。"""
    agent = _make_agent(result="react-final-result")
    trace_manager = _make_trace_manager()

    items = await _collect_stream(
        agent._handle_react_mode_stream(_source([]), trace_manager)
    )

    assert items == ["react-final-result"]
    trace_manager.on_chain_end.assert_awaited_once_with("react-final-result")


@pytest.mark.asyncio
async def test_tooluse_success_item_still_sets_result():
    """ToolUse 回归：SUCCESS 结果仍写入 self.result 并上报。"""
    agent = _make_agent()
    trace_manager = _make_trace_manager()

    items = await _collect_stream(
        agent._handle_tooluse_mode_stream(
            _source(
                [{"ret_code": RetCode.SUCCESS, "result": "tooluse-final-result"}]
            ),
            trace_manager,
        )
    )

    assert agent.result == "tooluse-final-result"
    assert items == ["tooluse-final-result"]
    trace_manager.on_chain_end.assert_awaited_once_with("tooluse-final-result")


@pytest.mark.asyncio
async def test_context_message_exception_reports_none_without_raising():
    """取上下文消息抛异常时：上报 None，不中断流程、不掩盖异常。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.side_effect = RuntimeError("boom")
    trace_manager = _make_trace_manager()

    items = await _collect_stream(
        agent._handle_default_mode_stream(_source([{"chunk": 3}]), trace_manager)
    )

    assert items == [{"chunk": 3}]
    trace_manager.on_chain_end.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_missing_context_message_reports_none():
    """上下文无结果消息且无 assistant 消息时上报 None。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.return_value = None
    agent.context_manager.get_latest_assistant_message.return_value = None
    trace_manager = _make_trace_manager()

    items = await _collect_stream(
        agent._handle_controller_mode_stream(_source([]), trace_manager)
    )

    assert items == []
    trace_manager.on_chain_end.assert_awaited_once_with(None)


def test_falls_back_to_latest_assistant_message():
    """无 result_message 时回退到最新 assistant 消息的 content。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.return_value = None
    agent.context_manager.get_latest_assistant_message.return_value = SimpleNamespace(
        role="assistant", content="assistant-latest-content"
    )

    assert agent._collect_chain_output() == "assistant-latest-content"


@pytest.mark.parametrize("blank", ["", "   ", "\n\t ", None])
def test_blank_content_returns_none(blank):
    """空白 content（含 None）视为无输出。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.return_value = SimpleNamespace(
        role="assistant", content=blank
    )

    assert agent._collect_chain_output() is None


def test_self_result_takes_priority():
    """self.result 优先于上下文消息。"""
    agent = _make_agent(result="react-result")
    agent.context_manager.get_result_message.return_value = SimpleNamespace(
        role="assistant", content="context-result"
    )

    assert agent._collect_chain_output() == "react-result"
    agent.context_manager.get_result_message.assert_not_called()


def test_plain_string_message_returned_as_is():
    """结果消息本身是字符串时直接返回该字符串。"""
    agent = _make_agent()
    agent.context_manager.get_result_message.return_value = "plain-string-output"

    assert agent._collect_chain_output() == "plain-string-output"


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_mode", ["Controller", "ReAct"])
async def test_prepare_execution_passes_inputs_in_controller_and_react(plan_mode):
    """Controller / ReAct 模式下 inputs 同样必须透传到 on_chain_start。"""
    agent = _make_agent()
    agent.control_mode.plan_config.plan_mode = plan_mode
    agent._initialize_chat_history = MagicMock()
    agent.update_controller_global_variables = MagicMock()
    agent._handle_react_mode_variables = AsyncMock()
    trace_manager = _make_trace_manager()
    runtime_context = SimpleNamespace(
        agent_workflow_context={WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY: {}}
    )

    with patch.object(
        agent_module.TraceManager, "generate_manager", return_value=trace_manager
    ), patch.object(agent_module, "get_instance_info", return_value={}), patch.object(
        agent_module, "get_agent_identity", return_value=None
    ):
        query, prompt_info, _, returned_manager = await agent.prepare_execution(
            "hi", {"runtime_context": runtime_context}
        )

    assert query == "hi"
    assert prompt_info is None
    assert returned_manager is trace_manager
    trace_manager.on_chain_start.assert_awaited_once_with("hi")
    if plan_mode == "Controller":
        agent.update_controller_global_variables.assert_called_once_with(
            runtime_context
        )
        agent._handle_react_mode_variables.assert_not_awaited()
    else:
        agent._handle_react_mode_variables.assert_awaited_once_with(runtime_context)
        agent.update_controller_global_variables.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler_name",
    ["_handle_controller_mode_stream", "_handle_default_mode_stream"],
)
async def test_stream_handlers_still_yield_self_result(handler_name):
    """self.result 有值时，Controller/default 分支仍会把它补发到流中。"""
    agent = _make_agent(result="tail-result")
    agent.context_manager.get_result_message.return_value = None
    agent.context_manager.get_latest_assistant_message.return_value = None
    trace_manager = _make_trace_manager()

    handler = getattr(agent, handler_name)
    items = await _collect_stream(handler(_source([{"chunk": 4}]), trace_manager))

    assert items == [{"chunk": 4}, "tail-result"]
    trace_manager.on_chain_end.assert_awaited_once_with("tail-result")
