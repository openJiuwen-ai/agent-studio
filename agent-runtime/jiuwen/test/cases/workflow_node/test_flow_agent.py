# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowAgent 工作流集成测试
测试覆盖:
- FlowAgent 在工作流中的完整生命周期
- 与其他组件的协作
- 输入处理与输出
- 工具调用能力
- 流式输出功能
"""

from unittest.mock import Mock, patch, AsyncMock

import pytest
from jiuwen.extension.workflow_node.flow_agent import FlowAgent, FlowAgentConfig
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.tool import Tool
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import (
    Workflow,
    Start,
    End,
    Input,
    Output,
    create_workflow_session,
)
from openjiuwen.core.workflow import WorkflowComponent
from openjiuwen.core.workflow import WorkflowExecutionState


class MessageComponent(WorkflowComponent):
    """消息组件，用于在工作流中传递/打印消息"""

    def __init__(self, message: str = ""):
        super().__init__()
        self._message = message

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """打印消息并返回输入"""
        print(f"[MessageComponent] {self._message}: {inputs}")
        return {"message": self._message, **inputs}


@pytest.mark.asyncio
@patch("jiuwen.extension.workflow_node.flow_agent.ReActAgent")
async def test_flow_agent_in_workflow(mock_react_agent_class):
    """测试 FlowAgent 在完整工作流中的功能"""
    # 设置 mock
    mock_react_instance = AsyncMock()
    mock_ability_mgr = Mock()
    mock_ability_mgr._tools = {}
    mock_react_instance._ability_manager = mock_ability_mgr
    mock_react_instance.configure = Mock()
    mock_react_instance.invoke = AsyncMock(
        return_value={"output": {"data": {"result": "Agent response"}}}
    )
    mock_react_agent_class.return_value = mock_react_instance

    # Mock Runner.resource_mgr.add_tool 方法
    with patch("openjiuwen.core.runner.Runner.resource_mgr") as mock_resource_mgr:
        mock_resource_mgr.add_tool = Mock()

        # 创建工作流
        flow = Workflow()

        # 1. 添加开始组件
        start = Start()
        flow.set_start_comp(
            "start", start, inputs_schema={"user_query": "${user_query}"}
        )

        # 2. 创建 FlowAgent 配置和组件
        agent_config = FlowAgentConfig(
            strategy_name="ReAct",
            max_iteration=5,
            streaming=False,
            system_prompt="You are a helpful assistant.",
            llm_config={
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
        )
        flow_agent = FlowAgent(agent_config)

        # 3. 添加 FlowAgent 到工作流
        flow.add_workflow_comp(
            "agent", flow_agent, inputs_schema={"query": "${start.user_query}"}
        )

        # 4. 添加结束组件 - 使用 userFields.output 来获取 FlowAgent 的输出
        end = End()
        flow.set_end_comp(
            "end", end, inputs_schema={"final_response": "${agent.userFields.output}"}
        )

        # 5. 连接组件
        flow.add_connection("start", "agent")
        flow.add_connection("agent", "end")

        # 6. 执行工作流
        result = await flow.invoke(
            inputs={"user_query": "What's the weather today?"},
            session=create_workflow_session(),
        )

        # 7. 验证结果
        assert result.state == WorkflowExecutionState.COMPLETED
        assert "output" in result.result
        assert "final_response" in result.result["output"]
        assert result.result["output"]["final_response"] == "Agent response"

        # 8. 验证 Agent 被正确调用
        mock_react_instance.invoke.assert_called_once()


@pytest.mark.asyncio
@patch("jiuwen.extension.workflow_node.flow_agent.ReActAgent")
async def test_flow_agent_with_tools_in_workflow(mock_react_agent_class):
    """测试带工具的 FlowAgent 在工作流中的功能"""
    # 设置 mock
    mock_react_instance = AsyncMock()
    mock_ability_mgr = Mock()
    mock_ability_mgr._tools = {}
    mock_react_instance._ability_manager = mock_ability_mgr
    mock_react_instance.configure = Mock()
    mock_react_instance.invoke = AsyncMock(
        return_value={
            "output": {"data": {"result": "Weather in Beijing is sunny today"}},
            "result_type": "success",
            "tool_used": "weather_tool",
        }
    )
    mock_react_agent_class.return_value = mock_react_instance

    # Mock Runner.resource_mgr.add_tool 方法
    with patch("openjiuwen.core.runner.Runner.resource_mgr") as mock_resource_mgr:
        mock_resource_mgr.add_tool = Mock()

        # 创建 mock 工具
        mock_tool = Mock(spec=Tool)
        mock_tool.card = Mock()
        mock_tool.card.name = "weather_tool"

        # 创建工作流
        flow = Workflow()

        # 添加开始组件
        start = Start()
        flow.set_start_comp("start", start, inputs_schema={"location": "${location}"})

        # 创建带工具的 FlowAgent
        agent_config = FlowAgentConfig(
            strategy_name="ReAct",
            max_iteration=10,
            system_prompt="Use tools to answer questions.",
            llm_config={
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
        )
        flow_agent = FlowAgent(agent_config)
        flow_agent.add_tool(mock_tool)

        # 添加到工作流
        flow.add_workflow_comp(
            "agent",
            flow_agent,
            inputs_schema={"query": "What's the weather in ${start.location}?"},
        )

        # 添加消息组件 - 使用 userFields.output 获取输出
        message_comp = MessageComponent("Processing agent response")
        flow.add_workflow_comp(
            "processor",
            message_comp,
            inputs_schema={"agent_response": "${agent.userFields.output}"},
        )

        # 添加结束组件
        end = End()
        flow.set_end_comp(
            "end", end, inputs_schema={"result": "${processor.agent_response}"}
        )

        # 连接组件
        flow.add_connection("start", "agent")
        flow.add_connection("agent", "processor")
        flow.add_connection("processor", "end")

        # 执行工作流
        result = await flow.invoke(
            inputs={"location": "Beijing"}, session=create_workflow_session()
        )

        # 验证结果
        assert result.state == WorkflowExecutionState.COMPLETED
        assert "output" in result.result
        assert "result" in result.result["output"]
        assert result.result["output"]["result"] == "Weather in Beijing is sunny today"

        # 验证工具被注册
        mock_resource_mgr.add_tool.assert_called_once_with(mock_tool)


@pytest.mark.asyncio
@patch("jiuwen.extension.workflow_node.flow_agent.ReActAgent")
async def test_flow_agent_simple_workflow(mock_react_agent_class):
    """测试 FlowAgent 在简单工作流中的基本功能"""
    # 设置 mock
    mock_react_instance = AsyncMock()
    mock_ability_mgr = Mock()
    mock_ability_mgr._tools = {}
    mock_react_instance._ability_manager = mock_ability_mgr
    mock_react_instance.configure = Mock()
    mock_react_instance.invoke = AsyncMock(
        return_value={"output": {"data": {"result": "Simple agent response"}}}
    )
    mock_react_agent_class.return_value = mock_react_instance

    # Mock Runner.resource_mgr.add_tool 方法
    with patch("openjiuwen.core.runner.Runner.resource_mgr") as mock_resource_mgr:
        mock_resource_mgr.add_tool = Mock()

        # 创建工作流
        flow = Workflow()

        # 添加开始组件
        start = Start()
        flow.set_start_comp("start", start, inputs_schema={"query": "${user_query}"})

        # 创建 FlowAgent
        agent_config = FlowAgentConfig(
            strategy_name="ReAct",
            streaming=False,
            llm_config={
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
        )
        flow_agent = FlowAgent(agent_config)

        # 添加到工作流
        flow.add_workflow_comp(
            "agent", flow_agent, inputs_schema={"query": "${start.query}"}
        )

        # 添加结束组件 - 使用 userFields.output 获取输出
        end = End()
        flow.set_end_comp(
            "end", end, inputs_schema={"result": "${agent.userFields.output}"}
        )

        # 连接组件
        flow.add_connection("start", "agent")
        flow.add_connection("agent", "end")

        # 执行工作流
        result = await flow.invoke(
            inputs={"user_query": "Hello world"}, session=create_workflow_session()
        )

        # 验证结果
        assert result.state == WorkflowExecutionState.COMPLETED
        assert "output" in result.result
        assert "result" in result.result["output"]
        assert result.result["output"]["result"] == "Simple agent response"


@pytest.mark.asyncio
@patch("jiuwen.extension.workflow_node.flow_agent.ReActAgent")
async def test_flow_agent_with_custom_system_prompt(mock_react_agent_class):
    """测试带自定义系统提示词的 FlowAgent 在工作流中的功能"""
    # 设置 mock
    mock_react_instance = AsyncMock()
    mock_ability_mgr = Mock()
    mock_ability_mgr._tools = {}
    mock_react_instance._ability_manager = mock_ability_mgr
    mock_react_instance.configure = Mock()
    mock_react_instance.invoke = AsyncMock(
        return_value={
            "output": {
                "data": {"result": "I'm a financial assistant. The answer is 100."}
            }
        }
    )
    mock_react_agent_class.return_value = mock_react_instance

    # Mock Runner.resource_mgr.add_tool 方法
    with patch("openjiuwen.core.runner.Runner.resource_mgr") as mock_resource_mgr:
        mock_resource_mgr.add_tool = Mock()

        # 创建工作流
        flow = Workflow()

        # 添加组件
        start = Start()
        flow.set_start_comp("start", start, inputs_schema={"query": "${user_query}"})

        # 创建带自定义系统提示词的 FlowAgent
        agent_config = FlowAgentConfig(
            strategy_name="ReAct",
            system_prompt="You are a financial assistant. Answer all questions about finance.",
            llm_config={
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
        )
        flow_agent = FlowAgent(agent_config)

        flow.add_workflow_comp(
            "agent", flow_agent, inputs_schema={"query": "${start.query}"}
        )

        end = End()
        flow.set_end_comp(
            "end", end, inputs_schema={"financial_advice": "${agent.userFields.output}"}
        )

        flow.add_connection("start", "agent")
        flow.add_connection("agent", "end")

        # 执行工作流
        result = await flow.invoke(
            inputs={"user_query": "What is 50 + 50?"}, session=create_workflow_session()
        )

        # 验证结果
        assert result.state == WorkflowExecutionState.COMPLETED
        assert "output" in result.result
        assert "financial_advice" in result.result["output"]
        assert "financial assistant" in result.result["output"]["financial_advice"]
        assert "100" in result.result["output"]["financial_advice"]


if __name__ == "__main__":
    # 使用 pytest 运行测试
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    if result.returncode == 0:
        print("\nAll tests passed!")
    else:
        print(f"\nTests failed with return code: {result.returncode}")
        sys.exit(result.returncode)
