#!/usr/bin/env python
"""
南向契约测试 -- ReAct mode agent (LLM 多工具调用 case 010)

=== 测试目标 ===
验证 ReAct 模式下，Agent 同时配置多种工具类型（插件 + 工作流）时，
LLM 能根据用户 query 正确路由到不同工 SSE 响应数据帧
的结构和内容符合契约。

=== 被测链路 ===
  用户请求 → IR 加载 → Agent 实例化 → ReactMode 控制循环
    → LLM 调用 → 工具路由（plugin_handler / workflow_handler）
    → 工具执行 → [LLM 再次调用] → SSE 响应流

=== 同一会话三轮请求（与原始客户端测试一致） ===
  第1轮: calculator_tool 插件（LLM×2 → plugin×1 → workflow×0）
  第2轮: workflow_react_tools 工作流（LLM×1 → plugin×0 → workflow×1）
  第3轮: mock_plugin_add 插件（LLM×2 → plugin×1 → workflow×0）

=== 核心设计 ===
  - 南向打桩：在框架即将发出外部调用的位置替换（5 路 monkeypatch）
  - LLM mock 在 BaseChatModel.astream 级别（而非 LLMModule.stream_function_call），
    保留框架的 _format_yield_result 流式处理逻辑
  - 可编程 Mock：Recording Runtime 同时充当 Stub（预设返回）和 Spy（记录调用）
  - 契约参考：resource/ 下的 txt 文件是从真实环境录制的 mock 数据

=== 验证维度 ===
  - SSE 数据帧：事件类型、字段结构、业务数据
  - 调用计数：LLM / Plugin / Workflow 的调用次数
  - 参数透传：tool_call 参数是否正确传递到工具执行层
  - 工具互斥：插件请求不触发工作流，反之亦然

详细设计文档见同目录 DESIGN.md。

用法：
  pytest -v test_case_llm_react_multy_tools_010.py
"""

__all__ = [
    "TestCaseLLMReactMultyTools010",
]

import asyncio
import json
import os
import time
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from jiuwen.test.cases.workflow_node.test_case_llm_react_multy_tools_010.test_workflow_react_tools import (
    create_workflow_react_tools,
)

# ---------------------------------------------------------------------------
# 环境变量预设（必须在 import jiuwen 之前设置）
# ---------------------------------------------------------------------------
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")
os.environ.setdefault("PLUGIN_SSL_API_CERT_KEY", "false")
os.environ["USE_TOOL_WRAPPER"] = "true"
os.environ.setdefault("USE_OPENJIUWEN_WORKFLOW", "true")
os.environ.setdefault("WORKFLOW_EXECUTE_TIMEOUT", "1200")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage, ToolCall, UsageMetadata
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.integration.agent_core_restful_new import AgentCoreRestfulLayer
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.plugin.models.tool import WORKFLOW_END_TYPE
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import distribute_execution_request
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest


# ---------------------------------------------------------------------------
# 路径常量
# - CASE_DIR: 本测试用例目录
# - PACKAGE_DIR: jiuwen 包根目录（CASE_DIR 向上 4 级：test_case → react_mode_agent → cases → test → jiuwen）
# - RESOURCE_TEMPLATE_DIR: 默认 prompt 模板目录，JiuWen.init() 需要
# - AGENT_DIR / WORKFLOW_DIR: Agent IR 和 Workflow IR 所在目录
# ---------------------------------------------------------------------------
CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[3]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
AGENT_DIR = CASE_DIR / "agent"
WORKFLOW_DIR = CASE_DIR / "workflow"
RESOURCE_DIR = CASE_DIR / "resource"

# ---------------------------------------------------------------------------
# Workflow ID（与 workflow IR 中的 workflowId 字段保持一致）
# 用于：1) 工作流 mock 的 scripted_by_workflow_id 键
#       2) test_2 中校验 workflow_runtime.calls[0]["workflow_id"]
# ---------------------------------------------------------------------------
WORKFLOW_ID = "1e2c49af-f38b-41b4-9129-af3f694c3f35"


# ===================================================================
# Mock 基础设施（共享层）
#
# 架构概览：
#   _IntegrationRegistry（进程级单例）
#       ├── .model    → _LocalModelAdapter → _RecordingModelRuntime
#       ├── .workflow  → _LocalWorkflowAdapter → _RecordingWorkflowRuntime
#       └── .plugin    → _RecordingPluginRuntime
#
# 每个 Recording Runtime 同时充当：
#   - Stub：按预设脚本返回确定性结果（scripted_outputs / scripted_by_name）
#   - Spy：记录所有调用的参数和顺序（calls 列表），供断言阶段验证
# ===================================================================
class _IntegrationRegistry:
    """进程级单例，注册 Mock Model / Workflow / Plugin 运行时。

    每个测试方法开始时通过 set_xxx() 注入预设的 mock，
    结束时调用 clear() 清理，防止测试间状态泄漏。
    """

    model = None
    workflow = None
    plugin = None

    @classmethod
    def clear(cls):
        cls.model = None
        cls.workflow = None
        cls.plugin = None

    @classmethod
    def set_model(cls, model):
        cls.model = model

    @classmethod
    def get_model(cls):
        return cls.model

    @classmethod
    def set_workflow(cls, workflow):
        cls.workflow = workflow

    @classmethod
    def get_workflow(cls):
        return cls.workflow

    @classmethod
    def set_plugin(cls, plugin):
        cls.plugin = plugin

    @classmethod
    def get_plugin(cls):
        return cls.plugin


class _FakeWorkflowSession:
    """模拟工作流会话，提供 get_state / update_state 接口。

    真实环境中工作流会话由 GraphEngine 管理，这里用简单的 dict 替代。
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._state = {}

    def get_state(self, key=None):
        if key is None:
            return dict(self._state)
        return self._state.get(key)

    def update_state(self, payload: dict):
        self._state.update(payload)


class _LocalModelAdapter:
    """将 _RecordingModelRuntime 适配为 _IntegrationRegistry.model 接口。

    提供 ainvoke 和 astream 方法。astream 是本测试的核心打桩点，
    直接替换 BaseChatModel.astream，保留框架的 _format_yield_result 逻辑。
    """

    def __init__(self, runtime):
        self.runtime = runtime

    async def ainvoke(self, inputs, **kwargs):
        if hasattr(self.runtime, "ainvoke"):
            return await self.runtime.ainvoke(inputs, **kwargs)
        return await self.runtime.invoke(inputs, **kwargs)

    async def astream(self, inputs, **kwargs):
        """async generator，yield AIMessage 对象。"""
        if hasattr(self.runtime, "astream"):
            async for item in self.runtime.astream(inputs, **kwargs):
                yield item


class _LocalWorkflowAdapter:
    """将 _RecordingWorkflowRuntime 适配为 _IntegrationRegistry.workflow 接口。

    提供 create_session / get_runtime_context / astream 方法，
    模拟真实工作流引擎的会话管理和流式执行。
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.sessions = {}

    def create_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session is None:
            session = _FakeWorkflowSession(session_id)
            self.sessions[session_id] = session
        return session

    def get_runtime_context(self, session):
        return session.get_state()

    async def astream(
        self, *, query, params, workflow_id, agent_id="", session_id="", context=None
    ):
        runner = getattr(self.runtime, "astream", None)
        if runner is None:
            runner = self.runtime.stream
        return runner(
            {"inputs": query, "params": params},
            session_id=session_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            context=context,
        )


@dataclass
class _ModelCall:
    inputs: Any
    model_id: str
    session_id: str
    kwargs: dict


@dataclass
class _PluginCall:
    tool_name: str
    inputs: dict


class _FallbackChatModel(BaseChatModel):
    """Deterministic fallback when no scripted output is configured."""

    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _RecordingModelRuntime:
    """可编程 LLM Mock，通过 astream 返回 AIMessage 流。

    核心设计：
      - astream 是 async generator，yield AIMessage 对象
      - 中间 chunk: finish_reason=""
      - 最终 chunk: finish_reason="function_call" 或 "stop"
      - ainvoke 用于 IntentionDetectModule 的非流式调用

    用法：
        runtime = _RecordingModelRuntime([
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="calc", args={"expr": "1+1"})],
                usage_metadata=UsageMetadata(
                    code=0, errmsg="成功", finish_reason="function_call",
                ),
            ),
            AIMessage(
                content='{"result": "2"}',
                usage_metadata=UsageMetadata(
                    code=0, errmsg="成功", finish_reason="stop",
                ),
            ),
        ])
        # ... 执行测试 ...
        assert len(runtime.calls) == 2          # Spy: 验证调用次数
        assert runtime.calls[0].inputs == ...   # Spy: 验证调用参数
    """

    def __repr__(self):
        return f"_RecordingModelRuntime(outputs_left={len(self.scripted_outputs)})"

    def __init__(self, scripted_outputs):
        self.scripted_outputs = list(scripted_outputs)
        self.calls = []

    async def ainvoke(self, inputs, session_id=None, **kwargs):
        """兼容 IntentionDetectModule._execute_llm_call 的 ainvoke 调用。"""
        self.calls.append(
            _ModelCall(
                inputs=inputs,
                model_id=kwargs.pop("model_id", ""),
                session_id=session_id or "",
                kwargs=kwargs,
            )
        )
        if self.scripted_outputs:
            return self.scripted_outputs.pop(0)
        return AIMessage(content="0")

    async def astream(self, inputs, **kwargs):
        """async generator，yield AIMessage 对象。

        模拟真实 LLM 的流式返回：
          1. yield 一个空内容的中间 chunk (finish_reason="")
          2. yield 最终 chunk (finish_reason="function_call" 或 "stop")
             包含完整的 tool_calls 和 usage_metadata
        """
        self.calls.append(
            _ModelCall(
                inputs=inputs,
                model_id=kwargs.pop("model_id", ""),
                session_id=kwargs.pop("session_id", ""),
                kwargs=kwargs,
            )
        )
        if self.scripted_outputs:
            final_msg = self.scripted_outputs.pop(0)
        else:
            final_msg = AIMessage(content="0")

        # 中间 chunk：空内容，finish_reason 为空
        yield AIMessage(
            content="",
            usage_metadata=UsageMetadata(code=0, errmsg="成功", finish_reason=""),
        )
        # 最终 chunk：包含完整的 tool_calls 和正确的 finish_reason
        if not final_msg.usage_metadata:
            fr = "function_call" if final_msg.tool_calls else "stop"
            final_msg.usage_metadata = UsageMetadata(
                code=0,
                errmsg="成功",
                finish_reason=fr,
            )
        yield final_msg


class _RecordingPluginRuntime:
    """可编程 Plugin Mock，按插件名返回预设结果，同时记录所有调用。

    用法：
        runtime = _RecordingPluginRuntime({
            "calculator_tool": [{"result": "18"}],   # calculator_tool 第1次调用返回
            "mock_plugin_add": [{"result": "12啦啦啦"}],
        })
        # ... 执行测试 ...
        assert len(runtime.calls) == 1
        assert runtime.calls[0].tool_name == "calculator_tool"
    """

    def __init__(self, scripted_by_name):
        self.scripted_by_name = {k: list(v) for k, v in scripted_by_name.items()}
        self.calls = []

    async def execute(self, tool_name, inputs):
        self.calls.append(_PluginCall(tool_name=tool_name, inputs=inputs))
        results = self.scripted_by_name.get(tool_name, [])
        if results:
            data = results.pop(0)
        else:
            data = {"result": "mock_result"}
        return {"errCode": 0, "errMessage": "success", "data": data}


class _RecordingWorkflowRuntime:
    """可编程 Workflow Mock，按 workflow_id 返回预设 SSE 事件序列。

    用法：
        runtime = _RecordingWorkflowRuntime({
            WORKFLOW_ID: [[  # 第1次调用返回的事件序列
                _build_workflow_start_stream_data(workflow_id=WORKFLOW_ID),
                _build_end_stream_data(answer="气温20度"),
            ]],
        })
        # ... 执行测试 ...
        assert len(runtime.calls) == 1
        assert runtime.calls[0]["workflow_id"] == WORKFLOW_ID
    """

    def __init__(self, scripted_by_workflow_id):
        self.scripted_by_workflow_id = {
            key: list(value) for key, value in scripted_by_workflow_id.items()
        }
        self.calls = []

    def stream(
        self, inputs, session_id=None, workflow_id=None, agent_id=None, context=None
    ):
        self.calls.append(
            {
                "inputs": inputs,
                "query": inputs.get("inputs", ""),
                "params": inputs.get("params", {}),
                "session_id": session_id or "",
                "workflow_id": workflow_id or "",
                "agent_id": agent_id or "",
                "context": context,
            }
        )
        scripted_events = self.scripted_by_workflow_id.get(workflow_id, [])
        if scripted_events:
            events = scripted_events.pop(0)
        else:
            events = [_build_end_stream_data(answer="workflow default")]

        async def _iterate():
            for item in events:
                yield item

        return _iterate()


class _WorkflowInstanceAdapter:
    """模拟 WorkflowHandler.create_workflow_instance 返回的工作流实例。

    真实环境中由 GraphEngine 创建，这里用 handler 函数模拟 astream/ainvoke 行为，
    并提供 graph_engine.graph_instance 属性以满足框架对工作流实例结构的要求。
    """

    def __init__(
        self,
        *,
        astream_handler,
        ainvoke_handler,
        state_getter,
        status_getter,
        cleanup_handler,
        runtime_context=None,
    ):
        self._astream_handler = astream_handler
        self._ainvoke_handler = ainvoke_handler
        self._state_getter = state_getter
        self._status_getter = status_getter
        self._cleanup_handler = cleanup_handler
        self.runtime_context = runtime_context

        class _GraphInstance:
            def __init__(self, ctx):
                self.runtime_context = ctx

            async def async_clean_up(self):
                return None

            def get_state(self):
                return {}

            def get_workflow_execute_status(self):
                return None

        self.graph_engine = type(
            "_GraphEngine",
            (),
            {"graph_instance": _GraphInstance(runtime_context)},
        )()

    async def astream(self, *args, **workflow_input):
        # ReAct 模式下 workflow handler 会以位置参数调用 astream
        if args:
            workflow_input["inputs"] = args[0]
            if len(args) > 1 and isinstance(args[1], dict):
                workflow_input.update(args[1])
        return await self._astream_handler(**workflow_input)

    async def ainvoke(self, **workflow_input):
        return await self._ainvoke_handler(**workflow_input)

    def get_workflow_execute_status(self):
        return self._status_getter()

    async def async_clean_up(self):
        result = self._cleanup_handler()
        if asyncio.iscoroutine(result):
            await result


# ===================================================================
# SSE StreamData 构建器
#
# 用于构建 Workflow mock 返回的 SSE 事件序列。
# 每个构建器对应一种 StreamCode 事件类型：
#   - PARTIAL_CONTENT (1206): 节点输出的部分内容
#   - MESSAGE_END (5000): 消息节点输出完成
#   - WORKFLOW_END (4000): 工作流结束
#   - FINISH (0): 工作流彻底结束
#   - WORKFLOW_START (3000): 工作流开始
#
# 事件序列参考 resource/mock_react_workflow_input_and_output.txt
# ===================================================================
def _build_partial_stream_data(
    *,
    answer: str,
    node_id: str,
    node_name: str,
    node_type: str,
    should_interrupt: bool = False,
):
    """构建 PARTIAL_CONTENT 事件（code=1206）。"""
    return StreamData(
        code=StreamCode.PARTIAL_CONTENT.value,
        msg=StreamDataMsg.SUCCESS.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "should_interrupt": should_interrupt,
        },
        execution_id="",
    )


def _build_message_end_stream_data(
    *,
    answer: str,
    node_id: str,
    node_name: str,
    node_type: str,
    should_interrupt: bool = False,
):
    """构建 MESSAGE_END 事件（消息组件输出后结束）。"""
    return StreamData(
        code=StreamCode.MESSAGE_END.value,
        msg=StreamDataMsg.MESSAGE_END.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "should_interrupt": should_interrupt,
            "enable_history": True,
        },
        execution_id="",
    )


def _build_workflow_end_stream_data(
    *,
    answer: str,
    node_id: str = "node_end",
    node_name: str = "结束",
    node_type: str = None,
    should_interrupt: bool = False,
):
    """构建 WORKFLOW_END 事件（code=4000），通常紧接 FINISH 之前。"""
    nt = node_type or WORKFLOW_END_TYPE
    return StreamData(
        code=StreamCode.WORKFLOW_END.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": nt,
            "should_interrupt": should_interrupt,
        },
        execution_id="",
    )


def _build_end_stream_data(*, answer: str):
    """构建 FINISH 事件（workflow 彻底结束）。"""
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": "node_end",
            "node_name": "node_end",
            "node_type": WORKFLOW_END_TYPE,
            "should_interrupt": False,
            "user_fields": {},
        },
        execution_id="",
    )


def _build_workflow_start_stream_data(*, workflow_id: str):
    """构建 WORKFLOW_START 事件（code=3000）。"""
    return StreamData(
        code=StreamCode.WORKFLOW_START.value,
        msg=StreamDataMsg.SUCCESS.value,
        data={"workflow_id": workflow_id},
        execution_id="",
    )


# ===================================================================
# Contract Runtime 初始化（5 路 monkeypatch）
#
# 打桩策略：在框架即将发出外部调用的位置替换，保留框架内部全部逻辑。
#
#   Patch 1: ModelFactory.get_model → _FallbackChatModel
#            防止框架初始化时访问真实模型配置
#
#   Patch 2: IntentionDetectModule._execute_llm_call → Registry.model
#            拦截意图识别阶段的 LLM 调用
#
#   Patch 3': BaseChatModel.astream → Registry.model.astream
#             替代旧的 LLMModule.stream_function_call 打桩，
#             保留框架的 _format_yield_result 流式处理逻辑，
#             包括 finish_reason 判断、process_finish_item 调用等
#
#   Patch 4: WorkflowHandler.create_workflow_instance → Registry.workflow
#            拦截工作流实例创建，返回 mock SSE 事件流
#
#   Patch 5: RestFulAPI.ainvoke → Registry.plugin
#            拦截插件调用，返回预设结果
# ===================================================================
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    """初始化 Contract Runtime，替换 Model/Workflow/Plugin 为 Mock。

    调用时机：pytest fixture `local_ir_path` 中，在 IR 复制之前执行。
    每个测试方法通过 fixture 自动获得已打桩的运行环境。
    """
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"
    os.environ["USE_EI_INTENT"] = "true"
    os.environ["USE_TOOL_WRAPPER"] = "true"
    os.environ["PLUGIN_SSL_API_CERT_KEY"] = "false"
    _IntegrationRegistry.clear()

    # --- Patch 1: ModelFactory.get_model → FallbackChatModel ---
    # 框架初始化时会通过 ModelFactory 获取模型实例，
    # 这里返回一个确定性的 FallbackChatModel，避免访问真实模型配置。
    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *args, **kwargs: _FallbackChatModel(),
    )

    # --- Patch 2: 初始化 JiuWen prompt manager ---
    # JiuWen.init() 加载默认 prompt 模板，是框架正常运行的前提。
    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {RESOURCE_TEMPLATE_DIR}"
        )
    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    # --- Patch 3: IntentionDetectModule._execute_llm_call → Registry.model ---
    # 拦截意图识别阶段的 LLM 调用，路由到 _IntegrationRegistry.model。
    # 返回值需要包装为 namedtuple 以匹配框架期望的返回结构。
    async def _patched_execute_llm_call(self, llm_input):
        start_time = time.time()
        model = _IntegrationRegistry.get_model()
        if model is not None:
            llm_message = await model.ainvoke(
                llm_input,
                model_id=getattr(self.llm, "model_name", ""),
                session_id=getattr(self.plan_config, "task_id", "") or "",
            )
        else:
            llm_message = await self.llm.ainvoke(llm_input)
        converted_output = convert_ai_message_to_llm_output(llm_message)
        total_time = time.time() - start_time
        model_stat, model_usage = self._extract_usage_metadata(llm_message)
        ResultTuple = namedtuple(
            "ResultTuple",
            [
                "converted_output",
                "total_time",
                "model_stat",
                "model_usage",
                "llm_message",
            ],
        )
        return ResultTuple(
            converted_output=converted_output,
            total_time=round(total_time, 2),
            model_stat=model_stat,
            model_usage=model_usage,
            llm_message=llm_message,
        )

    # --- Patch 4: WorkflowHandler.create_workflow_instance → Registry.workflow ---
    # 拦截工作流实例创建。当 Registry 中注册了 workflow mock 时，
    # 返回 _WorkflowInstanceAdapter（内部调用 mock 的 astream）；
    # 否则 fallback 到原始实现。
    original_create_workflow_instance = WorkflowHandler.create_workflow_instance

    async def _patched_create_workflow_instance(
        workflow_context,
        conversation_id,
        user_id,
    ):
        workflow = _IntegrationRegistry.get_workflow()
        if workflow is not None:
            session = workflow.create_session(conversation_id)
            runtime_context = workflow.get_runtime_context(session)

            async def _astream_handler(**workflow_input):
                query = workflow_input.get("inputs", "")
                params = workflow_input.get("params", {})
                return await workflow.astream(
                    query=query,
                    params=params,
                    workflow_id=workflow_context.workflow_id,
                    agent_id=getattr(workflow_context, "agent_id", "") or "",
                    session_id=conversation_id,
                    context=runtime_context,
                )

            async def _ainvoke_handler(**workflow_input):
                return await _astream_handler(**workflow_input)

            return _WorkflowInstanceAdapter(
                astream_handler=_astream_handler,
                ainvoke_handler=_ainvoke_handler,
                state_getter=lambda: session.get_state() if session else {},
                status_getter=lambda: None,
                cleanup_handler=lambda: None,
                runtime_context=runtime_context,
            )
        return await original_create_workflow_instance(
            workflow_context,
            conversation_id,
            user_id,
        )

    # --- Patch 5: AgentCoreRestfulLayer.ainvoke → Registry.plugin ---
    # 拦截插件调用入口。USE_TOOL_WRAPPER=true 时插件走 AgentCoreRestfulLayer，
    # 其 ainvoke 是子类方法（不走 RestFulAPI.ainvoke），必须直接 patch 子类。
    original_plugin_ainvoke = AgentCoreRestfulLayer.ainvoke

    async def _fake_plugin_ainvoke(self, inputs, **kwargs):
        plugin = _IntegrationRegistry.get_plugin()
        if plugin is not None:
            return await plugin.execute(
                self.name, inputs if isinstance(inputs, dict) else {}
            )
        return await original_plugin_ainvoke(self, inputs, **kwargs)

    # --- Patch 3': BaseChatModel.astream → Registry.model.astream ---
    # 核心差异：在 BaseChatModel.astream 级别打桩，而非 LLMModule.stream_function_call。
    # 这样保留了框架的 _format_yield_result 流式处理逻辑，
    # 包括 finish_reason 判断、process_finish_item 调用等。
    original_astream = BaseChatModel.astream

    async def _patched_astream(self, inputs, **kwargs):
        model = _IntegrationRegistry.get_model()
        if model is not None and hasattr(model, "astream"):
            async for item in model.astream(inputs, **kwargs):
                yield item
            return
        async for item in original_astream(self, inputs, **kwargs):
            yield item

    monkeypatch.setattr(
        IntentionDetectModule,
        "_execute_llm_call",
        _patched_execute_llm_call,
    )
    monkeypatch.setattr(
        BaseChatModel,
        "astream",
        _patched_astream,
    )
    if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
        monkeypatch.setattr(
            WorkflowHandler,
            "create_workflow_instance",
            staticmethod(_patched_create_workflow_instance),
        )
    else:
        _ensure_current_event_loop()
        create_workflow_react_tools()
    monkeypatch.setattr(
        AgentCoreRestfulLayer,
        "ainvoke",
        _fake_plugin_ainvoke,
    )


def _ensure_current_event_loop():
    """Ensure a current event loop exists before building openjiuwen workflow graphs."""
    try:
        asyncio.get_running_loop()
        return
    except RuntimeError:
        pass

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


# ===================================================================
# IR 加载与执行
#
# 流程：
#   1. _copy_ir_to_tmp: 将 Agent IR + Workflow IR 复制到 pytest 临时目录
#      - 避免测试间文件状态污染
#      - 自动更新 workflow 的 ir_path 引用为临时目录绝对路径
#   2. _run_local_ir: 执行完整的 IR 加载 → Agent 实例化 → 请求分发 → SSE 响应
#      - 模拟 serve 层的 HTTP 请求处理流程
#      - 返回完整的 SSE 响应文本，供测试方法解析和断言
# ===================================================================
def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_ir_to_tmp(tmp_path: Path) -> Path:
    """将 Agent IR 和所有 Workflow IR 复制到临时目录，更新引用路径。"""
    agent_files = list(AGENT_DIR.glob("*.json"))
    if len(agent_files) != 1:
        raise AssertionError(
            f"Expected exactly one agent json in {AGENT_DIR}, found {len(agent_files)}"
        )
    agent_ir = _load_json(agent_files[0])

    workflow_files = {f.stem: f for f in WORKFLOW_DIR.glob("*.json")}

    for wf_cfg in agent_ir.get("configs", {}).get("workflows", []):
        ir_path = wf_cfg.get("ir_path", "")
        wf_name = Path(ir_path).stem
        if wf_name in workflow_files:
            wf_dst = tmp_path / workflow_files[wf_name].name
            wf_dst.write_text(
                WORKFLOW_DIR.joinpath(workflow_files[wf_name].name).read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            wf_cfg["ir_path"] = str(wf_dst)

    agent_dst = tmp_path / agent_files[0].name
    agent_dst.write_text(
        json.dumps(agent_ir, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return agent_dst


async def _run_local_ir(
    *,
    ir_path: Path,
    query: str,
    conversation_id: str,
    conversation_history=None,
    params=None,
):
    """执行 IR 加载 + 分发请求，返回 SSE 响应文本。

    模拟 serve 层的完整请求处理流程：
      1. 构造 ExecutionRequest
      2. 加载 IR 并识别类型（Agent / MultiAgents / Workflow）
      3. 创建实例（ir_to_agent / ir_to_agent_group / async_ir_to_workflow）
      4. 补齐 agent_config.agent_id（框架 bug workaround，见 DESIGN.md）
      5. 调用 distribute_execution_request 执行请求
      6. 收集 SSE 响应流并返回完整文本
    """
    if conversation_history is None:
        conversation_history = []
    if params is None:
        params = {}

    default_params = {
        "conversationHistory": conversation_history,
        "pluginConfigs": [],
        "globalVariables": {},
        "llmExtraConfigs": {},
        "workflowSequence": [],
        "activeWorkflows": [],
    }
    default_params.update(params)

    req = ExecutionRequest.model_validate(
        {
            "conversationId": conversation_id,
            "query": query,
            "irPath": str(ir_path),
            "responseMode": "streaming",
            "executionMode": "sync",
            "params": default_params,
            "headers": {
                "Content-Type": "application/json",
                "x-code": "123",
                "name": "Tom",
                "userid": "1212",
                "status": "123.1",
            },
        }
    )

    ir_data = await async_ir_load(str(ir_path))
    ir_type = IRConverter.identify_ir(ir_data)

    if ir_type.name == "MultiAgents":
        instance = await IRConverter.ir_to_agent_group(
            ir_data,
            conversation_id=req.conversation_id,
            cust_headers={},
        )
    elif ir_type.name == "Agent":
        instance = await IRConverter.ir_to_agent(
            ir_data,
            conversation_id=req.conversation_id,
            cust_headers={},
        )
        # [Workaround] plugin_handler.py:48 访问 agent_config.agent_id，
        # 但 ir_to_agent（单 Agent 路径）不会设置该属性（框架已知不一致）。
        # 多 Agent 路径（ir_to_agent_group）会正确设置 metadata.id。
        # 这里从 IR 的 agentId 字段手动补齐，与 test_plugin_handler.py:92 的做法一致。
        if hasattr(instance, "context_manager"):
            instance.context_manager.agent_config.agent_id = ir_data.get("agentId", "")
    else:
        instance = await IRConverter.async_ir_to_workflow(ir_data)

    execution_data = ExecutionData(
        instance=instance,
        instance_type=ir_type,
        updated_time=int(time.time() * 1000),
    )
    fake_request = type("LocalRequest", (), {"headers": req.headers})()
    token = request_context.set(fake_request)
    try:
        response = await distribute_execution_request(req, execution_data)
    finally:
        request_context.reset(token)

    body = []
    async for chunk in response.body_iterator:
        body.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))
    return "".join(body)


# ===================================================================
# SSE 解析辅助函数
# ===================================================================


def _parse_sse_events(response_text: str):
    """解析 SSE 文本，返回 data payload 列表。"""
    events = []
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[len("data: ") :]
        events.append(json.loads(payload))
    return events


def _load_expected_sse_events() -> list:
    """从 resource/mock_e2e_output.txt 解析期望的 SSE 事件列表（按轮次分组）。

    返回 [round1_events, round2_events, round3_events]。
    """
    txt = (RESOURCE_DIR / "mock_e2e_output.txt").read_text(encoding="utf-8")
    rounds = []
    current_round = []
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("第") and "次请求" in line:
            if current_round:
                rounds.append(current_round)
            current_round = []
        elif line.startswith("data: "):
            current_round.append(json.loads(line[6:]))
    if current_round:
        rounds.append(current_round)
    return rounds


# 动态字段：每次运行都不同，跳过比对
# index: 录制走 legacy 路径（pass_async_streaming_data 递增），
#   测试走 OpenJiuwen wrapper 路径（end.py 等硬编码 index=0）。
_SKIP_KEYS = frozenset(
    {
        "createdTime",
        "executionId",
        "index",
        "isStructMessage",
        "time_consumption",
        "overall_latency",
        "total_latency",
        "model_latency",
        "wait_latency",
        "plugin_latency",
        "time",
        "execution_id",
        "task_id",
        "plan_id",
        "tool_call_id",
        "id",
        "latency",
    }
)


def _strip_dynamic(obj):
    """递归移除动态字段，返回新对象用于比对。"""
    if isinstance(obj, dict):
        return {k: _strip_dynamic(v) for k, v in obj.items() if k not in _SKIP_KEYS}
    elif isinstance(obj, list):
        return [_strip_dynamic(item) for item in obj]
    return obj


def _assert_sse_strict(actual_events, expected_events, round_label=""):
    """逐条严格比对 SSE 事件（去除动态字段后）。"""
    prefix = f"[{round_label}] " if round_label else ""

    # 先比对事件数量
    assert len(actual_events) == len(expected_events), (
        f"{prefix}SSE event count mismatch: "
        f"expected={len(expected_events)}, actual={len(actual_events)}\n"
        f"  expected types: {[e.get('event') for e in expected_events]}\n"
        f"  actual types:   {[e.get('event') for e in actual_events]}"
    )

    # 再比对事件类型序列
    actual_types = [e.get("event") for e in actual_events]
    expected_types = [e.get("event") for e in expected_events]
    assert actual_types == expected_types, (
        f"{prefix}SSE event type sequence mismatch:\n"
        f"  expected: {expected_types}\n"
        f"  actual:   {actual_types}"
    )

    # 逐条比对内容（去除动态字段）
    for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
        actual_clean = _strip_dynamic(actual)
        expected_clean = _strip_dynamic(expected)
        assert actual_clean == expected_clean, (
            f"{prefix}SSE event[{i}] ({expected.get('event')}) content mismatch:\n"
            f"  expected: {json.dumps(expected_clean, ensure_ascii=False, indent=2)}\n"
            f"  actual:   {json.dumps(actual_clean, ensure_ascii=False, indent=2)}"
        )


def _extract_model_prompt_text(call: _ModelCall) -> str:
    inputs = call.inputs
    if isinstance(inputs, dict):
        return json.dumps(inputs, ensure_ascii=False, default=str)
    if isinstance(inputs, list):
        return "\n".join(str(getattr(item, "content", item)) for item in inputs)
    return str(inputs)


# ===================================================================
# pytest fixture
# ===================================================================
@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("react_multy_tools_010")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例：ReAct Mode LLM 多工具调用南向契约测试
#
# 与原始客户端测试保持一致：同一个 conversation_id 下顺序发 3 次请求。
# 每轮请求前重置 _IntegrationRegistry 的 mock（因为每轮的 LLM/Plugin/Workflow 预设不同），
# 每轮请求后立即做该轮的 SSE 断言和 Spy 断言，最后做跨轮次的汇总断言。
# ===================================================================
class TestCaseLLMReactMultyTools010:
    """ReAct 模式多工具调用南向契约测试。

    Agent 配置：
      - 2 个插件：calculator_tool（计算器）、mock_plugin_add（追加"啦啦啦"）
      - 1 个工作流：workflow_react_tools（echo query + 固定输出"气温20度"）
      - 运行模式：ReAct，maxIteration=9

    同一会话中三次顺序请求分别触发不同工具，验证：
      - SSE 数据帧结构和内容
      - LLM / Plugin / Workflow 的调用次数和参数
      - 工具路由的排他性（插件请求不触发工作流，反之亦然）
      - 跨轮次 intermediate_message 的 tool_calls 正确性
    """

    def test_run(self, local_ir_path):
        """同一会话中三次顺序请求，覆盖插件和工作流两种工具类型。

        与原始客户端测试 test_case_llm_react_multy_tools_010 保持一致：
        在同一个 conversation_id 下，用 for 循环顺序发出 3 次请求。

        第1轮：calculator_tool 插件（LLM×2 → plugin×1）
        第2轮：workflow_react_tools 工作流（LLM×1 → workflow×1）
        第3轮：mock_plugin_add 插件（LLM×2 → plugin×1）

        严格逐条比对 resource/mock_e2e_output.txt 录制的 SSE 事件。
        """
        # 加载录制的期望 SSE 事件
        expected_rounds = _load_expected_sse_events()
        assert len(expected_rounds) == 3, (
            f"Expected 3 rounds in mock_e2e_output.txt, got {len(expected_rounds)}"
        )

        # 同一会话 ID，与原始客户端测试一致
        conversation_id = f"conv_{int(time.time() * 1000)}"

        # ==============================================================
        # 第1轮：calculator_tool 插件调用（LLM×2 → plugin×1 → workflow×0）
        # ==============================================================
        model_runtime_1 = _RecordingModelRuntime(
            [
                AIMessage(
                    content='calculator_tool|{"expression": "9+9"}',
                    tool_calls=[
                        ToolCall(
                            name="calculator_tool",
                            args={"expression": "9+9"},
                        )
                    ],
                    usage_metadata=UsageMetadata(
                        code=0,
                        errmsg="成功",
                        finish_reason="function_call",
                    ),
                ),
                AIMessage(
                    content='{"result": "18"}',
                    usage_metadata=UsageMetadata(
                        code=0,
                        errmsg="成功",
                        finish_reason="stop",
                    ),
                ),
            ]
        )
        plugin_runtime_1 = _RecordingPluginRuntime(
            {
                "calculator_tool": [{"result": "18"}],
            }
        )
        workflow_runtime_1 = _RecordingWorkflowRuntime({})

        _IntegrationRegistry.clear()
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime_1))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime_1)
        )
        _IntegrationRegistry.set_plugin(plugin_runtime_1)

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="调用calculator_tool输入9+9",
                conversation_id=conversation_id,
            )
        )

        events_1 = _parse_sse_events(response_text)
        for i, ev in enumerate(events_1):
            print(
                f"  R1[{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        # 严格 e2e 比对
        _assert_sse_strict(events_1, expected_rounds[0], "R1")

        # Spy 断言
        assert len(model_runtime_1.calls) == 2, (
            f"R1: Expected 2 LLM calls, got: {len(model_runtime_1.calls)}"
        )
        assert len(plugin_runtime_1.calls) == 1, (
            f"R1: Expected 1 plugin call, got: {len(plugin_runtime_1.calls)}"
        )
        assert plugin_runtime_1.calls[0].tool_name == "calculator_tool"
        assert len(workflow_runtime_1.calls) == 0, (
            f"R1: Expected 0 workflow calls, got: {len(workflow_runtime_1.calls)}"
        )

        # ==============================================================
        # 第2轮：workflow_react_tools 工作流调用（LLM×1 → plugin×0 → workflow×1）
        # ==============================================================
        model_runtime_2 = _RecordingModelRuntime(
            [
                AIMessage(
                    content='workflow_react_tools|{"query": "11"}',
                    tool_calls=[
                        ToolCall(
                            name="workflow_react_tools",
                            args={"query": "11"},
                        )
                    ],
                    usage_metadata=UsageMetadata(
                        code=0,
                        errmsg="成功",
                        finish_reason="function_call",
                    ),
                ),
            ]
        )

        # Workflow mock：预设完整的 SSE 事件序列
        # 工作流拓扑：Start → 消息节点(echo query) → 结束节点(固定输出"气温20度")
        # 对应 resource/mock_react_workflow_input_and_output.txt 第6-18行
        workflow_events = [
            _build_workflow_start_stream_data(workflow_id=WORKFLOW_ID),
            # 消息节点 partial content
            _build_partial_stream_data(
                answer="",
                node_id="node_1764123489825",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="11",
                node_id="node_1764123489825",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="",
                node_id="node_1764123489825",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            # 消息节点 message_end
            _build_message_end_stream_data(
                answer="11",
                node_id="node_1764123489825",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            # 结束节点 partial content
            _build_partial_stream_data(
                answer="",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="气温20度",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # 结束节点 message_end
            _build_message_end_stream_data(
                answer="气温20度",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # workflow_end (code=4000)
            _build_workflow_end_stream_data(
                answer="气温20度",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # finish (code=0)
            _build_end_stream_data(answer="气温20度"),
        ]

        plugin_runtime_2 = _RecordingPluginRuntime({})
        workflow_runtime_2 = _RecordingWorkflowRuntime(
            {WORKFLOW_ID: [workflow_events]},
        )

        _IntegrationRegistry.clear()
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime_2))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime_2)
        )
        _IntegrationRegistry.set_plugin(plugin_runtime_2)

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="调用workflow_react_tools输入11",
                conversation_id=conversation_id,
            )
        )

        # ---- 解析 SSE 响应 ----
        events_2 = _parse_sse_events(response_text)
        for i, ev in enumerate(events_2):
            print(
                f"  R2[{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        # 严格 e2e 比对
        _assert_sse_strict(events_2, expected_rounds[1], "R2")

        # Spy 断言
        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            assert len(model_runtime_2.calls) == 1, (
                f"R2: Expected 1 LLM call, got: {len(model_runtime_2.calls)}"
            )
            assert len(workflow_runtime_2.calls) == 1, (
                f"R2: Expected 1 workflow call, got: {len(workflow_runtime_2.calls)}"
            )
            assert workflow_runtime_2.calls[0]["workflow_id"] == WORKFLOW_ID
            assert len(plugin_runtime_2.calls) == 0, (
                f"R2: Expected 0 plugin calls, got: {len(plugin_runtime_2.calls)}"
            )

        # ==============================================================
        # 第3轮：mock_plugin_add 插件调用（LLM×2 → plugin×1 → workflow×0）
        # ==============================================================
        model_runtime_3 = _RecordingModelRuntime(
            [
                AIMessage(
                    content='mock_plugin_add|{"query": "12"}',
                    tool_calls=[
                        ToolCall(
                            name="mock_plugin_add",
                            args={"query": "12"},
                        )
                    ],
                    usage_metadata=UsageMetadata(
                        code=0,
                        errmsg="成功",
                        finish_reason="function_call",
                    ),
                ),
                AIMessage(
                    content='{"result": "12啦啦啦"}',
                    usage_metadata=UsageMetadata(
                        code=0,
                        errmsg="成功",
                        finish_reason="stop",
                    ),
                ),
            ]
        )
        plugin_runtime_3 = _RecordingPluginRuntime(
            {
                "mock_plugin_add": [{"result": "12啦啦啦"}],
            }
        )
        workflow_runtime_3 = _RecordingWorkflowRuntime({})

        _IntegrationRegistry.clear()
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime_3))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime_3)
        )
        _IntegrationRegistry.set_plugin(plugin_runtime_3)

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="调用插件mock_plugin_add输入12",
                conversation_id=conversation_id,
            )
        )

        events_3 = _parse_sse_events(response_text)
        for i, ev in enumerate(events_3):
            print(
                f"  R3[{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        # 严格 e2e 比对
        _assert_sse_strict(events_3, expected_rounds[2], "R3")

        # Spy 断言
        assert len(model_runtime_3.calls) == 2, (
            f"R3: Expected 2 LLM calls, got: {len(model_runtime_3.calls)}"
        )
        assert len(plugin_runtime_3.calls) == 1, (
            f"R3: Expected 1 plugin call, got: {len(plugin_runtime_3.calls)}"
        )
        assert plugin_runtime_3.calls[0].tool_name == "mock_plugin_add"
        assert len(workflow_runtime_3.calls) == 0, (
            f"R3: Expected 0 workflow calls, got: {len(workflow_runtime_3.calls)}"
        )

        _IntegrationRegistry.clear()
