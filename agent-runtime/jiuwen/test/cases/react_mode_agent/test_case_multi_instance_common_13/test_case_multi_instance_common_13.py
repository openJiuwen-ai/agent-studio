#!/usr/bin/env python
"""
南向契约测试 -- ReAct mode agent (双提问器串行工作流 test_case_multi_instance_common_13)

=== 业务场景 ===
信息采集：工作流包含两个串联的提问器，先收集歌手信息，再收集时间和水果信息。
两个提问器各自独立追问，全部收齐后拼接输出。

=== 原始客户端测试流程（test_case_multi_instance_common_13） ===
  1. 上传 IR 到 OBS，通过 HTTP 调用真实 jiuwen 服务
  2. Round 1: 用户说"你好" → 提问器1 问"请提供歌手信息"
  3. Round 2: 用户说"华晨宇" → 提问器1 收到歌手，提问器2 接手，问"请提供时间和水果"
  4. Round 3: 用户说"星期六" → 提问器2 收到时间，还缺水果，继续问"请提供水果"
  5. Round 4: 用户说"西瓜" → 提问器2 全齐 → 输出"歌手是华晨宇 而时间是星期六 水果是西瓜"
  6. 每轮 assertEqual 验证答案

=== 收编后的测试流程 ===
  - LLM 不真调：每轮预设返回 tool_call(2_questioners_zcm)
  - 工作流不真跑：前 3 轮预设返回提问器中断事件，第 4 轮预设返回 End 节点流式输出
  - 框架内部的 ReAct 循环、工具路由、SSE 组装全部真实执行
  - 断言每轮 SSE 里的追问消息或最终拼接结果

=== 验证维度 ===
  - SSE 数据帧：事件类型、字段结构、业务数据
  - 调用计数：每轮 LLM×1, Workflow×1, Plugin×0
  - 多轮中断/恢复：4 轮对话中 3 次中断 + 1 次完成
  - 串行提问器切换：questioner1 → questioner2 的节点切换

=== Mock 策略（与 test_012 一致） ===
  - LLM mock 在 BaseChatModel.astream 级别
  - Plugin mock 在 RestFulAPI.ainvoke 级别
  - 5 路 monkeypatch

详细设计文档见同目录 DESIGN.md。

用法：
  pytest -v test_case_multi_instance_common_13.py
"""

__all__ = [
    "TestCaseMultiInstanceCommon13",
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

# ---------------------------------------------------------------------------
# 环境变量预设（必须在 import jiuwen 之前设置）
# ---------------------------------------------------------------------------
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage, ToolCall, UsageMetadata
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.plugin.models.tool import WORKFLOW_END_TYPE
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import distribute_execution_request
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest


# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[3]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
AGENT_DIR = CASE_DIR / "agent"
WORKFLOW_DIR = CASE_DIR / "workflow"

# Workflow ID（与 workflow IR 中的 workflowId 字段保持一致）
WORKFLOW_ID = "208f87d9af522e103d89f84ca0aa419007643ec96fc5eb98"


# ===================================================================
# Mock 基础设施（与 test_012 完全一致）
# ===================================================================
class _IntegrationRegistry:
    """进程级单例，注册 Mock Model / Workflow / Plugin 运行时。"""

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
    """模拟工作流会话，提供 get_state / update_state 接口。"""

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
    """将 _RecordingModelRuntime 适配为 _IntegrationRegistry.model 接口。"""

    def __init__(self, runtime):
        self.runtime = runtime

    async def ainvoke(self, inputs, **kwargs):
        if hasattr(self.runtime, "ainvoke"):
            return await self.runtime.ainvoke(inputs, **kwargs)
        return await self.runtime.invoke(inputs, **kwargs)

    async def astream(self, inputs, **kwargs):
        """async generator，yield AIMessage 对象。"""
        async for item in self.runtime.astream(inputs, **kwargs):
            yield item


class _LocalWorkflowAdapter:
    """将 _RecordingWorkflowRuntime 适配为 _IntegrationRegistry.workflow 接口。"""

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
    """可编程 LLM Mock，通过 astream 返回 AIMessage 流。"""

    def __init__(self, scripted_outputs):
        self.scripted_outputs = list(scripted_outputs)
        self.calls = []

    async def ainvoke(self, inputs, session_id=None, **kwargs):
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
    """可编程 Plugin Mock，按插件名返回预设结果。"""

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
    """可编程 Workflow Mock，按 workflow_id 返回预设 SSE 事件序列。"""

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
    """模拟 WorkflowHandler.create_workflow_instance 返回的工作流实例。"""

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
        if args:
            workflow_input["inputs"] = args[0]
            if len(args) > 1 and isinstance(args[1], dict):
                workflow_input.update(args[1])
        return await self._astream_handler(**workflow_input)

    async def ainvoke(self, **workflow_input):
        return await self._ainvoke_handler(**workflow_input)

    def get_state(self):
        return self._state_getter()

    def get_workflow_execute_status(self):
        return self._status_getter()

    async def async_clean_up(self):
        result = self._cleanup_handler()
        if asyncio.iscoroutine(result):
            await result


# ===================================================================
# SSE StreamData 构建器
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
    """构建 MESSAGE_END 事件（code=5000）。"""
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
    """构建 WORKFLOW_END 事件（code=4000）。"""
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


def _build_end_stream_data(
    *,
    answer: str,
    node_id: str = "node_end",
    node_type: str = None,
):
    """构建 FINISH 事件（workflow 彻底结束）。"""
    nt = node_type or WORKFLOW_END_TYPE
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": "node_end",
            "node_type": nt,
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
# ===================================================================
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    """初始化 Contract Runtime，替换 Model/Workflow/Plugin 为 Mock。"""
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    _IntegrationRegistry.clear()

    # --- Patch 1: ModelFactory.get_model → FallbackChatModel ---
    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *a, **kw: _FallbackChatModel(),
    )

    # --- Patch 2: 初始化 JiuWen prompt manager ---
    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {RESOURCE_TEMPLATE_DIR}"
        )
    JiuWen.init(
        prompt_dir=str(RESOURCE_TEMPLATE_DIR),
        plugin_dir=None,
        cfg_file=None,
    )

    # --- Patch 3: IntentionDetectModule._execute_llm_call ---
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

    # --- Patch 3': BaseChatModel.astream → Registry.model.astream ---
    original_astream = BaseChatModel.astream

    async def _patched_astream(self, inputs, **kwargs):
        model = _IntegrationRegistry.get_model()
        if model is not None and hasattr(model, "astream"):
            async for item in model.astream(inputs, **kwargs):
                yield item
            return
        async for item in original_astream(self, inputs, **kwargs):
            yield item

    # --- Patch 4: WorkflowHandler.create_workflow_instance ---
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

    # --- Patch 5: RestFulAPI.ainvoke → Registry.plugin ---
    # 拦截插件调用入口，与 LLM mock（BaseChatModel.astream/ainvoke）保持一致的抽象层级。
    original_plugin_ainvoke = RestFulAPI.ainvoke

    async def _fake_plugin_ainvoke(self, inputs, **kwargs):
        plugin = _IntegrationRegistry.get_plugin()
        if plugin is not None:
            return await plugin.execute(
                self.name, inputs if isinstance(inputs, dict) else {}
            )
        return await original_plugin_ainvoke(self, inputs, **kwargs)

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
    monkeypatch.setattr(
        WorkflowHandler,
        "create_workflow_instance",
        staticmethod(_patched_create_workflow_instance),
    )
    monkeypatch.setattr(
        RestFulAPI,
        "ainvoke",
        _fake_plugin_ainvoke,
    )


# ===================================================================
# IR 加载与执行
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
    """执行 IR 加载 + 分发请求，返回 SSE 响应文本。"""
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
        if hasattr(instance, "context_manager"):
            instance.context_manager.agent_config.agent_id = ir_data.get(
                "agentId",
                "",
            )
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


# ===================================================================
# pytest fixture
# ===================================================================
@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("multi_instance_common_13")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例：ReAct Mode 双提问器串行工作流南向契约测试
#
# 与原始客户端测试 test_case_multi_instance_common_13 保持一致：
# 同一个 conversation_id 下顺序发 4 次请求。
#   第1轮：questioner1 中断（缺少 singer）
#   第2轮：questioner1 完成 + questioner2 中断（缺少 time+fruits）
#   第3轮：questioner2 部分补齐（time=星期六，仍缺 fruits）
#   第4轮：questioner2 完成，End 节点流式输出
#
# ==============================================================
# 工作流中断/恢复机制说明
#
# 【中断信号链 — ReAct 模式】
#   1. Questioner 节点输出 should_interrupt=True (code=1206 PARTIAL_CONTENT)
#   2. MESSAGE_END(code=5000) 携带 should_interrupt=True
#   3. FINISH(code=0) 的 node_type="jiuwen.questioner"（非 jiuwen.end）
#   4. WorkflowHandler._stream_handle_workflow_execute() 检测到
#      should_interrupt=True 或 node_type==QUESTIONER
#      → 设置 workflow_status["questioner_interrupted"] = True
#   5. WorkflowHandler 生成 Message(type=WORKFLOW_INTERRUPT)
#   6. BaseMode.process_task_execution_streaming_message() 检测到
#      WORKFLOW_INTERRUPT → should_output_to_user() 返回 True
#      → self.terminate = True → ReAct 循环终止
#
# 【ReAct 模式特殊行为】
#   - ReAct 模式调用 WorkflowHandler 时 emit_blocked=False，
#     因此 SSE 中不会出现 workflow_blocked(code=11000) 事件
#   - 中断信号通过 api_exec_data 事件中的追问消息传递
#   - 区别于 PlanExecute 模式，后者会显式发送 workflow_blocked 事件
#
# 【恢复信号链 — ReAct 模式】
#   1. 下一轮请求到达，Agent 从持久化状态恢复
#   2. 工作流从中断节点继续执行（由 Mock 预设的下一轮事件驱动）
#   3. ReAct 模式不发送 workflow_resume(code=12000) 事件
#
# 【区分正常完成 vs 中断】
#   - 正常完成: FINISH(code=0) + node_type="jiuwen.end" → 无中断
#   - 中断: FINISH(code=0) + node_type="jiuwen.questioner" → 有中断
#
# 【串行提问器切换】
#   - questioner1 完成后，questioner2 自动接手
#   - 切换体现在 FINISH 事件的 node_id 从 node_questioner1 变为 node_questioner2
# ==============================================================
# ===================================================================
class TestCaseMultiInstanceCommon13:
    """ReAct 模式双提问器串行工作流南向契约测试。

    业务场景：信息采集（歌手 + 时间 + 水果）
      工作流包含两个串联提问器：提问器1 收集歌手，提问器2 收集时间和水果。
      每个提问器独立追问，全部收齐后拼接输出。

    同一会话中四次顺序请求：
      Round 1: 用户说"你好" → 提问器1 追问"请提供歌手信息"
      Round 2: 用户说"华晨宇" → 提问器1 完成，提问器2 追问"请提供时间和水果"
      Round 3: 用户说"星期六" → 提问器2 收到时间，继续追问"请提供水果"
      Round 4: 用户说"西瓜" → 提问器2 完成 → 输出"歌手是华晨宇 而时间是星期六 水果是西瓜"
    """

    def test_run(self, local_ir_path):
        """同一会话中四次顺序请求，覆盖双提问器中断和恢复。"""
        conversation_id = f"conv_{int(time.time() * 1000)}"
        all_intermediate_messages = []

        # ==============================================================
        # 四轮测试数据定义
        #
        # 【业务流程】
        #   Round 1: 用户说"你好" → 提问器1 问"请提供歌手信息"
        #   Round 2: 用户说"华晨宇" → 提问器1 完成，提问器2 问"请提供时间和水果"
        #   Round 3: 用户说"星期六" → 提问器2 收到时间，继续问"请提供水果"
        #   Round 4: 用户说"西瓜" → 提问器2 完成 → 输出最终拼接结果
        #
        # 【Mock】每轮 LLM 预设 1 个 tool_call，工作流预设对应的中断或完成事件
        # ==============================================================
        TOOL_NAME = "2_questioners_zcm"

        rounds = [
            # Round 1: questioner1 中断（缺少 singer）
            # 【中断信号】should_interrupt=True, node_type="jiuwen.questioner"
            # 【预期 SSE】api_exec_data 包含追问消息，无 workflow_blocked/resume
            {
                "query": "调用2_questioners_zcm输入你好",
                "llm_args": {"query": "你好"},
                "interrupt_answer": "请您提供歌手相关的信息",
                "interrupt_node_id": "node_questioner1",
                "is_final": False,
            },
            # Round 2: questioner1 完成 + questioner2 中断（缺少 time+fruits）
            # 【恢复+中断】Agent 从持久化状态恢复，questioner1 完成后
            #   questioner2 自动接手并中断（串行提问器切换）
            # 【预期 SSE】api_exec_data 包含 questioner2 追问消息
            {
                "query": "调用2_questioners_zcm输入华晨宇",
                "llm_args": {"query": "华晨宇"},
                "interrupt_answer": "请您提供时间, 水果相关的信息",
                "interrupt_node_id": "node_questioner2",
                "is_final": False,
            },
            # Round 3: questioner2 部分补齐（time=星期六，仍缺 fruits）
            # 【恢复+中断】questioner2 收到时间但仍缺水果，继续中断
            # 【预期 SSE】api_exec_data 包含 questioner2 追问消息
            {
                "query": "调用2_questioners_zcm输入星期六",
                "llm_args": {"query": "星期六"},
                "interrupt_answer": "请您提供水果相关的信息",
                "interrupt_node_id": "node_questioner2",
                "is_final": False,
            },
            # Round 4: questioner2 完成，End 节点流式输出
            # 【恢复+完成】questioner2 全部字段齐全，工作流正常完成
            # 【预期 SSE】api_exec_data 包含最终拼接结果，无 workflow_blocked
            {
                "query": "调用2_questioners_zcm输入西瓜",
                "llm_args": {"query": "西瓜"},
                "final_answer": "歌手是华晨宇 而时间是星期六 水果是西瓜",
                "is_final": True,
            },
        ]

        for round_idx, rd in enumerate(rounds, start=1):
            # ---- 构建 LLM Mock ----
            args_json = json.dumps(rd["llm_args"], ensure_ascii=False)
            model_runtime = _RecordingModelRuntime(
                [
                    AIMessage(
                        content=f"{TOOL_NAME}|{args_json}",
                        tool_calls=[
                            ToolCall(
                                name=TOOL_NAME,
                                args=rd["llm_args"],
                                id="",
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

            # ---- 构建 Workflow Mock ----
            if rd["is_final"]:
                # Round 4: End 节点流式输出
                final_answer = rd["final_answer"]
                end_chunks = [
                    "歌手是",
                    "华晨宇",
                    " 而时间是",
                    "星期六",
                    " 水果是",
                    "西瓜",
                    "",
                ]
                wf_events = []
                for chunk in end_chunks:
                    wf_events.append(
                        _build_partial_stream_data(
                            answer=chunk,
                            node_id="node_end",
                            node_name="结束",
                            node_type="jiuwen.end",
                        )
                    )
                wf_events.append(
                    _build_message_end_stream_data(
                        answer=final_answer,
                        node_id="node_end",
                        node_name="结束",
                        node_type="jiuwen.end",
                    )
                )
                wf_events.append(
                    _build_workflow_end_stream_data(
                        answer=final_answer,
                        node_id="node_end",
                        node_name="结束",
                        node_type="jiuwen.end",
                    )
                )
                wf_events.append(
                    _build_end_stream_data(answer=final_answer),
                )
            else:
                # Rounds 1-3: Questioner 中断
                interrupt_answer = rd["interrupt_answer"]
                node_id = rd["interrupt_node_id"]
                wf_events = []
                # Round 1 only: WORKFLOW_START
                if round_idx == 1:
                    wf_events.append(
                        _build_workflow_start_stream_data(
                            workflow_id=WORKFLOW_ID,
                        )
                    )
                wf_events.extend(
                    [
                        _build_partial_stream_data(
                            answer=interrupt_answer,
                            node_id=node_id,
                            node_name="提问器",
                            node_type="jiuwen.questioner",
                            should_interrupt=True,
                        ),
                        _build_message_end_stream_data(
                            answer=interrupt_answer,
                            node_id=node_id,
                            node_name="提问器",
                            node_type="jiuwen.questioner",
                            should_interrupt=True,
                        ),
                        _build_end_stream_data(
                            answer="",
                            node_id=node_id,
                            node_type="jiuwen.questioner",
                        ),
                    ]
                )

            plugin_runtime = _RecordingPluginRuntime({})
            workflow_runtime = _RecordingWorkflowRuntime(
                {WORKFLOW_ID: [wf_events]},
            )

            _IntegrationRegistry.clear()
            _IntegrationRegistry.set_model(
                _LocalModelAdapter(runtime=model_runtime),
            )
            _IntegrationRegistry.set_workflow(
                _LocalWorkflowAdapter(runtime=workflow_runtime),
            )
            _IntegrationRegistry.set_plugin(plugin_runtime)

            response_text = asyncio.run(
                _run_local_ir(
                    ir_path=local_ir_path,
                    query=rd["query"],
                    conversation_id=conversation_id,
                )
            )

            # ---- 解析 SSE 响应 ----
            events = _parse_sse_events(response_text)
            rn = f"R{round_idx}"
            for i, ev in enumerate(events):
                print(
                    f"  {rn}[{i}] event={ev.get('event')}, "
                    f"answer={str(ev.get('data', {}).get('answer', ''))[:80]}"
                )

            event_types = [e.get("event") for e in events]

            # ---- 断言：SSE 数据帧校验 ----

            # 校验点 1：SSE 事件非空
            assert len(events) > 0, f"{rn}: Expected at least some SSE events"

            # 校验点 2：首事件为 start
            assert events[0].get("event") == "start", (
                f"{rn}: Expected first event 'start', got: {events[0].get('event')}"
            )

            # 校验点 3：function_call 事件存在
            fc_events = [e for e in events if e.get("event") == "function_call"]
            assert len(fc_events) > 0, (
                f"{rn}: Expected function_call event, got: {event_types}"
            )
            fc_data = fc_events[0].get("data", {}).get("answer", {})
            fc_name = fc_data.get("function_call", {}).get("name", "")
            assert fc_name == TOOL_NAME, (
                f"{rn}: Expected function_call name='{TOOL_NAME}', got: {fc_name}"
            )
            assert fc_data.get("is_workflow") is True, (
                f"{rn}: Expected is_workflow=true"
            )

            # 校验点 4：api_exec_data 事件存在
            api_events = [e for e in events if e.get("event") == "api_exec_data"]
            assert len(api_events) > 0, (
                f"{rn}: Expected api_exec_data event, got: {event_types}"
            )
            api_answer = api_events[0].get("data", {}).get("answer", {})
            api_content_str = json.dumps(
                api_answer.get("content", {}),
                ensure_ascii=False,
            )
            if rd["is_final"]:
                assert "歌手是华晨宇" in api_content_str, (
                    f"{rn}: Expected final answer, got: {api_content_str}"
                )
            else:
                # 中断场景：检查追问消息
                assert rd["interrupt_answer"][:6] in api_content_str, (
                    f"{rn}: Expected interrupt msg, got: {api_content_str}"
                )

            # 校验点 5：intermediate_message 事件存在
            intermediate_events = [
                e for e in events if e.get("event") == "intermediate_message"
            ]
            assert len(intermediate_events) > 0, (
                f"{rn}: Expected at least one intermediate_message event"
            )

            # 校验点 6：intermediate_message 结构校验
            conv_msgs = (
                intermediate_events[0]
                .get(
                    "data",
                    {},
                )
                .get("answer", [])
            )
            assert isinstance(conv_msgs, list), (
                f"{rn}: intermediate_message answer should be list"
            )
            for msg in conv_msgs:
                assert "role" in msg, f"{rn}: ConversationMessage missing 'role': {msg}"
                assert "content" in msg, (
                    f"{rn}: ConversationMessage missing 'content': {msg}"
                )

            # assistant 消息包含 tool_calls
            assistant_msgs = [
                m
                for m in conv_msgs
                if m.get("role") == "assistant" and m.get("tool_calls")
            ]
            assert assistant_msgs, f"{rn}: Expected assistant message with tool_calls"
            actual_function = assistant_msgs[0]["tool_calls"][0]["function"]
            assert actual_function["name"] == TOOL_NAME, (
                f"{rn}: Expected tool_calls name='{TOOL_NAME}'"
            )

            # 校验点 7：summary_response 事件存在
            summary_events = [e for e in events if e.get("event") == "summary_response"]
            assert len(summary_events) > 0, (
                f"{rn}: Expected summary_response event, got: {event_types}"
            )
            summary_content = (
                summary_events[0]
                .get(
                    "data",
                    {},
                )
                .get("answer", {})
                .get("content", "")
            )
            if rd["is_final"]:
                assert "歌手是华晨宇" in summary_content, (
                    f"{rn}: Expected final answer in summary"
                )
                assert "水果是西瓜" in summary_content, (
                    f"{rn}: Expected all fields in summary"
                )
            else:
                assert rd["interrupt_answer"][:6] in summary_content, (
                    f"{rn}: Expected interrupt msg in summary"
                )

            # ---- 断言：Spy 调用计数 ----

            # 校验点 8：Model 被调用 1 次
            assert len(model_runtime.calls) == 1, (
                f"{rn}: Expected 1 LLM call, got: {len(model_runtime.calls)}"
            )

            # 校验点 9：Workflow 被调用 1 次
            assert len(workflow_runtime.calls) == 1, (
                f"{rn}: Expected 1 workflow call, got: {len(workflow_runtime.calls)}"
            )
            assert workflow_runtime.calls[0]["workflow_id"] == WORKFLOW_ID, (
                f"{rn}: Expected workflow_id={WORKFLOW_ID}"
            )

            # 校验点 10：Plugin 未被调用
            assert len(plugin_runtime.calls) == 0, (
                f"{rn}: Expected 0 plugin calls, got: {len(plugin_runtime.calls)}"
            )

            # ---- 断言：中断/恢复信号校验 ----
            # 【ReAct 模式中断信号】
            #   - ReAct 模式 emit_blocked=False，SSE 中不会出现 workflow_blocked 事件
            #   - ReAct 模式不发送 workflow_resume 事件
            #   - 中断信号通过 api_exec_data 中的追问消息传递
            #   - 正常完成时 api_exec_data 包含最终拼接结果

            # 校验点 11：ReAct 模式不产生 workflow_blocked 事件
            assert "workflow_blocked" not in event_types, (
                f"{rn}: ReAct mode should NOT emit workflow_blocked, got: {event_types}"
            )

            # 校验点 12：ReAct 模式不产生 workflow_resume 事件
            assert "workflow_resume" not in event_types, (
                f"{rn}: ReAct mode should NOT emit workflow_resume, got: {event_types}"
            )

            if rd["is_final"]:
                # 校验点 13a：最终轮次 — 正常完成，api_exec_data 包含完整答案
                # node_type="jiuwen.end" 表示工作流到达 End 节点
                assert "歌手是华晨宇" in api_content_str, (
                    f"{rn}: Final round api_exec_data should have complete answer"
                )
            else:
                # 校验点 13b：中断轮次 — api_exec_data 包含追问消息
                # 这是 ReAct 模式下中断信号到达 SSE 层的唯一可观测路径
                # Questioner 节点的 should_interrupt=True 被框架转换为追问消息
                assert rd["interrupt_answer"][:6] in api_content_str, (
                    f"{rn}: Interrupt round api_exec_data should have questioner msg"
                )

            all_intermediate_messages.append(intermediate_events[0])

        _IntegrationRegistry.clear()

        # ==============================================================
        # 跨轮次汇总断言
        # ==============================================================
        exp_result = [
            {"name": TOOL_NAME, "arguments": '{"query": "你好"}'},
            {"name": TOOL_NAME, "arguments": '{"query": "华晨宇"}'},
            {"name": TOOL_NAME, "arguments": '{"query": "星期六"}'},
            {"name": TOOL_NAME, "arguments": '{"query": "西瓜"}'},
        ]
        assert len(all_intermediate_messages) == 4, (
            f"Expected 4 intermediate_messages, got: {len(all_intermediate_messages)}"
        )
        for i, (msg, expected) in enumerate(zip(all_intermediate_messages, exp_result)):
            actual_function = msg["data"]["answer"][0]["tool_calls"][0]["function"]
            assert actual_function == expected, (
                f"Round {i + 1}: expected {expected}, got {actual_function}"
            )
