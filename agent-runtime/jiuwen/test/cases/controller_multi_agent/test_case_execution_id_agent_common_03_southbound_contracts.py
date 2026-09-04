import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage
from jiuwen.controller.agent.agent import Agent
from jiuwen.controller.task_executor.handler.mcp_handler import McpHandler
from jiuwen.controller.task_planner.planning_modules.llm_module import LLMModule
from jiuwen.integration import AgentCoreMcpLayer
from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer
from jiuwen.plugin import Param
from jiuwen.plugin.models.mcpapi import McpServer
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import distribute_execution_request
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest
from jiuwen.test.cases.controller_multi_agent.agent_core_model_contract_runtime import (
    AgentCoreFunctionCallModelRuntime,
)


CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[2]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
CASE_ASSET_DIR = CASE_DIR / "test_case_execution_id_agent_common_03"
IR_PATH = CASE_ASSET_DIR / "agent_plugin_mcp_header.json"


@dataclass
class _ToolCallRecord:
    inputs: dict
    tool_id: str
    agent_id: str
    session_id: str | None
    kwargs: dict


@dataclass
class _ModelCallRecord:
    messages: Any
    functions: Any
    runtime_data: dict


class _RecordingPluginRuntime:
    def __init__(self):
        self.calls: list[_ToolCallRecord] = []
        self.name = "mock_plugin_header"
        self.description = "mock plugin header"
        self.parameters = {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "query"}},
            "required": ["input"],
        }
        self.params = [
            Param(name="input", description="query", param_type="string", required=True)
        ]
        self.input_parameters = {}
        self.response = []

    async def ainvoke(self, inputs, tool_id, agent_id, session_id, **kwargs):
        self.calls.append(
            _ToolCallRecord(
                inputs=inputs,
                tool_id=tool_id,
                agent_id=agent_id,
                session_id=session_id,
                kwargs=kwargs,
            )
        )
        runtime_context = kwargs.get("runtime_context")
        headers = {}
        if runtime_context is not None:
            headers = (
                getattr(runtime_context, "api_config", {}).get("headers", {}) or {}
            )
        return {
            "errCode": 0,
            "errMessage": "",
            "data": {
                "plugin_headers": headers,
                "args": inputs,
            },
        }


class _FakeMcpTool:
    def __init__(self, name: str, description: str, input_schema: dict):
        self.name = name
        self.description = description
        self.inputSchema = input_schema


class _RecordingMcpRuntime:
    def __init__(self):
        self.calls: list[_ToolCallRecord] = []
        self.name = "McpTimeout"
        self.description = "mock mcp timeout"
        self.server_name = "校验MCP组件超时"
        self.parameters = {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "query"}},
            "required": ["input"],
        }
        self.headers = {}
        self.auth = {}
        self.plugin_dependency = {}
        self.params = []
        self.expected_tool_id: str | None = None
        self.expected_agent_id: str | None = None
        self.expected_session_id: str | None = None
        self.identifier_validation_passed = False

    async def ainvoke(self, inputs, tool_id, agent_id, session_id, **kwargs):
        if self.expected_tool_id is not None:
            assert tool_id == self.expected_tool_id
        if self.expected_agent_id is not None:
            assert agent_id == self.expected_agent_id
        if self.expected_session_id is not None:
            assert session_id == self.expected_session_id
        if any(
            expected is not None
            for expected in (
                self.expected_tool_id,
                self.expected_agent_id,
                self.expected_session_id,
            )
        ):
            self.identifier_validation_passed = True

        self.calls.append(
            _ToolCallRecord(
                inputs=inputs,
                tool_id=tool_id,
                agent_id=agent_id,
                session_id=session_id,
                kwargs=kwargs,
            )
        )
        runtime_context = kwargs.get("runtime_context")
        headers = {}
        if runtime_context is not None:
            headers = (
                getattr(runtime_context, "api_config", {}).get("headers", {}) or {}
            )
        return {
            "errCode": 0,
            "errMessage": "",
            "data": {
                "headers": headers,
                "args": inputs,
            },
        }


class _FallbackToolModel(BaseChatModel):
    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="done")

    def _stream(self, messages, tools=None, **kwargs) -> Iterator[AIMessage]:
        yield self._chat(messages, tools, **kwargs)


class _RecordingModelRuntime:
    def __init__(self):
        self.calls: list[_ModelCallRecord] = []

    async def stream_function_call(self, messages, functions, runtime_data):
        self.calls.append(
            _ModelCallRecord(
                messages=messages,
                functions=functions,
                runtime_data=runtime_data,
            )
        )
        if len(self.calls) > 1:
            yield {"llm_output": {"content": "done"}}
            return

        latest_user = ""
        if messages:
            latest_user = messages[-1].get("content", "")

        yield {
            "llm_output": {
                "content": "",
                "function_call": {
                    "name": "McpTimeout",
                    "arguments": json.dumps({"input": latest_user}, ensure_ascii=False),
                    "tool_call_id": "tool_mcp_1",
                },
            }
        }


class _IntegrationRegistry:
    model = None

    @classmethod
    def clear(cls):
        cls.model = None

    @classmethod
    def set_model(cls, model):
        cls.model = model

    @classmethod
    def get_model(cls):
        return cls.model


def _init_local_runtime(monkeypatch: pytest.MonkeyPatch):
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"

    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *args, **kwargs: _FallbackToolModel(),
    )
    _IntegrationRegistry.clear()

    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {RESOURCE_TEMPLATE_DIR}"
        )

    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    original_stream_function_call = LLMModule.stream_function_call

    async def _patched_stream_function_call(self, messages, functions, runtime_data):
        model = _IntegrationRegistry.get_model()
        if model is not None:
            async for item in model.stream_function_call(
                messages, functions, runtime_data
            ):
                yield item
            return
        async for item in original_stream_function_call(
            self, messages, functions, runtime_data
        ):
            yield item

    monkeypatch.setattr(
        LLMModule, "stream_function_call", _patched_stream_function_call
    )


async def _build_local_agent(ir_path: Path) -> Agent:
    ir_data = await async_ir_load(str(ir_path))
    return await IRConverter.ir_to_agent(
        ir_data, conversation_id=f"conversation_{int(time.time() * 1000)}"
    )


async def _run_local_ir_request(
    *,
    ir_path: Path,
    query: str,
    conversation_id: str,
    headers: dict,
    params: dict,
):
    req = ExecutionRequest.model_validate(
        {
            "conversationId": conversation_id,
            "query": query,
            "irPath": str(ir_path),
            "responseMode": "streaming",
            "executionMode": "sync",
            "params": params,
            "headers": headers,
        }
    )

    ir_data = await async_ir_load(str(ir_path))
    instance = await IRConverter.ir_to_agent(
        ir_data, conversation_id=req.conversation_id, cust_headers={}
    )
    execution_data = ExecutionData(
        instance=instance,
        instance_type=IRConverter.identify_ir(ir_data),
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
    return execution_data.instance, "".join(body)


@pytest.fixture()
def runtimes(monkeypatch):
    _init_local_runtime(monkeypatch)
    model_runtime = AgentCoreFunctionCallModelRuntime()
    plugin_runtime = _RecordingPluginRuntime()
    mcp_runtime = _RecordingMcpRuntime()
    mcp_layer = AgentCoreMcpLayer(
        runtime=mcp_runtime,
        tool_id="McpTimeout",
        agent_id="agent-mcp-test",
        session_id="session-mcp-test",
        name="McpTimeout",
        description="mock mcp timeout",
        server_name="校验MCP组件超时",
        transport_type="sse",
    )
    _IntegrationRegistry.set_model(AgentCoreModelLayer(model_runtime))
    return model_runtime, plugin_runtime, mcp_runtime, mcp_layer


def _patch_agent_tools(monkeypatch: pytest.MonkeyPatch, plugin_runtime, mcp_layer):
    async def _patched_get_tools(self, query, kwargs):
        return [plugin_runtime], [], [mcp_layer]

    monkeypatch.setattr(Agent, "get_tools", _patched_get_tools)


def test_case03_mcp_southbound_headers_from_real_ir(monkeypatch, runtimes):
    model_runtime, _, mcp_runtime, _ = runtimes

    async def _patched_mcp_server_ainvoke(self, inputs=None, **kwargs):
        return SimpleNamespace(
            tools=[
                _FakeMcpTool(
                    name="McpTimeout",
                    description="mock mcp timeout",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "input": {"type": "string", "description": "query"}
                        },
                        "required": ["input"],
                    },
                )
            ]
        )

    monkeypatch.setattr(McpServer, "ainvoke", _patched_mcp_server_ainvoke)
    monkeypatch.setattr(
        AgentCoreMcpLayer, "_create_runtime", staticmethod(lambda **kwargs: mcp_runtime)
    )

    execution_id = "execution_id_test_case_execution_id_agent_common_03"
    request_id = "request_id_test_case_execution_id_agent_common_03"
    conversation_id = f"conversation_{int(time.time() * 1000)}"
    mcp_runtime.expected_tool_id = "校验MCP组件超时.校验MCP组件超时.McpTimeout"
    mcp_runtime.expected_agent_id = "0b34fea30e2a41b5af35b9b375edab83_0.6.0"
    mcp_runtime.expected_session_id = conversation_id
    params = {
        "conversationHistory": [],
        "pluginConfigs": [],
        "globalVariables": {"hcy": "0"},
        "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
        "workflowSequence": [],
        "activeWorkflows": [],
        "agent": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "x-execution-id": execution_id,
        "x-request-id": request_id,
    }

    instance, response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=IR_PATH,
            query="调用 McpTimeout 并返回 header",
            conversation_id=conversation_id,
            headers=headers,
            params=params,
        )
    )

    assert len(instance.mcps) == 1
    assert isinstance(instance.mcps[0], McpServer)
    assert not isinstance(instance.mcps[0], AgentCoreMcpLayer)
    assert len(model_runtime.calls) >= 1
    assert any(
        tool["name"] == "McpTimeout" for tool in model_runtime.calls[0].functions
    )
    assert len(mcp_runtime.calls) == 1
    assert mcp_runtime.calls[0].tool_id == mcp_runtime.expected_tool_id
    assert mcp_runtime.calls[0].agent_id == mcp_runtime.expected_agent_id
    assert mcp_runtime.calls[0].session_id == conversation_id
    assert mcp_runtime.identifier_validation_passed is True
    runtime_context = mcp_runtime.calls[0].kwargs.get("runtime_context")
    assert runtime_context is not None
    assert runtime_context.api_config["headers"]["x-request-id"] == request_id
    assert runtime_context.api_config["headers"]["x-execution-id"] == execution_id
    assert '"event":"function_call"' in response_text
    assert request_id in response_text
    assert execution_id in response_text
    assert '"event":"error"' not in response_text


def test_case03_mcp_handler_contract_records_headers(runtimes):
    _, _, mcp_runtime, mcp_layer = runtimes
    handler = McpHandler(
        context_manager=type(
            "_FakeContextManager",
            (),
            {
                "agent_config": type(
                    "_FakeAgentConfig",
                    (),
                    {"metadata": type("_FakeMetadata", (), {"id": "agent-mcp-test"})()},
                )(),
                "add_function_message": staticmethod(lambda **kwargs: None),
                "get_global_variables": staticmethod(lambda key, default=None: default),
            },
        )()
    )

    function_call = {
        "name": "McpTimeout",
        "arguments": json.dumps({"input": "mcp header check"}, ensure_ascii=False),
        "tool_call_id": "tool_mcp_1",
    }
    runtime_context = type(
        "_RuntimeContext",
        (),
        {"api_config": {"headers": {"x-execution-id": "exec-mcp"}}},
    )()
    mcp_runtime.expected_tool_id = "McpTimeout"
    mcp_runtime.expected_agent_id = "agent-mcp-test"
    mcp_runtime.expected_session_id = "session-mcp-test"

    result, latency = asyncio.run(
        handler.execute_mcp_from_function_call(
            function_call,
            mcp_layer,
            runtime_context=runtime_context,
        )
    )

    assert latency >= 0
    assert len(mcp_runtime.calls) == 1
    assert mcp_runtime.calls[0].inputs["input"] == "mcp header check"
    assert mcp_runtime.calls[0].tool_id == "McpTimeout"
    assert mcp_runtime.calls[0].agent_id == "agent-mcp-test"
    assert (
        mcp_runtime.calls[0]
        .kwargs["runtime_context"]
        .api_config["headers"]["x-execution-id"]
        == "exec-mcp"
    )
    assert result["errCode"] == 0
    assert result["data"]["headers"]["x-execution-id"] == "exec-mcp"
