# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
__all__ = [
    "TestCaseWorkflowAgentComponentCommon01",
]

import os
import sys
from typing import AsyncIterator

import pytest

sys.path.append(r"E:\jiuwen_fei")
os.environ.setdefault("TGF_ENABLE", "false")
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")
os.environ.setdefault("USE_OPENJIUWEN_WORKFLOW", "true")
os.environ.setdefault("WORKFLOW_EXECUTE_TIMEOUT", "1200")

from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.foundation.tool import Tool, ToolCard
from jiuwen.extension.wrapper.workflow_instance_layer import (
    OpenJiuWenWorkflowInstanceLayer,
)

from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_agent import FlowAgent, FlowAgentConfig

# 设置环境变量
os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")
os.environ.setdefault("LLM_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("LLM_VERIFY_SSL", "False")

# 工作流常量
WORKFLOW_ID = "4375361d-c00b-4f1a-a35c-f767bec8fe03"
AGENT_ID = "agent_custom_01"
WORKFLOW_NAME = "custom_strategy"


# =============================================================================
# Mock 工具实现
# =============================================================================


class MockAddTool(Tool):
    """模拟加法工具 - 对应 mock_plugin_add"""

    def __init__(self):
        card = ToolCard(
            id="78446531-cc3d-48d0-bb86-04b8dfb0d3f3",
            name="mock_plugin_add",
            description="mock_plugin_add，加上啦啦啦",
            input_parameters=[
                {
                    "name": "query",
                    "type": "string",
                    "description": "query",
                    "required": True,
                }
            ],
            output_parameters=[
                {"name": "result", "type": "string", "description": "result"}
            ],
            url="http://fakeIp:5003/add",
            method="POST",
            headers={"Content-Type": "application/json"},
            auth={},
        )
        super().__init__(card)

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """执行工具调用"""
        query = inputs.get("query", "")
        result = f"{query} 啦啦啦"
        return {"errCode": 0, "errMessage": "", "data": {"result": result}}

    async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[dict]:
        """流式执行工具调用"""
        query = inputs.get("query", "")
        result = f"{query} 啦啦啦"
        yield {"errCode": 0, "errMessage": "", "data": {"result": result}}


class CalculatorTool(Tool):
    """模拟计算器工具 - 对应 calculator_tool"""

    def __init__(self):
        card = ToolCard(
            id="95f5b153-13f6-4660-9575-7837e3135e78",
            name="calculator_tool",
            description="calculator_tool",
            input_parameters=[
                {
                    "name": "expression",
                    "type": "string",
                    "description": "expression",
                    "required": True,
                }
            ],
            output_parameters=[
                {"name": "result", "type": "string", "description": "result"}
            ],
            url="http://fakeIp:5003/calculator",
            method="POST",
            headers={"Content-Type": "application/json"},
            auth={},
        )
        super().__init__(card)

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """执行工具调用"""
        expression = inputs.get("expression", "")
        try:
            result = str(eval(expression))
        except Exception as e:
            result = f"计算错误: {str(e)}"
        return {"errCode": 0, "errMessage": "", "data": {"result": result}}

    async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[dict]:
        """流式执行工具调用"""
        expression = inputs.get("expression", "")
        try:
            result = str(eval(expression))
        except Exception as e:
            result = f"计算错误: {str(e)}"
        yield {"errCode": 0, "errMessage": "", "data": {"result": result}}


# =============================================================================
# 工作流创建
# =============================================================================


def create_agent_custom_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建自定义策略 Agent 工作流

    结构: start -> agent -> end

    Returns:
        Workflow: 工作流实例
        str: 工作流 ID
    """
    workflow_logger.info(f"Creating workflow: {WORKFLOW_NAME}")

    workflow_card = WorkflowCard(
        id=WORKFLOW_ID,
        name=WORKFLOW_NAME,
        version="0.6.0",
        description="custom_strategy",
    )
    workflow = Workflow(workflow_card)

    # 1. 配置开始节点
    start_conf = {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
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

    workflow.set_start_comp("node_start", Start(start_conf), inputs_schema={})

    # 2. 配置 Agent 节点
    add_tool = MockAddTool()
    calculator_tool = CalculatorTool()

    Runner.resource_mgr.add_tool(add_tool)
    Runner.resource_mgr.add_tool(calculator_tool)

    agent_config = FlowAgentConfig(
        strategy_name="ReAct",
        strategy_provider="JiuWen",
        max_iteration=3,
        streaming=True,
        with_chat_history=True,
        chat_history_max_turn=0,
        system_prompt="你是一个助手，根据{{input}}回答问题",
        llm_config={
            "model_name": "mock_model_name",
            "model_provider": "Mock",
            "api_key": "mock-api-key",
            "api_base": "https://api.siliconflow.cn/v1",
            "model_client_config": {
                "client_provider": "Mock",
                "api_key": "mock-api-key",
                "api_base": "https://api.siliconflow.cn/v1",
                "timeout": 60.0,
            },
            "request_config": {
                "model_name": "mock_model_name",
                "temperature": 0.2,
                "stream": True,
            },
        },
        plugins=[
            {
                "id": "78446531-cc3d-48d0-bb86-04b8dfb0d3f3",
                "name": "mock_plugin_add",
                "description": "mock_plugin_add，加上啦啦啦",
                "url": "http://fakeIp:5003/add",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "auth": {},
                "arguments": [
                    {
                        "name": "query",
                        "type": "string",
                        "required": True,
                        "description": "query",
                        "method": "Body",
                    }
                ],
                "response": [
                    {
                        "name": "result",
                        "type": "string",
                        "description": "result",
                        "required": True,
                    }
                ],
            },
            {
                "id": "95f5b153-13f6-4660-9575-7837e3135e78",
                "name": "calculator_tool",
                "description": "calculator_tool",
                "url": "http://fakeIp:5003/calculator",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "auth": {},
                "arguments": [
                    {
                        "name": "expression",
                        "type": "string",
                        "required": True,
                        "description": "expression",
                        "method": "Body",
                    }
                ],
                "response": [
                    {
                        "name": "result",
                        "type": "string",
                        "description": "result",
                        "required": True,
                    }
                ],
            },
        ],
    )

    flow_agent = FlowAgent(agent_config, tools=[add_tool, calculator_tool])

    workflow.add_workflow_comp(
        "node_agent",
        flow_agent,
        inputs_schema={"input": "${node_start.systemFields.query}"},
    )

    # 3. 配置结束节点
    end_conf = {
        "responseMode": "directResponse",
        "responseTemplate": "{{result}}",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "最终输出",
                    "id": "result",
                    "type": "string",
                    "required": False,
                }
            ],
            "outputs": [],
        },
        "systemFields": {"inputs": [], "outputs": []},
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"result": "${node_agent.userFields.output}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 4. 添加连接
    workflow.add_connection("node_start", "node_agent")
    workflow.add_connection("node_agent", "node_end")

    # 5. 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=AGENT_ID)

    workflow_logger.info(f"Workflow {WORKFLOW_NAME} created successfully")
    return workflow, WORKFLOW_ID


# ===================================================================
# 测试用例
# ===================================================================


class TestCaseWorkflowAgentComponentCommon01:
    """
    完整工作流测试：Start -> FlowAgent（带两个插件工具） -> End
    验证工作流创建、节点注册、工具调用和连接关系。
    """

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        # 1. 创建工作流并验证基本属性
        workflow, workflow_id = create_agent_custom_workflow(is_streaming=True)
        workflow_layer = OpenJiuWenWorkflowInstanceLayer()
        chunks = []

        stream_gen = await workflow_layer.astream(
            query="先调用calculator计算9+9，再将计算结果调用插件mock_plugin_add，返回结果",
            params={
                "global_variables": {
                    "sys": {
                        "conversationHistory": [
                            {
                                "role": "user",
                                "content": "先调用calculator计算9+9，再将计算结果调用插件mock_plugin_add，返回结果",
                                "function_call": [],
                                "enable_history": True,
                            },
                            {
                                "role": "assistant",
                                "content": "我是custom: 18啦啦啦",
                                "enable_history": True,
                            },
                        ],
                        "currentTime": "2026-04-23",
                        "userId": "test_user",
                        "conversationId": "test-conversation-id",
                    }
                }
            },
            workflow_id=workflow_id,
            session_id="test-session-id",
            agent_id=AGENT_ID,
        )
        async for chunk in stream_gen:
            chunks.append(chunk)
            workflow_logger.info(chunk)


if __name__ == "__main__":
    pytest.main([__file__])
