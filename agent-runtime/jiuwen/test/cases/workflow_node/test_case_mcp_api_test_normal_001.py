# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowMcp 组件 astream 方式工作流测试

完整工作流: Start -> FlowMcp -> End

测试基于 test_case_mcp_api_test_normal_001.json 配置，使用 WorkflowWrapper.astream() 作为入口。

运行方式:
    pytest jiuwen/test/cases/workflow_node/test_flow_mcp_astream.py -v -s
"""

import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.foundation.tool.mcp.base import McpToolCard
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow, WorkflowCard

USER_FIELDS = "userFields"
SYSTEM_FIELDS = "systemFields"

workflow_id = "826f2c9f-97d3-46fe-a9e9-561726c7f30"
agent_id = "39a8026s-2181-446f-8cf1-2887e9403h7c"
session_id = "e02b3673-1683-4a99-83b6-ecce9426bf0b"
os.environ["CLOSE_URL_JUDGE_SWITCH"] = "true"


def _make_start_conf() -> dict:
    """Start 组件配置（对应 JSON 中的 node_start）"""
    return {
        USER_FIELDS: {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "input1参数",
                    "id": "input1",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "input参数",
                    "id": "input",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "input1参数",
                    "id": "input1",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "input参数",
                    "id": "input",
                    "type": "string",
                    "required": True,
                },
            ],
        },
        SYSTEM_FIELDS: {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "schema": [
                        {
                            "schema": {
                                "schema": [
                                    {
                                        "description": "角色",
                                        "id": "role",
                                        "type": "string",
                                    },
                                    {
                                        "description": "消息内容",
                                        "id": "content",
                                        "type": "string",
                                    },
                                ],
                                "id": "",
                                "type": "object",
                            },
                            "description": "会话历史消息",
                            "id": "conversationHistory",
                            "type": "array",
                        },
                        {
                            "description": "当前系统时间",
                            "id": "currentTime",
                            "type": "string",
                        },
                        {
                            "description": "使用该工作流的唯一标识",
                            "id": "userId",
                            "type": "string",
                        },
                        {
                            "description": "工作流对话id",
                            "id": "conversationId",
                            "type": "string",
                        },
                    ],
                    "sourceType": "input",
                    "description": "系统变量",
                    "id": "sys",
                    "type": "object",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "schema": [
                        {
                            "schema": {
                                "schema": [
                                    {
                                        "description": "角色",
                                        "id": "role",
                                        "type": "string",
                                    },
                                    {
                                        "description": "消息内容",
                                        "id": "content",
                                        "type": "string",
                                    },
                                ],
                                "id": "",
                                "type": "object",
                            },
                            "description": "会话历史消息",
                            "id": "conversationHistory",
                            "type": "array",
                        },
                        {
                            "description": "当前系统时间",
                            "id": "currentTime",
                            "type": "string",
                        },
                        {
                            "description": "使用该工作流的唯一标识",
                            "id": "userId",
                            "type": "string",
                        },
                        {
                            "description": "工作流对话id",
                            "id": "conversationId",
                            "type": "string",
                        },
                    ],
                    "sourceType": "input",
                    "description": "系统变量",
                    "id": "sys",
                    "type": "object",
                    "required": True,
                },
            ],
        },
    }


def _make_flow_mcp_conf() -> dict:
    """FlowMcp 组件 IR 配置（对应 JSON 中的 node_1758076615132）"""
    return {
        "tool_name": "McpArgTypeStringCheck",
        USER_FIELDS: {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "input输入的值",
                    "id": "input",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "null",
                    "id": "isError",
                    "type": "boolean",
                    "required": True,
                },
                {
                    "schema": {
                        "schema": [
                            {"id": "type", "type": "string"},
                            {"id": "text", "type": "string"},
                        ],
                        "id": "",
                        "type": "object",
                    },
                    "sourceType": "null",
                    "description": "null",
                    "id": "content",
                    "type": "array",
                    "required": True,
                },
            ],
        },
        "arguments": [
            {
                "name": "input1",
                "type": "string",
                "description": "mcp tool input is string",
                "default_value": "mcp_tool_input_arg_type_is_string",
                "required": True,
                "visible": True,
                "schema": "",
            },
            {
                "name": "input",
                "type": "string",
                "description": "mcp component input is string",
                "default_value": "mcp_component_input_arg_type_is_string",
                "required": True,
                "visible": True,
                "schema": "",
            },
        ],
        "auth": {},
        "response": [
            {"name": "isError", "type": "boolean", "required": True},
            {
                "schema": {
                    "schema": [
                        {"name": "type", "type": "string", "required": True},
                        {"name": "text", "type": "string", "required": True},
                    ],
                    "type": "object",
                },
                "name": "content",
                "type": "array",
                "required": True,
            },
        ],
        "systemFields": {"inputs": [], "outputs": []},
        "name": "检验MCP组件中arg的type是否为string",
        "id": "McpArgTypeStringCheck",
        "type": "sse",
        "url": "http://fakeIp:8091/sse",
    }


def _make_end_conf() -> dict:
    """End 组件配置（对应 JSON 中的 node_end）"""
    return {
        "responseMode": "directResponse",
        USER_FIELDS: {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "最终输出",
                    "id": "content",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "错误标志",
                    "id": "isError",
                    "type": "boolean",
                    "required": True,
                },
            ],
            "outputs": [],
        },
        "responseTemplate": "{{content}}",
        SYSTEM_FIELDS: {"inputs": [], "outputs": []},
    }


def create_flow_mcp_workflow() -> tuple[Workflow, str]:
    """
    创建 FlowMcp 工作流（基于 test_case_mcp_api_test_normal_001.json）

    结构: start -> mcp -> end

    返回:
        Workflow: 工作流实例
        workflow_id: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="test_mcp",
        version="0.6.0",
        description="test_mcp11",
    )
    wf = Workflow(workflow_card)

    wf.set_start_comp(
        "node_start",
        Start(_make_start_conf()),
        inputs_schema={
            "input1": "${input1}",
            "input": "${input}",
            "query": "${query}",
            "sys": "${sys}",
        },
    )

    wf.add_workflow_comp(
        "node_1758076615132",
        FlowMcp(_make_flow_mcp_conf()),
        inputs_schema={USER_FIELDS: {"input": "${node_start.userFields.input}"}},
    )

    wf.set_end_comp(
        "node_end",
        End(_make_end_conf()),
        inputs_schema={
            "content": "${node_1758076615132.userFields.content}",
            "isError": "${node_1758076615132.userFields.isError}",
        },
        response_mode="streaming",
    )

    wf.add_connection("node_start", "node_1758076615132")
    wf.add_connection("node_1758076615132", "node_end")

    Runner.resource_mgr.add_workflow(
        workflow_card,
        lambda card=workflow_card: wf,
        tag=agent_id,
    )

    return wf, workflow_id


def _build_context(conversation_history: list):
    """从对话历史构建 ModelContext"""
    from openjiuwen.core.context_engine.context.context import SessionModelContext
    from openjiuwen.core.context_engine.schema.config import ContextEngineConfig

    model_context = SessionModelContext(
        context_id=f"{workflow_id}_context",
        session_id=session_id,
        config=ContextEngineConfig(),
        history_messages=[],
        processors=[],
    )
    return model_context


@pytest.fixture
def mock_mcp_client():
    """Mock SSEClientNew 的 list_tools 和 call_tool 方法，避免真实网络请求"""
    tool_card = McpToolCard(
        name="McpArgTypeStringCheck",
        server_name="test_mcp",
        description="检验MCP组件中arg的type是否为string",
        input_params={
            "type": "object",
            "properties": {
                "input1": {"type": "string"},
                "input": {"type": "string"},
                JIUWEN_RUNTIME_KWARGS: {"type": "object"},
            },
            "additionalProperties": True,
        },
    )

    with patch(
        "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.list_tools",
        new_callable=AsyncMock,
    ) as mock_list_tools:
        mock_list_tools.return_value = [tool_card]

        with patch(
            "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.call_tool",
            new_callable=AsyncMock,
        ) as mock_call_tool:
            mock_call_tool.return_value = [
                MagicMock(
                    **{
                        "model_dump": MagicMock(
                            return_value={
                                "type": "text",
                                "text": "Input is string ,iuput_type: <class 'str'>,input:mcp_tool_input_arg_type_is_string",
                            }
                        )
                    }
                ),
            ]
            yield {
                "list_tools": mock_list_tools,
                "call_tool": mock_call_tool,
            }


@pytest.mark.asyncio
async def test_flow_mcp_astream_workflow(mock_mcp_client):
    """
    测试 FlowMcp 工作流（使用 astream 方式）

    流程:
    1. 用户输入 query
    2. 开始节点 -> 传递参数
    3. MCP 节点调用 McpArgTypeStringCheck API
    4. 输出参数 (isError, content)
    5. 结束节点格式化输出
    """
    params = {
        "global_variables": {
            "input1": "test_input1_value",
            "input": "test_input_value",
            "sys": {
                # "conversationHistory": conversation_history,
                "conversationHistory": [],
                "currentTime": "2024-09-24 14:44:41",
                "userId": "test_user",
                "conversationId": session_id,
            },
        },
        # "conversation_history": conversation_history,
        "conversation_history": [],
        "CONTROLLER_MODE_SWITCH": False,
    }

    workflow, wf_id = create_flow_mcp_workflow()
    wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in wrapper.astream(
        query="调用McpArgTypeStringCheck输入String类型",
        workflow_id=wf_id,
        session_id=session_id,
        agent_id=agent_id,
        params=params,
        context=_build_context([]),
    ):
        chunks.append(chunk)
        print(f"收到 chunk: {chunk}")

    assert len(chunks) > 0
    print(f"共收到 {len(chunks)} 个 chunk")

    has_finish = False
    for chunk in chunks:
        if hasattr(chunk, "code") and chunk.code in [0, 4000, "FINISH"]:
            has_finish = True
            break
    assert has_finish, "工作流应该正常结束"

    # 新版本（有 arguments）不调 list_tools，只调 call_tool
    mock_mcp_client["list_tools"].assert_not_awaited()
    mock_mcp_client["call_tool"].assert_awaited_once()


@pytest.mark.skip(
    reason="需要真实 MCP Server 环境（McpArgTypeStringCheck 工具），在目标环境手动运行"
)
@pytest.mark.asyncio
async def test_flow_mcp_astream_real_call():
    """
    真实调用 McpArgTypeStringCheck 工具的端到端测试（无 mock）

    前置条件:
    - MCP Server 可达：http://fakeIp:8091/sse
    - MCP Server 已注册 McpArgTypeStringCheck 工具

    运行方式:
        pytest jiuwen/test/cases/workflow_node/test_case_mcp_api_test_normal_001.py \
            -k test_flow_mcp_astream_real_call -v -s

    流程:
    1. 用户输入 query
    2. 开始节点 -> 传递参数
    3. MCP 节点真实连接 MCP Server，调用 McpArgTypeStringCheck
    4. 输出参数 (isError, content)
    5. 结束节点格式化输出
    """
    params = {
        "global_variables": {
            "input1": "test_input1_value",
            "input": "test_input_value",
            "sys": {
                "conversationHistory": [],
                "currentTime": "2024-09-24 14:44:41",
                "userId": "test_user",
                "conversationId": session_id,
            },
        },
        "conversation_history": [],
        "CONTROLLER_MODE_SWITCH": False,
    }

    workflow, wf_id = create_flow_mcp_workflow()
    wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in wrapper.astream(
        query="调用McpArgTypeStringCheck输入String类型",
        workflow_id=wf_id,
        session_id=session_id,
        agent_id=agent_id,
        params=params,
        context=_build_context([]),
    ):
        chunks.append(chunk)
        print(f"收到 chunk: {chunk}")

    assert len(chunks) > 0, "应该收到至少一个 chunk"
    print(f"共收到 {len(chunks)} 个 chunk")

    # 验证工作流正常结束
    has_finish = False
    for chunk in chunks:
        if hasattr(chunk, "code") and chunk.code in [0, 4000, "FINISH"]:
            has_finish = True
            break
    assert has_finish, "工作流应该正常结束"

    # 验证返回内容包含预期的文本（McpArgTypeStringCheck 返回的 type 应为 text）
    final_content = ""
    for chunk in chunks:
        if hasattr(chunk, "data") and chunk.data:
            final_content += str(chunk.data)
    print(f"最终输出内容: {final_content}")
    assert "string" in final_content.lower(), (
        f"返回内容应包含 string 相关信息: {final_content}"
    )
