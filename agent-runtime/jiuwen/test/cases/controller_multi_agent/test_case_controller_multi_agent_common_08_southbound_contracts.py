import asyncio
import json
import os
import time
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage
from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.orchestration.flow.constant import REQUEST_VARIABLES
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.plugin.models.tool import WORKFLOW_END_TYPE
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import distribute_execution_request
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest
from jiuwen.test.cases.controller_multi_agent.agent_core_model_contract_runtime import (
    AgentCoreModelWrapperRuntime,
)

from jiuwen.test.cases.controller_multi_agent.test_case_controller_multi_agent_01 import (
    RESOURCE_TEMPLATE_DIR,
)


CASE_DIR = Path(__file__).resolve().parent
CASE_ASSET_DIR = CASE_DIR / "test_case_controller_multi_agent_common_08"
AGENT_DIR = CASE_ASSET_DIR / "agent"
SUB_AGENT_DIR = CASE_ASSET_DIR / "sub_agent"
WORKFLOW_DIR = CASE_ASSET_DIR / "workflow"

ROOT_WORKFLOW_ID = "ad21cfff-e864-4af8-be97-2e3fe605322c"
START_WORKFLOW_ID = "start_04558450-6d42-4b4b-9601-199be7504f9f"
TRANSFER_WORKFLOW_ID = "aeea775b-307e-4e46-867b-0c62bf6b6ed7"
DEFAULT_WORKFLOW_ID = "default_ebc41e93-894b-4adb-8009-e517d50a73a5"
ROUTABLE_WORKFLOW_IDS = {
    ROOT_WORKFLOW_ID,
    START_WORKFLOW_ID,
    TRANSFER_WORKFLOW_ID,
    DEFAULT_WORKFLOW_ID,
}


class _IntegrationRegistry:
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
        self.runtime_context = _FakeRuntimeContext(
            {REQUEST_VARIABLES: {"name": "", "status": ""}}
        )
        self._state = {"session_id": session_id}

    def get_state(self, key=None):
        if key is None:
            state = dict(self._state)
            state["runtime_context"] = self.runtime_context.snapshot()
            return state
        if key == "runtime_context":
            return self.runtime_context.snapshot()
        return self._state.get(key)

    def update_state(self, payload: dict):
        self._state.update(payload)


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

    def get_runtime_context(self):
        return self.runtime_context

    def get_workflow_execute_status(self):
        return self._status_getter()

    async def async_clean_up(self):
        result = self._cleanup_handler()
        if asyncio.iscoroutine(result):
            await result


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
        return session.runtime_context

    async def astream(
        self, *, query, params, workflow_id, agent_id="", session_id="", context=None
    ):
        runner = getattr(self.runtime, "astream", None)
        if runner is None:
            runner = self.runtime.stream
        session = self.create_session(session_id)
        return runner(
            {"inputs": query, "params": params},
            session=session,
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
    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _RecordingModelRuntime:
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
    def __init__(self, scripted_by_workflow_id):
        self.scripted_by_workflow_id = {
            key: list(value) for key, value in scripted_by_workflow_id.items()
        }
        self.calls = []

    def stream(
        self,
        inputs,
        session=None,
        session_id=None,
        workflow_id=None,
        agent_id=None,
        context=None,
    ):
        request_variables = {}
        if context is not None:
            request_variables = dict(context.get(REQUEST_VARIABLES, {}) or {})
        if session is not None:
            session.update_state(
                {
                    "last_workflow_id": workflow_id or "",
                    "last_query": inputs.get("inputs", ""),
                }
            )

        self.calls.append(
            {
                "inputs": inputs,
                "query": inputs.get("inputs", ""),
                "params": inputs.get("params", {}),
                "session_id": session_id or "",
                "workflow_id": workflow_id or "",
                "agent_id": agent_id or "",
                "context": context,
                "request_variables": request_variables,
            }
        )

        scripted_events = self.scripted_by_workflow_id.get(workflow_id, [])
        if scripted_events:
            events = scripted_events.pop(0)
        else:
            events = [
                _build_end_stream_data(
                    workflow_id=workflow_id or "", answer="workflow default"
                )
            ]

        if session is not None:
            updated_request_variables = dict(request_variables)
            updated_request_variables["latest_query"] = inputs.get("inputs", "")
            session.runtime_context.set(REQUEST_VARIABLES, updated_request_variables)

        async def _iterate():
            for item in events:
                yield item

        return _iterate()


def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"
    _IntegrationRegistry.clear()

    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *args, **kwargs: _FallbackChatModel(),
    )

    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {RESOURCE_TEMPLATE_DIR}"
        )

    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    async def _patched_execute_llm_call(self, llm_input):
        start_time = time.time()
        model = _IntegrationRegistry.get_model()
        if model is not None:
            llm_message = await model.ainvoke(
                llm_input,
                model_id=getattr(self.llm, "model_name", "")
                or getattr(self.llm, "default_model_id", ""),
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
            workflow_context, conversation_id, user_id
        )

    monkeypatch.setattr(
        WorkflowHandler,
        "create_workflow_instance",
        staticmethod(_patched_create_workflow_instance),
    )
    monkeypatch.setattr(
        IntentionDetectModule, "_execute_llm_call", _patched_execute_llm_call
    )


def _build_message_end_stream_data(
    *,
    workflow_id: str,
    answer: str,
    node_id: str,
    node_name: str,
    node_type: str,
    should_interrupt: bool = False,
    user_fields: dict | None = None,
):
    return StreamData(
        code=StreamCode.MESSAGE_END.value,
        msg=StreamDataMsg.MESSAGE_END.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "should_interrupt": should_interrupt,
            "workflow_id": workflow_id,
            "enable_history": True,
            "user_fields": user_fields or {},
        },
        execution_id=f"exec_{workflow_id}",
    )


def _build_end_stream_data(
    *, workflow_id: str, answer: str, user_fields: dict | None = None
):
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": "node_end",
            "node_name": "node_end",
            "node_type": WORKFLOW_END_TYPE,
            "should_interrupt": False,
            "workflow_id": workflow_id,
            "user_fields": user_fields or {},
        },
        execution_id=f"exec_{workflow_id}",
    )


def _build_questioner_finish_stream_data(*, workflow_id: str, answer: str):
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": "node_questioner",
            "node_name": "node_questioner",
            "node_type": "jiuwen.questioner",
            "should_interrupt": True,
            "workflow_id": workflow_id,
            "user_fields": {},
        },
        execution_id=f"exec_{workflow_id}",
    )


def _find_single_json(directory: Path) -> Path:
    json_files = sorted(directory.glob("*.json"))
    if len(json_files) != 1:
        raise AssertionError(
            f"Expected exactly one json file in {directory}, found {len(json_files)}"
        )
    return json_files[0]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_fixture_path(filename: str, *directories: Path) -> Path:
    for directory in directories:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Unable to resolve IR reference {filename!r} in {[str(d) for d in directories]}"
    )


def _copy_case_ir_bundle(tmp_path: Path) -> Path:
    root_src = _find_single_json(AGENT_DIR)
    child_src = _find_single_json(SUB_AGENT_DIR)
    root_ir = _load_json(root_src)
    child_ir = _load_json(child_src)

    child_dst = tmp_path / child_src.name
    root_dst = tmp_path / root_src.name

    for workflow in child_ir.get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow_src = _resolve_fixture_path(workflow_name, WORKFLOW_DIR)
            workflow["ir_path"] = str(workflow_src)

    for workflow in root_ir.get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow_src = _resolve_fixture_path(workflow_name, WORKFLOW_DIR)
            workflow["ir_path"] = str(workflow_src)

    for agent in root_ir.get("configs", {}).get("agents", []):
        child_name = Path(agent.get("ir_path", "")).name
        if child_name:
            child_ref = _resolve_fixture_path(child_name, SUB_AGENT_DIR)
            if child_ref.name != child_src.name:
                raise AssertionError(
                    f"Root IR points to unexpected child IR: {child_ref}"
                )
            agent["ir_path"] = str(child_dst)

    child_dst.write_text(
        json.dumps(child_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    root_dst.write_text(
        json.dumps(root_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root_dst


async def _run_local_ir_request(
    *,
    ir_path: Path,
    query: str,
    conversation_id: str,
    conversation_history=None,
):
    req = ExecutionRequest.model_validate(
        {
            "conversationId": conversation_id,
            "query": query,
            "irPath": str(ir_path),
            "responseMode": "streaming",
            "executionMode": "sync",
            "params": {
                "conversationHistory": conversation_history or [],
                "pluginConfigs": [],
                "globalVariables": {},
                "llmExtraConfigs": {},
                "workflowSequence": [],
                "activeWorkflows": [],
            },
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


def _extract_model_prompt_text(call: _ModelCall) -> str:
    inputs = call.inputs
    if isinstance(inputs, dict):
        return json.dumps(inputs, ensure_ascii=False, default=str)
    if isinstance(inputs, list):
        return "\n".join(str(getattr(item, "content", item)) for item in inputs)
    return str(inputs)


async def _collect_stream(stream):
    items = []
    async for item in stream:
        items.append(item)
    return items


@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("controller_multi_agent_common08_southbound")
    return _copy_case_ir_bundle(tmp_path)


def test_case08_modelnew_records_controller_inputs_from_real_ir(local_ir_path):
    model_runtime = AgentCoreModelWrapperRuntime(
        [
            AIMessage(content=json.dumps({"result": 2}, ensure_ascii=False)),
            AIMessage(content=json.dumps({"result": 1}, ensure_ascii=False)),
            AIMessage(content="0"),
        ]
    )
    workflow_runtime = _RecordingWorkflowRuntime(
        {
            ROOT_WORKFLOW_ID: [[]],
            START_WORKFLOW_ID: [[]],
            TRANSFER_WORKFLOW_ID: [[]],
            DEFAULT_WORKFLOW_ID: [[]],
        }
    )
    _IntegrationRegistry.set_model(
        AgentCoreModelLayer(_LocalModelAdapter(runtime=model_runtime))
    )
    _IntegrationRegistry.set_workflow(_LocalWorkflowAdapter(runtime=workflow_runtime))

    response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=local_ir_path,
            query="transfer money",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
        )
    )

    relevant_calls = [
        call for call in model_runtime.calls if isinstance(call.inputs, dict)
    ]
    assert len(relevant_calls) >= 1
    first_prompt = _extract_model_prompt_text(relevant_calls[0])
    assert "transfer money" in first_prompt
    assert len(workflow_runtime.calls) == 0
    assert "task_end" in response_text, response_text
    assert '"event":"error"' not in response_text, response_text
    _IntegrationRegistry.clear()


def test_case08_workflownew_resume_contract_keeps_stateful_runtime_context():
    workflow_runtime = _RecordingWorkflowRuntime(
        {
            TRANSFER_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=TRANSFER_WORKFLOW_ID,
                        answer="please provide 1.xxx 2.xxx",
                        node_id="node_questioner",
                        node_name="node_questioner",
                        node_type="jiuwen.questioner",
                        should_interrupt=True,
                    ),
                    _build_questioner_finish_stream_data(
                        workflow_id=TRANSFER_WORKFLOW_ID,
                        answer="",
                    ),
                ],
                [
                    _build_message_end_stream_data(
                        workflow_id=TRANSFER_WORKFLOW_ID,
                        answer="resume workflow answer",
                        node_id="node_message_resume",
                        node_name="node_message_resume",
                        node_type="jiuwen.message",
                    ),
                    _build_end_stream_data(
                        workflow_id=TRANSFER_WORKFLOW_ID,
                        answer="resume workflow answer",
                        user_fields={"name": "Jerry"},
                    ),
                ],
            ],
        }
    )
    workflow = _LocalWorkflowAdapter(runtime=workflow_runtime)
    session = workflow.create_session("conversation_resume")

    first_stream = asyncio.run(
        workflow.astream(
            query="transfer money",
            params={
                "conversation_history": [{"role": "user", "content": "transfer money"}]
            },
            workflow_id=TRANSFER_WORKFLOW_ID,
            agent_id="child-agent-common08",
            session_id="conversation_resume",
            context=workflow.get_runtime_context(session),
        )
    )
    first_events = asyncio.run(_collect_stream(first_stream))
    second_stream = asyncio.run(
        workflow.astream(
            query="continue with card 1234",
            params={
                "conversation_history": [
                    {"role": "user", "content": "transfer money"},
                    {"role": "assistant", "content": "please provide 1.xxx 2.xxx"},
                    {"role": "user", "content": "continue with card 1234"},
                ]
            },
            workflow_id=TRANSFER_WORKFLOW_ID,
            agent_id="child-agent-common08",
            session_id="conversation_resume",
            context=workflow.get_runtime_context(session),
        )
    )
    second_events = asyncio.run(_collect_stream(second_stream))

    assert len(workflow_runtime.calls) == 2
    assert workflow_runtime.calls[0]["session_id"] == "conversation_resume"
    assert workflow_runtime.calls[1]["session_id"] == "conversation_resume"
    assert workflow_runtime.calls[1]["query"] == "continue with card 1234"
    assert (
        workflow_runtime.calls[1]["request_variables"]["latest_query"]
        == "transfer money"
    )
    assert first_events[0].data["should_interrupt"] is True
    assert second_events[-1].data["answer"] == "resume workflow answer"
    assert (
        session.runtime_context.get(REQUEST_VARIABLES)["latest_query"]
        == "continue with card 1234"
    )


def test_case08_runtime_context_supports_request_variable_writeback():
    fake_context_manager = type(
        "FakeContextManager",
        (),
        {"agent_config": type("FakeAgentConfig", (), {"task_id": "task_common08"})()},
    )()
    handler = WorkflowHandler(fake_context_manager)
    runtime_context = _FakeRuntimeContext(
        {REQUEST_VARIABLES: {"name": "", "status": "pending"}}
    )
    workflow_instance = type(
        "FakeWorkflowInstance",
        (),
        {
            "get_runtime_context": lambda self: runtime_context,
        },
    )()

    handler._update_output_global_variables_for_request(
        {"name": "Jerry", "unknown": "ignored"},
        workflow_instance,
    )

    request_variables = runtime_context.get(REQUEST_VARIABLES)
    assert request_variables["name"] == "Jerry"
    assert request_variables["status"] == "pending"
    assert "unknown" not in request_variables
