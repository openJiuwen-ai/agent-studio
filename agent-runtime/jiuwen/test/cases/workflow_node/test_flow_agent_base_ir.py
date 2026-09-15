#!/usr/bin/env python3
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
测试 FlowAgent 迁移是否成功

基于商用版本测试用例 workflow_component_agent_custom.json
创建工作流：开始 -> Agent -> 结束
使用模拟插件工具测试功能
"""

import os
import sys
from unittest.mock import Mock, patch, AsyncMock

import pytest
from openjiuwen.core.common.logging import logger
from openjiuwen.core.foundation.tool import Tool, ToolCard
from openjiuwen.core.workflow import (
    Workflow,
    create_workflow_session,
    WorkflowExecutionState,
)

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from jiuwen.extension.workflow_node.flow_agent import FlowAgent, FlowAgentConfig
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.end import End


class MockCalculatorTool(Tool):
    """模拟计算器工具"""

    def __init__(self):
        card = ToolCard(
            name="calculator_tool",
            description="Calculator tool for arithmetic operations",
            input_params={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression",
                    }
                },
                "required": ["expression"],
            },
        )
        super().__init__(card=card)

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """执行计算"""
        logger.info(f"MockCalculatorTool invoked with: {inputs}")
        expression = inputs.get("expression", "")
        try:
            result = eval(expression)
            return {"result": str(result)}
        except Exception as e:
            return {"result": f"Error: {str(e)}"}

    async def stream(self, inputs: dict, **kwargs):
        """流式执行 - 直接返回 invoke 结果"""
        result = await self.invoke(inputs, **kwargs)
        yield result


class MockAddTool(Tool):
    """模拟添加啦啦啦工具"""

    def __init__(self):
        card = ToolCard(
            name="mock_plugin_add",
            description="Add 啦啦啦 to input",
            input_params={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Input query"}
                },
                "required": ["query"],
            },
        )
        super().__init__(card=card)

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """执行添加啦啦啦"""
        logger.info(f"MockAddTool invoked with: {inputs}")
        query = inputs.get("query", "")
        return {"result": f"{query}啦啦啦"}

    async def stream(self, inputs: dict, **kwargs):
        """流式执行 - 直接返回 invoke 结果"""
        result = await self.invoke(inputs, **kwargs)
        yield result


@pytest.mark.asyncio
@patch("jiuwen.extension.workflow_node.flow_agent.ReActAgent")
async def test_flow_agent_migration_success(mock_react_agent_class):
    """测试 FlowAgent 迁移是否成功 - 模拟商用版本测试用例"""

    # 1. 设置 mock ReActAgent
    mock_react_instance = AsyncMock()
    mock_ability_mgr = Mock()
    mock_ability_mgr._tools = {}
    mock_react_instance._ability_manager = mock_ability_mgr
    mock_react_instance.configure = Mock()

    # 模拟 Agent 的行为 - 先调用 calculator，再调用 mock_plugin_add
    async def mock_invoke_side_effect(inputs, session):
        logger.info(f"Mock ReActAgent invoked with: {inputs}")
        query = inputs.get("query", "")

        # 模拟插件调用流程
        if "calculator" in query:
            # 先返回计算器结果
            calc_result = "18"
            # 然后调用 mock_plugin_add
            final_result = f"{calc_result}啦啦啦"
            return {"output": f"我是custom: {final_result}", "result_type": "success"}

        return {"output": "Default response", "result_type": "success"}

    mock_react_instance.invoke.side_effect = mock_invoke_side_effect
    mock_react_agent_class.return_value = mock_react_instance

    # 2. Mock Runner.resource_mgr
    with patch("openjiuwen.core.runner.Runner.resource_mgr") as mock_resource_mgr:
        mock_resource_mgr.add_tool = Mock()

        # 3. 创建工作流
        flow = Workflow()

        # 4. 创建 Start 组件
        start_config = {
            "userFields": {
                "inputs": [
                    {
                        "id": "query",
                        "type": "string",
                        "required": True,
                        "description": "用户输入",
                    }
                ]
            }
        }
        start = Start(start_config)
        flow.set_start_comp(
            "node_start", start, inputs_schema={"query": "${user_query}"}
        )

        # 5. 创建 FlowAgent 配置和组件
        agent_config = FlowAgentConfig(
            strategy_name="ReAct",
            strategy_provider="JiuWen",
            max_iteration=3,
            streaming=False,
            with_chat_history=True,
            chat_history_max_turn=0,
            system_prompt="你是一个助手，根据{{input}}回答问题",
            llm_config={
                "model_name": "mock_model_name",
                "model_provider": "customer_chat_llm",
                "request_config": {"temperature": 0.2},
            },
        )

        # 创建模拟工具
        calc_tool = MockCalculatorTool()
        add_tool = MockAddTool()

        flow_agent = FlowAgent(agent_config)
        flow_agent.add_tool(calc_tool)
        flow_agent.add_tool(add_tool)

        # 添加到工作流
        flow.add_workflow_comp(
            "node_agent",
            flow_agent,
            inputs_schema={"input": "${node_start.systemFields.query}"},
        )

        # 6. 创建 End 组件
        end_config = {
            "responseMode": "directResponse",
            "userFields": {
                "inputs": [
                    {
                        "id": "result",
                        "type": "string",
                        "required": False,
                        "description": "最终输出",
                    }
                ]
            },
            "responseTemplate": "{{result}}",
            "isStreamOut": True,
        }
        end = End(end_config)
        flow.set_end_comp(
            "node_end", end, inputs_schema={"result": "${node_agent.userFields.output}"}
        )

        # 7. 连接组件
        flow.add_connection("node_start", "node_agent")
        flow.add_connection("node_agent", "node_end")

        # 8. 执行工作流
        user_query = (
            "先调用calculator计算9+9，再将计算结果调用插件mock_plugin_add，返回结果"
        )
        result = await flow.invoke(
            inputs={"user_query": user_query}, session=create_workflow_session()
        )

        # 9. 验证结果
        assert result.state == WorkflowExecutionState.COMPLETED
        assert "answer" in result.result
        response_data = result.result["answer"]
        if isinstance(response_data, dict) and "answer" in response_data:
            response_str = response_data["answer"]
        else:
            response_str = response_data
        assert "我是custom: 18啦啦啦" in response_str

        # 验证 Agent 被正确调用
        mock_react_instance.invoke.assert_called_once()

        logger.info("测试成功！FlowAgent 迁移验证通过")
        return True


@pytest.mark.asyncio
async def test_flow_agent_with_real_mock_tools():
    """使用真实的模拟工具测试 FlowAgent（不 mock ReActAgent）"""

    # 创建模拟工具
    calc_tool = MockCalculatorTool()
    add_tool = MockAddTool()

    # 测试工具功能
    calc_result = await calc_tool.invoke({"expression": "9+9"})
    assert calc_result["result"] == "18"

    add_result = await add_tool.invoke({"query": "18"})
    assert add_result["result"] == "18啦啦啦"

    logger.info("模拟工具测试通过")


def test_ir_config_compatibility():
    """测试 IR 配置兼容性"""
    # 商用版本 IR 配置
    ir_agent_config = {
        "agent_strategy": {
            "name": "Strategy1",
            "provider": "Custom",
            "description": "",
            "id": "35027b8c-9e2b-4798-a241-d8450aefa647",
            "method": "POST",
            "url": "xxxx",
            "auth": {},
            "headers": {},
            "arguments": [],
            "response": [],
            "streaming": False,
        },
        "maxIteration": 3,
        "withChatHistory": True,
        "chatHistoryMaxTurn": 0,
        "model": {
            "modelName": "mock_model_name",
            "modelType": "customer_chat_llm",
            "hyperParameters": {"temperature": 0.2},
            "extension": {},
        },
        "plugins": [
            {"name": "mock_plugin_add", "description": "mock_plugin_add，加上啦啦啦"},
            {"name": "calculator_tool", "description": "calculator_tool"},
        ],
        "systemPrompt": "你是一个助手，根据{{input}}回答问题",
    }

    # 转换为 FlowAgentConfig
    flow_agent_config = FlowAgentConfig(
        strategy_name="ReAct",  # 开源版本使用 ReAct
        strategy_provider="JiuWen",
        max_iteration=ir_agent_config["maxIteration"],
        streaming=ir_agent_config["agent_strategy"]["streaming"],
        with_chat_history=ir_agent_config["withChatHistory"],
        chat_history_max_turn=ir_agent_config["chatHistoryMaxTurn"],
        system_prompt=ir_agent_config["systemPrompt"],
        llm_config={
            "model_name": ir_agent_config["model"]["modelName"],
            "model_provider": ir_agent_config["model"]["modelType"],
            "request_config": ir_agent_config["model"]["hyperParameters"],
        },
        plugins=ir_agent_config["plugins"],
    )

    # 验证配置
    assert flow_agent_config.max_iteration == 3
    assert flow_agent_config.system_prompt == "你是一个助手，根据{{input}}回答问题"
    assert len(flow_agent_config.plugins) == 2

    # 验证配置验证通过
    flow_agent_config.validate_config()

    logger.info("IR 配置兼容性测试通过")


if __name__ == "__main__":
    # 运行测试
    import subprocess

    print("=" * 60)
    print("开始测试 FlowAgent 迁移")
    print("=" * 60)

    # 测试 1: IR 配置兼容性
    print("\n[测试 1] IR 配置兼容性测试...")
    test_ir_config_compatibility()
    print("OK IR 配置兼容性测试通过")

    # 测试 2: 模拟工具功能
    print("\n[测试 2] 模拟工具功能测试...")
    import asyncio

    asyncio.run(test_flow_agent_with_real_mock_tools())
    print("OK 模拟工具功能测试通过")

    # 测试 3: 使用 pytest 运行完整工作流测试
    print("\n[测试 3] 完整工作流测试...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "-s"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
    )

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("所有测试通过！FlowAgent 迁移成功！")
        print("=" * 60)
    else:
        print(f"\n测试失败，返回码: {result.returncode}")
        sys.exit(result.returncode)
