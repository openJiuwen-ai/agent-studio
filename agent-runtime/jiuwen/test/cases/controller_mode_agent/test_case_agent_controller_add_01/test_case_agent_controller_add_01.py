#!/usr/bin/env python
"""
南向契约测试 -- controller mode agent (case add 01)

场景：指定工作流顺序，全局意图 handler 是 Workflow，action_after_completion=Continue

覆盖场景：
  - Workflow 正常路由（Start → Normal → End）
  - 全局意图触发（提问器中断 → 投诉 → resume 后回到原流程）
  - 多轮对话：用户对天天盈感兴趣 / 不感兴趣 分支
  - Default Workflow fallback
  - SSE 事件断言和调用次数校验

用法：
  - pytest -v test_case_agent_controller_add_01.py
"""

__all__ = [
    "TestCaseControllerModeAgentAdd01",
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
# Workflow ID（与 agent IR 保持一致）
# ---------------------------------------------------------------------------
START_WF_ID = "acccdb9f-b479-4763-9f86-660009aa1d1a"
TIANTIANYING_WF_ID = "1f4c4496-0511-4367-a1bd-15d74d12ab0a"
END_WF_ID = "9a3d7a03-bcb8-44a2-9ed1-d5ec2fc0020d"
COMPLAIN_WF_ID = "eaef2c9f-97d3-46fe-a9e9-561726c7c61b"


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


def _build_workflow_blocked_stream_data(
    *,
    node_id: str,
    node_name: str,
    node_type: str,
    workflow_name: str,
    workflow_id: str,
    query: str,
    intent_id: str,
    intent_name: str,
):
    """构建 WORKFLOW_BLOCKED 事件（code=11000）。"""
    return StreamData(
        code=StreamCode.WORKFLOW_BLOCKED_MESSAGE.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "workflow_name": workflow_name,
            "workflow_id": workflow_id,
            "query": query,
            "intent_id": intent_id,
            "intent_name": intent_name,
        },
        execution_id="",
    )


def _build_questioner_finish_stream_data(*, answer: str):
    """构建 questioner 阻断后的 FINISH 事件（code=0 → done）。"""
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": "node_1746859174073",
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
STATE_DIR = Path(tempfile.gettempdir()) / "jiuwen_test_state"


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
# Contract Runtime 初始化（monkeypatch 三路）
# ===================================================================
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    """初始化 Contract Runtime，替换 Model/Workflow/Intent 为 Mock。"""
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
        print("  [DEBUG] _patched_execute_llm_call ENTERED!")
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
    monkeypatch.setattr(
        IntentionDetectModule, "_execute_llm_call", _patched_execute_llm_call
    )

    # 5) AsyncStateManager.get_state / save_state / delete_state → 基于本地文件的持久化
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
    # 找到 Agent IR 文件
    agent_files = list(AGENT_DIR.glob("*.json"))
    if len(agent_files) != 1:
        raise AssertionError(
            f"Expected exactly one agent json in {AGENT_DIR}, found {len(agent_files)}"
        )
    agent_ir = _load_json(agent_files[0])

    # 找到所有 Workflow JSON 文件
    workflow_files = {f.stem: f for f in WORKFLOW_DIR.glob("*.json")}

    agent_dst = tmp_path / agent_files[0].name

    # 更新 Agent IR 中的 workflow ir_path
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

    # 更新全局意图中的 workflow ir_path
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
    tmp_path = tmp_path_factory.mktemp("test_case_agent_controller_add_01")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例：Controller Mode Agent Add 01 南向契约测试
# ===================================================================
class TestCaseControllerModeAgentAdd01:
    """
    测试场景：指定工作流顺序，全局意图 handler 是 Workflow，
    action_after_completion=Continue。

    每个测试用例对应一次 SSE 请求，对响应数据帧中的关键字段
    （answer 等）作逐一校验。
    """

    # 多轮对话共享 conversation ID，保证状态文件 key 一致
    CONVERSATION_ID = "conv_multi_turn"

    @classmethod
    def setup_class(cls):
        """清理状态目录，确保测试从零开始"""
        shutil.rmtree(STATE_DIR, ignore_errors=True)

    def test_1(self, local_ir_path):
        """
        首次请求：你好
        -> 基于规则触发开始工作流 —— 输出关键数据帧 两帧：【开始工作流】你好 + 你好
        -> 基于规则触发第一顺序工作流 tiantianying 工作流
        -> 触发 tiantianying 工作流的提问器中断 —— 输出关键数据帧 一帧：#########我行天天盈换新升级，新增余额自动购买及自动快赎，产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，稍后我把产品介绍以短信形式发送给您？
        """

        # 依赖的 LLM mock输出：不依赖（_RecordingModelRuntime([])）
        model_runtime = _RecordingModelRuntime([])

        # 依赖的 Workflow mock输出（两个 workflow）
        # 开始工作流：workflow_start → 消息节点输出 → message_end → 结束节点 message → message_end → workflow_end → done
        start_wf_events = [
            # workflow_start
            _build_workflow_start_stream_data(workflow_id=START_WF_ID),
            _build_partial_stream_data(
                answer="【开始工作流】",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="你好",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            _build_partial_stream_data(
                answer="",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
            ),
            # 消息节点 message_end
            _build_message_end_stream_data(
                answer="【开始工作流】你好",
                node_id="node_1747275741185",
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
                answer="你好",
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
                answer="你好",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # workflow_end (code=4000)
            _build_workflow_end_stream_data(
                answer="你好",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # finish (code=0) — pass_streaming_data 看到 FINISH 会直接 return，不再写入
            _build_end_stream_data(answer="你好"),
        ]

        # tiantianying 工作流：提问器输出 → message_end (should_interrupt=True) → finish (should_interrupt=True)
        #
        # 对应 E2E 输出：
        #   workflow_start → message → message_end → done(answer="") → workflow_blocked
        #
        # 差异说明：
        #  - mock 中的提问器 finish 带有完整文本，而 E2E 的 done 事件 answer=""
        #  - workflow_blocked 不在这里 mock（由 Controller 层自动生成）
        #  - Controller 会扫描 questioner 节点产出的最后一个非空 answer
        #    并写入 workflow_blocked.intermediate_message 中
        tiantianying_wf_events = [
            # workflow_start
            _build_workflow_start_stream_data(workflow_id=TIANTIANYING_WF_ID),
            # 提问器 partial content (message event)
            _build_partial_stream_data(
                answer="#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
                node_id="node_1746859174073",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            # 提问器 message_end (should_interrupt=True)
            _build_message_end_stream_data(
                answer="#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
                node_id="node_1746859174073",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            # questioner finish — should_interrupt=True 是关键，
            # Controller 据此判断需要生成 workflow_blocked。
            # answer 为空串：与 E2E 一致，done 事件不携带文本摘要
            _build_questioner_finish_stream_data(answer=""),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {
                START_WF_ID: [start_wf_events],
                TIANTIANYING_WF_ID: [tiantianying_wf_events],
            }
        )
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        # End workflow mock: 开始工作流 → tiantianying → 提问器中断 → 本轮结束
        # 注意：此时 end workflow 不会被触发，所以不需要 mock
        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="你好",
                conversation_id=self.CONVERSATION_ID,
                params={
                    "workflowSequence": [TIANTIANYING_WF_ID],
                },
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, answer={ev.get('data', {}).get('answer', '')[:60]}"
            )

        # 校验点 1：SSE 事件非空
        assert len(events) > 0, "Expected at least some SSE events"

        # 校验点 2：第一个事件是 start
        assert events[0].get("event") == "start"

        # 校验点 3：存在 task_start 事件
        event_types = [e.get("event") for e in events]
        assert "task_start" in event_types, "Missing task_start event"

        # 校验点 4：存在 message 节点的 message_end 事件
        message_end_answers = [
            e.get("data", {}).get("answer", "")
            for e in events
            if e.get("event") == "message_end"
        ]
        assert any("【开始工作流】" in a for a in message_end_answers), (
            f"Expected message_end with '【开始工作流】', got: {message_end_answers}"
        )

        # 校验点 5：存在提问器 message_end 且 should_interrupt=True
        interrupt_events = [
            e
            for e in events
            if e.get("event") == "message_end"
            and e.get("data", {}).get("should_interrupt") is True
        ]
        assert len(interrupt_events) > 0, (
            "Expected at least one message_end with should_interrupt=True (questioner interruption)"
        )
        assert any(
            "天天盈" in e.get("data", {}).get("answer", "") for e in interrupt_events
        ), "Expected questioner message_end to contain '天天盈'"

        # 校验点 6：存在 task_terminated 或 agent_interrupted 事件（提问器中断后的终止信号）
        assert (
            "task_terminated" in event_types
            or "agent_interrupted" in event_types
            or "workflow_blocked" in event_types
        ), f"Expected termination/block event, got: {event_types}"

        # --- 校验点 7：intermediate_message 数据帧中必须包含 ConversationMessage 列表 ---
        # intermediate_message 由 Controller 自动产出，其 data.answer 是一个
        # list[ConversationMessage]（经过 JSON 序列化后变为 dict 列表）。
        # 见 mock_workflow_input_and_output.txt 第 15、26 行示例。
        intermediate_events = [
            e for e in events if e.get("event") == "intermediate_message"
        ]
        assert len(intermediate_events) > 0, (
            "Expected at least one intermediate_message event (code=7000)"
        )

        for int_evt in intermediate_events:
            conv_msgs = int_evt.get("data", {}).get("answer", [])
            assert isinstance(conv_msgs, list), (
                f"intermediate_message data.answer should be a list, got {type(conv_msgs).__name__}"
            )
            # 每条 ConversationMessage 至少应包含 role 和 content 字段
            for msg in conv_msgs:
                assert "role" in msg, f"ConversationMessage missing 'role': {msg}"
                assert "content" in msg, f"ConversationMessage missing 'content': {msg}"

        # 第一个 intermediate_message 必须包含用户的 "你好" 和助手的回答
        first_int = intermediate_events[0]
        first_convs = first_int.get("data", {}).get("answer", [])
        roles = [m.get("role") for m in first_convs]
        assert "user" in roles, (
            f"First intermediate_message should contain 'user' role, got roles: {roles}"
        )
        assert "assistant" in roles, (
            f"First intermediate_message should contain 'assistant' role, got roles: {roles}"
        )
        # 校验 content 中确实包含 "你好"
        contents = [m.get("content", "") for m in first_convs]
        assert any("你好" in c for c in contents), (
            f"Expected '你好' in conversation messages, got: {contents}"
        )

        _IntegrationRegistry.clear()

    def test_2(self, local_ir_path):
        """
        第二次请求：是本人，我要投诉
        -> 意图识别 —— 大模型输出：'{"class": "分类2"}'
        -> 触发 全局意图_提问器中断_投诉 工作流
        -> 触发 全局意图_提问器中断_投诉 工作流的提问器中断 —— 输出关键数据帧 一帧：非常抱歉给您带来困扰。祝您生活愉快，再见！
        """
        # 依赖的 LLM mock输出：意图识别返回分类2（投诉）
        model_runtime = _RecordingModelRuntime(
            [
                AIMessage(content='{"class": "分类2"}'),
            ]
        )

        # 依赖的 Workflow mock输出
        # 全局意图_提问器中断_投诉 工作流
        # workflow_start → 提问器 partial content → 提问器 message_end(should_interrupt=True) → finish(code=0)
        # 对应 mock_e2e_output.txt test_2 第49行：workflow_start(COMPLAIN_WF_ID)
        complain_wf_events = [
            _build_workflow_start_stream_data(workflow_id=COMPLAIN_WF_ID),
            # 提问器 partial content
            _build_partial_stream_data(
                answer="非常抱歉给您带来困扰。祝您生活愉快，再见！",
                node_id="node_1746862163890",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            # 提问器 message_end (should_interrupt=True)
            _build_message_end_stream_data(
                answer="非常抱歉给您带来困扰。祝您生活愉快，再见！",
                node_id="node_1746862163890",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            # finish (code=0) — questioner finish 后结束
            _build_questioner_finish_stream_data(
                answer="非常抱歉给您带来困扰。祝您生活愉快，再见！",
            ),
        ]

        # test_2 是 resume 场景：Controller 从 test_1 保存的中断状态恢复，
        # 直接路由到全局意图投诉工作流，不会重新执行 start/tiantianying/end 工作流。
        # 因此只需注册 complain_wf_events，其余工作流 mock 均不需要。
        workflow_runtime = _RecordingWorkflowRuntime(
            {
                COMPLAIN_WF_ID: [complain_wf_events],
            }
        )
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        # 提供对话历史，模拟 test_1 后的状态（用户说"你好"，助手回复tiantianying提问器消息）
        conversation_history = [
            {"role": "user", "content": "你好"},
            {
                "role": "assistant",
                "content": "#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
            },
        ]

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="是本人，我要投诉",
                conversation_id=self.CONVERSATION_ID,
                conversation_history=conversation_history,
                params={
                    "workflowSequence": [TIANTIANYING_WF_ID],
                    "activeWorkflows": [],
                },
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, answer={ev.get('data', {}).get('answer', '')[:60]}"
            )

        event_types = [e.get("event") for e in events]

        # --- 校验点 1：SSE 事件非空 ---
        assert len(events) > 0, "Expected at least some SSE events"

        # --- 校验点 2：第一个事件是 start ---
        assert events[0].get("event") == "start", (
            f"Expected first event to be 'start', got: {events[0].get('event')}"
        )

        # --- 校验点 3：续接对话（resume）场景不产生 task_start，直接进入工作流 ---
        # test_2 是从 test_1 中断状态恢复的续接请求，Controller 不会重新发出 task_start
        # E2E 参考输出（mock_e2e_output.txt）中 test_2 也没有 task_start 事件
        assert "task_start" not in event_types, (
            f"Resume scenario should NOT have task_start, got: {event_types}"
        )

        # --- 校验点 4：存在投诉工作流的提问器 message_end（should_interrupt=True） ---
        interrupt_events = [
            e
            for e in events
            if e.get("event") == "message_end"
            and e.get("data", {}).get("should_interrupt") is True
        ]
        assert len(interrupt_events) > 0, (
            "Expected at least one message_end with should_interrupt=True (complain questioner)"
        )
        interrupt_answers = [
            e.get("data", {}).get("answer", "") for e in interrupt_events
        ]
        assert any("抱歉" in a for a in interrupt_answers), (
            f"Expected complain questioner message_end to contain '抱歉', got: {interrupt_answers}"
        )

        # --- 校验点 5：存在投诉工作流的 workflow_start 事件 ---
        # 对应 mock_e2e_output.txt test_2 第49行
        wf_start_events = [e for e in events if e.get("event") == "workflow_start"]
        assert len(wf_start_events) > 0, (
            f"Expected workflow_start event, got event_types: {event_types}"
        )
        wf_start_ids = [
            e.get("data", {}).get("workflow_id", "") for e in wf_start_events
        ]
        assert any(COMPLAIN_WF_ID in wid for wid in wf_start_ids), (
            f"Expected workflow_start for COMPLAIN_WF_ID={COMPLAIN_WF_ID}, got: {wf_start_ids}"
        )

        # --- 校验点 6：存在 workflow_blocked 事件，且对应投诉工作流 ---
        blocked_events = [e for e in events if e.get("event") == "workflow_blocked"]
        assert len(blocked_events) > 0, (
            f"Expected workflow_blocked event, got event_types: {event_types}"
        )
        blocked_wf_ids = [
            e.get("data", {}).get("workflow_id", "") for e in blocked_events
        ]
        assert any(COMPLAIN_WF_ID in wid for wid in blocked_wf_ids), (
            f"Expected workflow_blocked for COMPLAIN_WF_ID={COMPLAIN_WF_ID}, got: {blocked_wf_ids}"
        )

        # --- 校验点 6：存在 agent_interrupted 事件（提问器中断后的终止信号） ---
        assert "agent_interrupted" in event_types, (
            f"Expected agent_interrupted event, got: {event_types}"
        )

        # --- 校验点 7：intermediate_message 包含完整的多轮对话历史 ---
        # intermediate_message.data.answer 是 list[ConversationMessage]
        # 应包含：test_1 的历史（你好 + 天天盈回复）+ test_2 的新一轮（我要投诉 + 抱歉回复）
        intermediate_events = [
            e for e in events if e.get("event") == "intermediate_message"
        ]
        assert len(intermediate_events) > 0, (
            "Expected at least one intermediate_message event"
        )

        last_int = intermediate_events[-1]
        conv_msgs = last_int.get("data", {}).get("answer", [])
        assert isinstance(conv_msgs, list), (
            f"intermediate_message data.answer should be a list, got {type(conv_msgs).__name__}"
        )
        for msg in conv_msgs:
            assert "role" in msg, f"ConversationMessage missing 'role': {msg}"
            assert "content" in msg, f"ConversationMessage missing 'content': {msg}"

        # 对话历史中必须包含本轮用户输入"我要投诉"和助手的投诉回复
        contents = [m.get("content", "") for m in conv_msgs]
        assert any("我要投诉" in c for c in contents), (
            f"Expected '我要投诉' in conversation history, got: {contents}"
        )
        assert any("抱歉" in c for c in contents), (
            f"Expected '抱歉' in conversation history (complain reply), got: {contents}"
        )

        # 对话历史中也应保留 test_1 的天天盈回复（多轮记忆）
        assert any("天天盈" in c for c in contents), (
            f"Expected '天天盈' in conversation history (from test_1), got: {contents}"
        )

        # --- 校验点 8：Model 被调用过意图识别 ---
        assert len(model_runtime.calls) > 0, (
            "Expected LLM to be called for intent recognition"
        )
        prompt_text = _extract_model_prompt_text(model_runtime.calls[0])
        assert "我要投诉" in prompt_text, (
            f"Expected '我要投诉' in LLM prompt, got: {prompt_text[:200]}"
        )

        # --- 校验点 9：投诉工作流被调用 ---
        assert len(workflow_runtime.calls) > 0, "Expected at least one workflow call"
        workflow_ids = [c["workflow_id"] for c in workflow_runtime.calls]
        assert any(COMPLAIN_WF_ID in wf for wf in workflow_ids), (
            f"Expected complain workflow to be called via intent detection, got: {workflow_ids}"
        )

        _IntegrationRegistry.clear()

    def test_3(self, local_ir_path):
        """
        第三次请求：不投诉了
        -> 意图识别 —— 大模型输出：'{"class": "分类1"}'
        -> 基于意图识别结果触发 全局意图_提问器中断_投诉 工作流
        -> 全局意图_提问器中断_投诉 返回 —— 输出关键数据帧 一帧：投诉，结束
        -> 触发 tiantianying 工作流 —— 输出关键数据帧 一帧：#########我行天天盈换新升级，新增余额自动购买及自动快赎，
           产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，稍后我把产品介绍以短信形式发送给您？
        """
        # 依赖的 LLM mock输出：意图识别返回分类1（意图不明）
        # 对应 mock_llm_input_and_output.txt test_3 第17行
        model_runtime = _RecordingModelRuntime(
            [
                AIMessage(content='{"class": "分类1"}'),
            ]
        )

        # 依赖的 Workflow mock输出（两个 workflow）
        #
        # test_3 是双 resume 场景：
        #   1. 先 resume 投诉工作流（COMPLAIN_WF_ID）—— 从提问器中断点继续，执行到结束节点
        #   2. 再 resume tiantianying 工作流（TIANTIANYING_WF_ID）—— 提问器再次中断
        #
        # 关键差异（对比 test_2）：
        #   - resume 场景不产生 workflow_start 帧（Controller 不重新启动工作流）
        #   - 投诉工作流 resume 后执行到 node_end，输出"投诉，结束"，然后 workflow_end + done
        #   - tiantianying 工作流 resume 后提问器再次中断，输出天天盈文本

        # 投诉工作流 resume 后的事件序列（无 workflow_start）
        complain_wf_resume_events = [
            # 结束节点 partial content
            _build_partial_stream_data(
                answer="投诉，结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # 结束节点 message_end
            _build_message_end_stream_data(
                answer="投诉，结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # workflow_end (code=4000)
            _build_workflow_end_stream_data(
                answer="投诉，结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            # finish (code=0)
            _build_end_stream_data(answer="投诉，结束"),
        ]

        # tiantianying 工作流 resume 后的事件序列（无 workflow_start）
        # 对应 mock_e2e_output.txt test_3 第81-87行
        tiantianying_wf_resume_events = [
            # 提问器 partial content (message event)
            _build_partial_stream_data(
                answer="#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
                node_id="node_1746859174073",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            # 提问器 message_end (should_interrupt=True)
            _build_message_end_stream_data(
                answer="#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
                node_id="node_1746859174073",
                node_name="提问器",
                node_type="jiuwen.questioner",
                should_interrupt=True,
            ),
            # questioner finish — should_interrupt=True，Controller 据此生成 workflow_blocked
            _build_questioner_finish_stream_data(answer=""),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {
                COMPLAIN_WF_ID: [complain_wf_resume_events],
                TIANTIANYING_WF_ID: [tiantianying_wf_resume_events],
            }
        )
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        # 提供对话历史，模拟 test_1 + test_2 后的状态
        conversation_history = [
            {"role": "user", "content": "你好"},
            {
                "role": "assistant",
                "content": "#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
            },
            {"role": "user", "content": "是本人，我要投诉"},
            {
                "role": "assistant",
                "content": "非常抱歉给您带来困扰。祝您生活愉快，再见！",
            },
        ]

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="不投诉了",
                conversation_id=self.CONVERSATION_ID,
                conversation_history=conversation_history,
                params={
                    "workflowSequence": [TIANTIANYING_WF_ID],
                    "activeWorkflows": [],
                },
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, answer={ev.get('data', {}).get('answer', '')[:60]}"
            )

        event_types = [e.get("event") for e in events]

        # --- 校验点 1：SSE 事件非空 ---
        assert len(events) > 0, "Expected at least some SSE events"

        # --- 校验点 2：第一个事件是 start ---
        # 对应 mock_e2e_output.txt test_3 第67行
        assert events[0].get("event") == "start", (
            f"Expected first event to be 'start', got: {events[0].get('event')}"
        )

        # --- 校验点 3：resume 场景不产生 task_start ---
        # test_3 是从 test_2 中断状态恢复的续接请求
        assert "task_start" not in event_types, (
            f"Resume scenario should NOT have task_start, got: {event_types}"
        )

        # --- 校验点 4：存在 workflow_resume 事件（投诉工作流 resume）---
        # 对应 mock_e2e_output.txt test_3 第69行：workflow_resume(COMPLAIN_WF_ID)
        resume_events = [e for e in events if e.get("event") == "workflow_resume"]
        assert len(resume_events) >= 1, (
            f"Expected at least one workflow_resume event, got: {event_types}"
        )
        resume_wf_ids = [
            e.get("data", {}).get("workflow_id", "") for e in resume_events
        ]
        assert any(COMPLAIN_WF_ID in wid for wid in resume_wf_ids), (
            f"Expected workflow_resume for COMPLAIN_WF_ID={COMPLAIN_WF_ID}, got: {resume_wf_ids}"
        )

        # --- 校验点 5：投诉工作流结束节点输出"投诉，结束" ---
        # 对应 mock_e2e_output.txt test_3 第71行：message(answer="投诉，结束", node_type=jiuwen.end)
        message_end_answers = [
            e.get("data", {}).get("answer", "")
            for e in events
            if e.get("event") == "message_end"
        ]
        assert any("投诉，结束" in a for a in message_end_answers), (
            f"Expected message_end with '投诉，结束' (complain wf end node), got: {message_end_answers}"
        )

        # --- 校验点 6：投诉工作流 workflow_end 事件 ---
        # 对应 mock_e2e_output.txt test_3 第75行：workflow_end(COMPLAIN_WF_ID)
        wf_end_events = [e for e in events if e.get("event") == "workflow_end"]
        assert len(wf_end_events) >= 1, (
            f"Expected at least one workflow_end event, got: {event_types}"
        )
        wf_end_ids = [e.get("data", {}).get("workflow_id", "") for e in wf_end_events]
        assert any(COMPLAIN_WF_ID in wid for wid in wf_end_ids), (
            f"Expected workflow_end for COMPLAIN_WF_ID={COMPLAIN_WF_ID}, got: {wf_end_ids}"
        )

        # --- 校验点 7：存在 tiantianying 工作流的 workflow_resume 事件 ---
        # 对应 mock_e2e_output.txt test_3 第79行：workflow_resume(TIANTIANYING_WF_ID)
        assert any(TIANTIANYING_WF_ID in wid for wid in resume_wf_ids), (
            f"Expected workflow_resume for TIANTIANYING_WF_ID={TIANTIANYING_WF_ID}, got: {resume_wf_ids}"
        )

        # --- 校验点 8：tiantianying 提问器再次中断，message_end 含天天盈文本 ---
        # 对应 mock_e2e_output.txt test_3 第81-83行
        interrupt_events = [
            e
            for e in events
            if e.get("event") == "message_end"
            and e.get("data", {}).get("should_interrupt") is True
        ]
        assert len(interrupt_events) > 0, (
            "Expected at least one message_end with should_interrupt=True (tiantianying questioner)"
        )
        assert any(
            "天天盈" in e.get("data", {}).get("answer", "") for e in interrupt_events
        ), "Expected tiantianying questioner message_end to contain '天天盈'"

        # --- 校验点 9：存在 tiantianying 工作流的 workflow_blocked 事件 ---
        # 对应 mock_e2e_output.txt test_3 第87行：workflow_blocked(TIANTIANYING_WF_ID)
        blocked_events = [e for e in events if e.get("event") == "workflow_blocked"]
        assert len(blocked_events) > 0, (
            f"Expected workflow_blocked event, got: {event_types}"
        )
        blocked_wf_ids = [
            e.get("data", {}).get("workflow_id", "") for e in blocked_events
        ]
        assert any(TIANTIANYING_WF_ID in wid for wid in blocked_wf_ids), (
            f"Expected workflow_blocked for TIANTIANYING_WF_ID={TIANTIANYING_WF_ID}, got: {blocked_wf_ids}"
        )

        # --- 校验点 10：存在 agent_interrupted 事件 ---
        # 对应 mock_e2e_output.txt test_3 第91行
        assert "agent_interrupted" in event_types, (
            f"Expected agent_interrupted event, got: {event_types}"
        )

        # --- 校验点 11：intermediate_message 包含完整的多轮对话历史 ---
        # 对应 mock_e2e_output.txt test_3 第89行：7条历史消息
        # 包含：你好/天天盈/投诉/抱歉/不投诉了/投诉结束/天天盈再次
        intermediate_events = [
            e for e in events if e.get("event") == "intermediate_message"
        ]
        assert len(intermediate_events) > 0, (
            "Expected at least one intermediate_message event"
        )

        last_int = intermediate_events[-1]
        conv_msgs = last_int.get("data", {}).get("answer", [])
        assert isinstance(conv_msgs, list), (
            f"intermediate_message data.answer should be a list, got {type(conv_msgs).__name__}"
        )
        for msg in conv_msgs:
            assert "role" in msg, f"ConversationMessage missing 'role': {msg}"
            assert "content" in msg, f"ConversationMessage missing 'content': {msg}"

        contents = [m.get("content", "") for m in conv_msgs]
        # 本轮用户输入"不投诉了"
        assert any("不投诉了" in c for c in contents), (
            f"Expected '不投诉了' in conversation history, got: {contents}"
        )
        # 投诉工作流结束输出"投诉，结束"
        assert any("投诉，结束" in c for c in contents), (
            f"Expected '投诉，结束' in conversation history, got: {contents}"
        )
        # tiantianying 工作流再次输出天天盈文本
        assert any("天天盈" in c for c in contents), (
            f"Expected '天天盈' in conversation history (tiantianying resume), got: {contents}"
        )

        # --- 校验点 12：LLM 被调用，prompt 含"不投诉了" ---
        assert len(model_runtime.calls) > 0, (
            "Expected LLM to be called for intent recognition"
        )
        prompt_text = _extract_model_prompt_text(model_runtime.calls[0])
        assert "不投诉了" in prompt_text, (
            f"Expected '不投诉了' in LLM prompt, got: {prompt_text[:200]}"
        )

        # --- 校验点 13：两个工作流均被调用 ---
        assert len(workflow_runtime.calls) >= 2, (
            f"Expected at least 2 workflow calls (complain + tiantianying), got: {len(workflow_runtime.calls)}"
        )
        called_wf_ids = [c["workflow_id"] for c in workflow_runtime.calls]
        assert any(COMPLAIN_WF_ID in wid for wid in called_wf_ids), (
            f"Expected COMPLAIN_WF_ID to be called, got: {called_wf_ids}"
        )
        assert any(TIANTIANYING_WF_ID in wid for wid in called_wf_ids), (
            f"Expected TIANTIANYING_WF_ID to be called, got: {called_wf_ids}"
        )

        _IntegrationRegistry.clear()

    def test_4(self, local_ir_path):
        """
        第四次请求：我对天天盈感兴趣
        -> 意图识别 —— 大模型输出：'{"class": "分类3"}'
        -> 基于意图识别结果触发 tiantianying 工作流
        -> tiantianying 工作流返回 —— 输出关键数据帧 两帧：用户表示感兴趣，给出天天盈介绍 + 【这是天天盈工作流的结束节点】天天盈结束
        -> 基于规则触发 结束 工作流
        -> 基于规则触发 结束 工作流返回 —— 输出关键数据帧 两帧：【结束工作流】我对天天盈感兴趣 + 我对天天盈感兴趣
        """
        # 依赖的 LLM mock 输出：意图识别返回分类3（天天盈理财产品推荐）
        # 对应 mock_llm_input_and_output.txt test_4 第27行
        model_runtime = _RecordingModelRuntime(
            [
                AIMessage(content='{"class": "分类3"}'),
            ]
        )

        # tiantianying 工作流 resume 后的事件序列（无 workflow_start）
        # 对应 mock_workflow_input_and_output.txt test_4 第70-77行
        tiantianying_wf_resume_events = [
            # 消息_2 节点：用户表示感兴趣，给出天天盈介绍
            _build_partial_stream_data(
                answer="用户表示感兴趣，给出天天盈介绍",
                node_id="node_1747292875948",
                node_name="消息_2",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="用户表示感兴趣，给出天天盈介绍",
                node_id="node_1747292875948",
                node_name="消息_2",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            # 结束节点：天天盈结束
            _build_partial_stream_data(
                answer="【这是天天盈工作流的结束节点】天天盈结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="【这是天天盈工作流的结束节点】天天盈结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_workflow_end_stream_data(
                answer="【这是天天盈工作流的结束节点】天天盈结束",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_end_stream_data(answer="【这是天天盈工作流的结束节点】天天盈结束"),
        ]

        # 结束工作流的事件序列（新启动，有 workflow_start）
        # 对应 mock_workflow_input_and_output.txt test_4 第82-94行
        end_wf_events = [
            _build_workflow_start_stream_data(workflow_id=END_WF_ID),
            # 消息节点：【结束工作流】我对天天盈感兴趣
            _build_partial_stream_data(
                answer="【结束工作流】",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_partial_stream_data(
                answer="我对天天盈感兴趣",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_partial_stream_data(
                answer="",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="【结束工作流】我对天天盈感兴趣",
                node_id="node_1747275741185",
                node_name="消息",
                node_type="jiuwen.message",
                should_interrupt=False,
            ),
            # 结束节点：我对天天盈感兴趣
            _build_partial_stream_data(
                answer="",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_partial_stream_data(
                answer="我对天天盈感兴趣",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_partial_stream_data(
                answer="",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_message_end_stream_data(
                answer="我对天天盈感兴趣",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
                should_interrupt=False,
            ),
            _build_workflow_end_stream_data(
                answer="我对天天盈感兴趣",
                node_id="node_end",
                node_name="结束",
                node_type="jiuwen.end",
            ),
            _build_end_stream_data(answer="我对天天盈感兴趣"),
        ]

        workflow_runtime = _RecordingWorkflowRuntime(
            {
                TIANTIANYING_WF_ID: [tiantianying_wf_resume_events],
                END_WF_ID: [end_wf_events],
            }
        )
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))
        _IntegrationRegistry.set_workflow(
            _LocalWorkflowAdapter(runtime=workflow_runtime)
        )

        # 提供对话历史，模拟 test_1 + test_2 + test_3 后的状态
        conversation_history = [
            {"role": "user", "content": "你好"},
            {
                "role": "assistant",
                "content": "#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
            },
            {"role": "user", "content": "是本人，我要投诉"},
            {
                "role": "assistant",
                "content": "非常抱歉给您带来困扰。祝您生活愉快，再见！",
            },
            {"role": "user", "content": "不投诉了"},
            {
                "role": "assistant",
                "content": "#########我行天天盈换新升级，新增余额自动购买及自动快赎，"
                "产品扩容到58只底层货币基金，普通赎回到账时间最快提速约半天，"
                "稍后我把产品介绍以短信形式发送给您？",
            },
        ]

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="我对天天盈感兴趣",
                conversation_id=self.CONVERSATION_ID,
                conversation_history=conversation_history,
                params={
                    "workflowSequence": [TIANTIANYING_WF_ID],
                    "activeWorkflows": [],
                },
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  [{i}] event={ev.get('event')}, answer={ev.get('data', {}).get('answer', '')[:60]}"
            )

        event_types = [e.get("event") for e in events]

        # --- 校验点 1：SSE 事件非空 ---
        assert len(events) > 0, "Expected at least some SSE events"

        # --- 校验点 2：第一个事件是 start ---
        # 对应 mock_e2e_output.txt test_4 第97行
        assert events[0].get("event") == "start", (
            f"Expected first event to be 'start', got: {events[0].get('event')}"
        )

        # --- 校验点 3：resume 场景不产生 task_start ---
        # test_4 是从 test_3 中断状态恢复的续接请求
        assert "task_start" not in event_types, (
            f"Resume scenario should NOT have task_start, got: {event_types}"
        )

        # --- 校验点 4：存在 tiantianying 工作流的 workflow_resume 事件 ---
        # 对应 mock_e2e_output.txt test_4 第99行：workflow_resume(TIANTIANYING_WF_ID)
        resume_events = [e for e in events if e.get("event") == "workflow_resume"]
        assert len(resume_events) >= 1, (
            f"Expected at least one workflow_resume event, got: {event_types}"
        )
        resume_wf_ids = [
            e.get("data", {}).get("workflow_id", "") for e in resume_events
        ]
        assert any(TIANTIANYING_WF_ID in wid for wid in resume_wf_ids), (
            f"Expected workflow_resume for TIANTIANYING_WF_ID={TIANTIANYING_WF_ID}, got: {resume_wf_ids}"
        )

        # --- 校验点 5：tiantianying 工作流输出"用户表示感兴趣，给出天天盈介绍" ---
        # 对应 mock_e2e_output.txt test_4 第101-103行
        message_end_answers = [
            e.get("data", {}).get("answer", "")
            for e in events
            if e.get("event") == "message_end"
        ]
        assert any("用户表示感兴趣" in a for a in message_end_answers), (
            f"Expected message_end with '用户表示感兴趣' (tiantianying intro), got: {message_end_answers}"
        )

        # --- 校验点 6：tiantianying 工作流结束节点输出"天天盈结束" ---
        # 对应 mock_e2e_output.txt test_4 第105-107行
        assert any("天天盈结束" in a for a in message_end_answers), (
            f"Expected message_end with '天天盈结束' (tiantianying end node), got: {message_end_answers}"
        )

        # --- 校验点 7：tiantianying 工作流 workflow_end 事件 ---
        # 对应 mock_e2e_output.txt test_4 第109行
        wf_end_events = [e for e in events if e.get("event") == "workflow_end"]
        assert len(wf_end_events) >= 1, (
            f"Expected at least one workflow_end event, got: {event_types}"
        )
        wf_end_ids = [e.get("data", {}).get("workflow_id", "") for e in wf_end_events]
        assert any(TIANTIANYING_WF_ID in wid for wid in wf_end_ids), (
            f"Expected workflow_end for TIANTIANYING_WF_ID={TIANTIANYING_WF_ID}, got: {wf_end_ids}"
        )

        # --- 校验点 8：结束工作流 workflow_start 事件 ---
        # 对应 mock_e2e_output.txt test_4 第113行：workflow_start(END_WF_ID)
        wf_start_events = [e for e in events if e.get("event") == "workflow_start"]
        assert len(wf_start_events) >= 1, (
            f"Expected at least one workflow_start event (end workflow), got: {event_types}"
        )
        wf_start_ids = [
            e.get("data", {}).get("workflow_id", "") for e in wf_start_events
        ]
        assert any(END_WF_ID in wid for wid in wf_start_ids), (
            f"Expected workflow_start for END_WF_ID={END_WF_ID}, got: {wf_start_ids}"
        )

        # --- 校验点 9：结束工作流输出"【结束工作流】我对天天盈感兴趣" ---
        # 对应 mock_e2e_output.txt test_4 第121行
        assert any("结束工作流" in a for a in message_end_answers), (
            f"Expected message_end with '结束工作流' (end workflow node), got: {message_end_answers}"
        )

        # --- 校验点 10：结束工作流结束节点输出"我对天天盈感兴趣" ---
        # 对应 mock_e2e_output.txt test_4 第129行
        assert any("我对天天盈感兴趣" in a for a in message_end_answers), (
            f"Expected message_end with '我对天天盈感兴趣' (end workflow end node), got: {message_end_answers}"
        )

        # --- 校验点 11：结束工作流 workflow_end 事件 ---
        # 对应 mock_e2e_output.txt test_4 第131行
        assert any(END_WF_ID in wid for wid in wf_end_ids), (
            f"Expected workflow_end for END_WF_ID={END_WF_ID}, got: {wf_end_ids}"
        )

        # --- 校验点 12：task_terminated 事件，含 END_WF_ID ---
        # 对应 mock_e2e_output.txt test_4 第135行
        terminated_events = [e for e in events if e.get("event") == "task_terminated"]
        assert len(terminated_events) > 0, (
            f"Expected task_terminated event, got: {event_types}"
        )
        assert any(
            END_WF_ID in e.get("data", {}).get("workflow_id", "")
            for e in terminated_events
        ), (
            f"Expected task_terminated with END_WF_ID={END_WF_ID}, got: {terminated_events}"
        )

        # --- 校验点 13：task_end 事件 ---
        # 对应 mock_e2e_output.txt test_4 第137行
        assert "task_end" in event_types, f"Expected task_end event, got: {event_types}"

        # --- 校验点 14：LLM 被调用，prompt 含"我对天天盈感兴趣" ---
        assert len(model_runtime.calls) > 0, (
            "Expected LLM to be called for intent recognition"
        )
        prompt_text = _extract_model_prompt_text(model_runtime.calls[0])
        assert "我对天天盈感兴趣" in prompt_text, (
            f"Expected '我对天天盈感兴趣' in LLM prompt, got: {prompt_text[:200]}"
        )

        # --- 校验点 15：两个工作流均被调用 ---
        assert len(workflow_runtime.calls) >= 2, (
            f"Expected at least 2 workflow calls (tiantianying + end), got: {len(workflow_runtime.calls)}"
        )
        called_wf_ids = [c["workflow_id"] for c in workflow_runtime.calls]
        assert any(TIANTIANYING_WF_ID in wid for wid in called_wf_ids), (
            f"Expected TIANTIANYING_WF_ID to be called, got: {called_wf_ids}"
        )
        assert any(END_WF_ID in wid for wid in called_wf_ids), (
            f"Expected END_WF_ID to be called, got: {called_wf_ids}"
        )

        _IntegrationRegistry.clear()


# ===================================================================
# 辅助函数
# ===================================================================
async def _collect_stream(stream):
    """收集异步流中的所有事件。"""
    items = []
    async for item in stream:
        items.append(item)
    return items

