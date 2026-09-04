import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

os.environ.setdefault("TGF_ENABLE", "false")

from openjiuwen.core.foundation.tool.mcp.base import McpToolCard
from openjiuwen.core.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.session.stream.base import OutputSchema

import jiuwen.extension.workflow_node.flow_agent as flow_agent_module
from jiuwen.extension.workflow_node.flow_agent import FlowAgent, FlowAgentConfig
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.workflow_node.sub_workflow import (
    GLOBAL_VARIABLES,
    REQUEST_VARIABLES,
    WORKFLOW_INSTANCE_DICT,
    SubWorkflow,
)
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from jiuwen.extension.wrapper.restful_api_new import RestfulApiToolNew
from jiuwen.extension.wrapper.sse_client_new import SSEClientNew
from jiuwen.serve.controllers.execution.ir_converter import (
    _build_start_inputs_schema,
    _resolve_branch_condition,
    IRConverter,
)
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.controller.context_manager.workflow_context import (
    NodeExecutionInfo,
    WorkflowContext,
    WorkflowStatus,
)
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.test.cases.controller_multi_agent.openjiuwen_workflow_case_runtime import (
    init_openjiuwen_workflow_runtime,
    run_local_ir_with_openjiuwen_workflow,
)
from jiuwen.test.cases.controller_multi_agent.test_case_controller_multi_agent_27 import (
    RESOURCE_TEMPLATE_DIR,
    _append_history,
    _event_names,
    _extract_sse_events,
    _resolve_fixture_path,
    _select_case_intent,
)


CASE_DIR = Path(__file__).resolve().parent
SOURCE_CASE_DIR = CASE_DIR / "test_case_controller_multi_agent_27"
AGENT_DIR = SOURCE_CASE_DIR / "agent"
SUB_AGENT_DIR = SOURCE_CASE_DIR / "sub_agent"
WORKFLOW_DIR = SOURCE_CASE_DIR / "workflow"
CASE_FILE = SOURCE_CASE_DIR / "test_case_controller_multi_agent_27.yaml"
REAL_COMPONENT_WORKFLOW_DIR = (
    CASE_DIR
    / "test_case_controller_multi_agent_openjiuwen_real_components"
    / "workflow"
)
CURRENT_CASE_ANSWERS: list[str] = []
NESTED_LEAF_AGENT_ID = "child-agent-理财服务"


def _load_cases() -> list[dict]:
    return yaml.safe_load(CASE_FILE.read_text(encoding="utf-8"))


def _find_single_json(directory: Path) -> Path:
    json_files = sorted(directory.glob("*.json"))
    if len(json_files) != 1:
        raise AssertionError(
            f"Expected exactly one json file in {directory}, found {len(json_files)}"
        )
    return json_files[0]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_real_component_workflow_ir(workflow_filename: str) -> dict:
    return _load_json(REAL_COMPONENT_WORKFLOW_DIR / workflow_filename)


def _copy_nested_child_agent_bundle(tmp_path: Path) -> Path:
    root_src = _find_single_json(AGENT_DIR)
    leaf_src = _find_single_json(SUB_AGENT_DIR)

    root_ir = _load_json(root_src)
    middle_ir = _load_json(root_src)
    leaf_ir = _load_json(leaf_src)

    root_dst = tmp_path / root_src.name
    middle_dst = tmp_path / "middle_agent_ir_nested.json"
    leaf_dst = tmp_path / leaf_src.name

    for workflow in leaf_ir.get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow["ir_path"] = str(WORKFLOW_DIR / workflow_name)

    middle_ir["agentId"] = "middle-agent-nested"
    middle_ir["agentName"] = "middle-agent-nested"
    middle_ir["configs"]["workflows"] = []
    middle_ir["configs"]["agents"] = [
        {
            "id": "理财服务Agent",
            "name": "理财服务Agent",
            "description": "nested leaf agent",
            "ir_path": str(leaf_dst),
            "arguments": [
                {
                    "description": "请求入参",
                    "method": "Body",
                    "name": "query",
                    "required": True,
                    "type": "string",
                    "visible": True,
                }
            ],
            "response": [
                {
                    "description": "响应内容",
                    "name": "response_content",
                    "type": "string",
                }
            ],
            "mode": "Controller",
        }
    ]

    for agent in root_ir.get("configs", {}).get("agents", []):
        agent["id"] = "middle-agent-nested"
        agent["name"] = "middle-agent-nested"
        agent["description"] = "nested middle agent"
        agent["ir_path"] = str(middle_dst)

    leaf_dst.write_text(
        json.dumps(leaf_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    middle_dst.write_text(
        json.dumps(middle_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    root_dst.write_text(
        json.dumps(root_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root_dst


def _init_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    init_openjiuwen_workflow_runtime(
        monkeypatch,
        resource_template_dir=RESOURCE_TEMPLATE_DIR,
        answer_provider=lambda: CURRENT_CASE_ANSWERS,
        intent_selector=_select_case_intent,
    )


class _FakeSession:
    def __init__(
        self, *, component_id: str = "node_test", global_state: dict | None = None
    ):
        self._component_id = component_id
        self._global_state = dict(global_state or {})
        self.custom_streams: list[object] = []
        self.streams: list[object] = []
        self.interactions: list[object] = []

    def get_session_id(self):
        return "test-session-id"

    def get_component_id(self):
        return self._component_id

    def get_global_state(self, key=None):
        if key is None:
            return self._global_state
        return self._global_state.get(key)

    def update_global_state(self, data: dict):
        self._global_state.update(data)

    def get_env(self, key=None):
        return None

    async def interact(self, payload):
        self.interactions.append(payload)
        return payload

    async def write_custom_stream(self, schema):
        self.custom_streams.append(schema)

    async def write_stream(self, schema):
        self.streams.append(schema)


class _FakeContext:
    def __init__(self, messages: list[object] | None = None):
        self._messages = list(messages or [])

    def get_messages(self):
        return list(self._messages)


def test_nested_child_agent_can_reach_leaf_openjiuwen_workflow(tmp_path, monkeypatch):
    _init_runtime(monkeypatch)
    ir_path = _copy_nested_child_agent_bundle(tmp_path)
    case_data = _load_cases()[0]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(case_data.get("answer") or [])

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            case_data["query"],
            conversation_id="conversation_openjiuwen_nested_child_agent",
        )
    )
    events = _event_names(response_text)

    assert '"event":"error"' not in response_text, response_text
    assert "workflow_start" in events, response_text
    assert "workflow_end" in events, response_text
    assert "intermediate_message" in events, response_text
    assert NESTED_LEAF_AGENT_ID in response_text, response_text


def test_nested_child_agent_interrupt_detour_and_resume_contract(tmp_path, monkeypatch):
    _init_runtime(monkeypatch)
    ir_path = _copy_nested_child_agent_bundle(tmp_path)
    cases = _load_cases()
    conversation_id = "conversation_openjiuwen_nested_interrupt_resume"
    conversation_history: list[dict] = []

    first_turn = cases[0]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])
    first_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            first_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    first_events = _event_names(first_response)
    first_payloads = [
        event.get("data", {}) for event in _extract_sse_events(first_response)
    ]

    assert '"event":"error"' not in first_response, first_response
    assert "workflow_start" in first_events, first_response
    assert "workflow_blocked" in first_events, first_response
    assert any(
        payload.get("node_type") == "jiuwen.questioner" for payload in first_payloads
    ), first_response
    _append_history(conversation_history, first_turn)

    detour_turn = cases[1]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(detour_turn.get("answer") or [])
    detour_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            detour_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    detour_events = _event_names(detour_response)

    assert '"event":"error"' not in detour_response, detour_response
    assert "message_end" in detour_events, detour_response
    assert "intermediate_message" in detour_events, detour_response
    _append_history(conversation_history, detour_turn)

    resume_turn = cases[2]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(resume_turn.get("answer") or [])
    resume_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            resume_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    resume_events = _event_names(resume_response)

    assert '"event":"error"' not in resume_response, resume_response
    assert "workflow_resume" in resume_events, resume_response
    assert "message_end" in resume_events, resume_response
    assert "intermediate_message" in resume_events, resume_response
    assert NESTED_LEAF_AGENT_ID in resume_response, resume_response


def test_nested_child_agent_leaf_workflow_done_keeps_user_fields(tmp_path, monkeypatch):
    _init_runtime(monkeypatch)
    ir_path = _copy_nested_child_agent_bundle(tmp_path)
    first_turn = _load_cases()[0]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            first_turn["query"],
            conversation_id="conversation_openjiuwen_nested_user_fields",
        )
    )
    events = _extract_sse_events(response_text)
    done_events = [event for event in events if event.get("event") == "done"]
    leaf_done = next(
        event
        for event in done_events
        if event.get("data", {}).get("node_type") == "jiuwen.end"
        and "user_fields" in event.get("data", {})
    )

    assert leaf_done["data"]["user_fields"]["query"] == first_turn["query"]


def test_nested_child_agent_resume_keeps_intermediate_history_continuity(
    tmp_path, monkeypatch
):
    _init_runtime(monkeypatch)
    ir_path = _copy_nested_child_agent_bundle(tmp_path)
    cases = _load_cases()
    conversation_id = "conversation_openjiuwen_nested_history_continuity"
    conversation_history: list[dict] = []

    first_turn = cases[0]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])
    first_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            first_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    first_intermediate = next(
        event
        for event in _extract_sse_events(first_response)
        if event.get("event") == "intermediate_message"
    )
    first_history_len = len(first_intermediate.get("data", {}).get("answer", []))
    _append_history(conversation_history, first_turn)

    detour_turn = cases[1]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(detour_turn.get("answer") or [])
    detour_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            detour_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    _append_history(conversation_history, detour_turn)

    resume_turn = cases[2]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(resume_turn.get("answer") or [])
    resume_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            resume_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    resume_intermediate = next(
        event
        for event in _extract_sse_events(resume_response)
        if event.get("event") == "intermediate_message"
    )
    resume_history = resume_intermediate.get("data", {}).get("answer", [])

    assert '"event":"error"' not in detour_response, detour_response
    assert '"event":"error"' not in resume_response, resume_response
    assert len(resume_history) > first_history_len, resume_response
    assert any(
        item.get("content") == detour_turn["query"] for item in resume_history
    ), resume_response
    assert any(
        item.get("content") == resume_turn["query"] for item in resume_history
    ), resume_response


def test_nested_child_agent_default_workflow_fallback_still_reaches_leaf_workflow(
    tmp_path, monkeypatch
):
    _init_runtime(monkeypatch)
    ir_path = _copy_nested_child_agent_bundle(tmp_path)
    default_turn = _load_cases()[3]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(default_turn.get("answer") or [])

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            default_turn["query"],
            conversation_id="conversation_openjiuwen_nested_default_fallback",
        )
    )
    events = _event_names(response_text)

    assert '"event":"error"' not in response_text, response_text
    assert "workflow_start" in events, response_text
    assert "workflow_end" in events, response_text
    assert "done" in events, response_text
    assert NESTED_LEAF_AGENT_ID in response_text, response_text


def test_flow_api_minimal_executable_contract(monkeypatch):
    class _FakeApiTool:
        def __init__(self):
            self.name = "fake_api"
            self.params = [
                SimpleNamespace(
                    name="query", type="string", required=True, description="query"
                )
            ]
            self.response = [{"name": "result"}]
            self.invoke_calls = []
            self.stream_calls = []

        async def ainvoke(self, inputs, runtime_auth=None):
            self.invoke_calls.append({"inputs": inputs, "runtime_auth": runtime_auth})
            return {
                "errCode": 0,
                "errMessage": "success",
                "data": {"result": f"invoke::{inputs['query']}"},
            }

        async def astream(self, inputs, runtime_auth=None):
            self.stream_calls.append({"inputs": inputs, "runtime_auth": runtime_auth})
            yield SimpleNamespace(content="api-stream-1")
            yield SimpleNamespace(content="api-stream-2")

    class _FakeResourceManager:
        def __init__(self, tool):
            self._tool = tool

        def get_tool(self, tool_id):
            return self._tool

    fake_tool = _FakeApiTool()
    monkeypatch.setattr(Runner, "resource_mgr", _FakeResourceManager(fake_tool))
    flow_api = FlowApi(
        {
            "apiId": "fake_api_id",
            "userFields": {"outputs": [{"id": "api_result", "required": True}]},
        }
    )
    session = _FakeSession(
        global_state={"runtime_auth_headers": {"fake_api_id": {"x-test": "1"}}}
    )

    invoke_result = asyncio.run(
        flow_api.invoke(
            {"userFields": {"query": "hello"}}, session=session, context=_FakeContext()
        )
    )
    stream_chunks = asyncio.run(
        _collect_async(
            flow_api.stream(
                {"userFields": {"query": "world"}},
                session=session,
                context=_FakeContext(),
            )
        )
    )

    assert invoke_result["userFields"]["result"] == "invoke::hello"
    assert fake_tool.invoke_calls[0]["inputs"] == {"query": "hello"}
    assert fake_tool.invoke_calls[0]["runtime_auth"] == {"headers": {"x-test": "1"}}
    assert all(isinstance(chunk, dict) for chunk in stream_chunks)
    assert stream_chunks[-1]["userFields"]["api_result"] == "api-stream-1api-stream-2"


def test_flow_mcp_minimal_executable_contract(monkeypatch):
    class _FakeMcpClient:
        _tool_params = [
            SimpleNamespace(
                name="query", type="string", required=True, description="query"
            )
        ]

    class _FakeMcpApi:
        def __init__(self):
            self.calls = []

        async def invoke(self, inputs):
            self.calls.append(inputs)
            return {"result": {"content": f"mcp::{inputs['query']}", "isError": False}}

    fake_api = _FakeMcpApi()

    def _fake_create_client(self, conf):
        self._client = _FakeMcpClient()

    async def _fake_init_api(self):
        self.api = fake_api

    monkeypatch.setattr(FlowMcp, "_create_client", _fake_create_client)
    monkeypatch.setattr(FlowMcp, "_init_api", _fake_init_api)

    flow_mcp = FlowMcp(
        {
            "type": "sse",
            "name": "mcp_server",
            "tool_name": "tool_a",
            "url": "http://localhost:8080/sse",
            "arguments": [
                {"name": "query", "type": "string", "required": True, "method": "Body"}
            ],
        }
    )
    session = _FakeSession(
        global_state={
            "runtime_auth_headers": {"tool_a": {"Authorization": "Bearer test"}},
            "api_config": {"tenant": "mock"},
        }
    )

    result = asyncio.run(
        flow_mcp.invoke(
            {"userFields": {"query": "hello"}}, session=session, context=_FakeContext()
        )
    )

    assert result["userFields"]["content"] == "mcp::hello"
    assert fake_api.calls[0]["query"] == "hello"
    assert (
        fake_api.calls[0][JIUWEN_RUNTIME_KWARGS]["runtime_auth"]["headers"][
            "Authorization"
        ]
        == "Bearer test"
    )
    assert (
        fake_api.calls[0][JIUWEN_RUNTIME_KWARGS]["runtime_context"]["tenant"] == "mock"
    )


def test_flow_agent_minimal_executable_contract(monkeypatch):
    class _FakeReactAgent:
        def __init__(self, card):
            self.card = card
            self._ability_manager = SimpleNamespace(_tools={})
            self.config = None

        def configure(self, config):
            self.config = config

        async def invoke(self, inputs, session):
            return {"output": f"agent::{inputs['query']}", "result_type": "success"}

        async def stream(self, inputs, session):
            yield {
                "type": "message",
                "payload": {"output": f"stream::{inputs['query']}"},
            }

    monkeypatch.setattr(flow_agent_module, "ReActAgent", _FakeReactAgent)

    flow_agent = FlowAgent(
        FlowAgentConfig(
            strategy_name="ReAct",
            strategy_provider="JiuWen",
            max_iteration=3,
            streaming=True,
            llm_config={},
            plugins=[],
        )
    )

    invoke_result = asyncio.run(
        flow_agent.invoke(
            {"user_input": "hello"}, session=_FakeSession(), context=_FakeContext()
        )
    )
    stream_chunks = asyncio.run(
        _collect_async(
            flow_agent.stream(
                {"user_input": "world"}, session=_FakeSession(), context=_FakeContext()
            )
        )
    )

    assert invoke_result["userFields"]["output"] == "agent::hello"
    assert stream_chunks == [
        {"type": "message", "payload": {"output": "stream::world"}}
    ]


def test_sub_workflow_minimal_executable_contract():
    class _FakeSubWorkflow:
        async def invoke(self, *, inputs, session, context, is_sub):
            session.update_global_state(
                {
                    "_sub_session_state": {
                        REQUEST_VARIABLES: {"slot": "updated", "extra": "x"}
                    }
                }
            )
            return {
                "answer": f"sub::{inputs['query']}",
                "user_fields": {"slot": "updated"},
            }

        async def stream(self, *, inputs, session, context, is_sub):
            session.update_global_state(
                {
                    "_sub_session_state": {
                        REQUEST_VARIABLES: {"slot": "updated", "extra": "x"}
                    }
                }
            )
            yield OutputSchema(
                type="partial_content",
                index=0,
                payload={"answer": f"sub::{inputs['query']}"},
            )
            yield OutputSchema(type="message_end", index=1, payload={})
            yield OutputSchema(
                type="workflow_final",
                index=2,
                payload={"user_fields": {"slot": "updated"}},
            )

    component = SubWorkflow(
        {
            "node_id": "node_sub_workflow",
            "userFields": {},
            "systemFields": {},
            "preDefineFields": {},
            "reference": {"id": "sub_workflow_id", "path": "sub_workflow.json"},
        }
    )
    session = _FakeSession(
        component_id="node_sub_workflow",
        global_state={
            WORKFLOW_INSTANCE_DICT: {"node_sub_workflow": _FakeSubWorkflow()},
            GLOBAL_VARIABLES: {"userId": "user-1"},
            REQUEST_VARIABLES: {"slot": "initial", "keep": "origin"},
        },
    )
    context = _FakeContext([SimpleNamespace(content="resume query")])

    invoke_result = asyncio.run(
        component.invoke(
            {
                "systemFields": {"query": "invoke query"},
                "userFields": {"slot": "local"},
            },
            session=session,
            context=context,
        )
    )
    stream_chunks = asyncio.run(
        _collect_async(
            component.stream(
                {
                    "systemFields": {"query": "stream query"},
                    "userFields": {"slot": "local"},
                },
                session=session,
                context=context,
            )
        )
    )

    assert invoke_result["responseContent"] == "sub::invoke query"
    assert invoke_result["userFields"]["slot"] == "updated"
    assert session.get_global_state(REQUEST_VARIABLES)["slot"] == "updated"
    assert session.get_global_state(REQUEST_VARIABLES)["keep"] == "origin"
    assert "extra" not in session.get_global_state(REQUEST_VARIABLES)
    assert stream_chunks[0]["content"] == "sub::stream query"


def test_sub_workflow_env_only_instance_injection_gap_is_explicit():
    class _EnvAwareSession(_FakeSession):
        def __init__(self, *, env: dict, **kwargs):
            super().__init__(**kwargs)
            self._env = dict(env)

        def get_env(self, key=None):
            if key is None:
                return dict(self._env)
            return self._env.get(key)

    component = SubWorkflow(
        {
            "node_id": "node_sub_workflow",
            "userFields": {},
            "systemFields": {},
            "preDefineFields": {},
            "reference": {"id": "sub_workflow_id", "path": "sub_workflow.json"},
        }
    )
    session = _EnvAwareSession(
        component_id="node_sub_workflow",
        global_state={
            GLOBAL_VARIABLES: {"userId": "user-1"},
            REQUEST_VARIABLES: {"query": "parent-query"},
        },
        env={WORKFLOW_INSTANCE_DICT: {"node_sub_workflow": object()}},
    )

    with pytest.raises(Exception, match="sub_workflow instance not found"):
        asyncio.run(component._get_workflow_instance(session))


def test_sub_workflow_component_is_now_buildable():
    workflow_ir = {
        "workflowId": "workflow_with_sub_workflow",
        "workflowName": "workflow_with_sub_workflow",
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "configs": {}, "inputs": {}},
            {
                "id": "node_sub_workflow",
                "type": "jiuwen.subWorkflow",
                "configs": {
                    "systemFields": {},
                    "preDefineFields": {},
                    "reference": {"id": "sub_workflow_id", "path": "sub_workflow.json"},
                },
                "inputs": {},
            },
            {"id": "node_end", "type": "jiuwen.end", "configs": {}, "inputs": {}},
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_sub_workflow"},
            },
            {
                "source": {"componentId": "node_sub_workflow"},
                "target": {"componentId": "node_end"},
            },
        ],
    }

    workflow = asyncio.run(
        _build_workflow_async(workflow_ir, workflow_id="workflow_with_sub_workflow")
    )

    assert workflow.card.id == "workflow_with_sub_workflow"


def _copy_component_workflow_bundle(
    tmp_path: Path, workflow_ir: dict, workflow_filename: str
) -> Path:
    root_src = _find_single_json(AGENT_DIR)
    child_src = _find_single_json(SUB_AGENT_DIR)

    root_ir = _load_json(root_src)
    child_ir = _load_json(child_src)

    workflow_dst = tmp_path / workflow_filename
    child_dst = tmp_path / child_src.name
    root_dst = tmp_path / root_src.name

    start_workflow_overridden = False
    for workflow in child_ir.get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow.get("workflow_type") == "Start" and not start_workflow_overridden:
            workflow["ir_path"] = str(workflow_dst)
            start_workflow_overridden = True
        elif workflow_name:
            workflow["ir_path"] = str(
                _resolve_fixture_path(workflow_name, WORKFLOW_DIR)
            )

    for agent in root_ir.get("configs", {}).get("agents", []):
        child_name = Path(agent.get("ir_path", "")).name
        if child_name:
            child_ref = _resolve_fixture_path(child_name, SUB_AGENT_DIR)
            if child_ref.name != child_src.name:
                raise AssertionError(
                    f"Root IR points to unexpected child IR: {child_ref}"
                )
            agent["ir_path"] = str(child_dst)

    workflow_dst.write_text(
        json.dumps(workflow_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    child_dst.write_text(
        json.dumps(child_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    root_dst.write_text(
        json.dumps(root_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root_dst


def _make_controller_component_workflow_ir(
    node_type: str, configs: dict | None = None, *, workflow_id: str
) -> dict:
    return {
        "workflowId": workflow_id,
        "workflowName": workflow_id,
        "components": [
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "name": "结束",
                "outputs": {"userFields": {}, "responseContent": ""},
                "configs": {
                    "responseMode": "directResponse",
                    "userFields": {"inputs": [], "outputs": []},
                    "responseTemplate": "",
                    "systemFields": {"inputs": [], "outputs": []},
                    "isStreamOut": True,
                },
                "inputs": {"userFields": {}},
            },
            {
                "id": "node_component",
                "type": node_type,
                "name": "组件",
                "outputs": {"userFields": {}, "responseContent": ""},
                "configs": configs or {},
                "inputs": {"userFields": {}, "systemFields": {"query": "", "sys": {}}},
            },
            {
                "id": "node_start",
                "type": "jiuwen.start",
                "name": "开始",
                "outputs": {"userFields": {}, "systemFields": {"query": "", "sys": {}}},
                "configs": {
                    "userFields": {"inputs": [], "outputs": []},
                    "systemFields": {
                        "inputs": [
                            {
                                "sourceType": "input",
                                "description": "query",
                                "id": "query",
                                "type": "string",
                                "required": True,
                            },
                            {
                                "sourceType": "input",
                                "description": "sys",
                                "id": "sys",
                                "type": "object",
                                "required": True,
                                "schema": [],
                            },
                        ],
                        "outputs": [
                            {
                                "sourceType": "input",
                                "description": "query",
                                "id": "query",
                                "type": "string",
                                "required": True,
                            },
                            {
                                "sourceType": "input",
                                "description": "sys",
                                "id": "sys",
                                "type": "object",
                                "required": True,
                                "schema": [],
                            },
                        ],
                    },
                },
                "inputs": {"userFields": {}, "systemFields": {"query": "", "sys": {}}},
            },
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_component"},
            },
            {
                "source": {"componentId": "node_component"},
                "target": {"componentId": "node_end"},
            },
        ],
    }


def _make_controller_component_inputs() -> dict:
    return {
        "userFields": {
            "query": "{start.systemFields.query}",
        },
        "systemFields": {
            "query": "{start.systemFields.query}",
            "sys": "{start.systemFields.sys}",
        },
    }


def _make_controller_flow_api_config() -> dict:
    return {
        "id": "controller_api_tool",
        "name": "controller_api_tool",
        "description": "mock controller api tool",
        "url": "https://example.com/mock-api",
        "method": "GET",
        "headers": {"Accept": "application/json"},
        "auth": {},
        "arguments": [
            {
                "name": "query",
                "description": "query",
                "type": "string",
                "required": True,
                "method": "Query",
            },
        ],
        "response": [
            {
                "name": "result",
                "description": "mock result",
                "type": "string",
                "required": False,
            },
        ],
        "pluginDependency": {},
        "asyncInvoke": {},
        "inputParameters": {},
        "userFields": {"outputs": [{"id": "result", "required": True}]},
    }


def _make_controller_flow_mcp_config() -> dict:
    return {
        "type": "sse",
        "url": "http://localhost:3000/mcp",
        "name": "controller_mcp_server",
        "tool_name": "mock_tool",
        "description": "mock controller mcp tool",
        "headers": {"Authorization": "Bearer test-token"},
        "auth": {"headers": {}, "query": {}, "scope": "SERVICE"},
        "arguments": [
            {
                "name": "query",
                "description": "query",
                "type": "string",
                "required": True,
                "method": "Body",
            },
        ],
    }


def _make_controller_flow_agent_config() -> dict:
    return {
        "strategy_name": "ReAct",
        "strategy_provider": "JiuWen",
        "max_iteration": 5,
        "streaming": False,
        "with_chat_history": True,
        "chat_history_max_turn": 4,
        "system_prompt": "You are a helpful workflow agent.",
        "llm_config": {
            "model_name": "test_model",
            "model_provider": "OpenAI",
            "model_client_config": {
                "client_provider": "OpenAI",
                "api_key": "test-api-key",
                "api_base": "https://api.test.com",
            },
            "request_config": {
                "model_name": "test_model",
                "temperature": 0.7,
                "top_p": 1.0,
            },
        },
    }


def _patch_controller_flow_api_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_ainvoke(self, inputs, **kwargs):
        return {
            "errCode": 0,
            "errMessage": "success",
            "data": {"result": f"api::{inputs.get('query', '')}"},
        }

    async def _fake_astream(self, inputs, **kwargs):
        yield "api-stream"

    monkeypatch.setattr(RestfulApiToolNew, "ainvoke", _fake_ainvoke)
    monkeypatch.setattr(RestfulApiToolNew, "astream", _fake_astream)


def _patch_controller_flow_mcp_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeMcpItem:
        def model_dump(self):
            return {"type": "text", "text": "mcp-ok"}

    async def _fake_list_tools(self, *args, **kwargs):
        return [
            McpToolCard(
                name="mock_tool",
                server_name="controller_mcp_server",
                description="mock controller mcp tool",
                input_params={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        JIUWEN_RUNTIME_KWARGS: {"type": "object"},
                    },
                    "additionalProperties": True,
                },
            )
        ]

    async def _fake_call_tool(self, tool_name, arguments, *args, **kwargs):
        return [_FakeMcpItem()]

    async def _bridge_stream(self, inputs, session, context):
        yield await self.invoke(inputs, session, context)

    monkeypatch.setattr(SSEClientNew, "list_tools", _fake_list_tools)
    monkeypatch.setattr(SSEClientNew, "call_tool", _fake_call_tool)
    monkeypatch.setattr(FlowMcp, "stream", _bridge_stream)


def _patch_controller_flow_agent_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeReActAgent:
        def __init__(self, *args, **kwargs):
            self._ability_manager = SimpleNamespace(_tools={})
            self.configure = Mock()

        async def invoke(self, inputs, session):
            return {
                "output": f"agent::{inputs.get('query', '')}",
                "result_type": "success",
            }

        async def stream(self, inputs, session):
            yield {
                "output": f"agent::{inputs.get('query', '')}",
                "result_type": "success",
            }

    monkeypatch.setattr(flow_agent_module, "ReActAgent", _FakeReActAgent)


@pytest.mark.parametrize(
    ("workflow_id", "runtime_patcher"),
    [
        ("controller_flow_api", _patch_controller_flow_api_runtime),
        ("controller_flow_mcp", _patch_controller_flow_mcp_runtime),
        ("controller_flow_agent", _patch_controller_flow_agent_runtime),
    ],
)
def test_controller_multi_agent_component_workflows_can_run_end_to_end(
    tmp_path,
    monkeypatch,
    workflow_id: str,
    runtime_patcher,
):
    _init_runtime(monkeypatch)

    runtime_patcher(monkeypatch)

    workflow_ir = _load_real_component_workflow_ir(f"{workflow_id}.json")
    ir_path = _copy_component_workflow_bundle(
        tmp_path, workflow_ir, f"{workflow_id}.json"
    )
    CURRENT_CASE_ANSWERS.clear()

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            "我要赎回理财",
            conversation_id=f"conversation_{workflow_id}",
        )
    )
    events = _event_names(response_text)

    assert '"event":"error"' not in response_text, response_text
    assert "workflow_start" in events, response_text
    assert "workflow_end" in events, response_text
    assert "done" in events, response_text


def test_controller_multi_agent_sub_workflow_can_run_with_injected_instance(
    tmp_path, monkeypatch
):
    _init_runtime(monkeypatch)

    class _FakeSubWorkflowForController:
        async def invoke(self, *, inputs, session, context, is_sub):
            session.update_global_state(
                {"_sub_session_state": {REQUEST_VARIABLES: {"query": "sub-updated"}}}
            )
            return {"answer": "subworkflow-ok", "user_fields": {"query": "sub-updated"}}

        async def stream(self, *, inputs, session, context, is_sub):
            session.update_global_state(
                {"_sub_session_state": {REQUEST_VARIABLES: {"query": "sub-updated"}}}
            )
            yield OutputSchema(
                type="workflow_final",
                index=0,
                payload={"user_fields": {"query": "sub-updated"}},
            )

    original_build_envs = WorkflowWrapper._build_envs
    original_get_workflow_instance = SubWorkflow._get_workflow_instance

    def _patched_build_envs(self, params):
        envs = original_build_envs(self, params)
        envs[WORKFLOW_INSTANCE_DICT] = {
            "node_component": _FakeSubWorkflowForController()
        }
        return envs

    async def _patched_get_workflow_instance(self, session):
        try:
            return await original_get_workflow_instance(self, session)
        except Exception:
            workflow_instance_dict = session.get_env(WORKFLOW_INSTANCE_DICT) or {}
            workflow_instance = workflow_instance_dict.get(self._node_id)
            if workflow_instance:
                return workflow_instance
            raise

    monkeypatch.setattr(WorkflowWrapper, "_build_envs", _patched_build_envs)
    monkeypatch.setattr(
        SubWorkflow, "_get_workflow_instance", _patched_get_workflow_instance
    )

    workflow_ir = _load_real_component_workflow_ir("controller_sub_workflow.json")
    ir_path = _copy_component_workflow_bundle(
        tmp_path, workflow_ir, "controller_sub_workflow.json"
    )
    CURRENT_CASE_ANSWERS.clear()

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            "我要赎回理财",
            conversation_id="conversation_controller_sub_workflow",
        )
    )
    events = _event_names(response_text)

    assert '"event":"error"' not in response_text, response_text
    assert "workflow_start" in events, response_text
    assert "workflow_end" in events, response_text
    assert "done" in events, response_text


def test_workflow_handler_only_emits_resume_for_interrupted_workflow_in_history():
    class _FakeHistory:
        def __init__(self, intents):
            self._intents = set(intents)

        def has_intent_in_history(self, intent_name):
            return intent_name in self._intents

    context_manager = SimpleNamespace(
        agent_config=SimpleNamespace(task_id="task_resume_contract"),
        engine=SimpleNamespace(history=_FakeHistory({"resume_workflow"})),
    )
    handler = WorkflowHandler(context_manager)
    resume_node = NodeExecutionInfo(
        node_id="node_questioner",
        node_name="questioner",
        node_type="jiuwen.questioner",
        execution_id="exec-resume",
        workflow_id="workflow_resume",
        workflow_name="resume_workflow",
    )
    interrupted_context = WorkflowContext(
        workflow_id="workflow_resume",
        workflow_name="resume_workflow",
        description="resume workflow",
        status=WorkflowStatus.INTERRUPTED,
        current_node_info=resume_node,
    )
    pending_context = WorkflowContext(
        workflow_id="workflow_pending",
        workflow_name="pending_workflow",
        description="pending workflow",
        status=WorkflowStatus.PENDING,
        current_node_info=resume_node,
    )

    interrupted_chunks = list(
        handler._generate_workflow_resume_message("resume query", interrupted_context)
    )
    pending_chunks = list(
        handler._generate_workflow_resume_message("resume query", pending_context)
    )

    assert [chunk.code for chunk in interrupted_chunks] == [
        StreamCode.WORKFLOW_RESUME_MESSAGE.value
    ]
    assert interrupted_chunks[0].data["workflow_id"] == "workflow_resume"
    assert interrupted_chunks[0].data["node_id"] == "node_questioner"
    assert pending_chunks == []


def test_workflow_handler_multi_suspended_resume_selects_only_history_matched_workflow():
    class _FakeHistory:
        def __init__(self, intents):
            self._intents = set(intents)

        def has_intent_in_history(self, intent_name):
            return intent_name in self._intents

    context_manager = SimpleNamespace(
        agent_config=SimpleNamespace(task_id="task_multi_resume_contract"),
        engine=SimpleNamespace(history=_FakeHistory({"matched_workflow"})),
    )
    handler = WorkflowHandler(context_manager)

    matched_node = NodeExecutionInfo(
        node_id="node_matched_questioner",
        node_name="matched questioner",
        node_type="jiuwen.questioner",
        execution_id="exec-matched",
        workflow_id="workflow_matched",
        workflow_name="matched_workflow",
    )
    other_node = NodeExecutionInfo(
        node_id="node_other_questioner",
        node_name="other questioner",
        node_type="jiuwen.questioner",
        execution_id="exec-other",
        workflow_id="workflow_other",
        workflow_name="other_workflow",
    )
    matched_context = WorkflowContext(
        workflow_id="workflow_matched",
        workflow_name="matched_workflow",
        description="matched workflow",
        status=WorkflowStatus.INTERRUPTED,
        current_node_info=matched_node,
    )
    other_context = WorkflowContext(
        workflow_id="workflow_other",
        workflow_name="other_workflow",
        description="other workflow",
        status=WorkflowStatus.INTERRUPTED,
        current_node_info=other_node,
    )

    matched_chunks = list(
        handler._generate_workflow_resume_message("resume matched", matched_context)
    )
    other_chunks = list(
        handler._generate_workflow_resume_message("resume other", other_context)
    )

    assert [chunk.code for chunk in matched_chunks] == [
        StreamCode.WORKFLOW_RESUME_MESSAGE.value
    ]
    assert matched_chunks[0].data["workflow_id"] == "workflow_matched"
    assert matched_chunks[0].data["node_id"] == "node_matched_questioner"
    assert other_chunks == []


def test_controller_multi_agent_child_workflow_error_propagates_without_false_completion(
    tmp_path, monkeypatch
):
    _init_runtime(monkeypatch)

    async def _failing_ainvoke(self, inputs, **kwargs):
        raise RuntimeError("controller workflow component boom")

    async def _failing_astream(self, inputs, **kwargs):
        if False:
            yield None
        raise RuntimeError("controller workflow component boom")

    monkeypatch.setattr(RestfulApiToolNew, "ainvoke", _failing_ainvoke)
    monkeypatch.setattr(RestfulApiToolNew, "astream", _failing_astream)

    workflow_ir = _load_real_component_workflow_ir("controller_flow_api_error.json")
    ir_path = _copy_component_workflow_bundle(
        tmp_path, workflow_ir, "controller_flow_api_error.json"
    )
    CURRENT_CASE_ANSWERS.clear()

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            ir_path,
            "我要赎回理财",
            conversation_id="conversation_controller_flow_api_error",
        )
    )
    events = _event_names(response_text)

    assert "error" in events, response_text
    assert "workflow_start" not in events, response_text
    assert "workflow_end" not in events, response_text
    assert "done" not in events, response_text
    assert "执行报错" in response_text, response_text


def test_questioner_resume_wrapper_uses_interactive_input_without_new_workflow_start(
    monkeypatch,
):
    class _FakeWorkflow:
        def __init__(self):
            self.seen_inputs = []

        async def stream(self, *, inputs, session, context, stream_modes):
            self.seen_inputs.append(inputs)
            yield OutputSchema(
                type="message_end",
                index=0,
                payload={
                    "answer": "resume answered",
                    "node_id": "node_questioner",
                    "node_type": "jiuwen.questioner",
                    "workflow_id": "wf_resume",
                },
            )
            yield OutputSchema(
                type="workflow_final",
                index=0,
                payload={"answer": "resume answered", "node_id": "node_questioner"},
            )

    class _FakeResourceManager:
        def __init__(self, workflow):
            self.workflow = workflow

        async def get_workflow(self, workflow_id, tag=None):
            return self.workflow

    fake_workflow = _FakeWorkflow()
    monkeypatch.setattr(Runner, "resource_mgr", _FakeResourceManager(fake_workflow))
    wrapper = WorkflowWrapper()
    interactive_input = InteractiveInput({"answer": "第一笔，全部赎回。"})

    chunks = asyncio.run(
        _collect_async(
            wrapper.astream(
                interactive_input,
                params={
                    "conversation_history": [
                        {"role": "user", "content": "我要赎回理财"}
                    ]
                },
                workflow_id="wf_resume",
                agent_id="agent_id",
                session_id="session_questioner_resume",
            )
        )
    )

    assert fake_workflow.seen_inputs == [interactive_input]
    assert StreamCode.WORKFLOW_START.value not in [
        getattr(item, "code", None) for item in chunks
    ]
    assert StreamCode.MESSAGE_END.value in [
        getattr(item, "code", None) for item in chunks
    ]
    assert StreamCode.FINISH.value in [getattr(item, "code", None) for item in chunks]


def test_plugin_branch_and_variable_loader_contracts_are_explicit():
    start_schema = _build_start_inputs_schema(
        {
            "inputs": [
                {
                    "name": "amount",
                    "sourceType": "reference",
                    "value": "start.user_fields.amount",
                },
                {"name": "query", "sourceType": "reference", "value": "query"},
            ],
            "configs": {},
        }
    )
    branch_condition = _resolve_branch_condition(
        {
            "id": "node_branch",
            "configs": {
                "branches": [
                    {
                        "id": "branch_amount",
                        "boolExpression": "{start.user_fields.amount} > 0 && {start.system_fields.query} != ''",
                    }
                ]
            },
        },
        "jiuwen.branch",
        "branch_amount",
    )

    assert start_schema["amount"] == "${amount}"
    assert (
        branch_condition
        == "${start.userFields.amount} > 0 and ${start.systemFields.query} != ''"
    )

    plugin_ir = {
        "workflowId": "workflow_with_plugin",
        "workflowName": "workflow_with_plugin",
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "configs": {}, "inputs": {}},
            {"id": "node_plugin", "type": "jiuwen.plugin", "configs": {}, "inputs": {}},
            {"id": "node_end", "type": "jiuwen.end", "configs": {}, "inputs": {}},
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_plugin"},
            },
            {
                "source": {"componentId": "node_plugin"},
                "target": {"componentId": "node_end"},
            },
        ],
    }
    workflow = asyncio.run(
        _build_workflow_async(plugin_ir, workflow_id="workflow_with_plugin")
    )

    assert workflow.card.id == "workflow_with_plugin"


@pytest.mark.parametrize(
    ("node_type", "workflow_id"),
    [
        ("jiuwen.agent", "workflow_with_agent"),
        ("jiuwen.flowAgent", "workflow_with_flow_agent"),
        ("jiuwen.mcp", "workflow_with_mcp"),
        ("jiuwen.flowMcp", "workflow_with_flow_mcp"),
        ("jiuwen.api", "workflow_with_api"),
        ("jiuwen.flowApi", "workflow_with_flow_api"),
    ],
)
def test_newly_connected_extension_components_are_buildable(
    node_type: str, workflow_id: str
):
    configs = {}
    if node_type in {"jiuwen.agent", "jiuwen.flowAgent"}:
        configs = {
            "strategy_name": "ReAct",
            "strategy_provider": "JiuWen",
            "max_iteration": 3,
            "streaming": False,
            "llm_config": {},
            "plugins": [],
        }
    elif node_type in {"jiuwen.mcp", "jiuwen.flowMcp"}:
        configs = {
            "type": "sse",
            "name": "mcp_server",
            "tool_name": "tool_a",
            "url": "http://localhost:8080/sse",
        }

    workflow_ir = {
        "workflowId": workflow_id,
        "workflowName": workflow_id,
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "configs": {}, "inputs": {}},
            {
                "id": "node_component",
                "type": node_type,
                "configs": configs,
                "inputs": {},
            },
            {"id": "node_end", "type": "jiuwen.end", "configs": {}, "inputs": {}},
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_component"},
            },
            {
                "source": {"componentId": "node_component"},
                "target": {"componentId": "node_end"},
            },
        ],
    }

    workflow = asyncio.run(_build_workflow_async(workflow_ir, workflow_id=workflow_id))

    assert workflow.card.id == workflow_id


@pytest.mark.parametrize(
    ("node_type", "workflow_id"),
    [
        ("jiuwen.loop", "workflow_with_loop"),
        ("jiuwen.forEach", "workflow_with_foreach"),
        ("jiuwen.parallel", "workflow_with_parallel"),
    ],
)
def test_loop_and_parallel_gaps_are_explicitly_reported(
    node_type: str, workflow_id: str
):
    workflow_ir = {
        "workflowId": workflow_id,
        "workflowName": workflow_id,
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "configs": {}, "inputs": {}},
            {"id": "node_gap", "type": node_type, "configs": {}, "inputs": {}},
            {"id": "node_end", "type": "jiuwen.end", "configs": {}, "inputs": {}},
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_gap"},
            },
            {
                "source": {"componentId": "node_gap"},
                "target": {"componentId": "node_end"},
            },
        ],
    }

    with pytest.raises(ValueError, match=node_type):
        asyncio.run(_build_workflow_async(workflow_ir, workflow_id=workflow_id))


def test_parallel_aggregate_only_contract_is_currently_explicit():
    workflow_ir = {
        "workflowId": "workflow_parallel_aggregate_gap",
        "workflowName": "workflow_parallel_aggregate_gap",
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "configs": {}, "inputs": {}},
            {
                "id": "node_parallel",
                "type": "jiuwen.parallel",
                "configs": {},
                "inputs": {},
            },
            {
                "id": "node_aggregate",
                "type": "jiuwen.flowAggregate",
                "configs": {},
                "inputs": {},
            },
            {"id": "node_end", "type": "jiuwen.end", "configs": {}, "inputs": {}},
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_parallel"},
            },
            {
                "source": {"componentId": "node_parallel"},
                "target": {"componentId": "node_aggregate"},
            },
            {
                "source": {"componentId": "node_aggregate"},
                "target": {"componentId": "node_end"},
            },
        ],
    }

    with pytest.raises(ValueError, match="jiuwen.parallel"):
        asyncio.run(
            _build_workflow_async(
                workflow_ir, workflow_id="workflow_parallel_aggregate_gap"
            )
        )


async def _collect_async(async_iterable):
    return [item async for item in async_iterable]


async def _build_workflow_async(workflow_ir: dict, workflow_id: str):
    return IRConverter.ir_to_workflow(workflow_ir)
