# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
__all__ = [
    "TestCaseControllerModeSetTerminal06",
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
from jiuwen.test.cases.workflow_node.test_case_agent_controller_new_06.test_end_workflow import (
    create_end_workflow,
)
from jiuwen.test.cases.workflow_node.test_case_agent_controller_new_06.test_shengjin_youli_workflow import (
    create_shengjin_youli_workflow,
)
from jiuwen.test.cases.workflow_node.test_case_agent_controller_new_06.test_smart_workflow import (
    create_smart_workflow,
)
from jiuwen.test.cases.workflow_node.test_case_agent_controller_new_06.test_start_workflow import (
    create_start_workflow,
)
from openjiuwen.core.runner import Runner

os.environ.setdefault("TGF_ENABLE", "false")
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "true")
# os.environ["BASE_AGENT_SWITCH"] = "true"
os.environ.setdefault("USE_OPENJIUWEN_WORKFLOW", "true")
os.environ.setdefault("WORKFLOW_EXECUTE_TIMEOUT", "1200")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage
from jiuwen.controller.agent.agent import Agent
from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade
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
START_WF_ID = "dfac616f-95d5-425a-aa52-e5432f24624a"
FIRST_WF_ID = "5710b24a-490f-419a-96d4-7eff0da204be"
UNUSED_WF_ID = "1921a930-e06d-4944-a890-b290e0d58147"
FINANCIAL_WF_ID = "875aeb56-1cd4-404c-9ef9-220c073f2e30"
END_WF_ID = "8f9ac059-0b15-4b11-baf2-18d10665c38c"


# ===================================================================
# Mock 基础设施（共享层）
# ===================================================================
class _IntegrationRegistry:
    """进程级单例，注册 Mock Model 和 Workflow 运行时。"""

    model = None
    workflow = None
    _mock_runtime_contexts: dict = {}
    _runner_calls: list = []

    @classmethod
    def clear(cls):
        cls.model = None
        cls.workflow = None
        cls._mock_runtime_contexts = {}
        cls._runner_calls = []

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
    def set_mock_runtime_context(cls, workflow_id: str, context: dict):
        cls._mock_runtime_contexts[workflow_id] = context

    @classmethod
    def get_mock_runtime_context(cls, workflow_id: str) -> dict:
        return cls._mock_runtime_contexts.get(workflow_id, {})

    @classmethod
    def add_runner_call(cls, payload: dict):
        cls._runner_calls.append(payload)

    @classmethod
    def get_runner_calls(cls):
        return list(cls._runner_calls)


class _FakeRuntimeContext:
    def __init__(self, initial=None):
        self._data = dict(initial or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def snapshot(self):
        return dict(self._data)


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
        mock_runtime_context=None,
    ):
        self._astream_handler = astream_handler
        self._ainvoke_handler = ainvoke_handler
        self._state_getter = state_getter
        self._status_getter = status_getter
        self._cleanup_handler = cleanup_handler
        self.runtime_context = runtime_context
        self._mock_runtime_context = (
            _FakeRuntimeContext(mock_runtime_context) if mock_runtime_context else None
        )

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
        return self._mock_runtime_context


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
    outputs: dict = None,
):
    """构建 MESSAGE_END 事件（code=5000）。"""
    data = {
        "answer": answer,
        "node_id": node_id,
        "node_name": node_name,
        "node_type": node_type,
        "should_interrupt": should_interrupt,
        "enable_history": True,
    }
    if outputs is not None:
        data["outputs"] = outputs
    return StreamData(
        code=StreamCode.MESSAGE_END.value,
        msg=StreamDataMsg.MESSAGE_END.value,
        data=data,
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


def _build_end_stream_data(*, answer: str, user_fields: dict = None):
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
            "user_fields": user_fields if user_fields is not None else {},
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


def _build_questioner_finish_stream_data(*, answer: str):
    """构建 questioner 阻断后的 FINISH 事件（code=0 → done）。"""
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": "node_questioner",
            "node_name": "提问器",
            "node_type": "jiuwen.questioner",
            "should_interrupt": True,
            "user_fields": {},
        },
        execution_id="",
    )


# ===================================================================
# 基于本地文件的状态存储（替代 Redis/Memory，支持多轮对话中断恢复）
# ===================================================================
STATE_DIR = Path(tempfile.gettempdir()) / "jiuwen_test_state_terminal_06"


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

            wf_mock_runtime_context = _IntegrationRegistry.get_mock_runtime_context(
                workflow_context.workflow_id
            )

            return _WorkflowInstanceAdapter(
                astream_handler=_astream_handler,
                ainvoke_handler=_ainvoke_handler,
                state_getter=lambda: session.get_state() if session else {},
                status_getter=lambda: None,
                cleanup_handler=lambda: None,
                runtime_context=runtime_context,
                mock_runtime_context=wf_mock_runtime_context,
            )
        return await original_create_workflow_instance(
            workflow_context,
            conversation_id,
            user_id,
        )

    if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
        monkeypatch.setattr(
            WorkflowHandler,
            "create_workflow_instance",
            staticmethod(_patched_create_workflow_instance),
        )
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            create_start_workflow()
            create_smart_workflow()
            create_shengjin_youli_workflow()
            create_end_workflow()
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    # 5) Runner.run_agent_streaming → 记录调用，同时保留真实执行逻辑
    original_run_agent_streaming = Runner.run_agent_streaming

    async def _recording_run_agent_streaming(*args, **kwargs):
        _IntegrationRegistry.add_runner_call(
            {
                "agent": kwargs.get("agent"),
                "inputs": kwargs.get("inputs"),
            }
        )
        async for item in original_run_agent_streaming(*args, **kwargs):
            yield item

    monkeypatch.setattr(Runner, "run_agent_streaming", _recording_run_agent_streaming)

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
        if os.getenv("BASE_AGENT_SWITCH", "false") == "true":
            assert isinstance(instance, OpenJiuwenAgentFacade)
            assert isinstance(instance._delegate_agent, Agent)
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
    tmp_path = tmp_path_factory.mktemp("test_case_agent_controller_terminal_06")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例
# ===================================================================
# @pytest.mark.skip(reason="临时跳过")
class TestCaseControllerModeSetTerminal06:
    """
    测试场景：工作流执行过程中，通过runtime_context更改 Continue -> Terminal
    """

    CONVERSATION_ID = "conv_terminal_06"

    @classmethod
    def setup_class(cls):
        """清理状态目录，确保测试从零开始"""
        shutil.rmtree(STATE_DIR, ignore_errors=True)

    def test_1(self, local_ir_path):
        """
        首次请求：你好
        -> 基于规则触发开始工作流
        -> 开始工作流中断（提问器）
        -> 注意：此处不作校验
        """
        model_runtime = _RecordingModelRuntime([])
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        start_wf_events = [
            _build_workflow_start_stream_data(workflow_id=START_WF_ID),
            _build_partial_stream_data(
                answer="您好，这里是银行，请问你是tom先生吗？",
                node_id="node_1747663017657",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_message_end_stream_data(
                answer="您好，这里是银行，请问你是tom先生吗？",
                node_id="node_1747663017657",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_questioner_finish_stream_data(answer=""),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {
                START_WF_ID: [start_wf_events],
            }
        )

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            _IntegrationRegistry.set_workflow(
                _LocalWorkflowAdapter(runtime=workflow_runtime)
            )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="你好",
                conversation_id=self.CONVERSATION_ID,
                params={
                    "globalVariables": {"name": "tom", "age": "25", "continue": "true"},
                    "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
                    "workflowSequence": [FIRST_WF_ID, UNUSED_WF_ID, FINANCIAL_WF_ID],
                },
            )
        )

        if os.getenv("BASE_AGENT_SWITCH", "false") == "true":
            runner_calls = _IntegrationRegistry.get_runner_calls()
            assert runner_calls, "Runner.run_agent_streaming should be called"
            last_call = runner_calls[-1]
            called_agent = last_call["agent"]
            called_inputs = last_call["inputs"]

            assert isinstance(called_agent, OpenJiuwenAgentFacade)
            assert isinstance(called_inputs, dict)
            assert called_inputs["query"] == "你好"
            assert called_inputs["conversation_id"] == self.CONVERSATION_ID
            assert "_jiuwen_runtime_kwargs" in called_inputs

            runtime_kwargs = called_inputs["_jiuwen_runtime_kwargs"]
            assert runtime_kwargs["stream"] is True
            assert "runtime_context" in runtime_kwargs
            assert "tool_switch_dict" in runtime_kwargs
            assert "trace_handlers" in runtime_kwargs

        events = _parse_sse_events(response_text)
        _err_evts = [e for e in events if e.get("event") == "error"]
        assert not _err_evts, (
            f"REQUEST 1 ERROR: {_err_evts[0].get('data', {}).get('message', 'unknown')}"
        )

        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好，这里是银行，请问你是tom先生吗？"},
        ]

        """
        第二次请求：是本人
        -> 恢复调用开始工作流
        -> 开始工作流执行完成
        -> 触发调用智能工作流
        -> 智能工作流触发中断
        """
        model_runtime = _RecordingModelRuntime(
            [AIMessage(content='{"class": "分类1"}')]
        )

        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        start_wf_events = [
            _build_partial_stream_data(
                answer="##开始工作流 continue：",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="True",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer=";age_temp: ",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="25",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="，age改为 10",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_message_end_stream_data(
                answer="##开始工作流 continue：True;age_temp: 25，age改为 10",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                outputs={"user_fields": {"age": "10", "continue": True}},
            ),
            _build_workflow_end_stream_data(
                answer="##开始工作流 continue：True;age_temp: 25，age改为 10",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_end_stream_data(
                answer="##开始工作流 continue：True;age_temp: 25，age改为 10",
                user_fields={"age": "10", "continue": True},
            ),
        ]

        first_wf_events = [
            _build_workflow_start_stream_data(workflow_id=FIRST_WF_ID),
            _build_partial_stream_data(
                answer="#BDD#/本次致电，是邀请您体验我航\u201c天天盈自动购买服务\u201d,\u201c天天盈\u201d底层关联货币基金。"
                "您可设置自动购买频率及自动购买日，系统在约定购买日检索关联账户余额、"
                "计算购买金额并自动扣款购买天天盈。市场有风险，投资须谨慎。"
                "后续会有人工联系您介绍可以吗?",
                node_id="node_1747193680786",
                node_name="开场白-提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_message_end_stream_data(
                answer="#BDD#/本次致电，是邀请您体验我航\u201c天天盈自动购买服务\u201d,\u201c天天盈\u201d底层关联货币基金。"
                "您可设置自动购买频率及自动购买日，系统在约定购买日检索关联账户余额、"
                "计算购买金额并自动扣款购买天天盈。市场有风险，投资须谨慎。"
                "后续会有人工联系您介绍可以吗?",
                node_id="node_1747193680786",
                node_name="开场白-提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_questioner_finish_stream_data(answer=""),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {START_WF_ID: [start_wf_events], FIRST_WF_ID: [first_wf_events]}
        )

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            _IntegrationRegistry.set_workflow(
                _LocalWorkflowAdapter(runtime=workflow_runtime)
            )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="是本人",
                conversation_id=self.CONVERSATION_ID,
                conversation_history=conversation_history,
                params={
                    "globalVariables": {"name": "tom", "age": "25", "continue": "true"},
                    "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
                    "workflowSequence": [FIRST_WF_ID, UNUSED_WF_ID, FINANCIAL_WF_ID],
                },
            )
        )

        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好，这里是银行，请问你是tom先生吗？"},
            {"role": "user", "content": "是本人"},
            {
                "role": "assistant",
                "content": "##开始工作流 continue：True;age_temp: 25，age改为 10",
            },
        ]

        """
        第三次请求：我要买升金
        -> 意图识别触发调用 升金有礼工作流
        -> 升金有礼工作流 中断
        """
        model_runtime = _RecordingModelRuntime(
            [AIMessage(content='{"class": "分类7"}')]
        )

        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        financial_wf_events = [
            _build_workflow_start_stream_data(workflow_id=FINANCIAL_WF_ID),
            _build_partial_stream_data(
                answer="#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出\u201c升金有礼\u201d积分回馈活动，即日起至",
                node_id="node_1747212048020",
                node_name="开场白-首轮澄清",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="123",
                node_id="node_1747212048020",
                node_name="开场白-首轮澄清",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，"
                "您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，"
                "我现在把活动短信发给您，好吗？",
                node_id="node_1747212048020",
                node_name="开场白-首轮澄清",
                node_type="jiuwen.message",
            ),
            _build_message_end_stream_data(
                answer="#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出\u201c升金有礼\u201d积分回馈活动，"
                "即日起至123，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，"
                "您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，"
                "我现在把活动短信发给您，好吗？",
                node_id="node_1747212048020",
                node_name="开场白-首轮澄清",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="##",
                node_id="node_1747212899505",
                node_name="开场白-提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_message_end_stream_data(
                answer="##",
                node_id="node_1747212899505",
                node_name="开场白-提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            _build_questioner_finish_stream_data(answer=""),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {
                FINANCIAL_WF_ID: [financial_wf_events],
            }
        )

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            _IntegrationRegistry.set_workflow(
                _LocalWorkflowAdapter(runtime=workflow_runtime)
            )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="我要买升金",
                conversation_id=self.CONVERSATION_ID,
                conversation_history=conversation_history,
                params={
                    "globalVariables": {"name": "tom", "age": "25", "continue": "true"},
                    "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
                    "workflowSequence": [FIRST_WF_ID, UNUSED_WF_ID, FINANCIAL_WF_ID],
                },
            )
        )

        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好，这里是银行，请问你是tom先生吗？"},
            {"role": "user", "content": "是本人"},
            {
                "role": "assistant",
                "content": "##开始工作流 continue：True;age_temp: 25，age改为 10",
            },
            {"role": "user", "content": "我要买升金"},
            {"role": "assistant", "content": "##"},
        ]

        """
        第四次请求：升金感兴趣
        -> 恢复调用 升金有礼工作流
        -> 升金有礼工作流 执行完成（continue=False, action_after_completion=Terminal）
        -> 触发执行结束工作流
        -> 结束工作流执行完成
        """
        model_runtime = _RecordingModelRuntime(
            [AIMessage(content='{"class": "分类7"}')]
        )

        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        financial_wf_events = [
            _build_partial_stream_data(
                answer=" ##内部系统插件，发短信##",
                node_id="node_1747293876339",
                node_name="发短息",
                node_type="jiuwen.message",
            ),
            _build_message_end_stream_data(
                answer=" ##内部系统插件，发短信##",
                node_id="node_1747293876339",
                node_name="发短息",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="#BDD#,#GD#/感谢您的支持，祝您生活愉快，再见！",
                node_id="node_1747293794534",
                node_name="成功结束",
                node_type="jiuwen.message",
            ),
            _build_message_end_stream_data(
                answer="#BDD#,#GD#/感谢您的支持，祝您生活愉快，再见！",
                node_id="node_1747293794534",
                node_name="成功结束",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="##升金结束continue: ",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="False",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="。action_after_completion：",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_partial_stream_data(
                answer="Terminal",
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
            _build_message_end_stream_data(
                answer="##升金结束continue: False。action_after_completion：Terminal",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                outputs={
                    "user_fields": {
                        "continue": False,
                        "action_after_completion": "Terminal",
                    }
                },
            ),
            _build_workflow_end_stream_data(
                answer="##升金结束continue: False。action_after_completion：Terminal",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_end_stream_data(
                answer="##升金结束continue: False。action_after_completion：Terminal",
                user_fields={"continue": False, "action_after_completion": "Terminal"},
            ),
        ]

        end_wf_events = [
            _build_workflow_start_stream_data(workflow_id=END_WF_ID),
            _build_partial_stream_data(
                answer="## 流程结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_message_end_stream_data(
                answer="## 流程结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_workflow_end_stream_data(
                answer="## 流程结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_end_stream_data(
                answer="## 流程结束",
            ),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {FINANCIAL_WF_ID: [financial_wf_events], END_WF_ID: [end_wf_events]}
        )

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            _IntegrationRegistry.set_workflow(
                _LocalWorkflowAdapter(runtime=workflow_runtime)
            )
            _IntegrationRegistry.set_mock_runtime_context(
                FINANCIAL_WF_ID,
                {
                    "_REQUEST": {
                        "dataId": "1",
                        "huashu_result": "1",
                        "ActivityTime": "123",
                        "continue": "true",
                        "name": "tom",
                        "age": "25",
                    }
                },
            )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="升金感兴趣",
                conversation_id=self.CONVERSATION_ID,
                conversation_history=conversation_history,
                params={
                    "globalVariables": {"name": "tom", "age": "25", "continue": "true"},
                    "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
                    "workflowSequence": [FIRST_WF_ID, UNUSED_WF_ID, FINANCIAL_WF_ID],
                },
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        event_types = [e.get("event") for e in events]
        error_events = [e for e in events if e.get("event") == "error"]
        error_detail = ""
        if error_events:
            import json  # noqa: redefined-outer-name

            error_detail = f"\n\nERROR EVENT: {json.dumps(error_events[0], ensure_ascii=False, default=str)}"
        assert not error_events, f"Error in request 4: {error_detail}"

        # CP1: events non-empty
        assert len(events) > 0, "Expected at least some SSE events"

        # CP2: first event is start
        assert events[0].get("event") == "start"

        # CP3: resume scenario, no task_start
        assert "task_start" not in event_types, (
            f"Resume scenario should NOT have task_start, got: {event_types}"
        )

        # CP4: workflow_resume contains FINANCIAL_WF_ID
        resume_events = [e for e in events if e.get("event") == "workflow_resume"]
        resume_wf_ids = [
            e.get("data", {}).get("workflow_id", "") for e in resume_events
        ]
        assert any(FINANCIAL_WF_ID in wid for wid in resume_wf_ids), (
            f"Expected workflow_resume for FINANCIAL_WF_ID, got: {resume_wf_ids}"
        )

        # CP5: message_end contains "发短信"
        message_end_answers = [
            e.get("data", {}).get("answer", "")
            for e in events
            if e.get("event") == "message_end"
        ]
        assert any("发短信" in a for a in message_end_answers), (
            f"Expected message_end with '发短信', got: {message_end_answers}"
        )

        # CP6: message_end contains "感谢您的支持"
        assert any("感谢您的支持" in a for a in message_end_answers), (
            f"Expected message_end with '感谢您的支持', got: {message_end_answers}"
        )

        # CP7: message_end contains "升金结束continue: False"
        assert any("升金结束continue: False" in a for a in message_end_answers), (
            f"Expected message_end with '升金结束continue: False', got: {message_end_answers}"
        )

        # CP8: message_end for end node has outputs with continue=False and action_after_completion=Terminal
        end_msg_end_events = [
            e
            for e in events
            if e.get("event") == "message_end"
            and e.get("data", {}).get("node_type") == "jiuwen.end"
        ]
        assert len(end_msg_end_events) > 0, (
            "Expected at least one message_end from jiuwen.end node"
        )
        terminal_end = [
            e
            for e in end_msg_end_events
            if e.get("data", {})
            .get("outputs", {})
            .get("user_fields", {})
            .get("action_after_completion")
            == "Terminal"
        ]
        assert len(terminal_end) > 0, (
            "Expected message_end with action_after_completion=Terminal in outputs.user_fields"
        )

        # CP9: workflow_end contains FINANCIAL_WF_ID
        wf_end_events = [e for e in events if e.get("event") == "workflow_end"]
        wf_end_ids = [e.get("data", {}).get("workflow_id", "") for e in wf_end_events]
        assert any(FINANCIAL_WF_ID in wid for wid in wf_end_ids), (
            f"Expected workflow_end for FINANCIAL_WF_ID, got: {wf_end_ids}"
        )

        # CP10: done event contains "升金结束continue: False"
        done_events = [e for e in events if e.get("event") == "done"]
        done_answers = [e.get("data", {}).get("answer", "") for e in done_events]
        assert any("升金结束continue: False" in a for a in done_answers), (
            f"Expected done with '升金结束continue: False', got: {done_answers}"
        )

        # CP11: task_terminated for FINANCIAL_WF_ID
        task_terminated_events = [
            e for e in events if e.get("event") == "task_terminated"
        ]
        terminated_wf_ids = [
            e.get("data", {}).get("workflow_id", "") for e in task_terminated_events
        ]
        assert any(FINANCIAL_WF_ID in wid for wid in terminated_wf_ids), (
            f"Expected task_terminated for FINANCIAL_WF_ID, got: {terminated_wf_ids}"
        )

        # CP12: workflow_start for END_WF_ID
        wf_start_events = [e for e in events if e.get("event") == "workflow_start"]
        wf_start_ids = [
            e.get("data", {}).get("workflow_id", "") for e in wf_start_events
        ]
        assert any(END_WF_ID in wid for wid in wf_start_ids), (
            f"Expected workflow_start for END_WF_ID, got: {wf_start_ids}"
        )

        # CP13: message_end contains "流程结束"
        assert any("流程结束" in a for a in message_end_answers), (
            f"Expected message_end with '流程结束', got: {message_end_answers}"
        )

        # CP14: workflow_end contains END_WF_ID
        assert any(END_WF_ID in wid for wid in wf_end_ids), (
            f"Expected workflow_end for END_WF_ID, got: {wf_end_ids}"
        )

        # CP15: task_terminated for END_WF_ID
        assert any(END_WF_ID in wid for wid in terminated_wf_ids), (
            f"Expected task_terminated for END_WF_ID, got: {terminated_wf_ids}"
        )

        # CP16: task_end event exists
        assert "task_end" in event_types, f"Expected task_end event, got: {event_types}"

        _IntegrationRegistry.clear()
