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

from jiuwen.test.cases.controller_multi_agent.test_case_agent_controller_default_workflow_03 import (
    RESOURCE_TEMPLATE_DIR,
    _copy_case_ir_bundle,
)


AGENT_ID = "935a8125-c836-45f0-95ae-90622cdf0459"
NORMAL_WORKFLOW_ID = "fcde5452-858c-4a71-b9b3-cda35a910f78"
ACCOUNT_DETAIL_WORKFLOW_ID = "4692a481-a539-4afe-bf6c-801721ec664d"
FINANCE_WORKFLOW_ID = "83a951bc-27d7-4ccc-9131-268e93267365"
DEFAULT_WORKFLOW_ID = "ef802b42-9f76-4fb3-bfbb-910e5c091ced"
END_WORKFLOW_ID = "6bcb3df8-0f29-41fd-a583-273414629b67"


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
            "_GraphEngine", (), {"graph_instance": _GraphInstance(runtime_context)}
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


class _LocalModelAdapter:
    def __init__(self, runtime):
        self.runtime = runtime

    async def ainvoke(self, inputs, **kwargs):
        if hasattr(self.runtime, "ainvoke"):
            return await self.runtime.ainvoke(inputs, **kwargs)
        return await self.runtime.invoke(inputs, **kwargs)


class _FakeRuntimeContext:
    def __init__(self, initial=None):
        self._state = dict(initial or {})

    def get(self, key, default=None):
        return self._state.get(key, default)

    def set(self, key, value):
        self._state[key] = value

    def snapshot(self):
        return dict(self._state)


class _FakeWorkflowSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.runtime_context = _FakeRuntimeContext({})

    def get_state(self, key=None):
        state = self.runtime_context.snapshot()
        if key is None:
            return state
        return state.get(key)


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
            events = [
                _build_end_stream_data(
                    workflow_id=workflow_id or "", answer="workflow default"
                )
            ]

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
    *, workflow_id: str, answer: str, node_type: str = "jiuwen.message"
):
    return StreamData(
        code=StreamCode.MESSAGE_END.value,
        msg=StreamDataMsg.MESSAGE_END.value,
        data={
            "answer": answer,
            "node_id": "node_message",
            "node_name": "node_message",
            "node_type": node_type,
            "should_interrupt": False,
            "workflow_id": workflow_id,
            "enable_history": True,
            "user_fields": {},
        },
        execution_id=f"exec_{workflow_id}",
    )


def _build_end_stream_data(*, workflow_id: str, answer: str):
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
            "user_fields": {"action_after_completion": "Terminal"},
        },
        execution_id=f"exec_{workflow_id}",
    )


async def _run_local_ir_request(
    *, ir_path: Path, query: str, conversation_id: str, conversation_history=None
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
                "globalVariables": {"name": "tom"},
                "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
                "workflowSequence": [],
                "activeWorkflows": [],
            },
            "headers": {
                "Content-Type": "application/json",
                "X-Invoke-Mode": "debug",
            },
            "userId": "123",
        }
    )

    ir_data = await async_ir_load(str(ir_path))
    ir_type = IRConverter.identify_ir(ir_data)

    if ir_type.name == "Agent":
        instance = await IRConverter.ir_to_agent(
            ir_data, conversation_id=req.conversation_id, cust_headers={}
        )
    elif ir_type.name == "MultiAgents":
        instance = await IRConverter.ir_to_agent_group(
            ir_data, conversation_id=req.conversation_id, cust_headers={}
        )
    else:
        instance = await IRConverter.async_ir_to_workflow(ir_data)

    execution_data = ExecutionData(
        instance=instance, instance_type=ir_type, updated_time=int(time.time() * 1000)
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
    tmp_path = tmp_path_factory.mktemp(
        "agent_controller_default_workflow_03_southbound"
    )
    return _copy_case_ir_bundle(tmp_path)


def test_default_workflow_modelnew_records_inputs_from_real_ir(local_ir_path):
    model_runtime = AgentCoreModelWrapperRuntime([AIMessage(content="0")])
    workflow_runtime = _RecordingWorkflowRuntime(
        {
            DEFAULT_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=DEFAULT_WORKFLOW_ID,
                        answer="default workflow answer",
                    ),
                    _build_end_stream_data(
                        workflow_id=DEFAULT_WORKFLOW_ID,
                        answer="default workflow answer",
                    ),
                ]
            ],
        }
    )
    _IntegrationRegistry.set_model(
        AgentCoreModelLayer(_LocalModelAdapter(runtime=model_runtime))
    )
    _IntegrationRegistry.set_workflow(_LocalWorkflowAdapter(runtime=workflow_runtime))

    response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=local_ir_path,
            query="default workflow query",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
        )
    )

    relevant_calls = [
        call for call in model_runtime.calls if isinstance(call.inputs, dict)
    ]
    assert len(relevant_calls) >= 1
    assert "default workflow query" in _extract_model_prompt_text(relevant_calls[0])
    assert "task_end" in response_text
    assert '"event":"error"' not in response_text
    _IntegrationRegistry.clear()


def test_default_workflownew_astream_complete_contract():
    workflow_runtime = _RecordingWorkflowRuntime(
        {
            DEFAULT_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=DEFAULT_WORKFLOW_ID,
                        answer="default workflow answer",
                    ),
                    _build_end_stream_data(
                        workflow_id=DEFAULT_WORKFLOW_ID,
                        answer="default workflow answer",
                    ),
                ]
            ],
        }
    )
    workflow = _LocalWorkflowAdapter(runtime=workflow_runtime)
    session = workflow.create_session("conversation_default")
    stream = asyncio.run(
        workflow.astream(
            query="default workflow query",
            params={
                "conversation_history": [
                    {"role": "user", "content": "default workflow query"}
                ]
            },
            workflow_id=DEFAULT_WORKFLOW_ID,
            agent_id=AGENT_ID,
            session_id="conversation_default",
            context=workflow.get_runtime_context(session),
        )
    )
    events = asyncio.run(_collect_stream(stream))

    assert len(workflow_runtime.calls) == 1
    assert workflow_runtime.calls[0]["query"] == "default workflow query"
    assert workflow_runtime.calls[0]["workflow_id"] == DEFAULT_WORKFLOW_ID
    assert workflow_runtime.calls[0]["agent_id"] == AGENT_ID
    assert workflow_runtime.calls[0]["session_id"] == "conversation_default"
    assert events[0].code == StreamCode.MESSAGE_END.value
    assert events[1].code == StreamCode.FINISH.value
    assert events[-1].data["answer"] == "default workflow answer"


def test_default_workflownew_end_workflow_contract():
    workflow_runtime = _RecordingWorkflowRuntime(
        {
            END_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=END_WORKFLOW_ID,
                        answer="end workflow answer",
                    ),
                    _build_end_stream_data(
                        workflow_id=END_WORKFLOW_ID,
                        answer="end workflow answer",
                    ),
                ]
            ],
        }
    )
    workflow = _LocalWorkflowAdapter(runtime=workflow_runtime)
    session = workflow.create_session("conversation_end")
    stream = asyncio.run(
        workflow.astream(
            query="end workflow query",
            params={
                "conversation_history": [
                    {"role": "user", "content": "end workflow query"}
                ]
            },
            workflow_id=END_WORKFLOW_ID,
            agent_id=AGENT_ID,
            session_id="conversation_end",
            context=workflow.get_runtime_context(session),
        )
    )
    events = asyncio.run(_collect_stream(stream))

    assert workflow_runtime.calls[0]["workflow_id"] == END_WORKFLOW_ID
    assert workflow_runtime.calls[0]["query"] == "end workflow query"
    assert events[0].code == StreamCode.MESSAGE_END.value
    assert events[1].code == StreamCode.FINISH.value
