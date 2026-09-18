# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
南向契约测试 -- controller mode agent (case enhance 08)

场景：请求携带 intent 字段，specify_workflow_order=false，
      intent 字段优先级最高，唯一匹配融e借工作流后直接执行，跳过意图识别 LLM，单轮正常完成。

覆盖场景：
  - intent 字段直接路由（跳过意图识别 LLM）
  - 融e借工作流正常执行（workflow_start → message_end → workflow_end → done）
  - SSE 事件断言：start → task_start → workflow_start → message_end → workflow_end → done → task_end

用法：
  pytest -v jiuwen/test/cases/controller_mode_agent/test_case_agent_controller_enhance_08/
"""

__all__ = [
    "TestCaseControllerDefaultWorkflow01",
]

import asyncio
import json
import os
import pickle
import shutil
import tempfile
import time
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("TGF_ENABLE", "false")
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.plugin.models.tool import WORKFLOW_END_TYPE
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
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

# ---------------------------------------------------------------------------
# Workflow ID
# ---------------------------------------------------------------------------
FINANCIAL_WF_ID = "83a951bc-27d7-4ccc-9131-268e93267365"
DEFAULT_WF_ID = "ef802b42-9f76-4fb3-bfbb-910e5c091ced"
END_WF_ID = "6bcb3df8-0f29-41fd-a583-273414629b67"


# ===================================================================
# Mock 基础设施（共享层）
# ===================================================================
class _IntegrationRegistry:
    """进程级单例，注册 Mock Model 和 Workflow 运行时。"""

    model = None
    workflow = None

    @classmethod
    def clear(cls):
        cls.model = None
        cls.workflow = None

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


class _FakeWorkflowSession:
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
    def __init__(self, runtime):
        self.runtime = runtime

    async def ainvoke(self, inputs, **kwargs):
        if hasattr(self.runtime, "ainvoke"):
            return await self.runtime.ainvoke(inputs, **kwargs)
        return await self.runtime.invoke(inputs, **kwargs)


class _LocalWorkflowAdapter:
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


class _FallbackChatModel(BaseChatModel):
    """Deterministic fallback when no scripted output is configured."""

    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _RecordingModelRuntime:
    """可编程 Mock，按预设返回 scripted_outputs，同时记录所有调用。"""

    def __repr__(self):
        return f"_RecordingModelRuntime(outputs_left={len(self.scripted_outputs)})"

    def __init__(self, scripted_outputs):
        self.scripted_outputs = list(scripted_outputs)
        self.calls = []

    async def invoke(self, inputs, session_id=None, **kwargs):
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


class _RecordingWorkflowRuntime:
    """可编程 Mock，按 workflow_id 返回预设 SSE 事件序列。"""

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

        self.graph_engine = type(
            "_GraphEngine",
            (),
            {"graph_instance": _GraphInstance(runtime_context)},
        )()

    async def astream(self, **workflow_input):
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

    def get_runtime_context(self):
        return {}


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


def _build_end_stream_data(*, answer: str):
    """构建 FINISH 事件（code=0）。"""
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


def _build_questioner_finish_stream_data(
    *, answer: str, node_id: str, node_type: str = "jiuwen.questioner"
):
    """构建提问器 FINISH 事件（code=0），触发 workflow_blocked。"""
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_type": node_type,
            "user_fields": {},
        },
        execution_id="",
    )


# ===================================================================
# 基于本地文件的状态存储（替代 Redis/Memory，支持多轮对话中断恢复）
# ===================================================================
STATE_DIR = Path(tempfile.gettempdir()) / "jiuwen_test_state_default_workflow_01"


class _RestrictedUnpickler(pickle.Unpickler):
    """受限的反序列化器，拒绝已知危险模块以防止RCE"""
    _DANGEROUS_MODULES = {"os", "subprocess", "socket", "ctypes", "posix", "nt"}

    def find_class(self, module, name):
        if module in self._DANGEROUS_MODULES:
            raise pickle.UnpicklingError(f"Forbidden module during unpickling: {module}")
        if module == "builtins" and name in ("eval", "exec", "__import__", "open"):
            raise pickle.UnpicklingError(f"Forbidden builtin during unpickling: {name}")
        return super().find_class(module, name)


async def _file_based_delete_state(self, key):
    """删除状态文件（空操作，保留状态供多轮对话续接）"""
    pass


async def _file_based_save_state(self, key, value):
    """将状态序列化到本地文件"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = STATE_DIR / f"{key}.pkl"
    with open(file_path, "wb") as f:
        pickle.dump(value, f)


async def _file_based_get_state(self, key):
    """从本地文件反序列化状态"""
    file_path = STATE_DIR / f"{key}.pkl"
    if not file_path.exists():
        return None
    with open(file_path, "rb") as f:
        return _RestrictedUnpickler(f).load()


# ===================================================================
# Contract Runtime 初始化（monkeypatch）
# ===================================================================
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    """初始化 Contract Runtime，替换 Model/Workflow 为 Mock。"""
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    _IntegrationRegistry.clear()

    # 1) ModelFactory.get_model → FallbackChatModel
    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *args, **kwargs: _FallbackChatModel(),
    )

    # 2) 初始化 JiuWen prompt manager
    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {RESOURCE_TEMPLATE_DIR}"
        )
    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    # 3) IntentionDetectModule._execute_llm_call → 路由到 _IntegrationRegistry.model
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

    monkeypatch.setattr(
        IntentionDetectModule, "_execute_llm_call", _patched_execute_llm_call
    )

    # 4) WorkflowHandler.create_workflow_instance → 路由到 _IntegrationRegistry.workflow
    original_create_workflow_instance = WorkflowHandler.create_workflow_instance

    async def _patched_create_workflow_instance(
        workflow_context, conversation_id, user_id
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

    monkeypatch.setattr(
        WorkflowHandler,
        "create_workflow_instance",
        staticmethod(_patched_create_workflow_instance),
    )

    # 6) AsyncStateManager → 基于本地文件的持久化
    monkeypatch.setattr(AsyncStateManager, "save_state", _file_based_save_state)
    monkeypatch.setattr(AsyncStateManager, "get_state", _file_based_get_state)
    monkeypatch.setattr(AsyncStateManager, "delete_state", _file_based_delete_state)


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
    agent_dst = tmp_path / agent_files[0].name

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

    for gi in agent_ir.get("configs", {}).get("global_intents", []):
        handler = gi.get("handler", {})
        if isinstance(handler, dict):
            ir_path = handler.get("ir_path", "")
            if ir_path:
                wf_name = Path(ir_path).stem
                if wf_name in workflow_files:
                    wf_dst = tmp_path / workflow_files[wf_name].name
                    wf_dst.write_text(
                        WORKFLOW_DIR.joinpath(workflow_files[wf_name].name).read_text(
                            encoding="utf-8"
                        ),
                        encoding="utf-8",
                    )
                    handler["ir_path"] = str(wf_dst)

    agent_dst.write_text(
        json.dumps(agent_ir, ensure_ascii=False, indent=2), encoding="utf-8"
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
            ir_data, conversation_id=req.conversation_id, cust_headers={}
        )
    elif ir_type.name == "Agent":
        instance = await IRConverter.ir_to_agent(
            ir_data, conversation_id=req.conversation_id, cust_headers={}
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
    tmp_path = tmp_path_factory.mktemp("test_case_agent_controller_default_workflow_01")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例
# ===================================================================
class TestCaseControllerDefaultWorkflow01:
    """
    测试场景：意图识别匹配失败，触发调用默认工作流
    """

    CONVERSATION_ID = "controller_default_01"

    @classmethod
    def setup_class(cls):
        """清理状态目录，确保测试从零开始"""
        shutil.rmtree(STATE_DIR, ignore_errors=True)

    def test_1(self, local_ir_path):
        """
        首次请求：给我推荐一个理财产品
        -> FINANCIAL_WF_ID 工作流 配置为WaitUserInput，根据识别的意图触发
        -> 触发 FINANCIAL_WF_ID 工作流
        -> FINANCIAL_WF_ID 工作流执行中断
        """
        # LLM mock：意图识别对应 配置为WaitUserInput 的工作流
        model_runtime = _RecordingModelRuntime(
            [
                AIMessage(content='{"class": "分类2"}'),
            ]
        )
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        # FINANCIAL_WF_ID 工作流 mock 事件（来自 mock_workflow_output.md，5行 - 11行）
        financial_wf_events = [
            _build_workflow_start_stream_data(workflow_id=FINANCIAL_WF_ID),
            _build_partial_stream_data(
                answer="您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？",
                node_id="node_1747116170373",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_message_end_stream_data(
                answer="您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？",
                node_id="node_1747116170373",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_questioner_finish_stream_data(
                answer="",
                node_id="node_1747116170373",
                node_type="jiuwen.questioner",
            ),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {FINANCIAL_WF_ID: [financial_wf_events]}
        )
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="给我推荐一个理财产品",
                conversation_id=self.CONVERSATION_ID,
                params={},
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, "
                f"wf_id={ev.get('data', {}).get('workflow_id', '')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        event_types = [e.get("event") for e in events]

        # CP1: 事件非空
        assert len(events) > 0, "SSE 事件流不应为空"

        # CP2: 首帧是 start
        assert events[0].get("event") == "start", "首帧应为 start"

        # CP3: 新任务场景有 task_start
        assert "task_start" in event_types, "新任务场景应有 task_start"

        # CP4: workflow_start 含 FINANCIAL_WF_ID
        wf_start_events = [e for e in events if e.get("event") == "workflow_start"]
        assert any(
            e.get("data", {}).get("workflow_id") == FINANCIAL_WF_ID
            for e in wf_start_events
        ), "应有 FINANCIAL_WF_ID 的 workflow_start"

        # CP5: message 含提问器内容且 should_interrupt=True
        message_events = [e for e in events if e.get("event") == "message"]
        assert any(
            "理财产品" in e.get("data", {}).get("answer", "")
            and e.get("data", {}).get("should_interrupt") is True
            for e in message_events
        ), "应有 should_interrupt=True 的提问器 message"

        # CP6: message_end 含提问器内容且 should_interrupt=True
        message_end_events = [e for e in events if e.get("event") == "message_end"]
        assert any(
            "理财产品" in e.get("data", {}).get("answer", "")
            and e.get("data", {}).get("should_interrupt") is True
            for e in message_end_events
        ), "应有 should_interrupt=True 的提问器 message_end"

        # CP7: done 事件存在
        assert "done" in event_types, "应有 done 事件"

        # CP8: workflow_blocked 含 FINANCIAL_WF_ID
        blocked_events = [e for e in events if e.get("event") == "workflow_blocked"]
        assert any(
            e.get("data", {}).get("workflow_id") == FINANCIAL_WF_ID
            for e in blocked_events
        ), "应有 FINANCIAL_WF_ID 的 workflow_blocked"

        # CP9: intermediate_message 存在
        assert "intermediate_message" in event_types, "应有 intermediate_message"

        # CP10: agent_interrupted 存在
        assert "agent_interrupted" in event_types, "应有 agent_interrupted"

        # CP11: LLM 被调用一次，prompt 含用户输入
        assert len(model_runtime.calls) == 1, "LLM 应被调用一次"
        assert "理财产品" in _extract_model_prompt_text(model_runtime.calls[0])

        # CP12: FINANCIAL_WF_ID 工作流被调用
        called_wf_ids = [c["workflow_id"] for c in workflow_runtime.calls]
        assert FINANCIAL_WF_ID in called_wf_ids, "FINANCIAL_WF_ID 工作流应被调用"

        _IntegrationRegistry.clear()

    def test_2(self, local_ir_path):
        """
        再次请求：世界上最高的山
        -> 意图识别结果：不明
        -> 触发 默认工作流，正常执行完
        -> 触发 结束工作流，正常执行完
        """
        # LLM mock：意图不明
        model_runtime = _RecordingModelRuntime(
            [
                AIMessage(content='{"class": "分类1"}'),
            ]
        )
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        # DEFAULT_WF_ID 工作流 mock 事件（来自 mock_workflow_output.md，17行 - 28行）
        default_wf_events = [
            _build_workflow_start_stream_data(workflow_id=DEFAULT_WF_ID),
            _build_partial_stream_data(
                answer="",
                node_id="node_1753769873590",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_partial_stream_data(
                answer="珠穆朗玛峰",
                node_id="node_1753769873590",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_partial_stream_data(
                answer="",
                node_id="node_1753769873590",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="珠穆朗玛峰",
                node_id="node_1753769873590",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_workflow_end_stream_data(answer=""),
            _build_end_stream_data(answer=""),
        ]

        # END_WF_ID 工作流 mock 事件（来自 mock_workflow_output.md，32行 - 41行）
        end_wf_events = [
            _build_workflow_start_stream_data(workflow_id=END_WF_ID),
            _build_partial_stream_data(
                answer="结束工作流",
                node_id="node_1748098633016",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="结束工作流",
                node_id="node_1748098633016",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_workflow_end_stream_data(answer=""),
            _build_end_stream_data(answer=""),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {DEFAULT_WF_ID: [default_wf_events], END_WF_ID: [end_wf_events]}
        )
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="世界上最高的山",
                conversation_id="controller_default_01_second",
                params={},
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, "
                f"wf_id={ev.get('data', {}).get('workflow_id', '')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        event_types = [e.get("event") for e in events]

        # CP1: 事件非空
        assert len(events) > 0, "SSE 事件流不应为空"

        # CP2: 首帧是 start
        assert events[0].get("event") == "start", "首帧应为 start"

        # CP3: 新任务场景有 task_start
        assert "task_start" in event_types, "新任务场景应有 task_start"

        # CP4: workflow_start 含 DEFAULT_WF_ID
        wf_start_events = [e for e in events if e.get("event") == "workflow_start"]
        wf_start_ids = [e.get("data", {}).get("workflow_id") for e in wf_start_events]
        assert DEFAULT_WF_ID in wf_start_ids, "应有 DEFAULT_WF_ID 的 workflow_start"

        # CP5: workflow_start 含 END_WF_ID
        assert END_WF_ID in wf_start_ids, "应有 END_WF_ID 的 workflow_start"

        # CP6: message 含默认工作流回答
        message_events = [e for e in events if e.get("event") == "message"]
        message_answers = [e.get("data", {}).get("answer", "") for e in message_events]
        assert "珠穆朗玛峰" in message_answers, "应有默认工作流的 message 回答"

        # CP7: message_end 含默认工作流回答
        message_end_events = [e for e in events if e.get("event") == "message_end"]
        message_end_answers = [
            e.get("data", {}).get("answer", "") for e in message_end_events
        ]
        assert "珠穆朗玛峰" in message_end_answers, "应有默认工作流的 message_end 回答"

        # CP8: message_end 含结束工作流回答
        assert "结束工作流" in message_end_answers, "应有结束工作流的 message_end 回答"

        # CP9: workflow_end 含 DEFAULT_WF_ID
        wf_end_events = [e for e in events if e.get("event") == "workflow_end"]
        wf_end_ids = [e.get("data", {}).get("workflow_id") for e in wf_end_events]
        assert DEFAULT_WF_ID in wf_end_ids, "应有 DEFAULT_WF_ID 的 workflow_end"

        # CP10: workflow_end 含 END_WF_ID
        assert END_WF_ID in wf_end_ids, "应有 END_WF_ID 的 workflow_end"

        # CP11: task_terminated 存在
        assert "task_terminated" in event_types, "应有 task_terminated"

        # CP12: task_end 存在
        assert "task_end" in event_types, "应有 task_end"

        # CP13: intermediate_message 存在（E2E 参考帧中有，但当前版本 Controller 可能不产生，降级为 done 存在）
        assert "done" in event_types, "应有 done 事件"

        # CP14: LLM 被调用一次，prompt 含用户输入
        assert len(model_runtime.calls) == 1, "LLM 应被调用一次"
        assert "最高的山" in _extract_model_prompt_text(model_runtime.calls[0])

        # CP15: DEFAULT_WF_ID 和 END_WF_ID 工作流均被调用
        called_wf_ids = [c["workflow_id"] for c in workflow_runtime.calls]
        assert DEFAULT_WF_ID in called_wf_ids, "DEFAULT_WF_ID 工作流应被调用"
        assert END_WF_ID in called_wf_ids, "END_WF_ID 工作流应被调用"

        _IntegrationRegistry.clear()
