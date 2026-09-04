import asyncio
import os
import time

import pytest

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.integration import AgentCoreMcpLayer
from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer
from jiuwen.test.cases.controller_multi_agent.agent_core_model_contract_runtime import (
    AgentCoreFunctionCallModelRuntime,
)
from jiuwen.test.cases.controller_multi_agent.test_case_execution_id_agent_common_03_southbound_contracts import (
    IR_PATH,
    _IntegrationRegistry,
    _RecordingMcpRuntime,
    _RecordingPluginRuntime,
    _init_local_runtime,
    _patch_agent_tools,
    _run_local_ir_request,
)


@pytest.fixture()
def runtimes(monkeypatch):
    _init_local_runtime(monkeypatch)
    model_runtime = AgentCoreFunctionCallModelRuntime()
    plugin_runtime = _RecordingPluginRuntime()
    mcp_runtime = _RecordingMcpRuntime()
    _IntegrationRegistry.set_model(AgentCoreModelLayer(model_runtime))
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
    _patch_agent_tools(monkeypatch, plugin_runtime, mcp_layer)
    return model_runtime, plugin_runtime, mcp_runtime


def test_run(runtimes):
    model_runtime, plugin_runtime, mcp_runtime = runtimes
    execution_id = "execution_id_test_case_execution_id_agent_common_03"
    request_id = "request_id_test_case_execution_id_agent_common_03"
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
    mcp_runtime.expected_tool_id = "McpTimeout"
    mcp_runtime.expected_agent_id = "agent-mcp-test"
    mcp_runtime.expected_session_id = "session-mcp-test"

    _, response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=IR_PATH,
            query="调用 McpTimeout 并返回 header",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
            headers=headers,
            params=params,
        )
    )

    assert len(model_runtime.calls) >= 1
    assert len(mcp_runtime.calls) == 1
    assert plugin_runtime.calls == []
    assert mcp_runtime.calls[0].inputs["input"] == "调用 McpTimeout 并返回 header"
    assert (
        mcp_runtime.calls[0]
        .kwargs["runtime_context"]
        .api_config["headers"]["x-request-id"]
        == request_id
    )
    assert (
        mcp_runtime.calls[0]
        .kwargs["runtime_context"]
        .api_config["headers"]["x-execution-id"]
        == execution_id
    )
    assert request_id in response_text
    assert execution_id in response_text
    assert '"event":"error"' not in response_text
