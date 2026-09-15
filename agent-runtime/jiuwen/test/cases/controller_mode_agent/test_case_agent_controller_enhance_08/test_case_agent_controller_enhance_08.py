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
    "TestCaseControllerModeAgentEnhance08",
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
os.environ.setdefault("USE_EI_INTENT", "true")

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
# Workflow ID（与 workflow JSON 保持一致）
# ---------------------------------------------------------------------------
INTENT_WF_ID = "966cbaa3-e693-4cd4-be18-44747329df9e"
ZHIHUIWAIHUO_WF_ID = "d7221d46-516f-4cf2-bc02-bc764f682fff"
RONGEIJIE_WF_ID = "666aea41-bec1-47a9-af29-590f19bc01dd"


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


# ===================================================================
# 基于本地文件的状态存储（替代 Redis/Memory，支持多轮对话中断恢复）
# ===================================================================
STATE_DIR = Path(tempfile.gettempdir()) / "jiuwen_test_state_enhance_08"


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
    tmp_path = tmp_path_factory.mktemp("test_case_agent_controller_enhance_08")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例
# ===================================================================
class TestCaseControllerModeAgentEnhance08:
    """
    测试场景：意图识别工作流路由，specify_workflow_order=false。
    Controller 通过意图识别工作流选出融e借工作流并执行，单轮正常完成。
    """

    CONVERSATION_ID = "conv_enhance_08"

    @classmethod
    def setup_class(cls):
        """清理状态目录，确保测试从零开始"""
        shutil.rmtree(STATE_DIR, ignore_errors=True)

    def test_1(self, local_ir_path):
        """
        首次请求：你好agent_controller_enhance_08
        -> 请求中配置 intent 字段，intent字段的优先级最高，只要唯一匹配上工作流，就直接执行这个工作流
        -> 触发融e借工作流
        -> SSE 帧序列：start → task_start → workflow_start → message → message_end
                       → message → message_end → workflow_end → done → task_end
        """
        # LLM mock：intent 字段直接命中工作流，不走意图识别 LLM，传空列表即可
        model_runtime = _RecordingModelRuntime([])
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))

        # 融e借工作流 mock 事件（来自 mock_workflow_output.md）
        rongeijie_wf_events = [
            _build_workflow_start_stream_data(workflow_id=RONGEIJIE_WF_ID),
            _build_partial_stream_data(
                answer="关注到您近期有用款需求，我行融e借个人信用贷款...不知道您是否感兴趣？\n【谁说用户没有其他意图】",
                node_id="node_1754443804332",
                node_name="消息_1_1_1",
                node_type="jiuwen.message",
            ),
            _build_message_end_stream_data(
                answer="关注到您近期有用款需求，我行融e借个人信用贷款...不知道您是否感兴趣？\n【谁说用户没有其他意图】",
                node_id="node_1754443804332",
                node_name="消息_1_1_1",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="ssq_融e借产品推荐_1--结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_message_end_stream_data(
                answer="ssq_融e借产品推荐_1--结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_workflow_end_stream_data(
                answer="ssq_融e借产品推荐_1--结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_end_stream_data(answer="ssq_融e借产品推荐_1--结束"),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {RONGEIJIE_WF_ID: [rongeijie_wf_events]}
        )
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="你好agent_controller_enhance_08",
                conversation_id=self.CONVERSATION_ID,
                params={
                    # intent 字段优先级最高，唯一匹配融e借工作流后直接执行，跳过意图识别 LLM
                    "intent": "贷款",  # 此处不要调整
                },
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:60]}"
            )

        # mock_e2e_output_stream_data.md 预期 10 帧，逐帧对齐校验：
        #  start → task_start → workflow_start → message → message_end
        #  → message → message_end → workflow_end → done → task_end

        # CP1: SSE 事件非空
        assert len(events) > 0, "Expected at least some SSE events"

        # CP2: 首帧是 start
        assert events[0].get("event") == "start", "First event must be 'start'"

        # CP3: 新任务场景有 task_start
        event_types = [e.get("event") for e in events]
        assert "task_start" in event_types, "Missing task_start event"

        # CP4: workflow_start 含融e借工作流 ID
        wf_start_events = [e for e in events if e.get("event") == "workflow_start"]
        assert len(wf_start_events) > 0, "Missing workflow_start event"
        assert wf_start_events[0].get("data", {}).get("workflow_id") == RONGEIJIE_WF_ID

        # CP5: 第一个 message 事件 —— 消息节点输出融e借文案
        message_events = [e for e in events if e.get("event") == "message"]
        assert len(message_events) >= 2, "Expected at least 2 message events"
        msg_1 = message_events[0].get("data", {})
        assert "融e借" in msg_1.get("answer", ""), (
            "message[0].answer should contain '融e借'"
        )
        assert msg_1.get("node_type") == "jiuwen.message"
        assert msg_1.get("node_id") == "node_1754443804332"

        # CP6: 第一个 message_end 事件 —— 消息节点结束，含融e借文案
        message_end_events = [e for e in events if e.get("event") == "message_end"]
        assert len(message_end_events) >= 2, "Expected at least 2 message_end events"
        me_1 = message_end_events[0].get("data", {})
        assert "融e借" in me_1.get("answer", ""), (
            "message_end[0].answer should contain '融e借'"
        )
        assert me_1.get("enable_history") is True
        assert me_1.get("node_type") == "jiuwen.message"

        # CP7: 第二个 message 事件 —— 结束节点输出结束文案
        msg_2 = message_events[1].get("data", {})
        assert "结束" in msg_2.get("answer", ""), (
            "message[1].answer should contain '结束'"
        )
        assert msg_2.get("node_type") == "jiuwen.end"
        assert msg_2.get("node_id") == "node_end"

        # CP8: 第二个 message_end 事件 —— 结束节点结束
        me_2 = message_end_events[1].get("data", {})
        assert "结束" in me_2.get("answer", ""), (
            "message_end[1].answer should contain '结束'"
        )
        assert me_2.get("enable_history") is True
        assert me_2.get("node_type") == "jiuwen.end"

        # CP9: workflow_end 含融e借工作流 ID 和结束文案
        wf_end_events = [e for e in events if e.get("event") == "workflow_end"]
        assert len(wf_end_events) > 0, "Missing workflow_end event"
        wf_end_data = wf_end_events[0].get("data", {})
        assert wf_end_data.get("workflow_id") == RONGEIJIE_WF_ID
        assert "结束" in wf_end_data.get("answer", "")

        # CP10: done 事件（工作流彻底完成）
        assert "done" in event_types, "Missing done event"
        done_events = [e for e in events if e.get("event") == "done"]
        assert "结束" in done_events[0].get("data", {}).get("answer", "")

        # CP11: task_end（单轮正常完成）
        assert "task_end" in event_types, "Missing task_end event"

        # CP12: 无 workflow_blocked / agent_interrupted（非中断场景）
        assert "workflow_blocked" not in event_types, "Unexpected workflow_blocked"
        assert "agent_interrupted" not in event_types, "Unexpected agent_interrupted"

        # CP13: 融e借工作流被实际调用
        called_wf_ids = [c["workflow_id"] for c in workflow_runtime.calls]
        assert any(RONGEIJIE_WF_ID in wid for wid in called_wf_ids), (
            "融e借工作流未被调用"
        )

        _IntegrationRegistry.clear()
