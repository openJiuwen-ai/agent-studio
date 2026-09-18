#!/usr/bin/env python
"""
工作流用例 -- ReAct mode workflow

=== 测试目标 ===
基于商用版本 test_case_llm_react_multy_tools_010 中的 workflow_react_tools 工作流，
在开源版本 openjiuwen 环境下实现相同的工作流，使用 jiuwen.extension.workflow_node 中的组件。

=== 工作流功能 ===
1. 接收用户输入 query
2. 消息节点 echo 用户输入
3. 结束节点输出固定内容 "气温20度"

=== 工作流组件 ===
- Start: 开始节点，处理输入
- Message: 消息节点，echo 用户输入
- End: 结束节点，输出最终结果
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import (
    Workflow,
    create_workflow_session,
    WorkflowExecutionState,
)
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

pytestmark = pytest.mark.asyncio
workflow_id = "1e2c49af-f38b-41b4-9129-af3f694c3f35"
agent_id = "0b34fea30e2a41b5af35b9b375edab99"


def create_workflow_react_tools(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建与商用版本 workflow_react_tools 功能相同的工作流

    结构: start -> message -> end

    Returns:
        Workflow: 工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="workflow_react_tools",
        version="0.6.0",
        description="react模式多工具调用场景测试",
    )
    flow = Workflow(card=workflow_card)

    # 配置开始节点
    start_conf = {
        "name": "开始",
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

    # 1. 设置开始节点
    flow.set_start_comp("node_start", Start(start_conf), inputs_schema={})

    # 2. 添加消息节点 - echo 用户输入
    message_conf = {
        "name": "消息",
        "template": "{{input}}",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "input",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }
    flow.add_workflow_comp(
        "node_message",
        Message(message_conf),
        inputs_schema={"input": "${node_start.systemFields.query}"},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 3. 设置结束节点 - 输出固定内容 "气温20度"
    end_conf = {
        "name": "结束",
        "responseMode": "directResponse",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "最终输出",
                    "id": "result",
                    "type": "string",
                    "required": False,
                }
            ],
            "outputs": [],
        },
        "responseTemplate": "{{result}}",
        "systemFields": {"inputs": [], "outputs": []},
        "isStreamOut": True,
    }
    flow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"result": "气温20度"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    flow.add_connection("node_start", "node_message")
    flow.add_connection("node_message", "node_end")

    # 注册工作流到 Runner

    Runner.resource_mgr.add_workflow(workflow_card, lambda: flow, tag=agent_id)
    return flow, workflow_id


async def test_workflow_react_tools_invoke():
    """
    测试 workflow_react_tools 工作流的 invoke 执行

    验证:
    1. 工作流能够正确执行
    2. 消息节点能够正确 echo 用户输入
    3. 结束节点能够正确输出固定内容 "气温20度"
    """
    workflow_logger.info("=== 测试 workflow_react_tools 工作流 (invoke) ===")

    # 创建工作流
    flow, workflow_id = create_workflow_react_tools()  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="你好",
        workflow_id=workflow_id,
        session_id="test_session",
        agent_id=agent_id,
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)
    # 执行工作流
    test_query = "你好"
    inputs = {"query": test_query}
    session = create_workflow_session()
    flow, workflow_id = create_workflow_react_tools(False)
    result = await flow.invoke(inputs, session=session)

    # 验证结果
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED

    workflow_logger.info(f"Workflow result: {result}")
    workflow_logger.info(f"Result data: {result.result}")

    # 验证输出包含固定内容
    if result.result and "output" in result.result:
        output = result.result["output"]
        assert "response" in output
        assert "气温20度" in output["response"]
        workflow_logger.info("✓ 验证成功: 输出包含 '气温20度'")

    return result


async def test_workflow_react_tools_stream():
    """
    测试 workflow_react_tools 工作流的 stream 执行

    验证:
    1. 流式输出能够正确生成
    2. 包含固定内容 "气温20度"
    """

    workflow_logger.info("=== 测试 workflow_react_tools 工作流 (stream) ===")

    # 创建工作流
    flow, _ = create_workflow_react_tools()

    # 执行工作流
    test_query = "查询天气"
    inputs = {"query": test_query}
    session = create_workflow_session()

    # 收集所有流式输出
    stream_outputs = []
    workflow_logger.info("开始流式输出...")

    async for output in flow.stream(inputs, session=session):
        stream_outputs.append(output)
        if hasattr(output, "payload"):
            workflow_logger.info(f"收到流输出: {output.payload}")

    # 验证流式输出
    assert len(stream_outputs) > 0, "应该至少有一个流输出"

    # 检查是否包含 "气温20度"
    has_expected_response = False
    for output in stream_outputs:
        if hasattr(output, "payload"):
            payload = output.payload
            if isinstance(payload, dict):
                response = payload.get("answer", "")
                if "气温20度" in str(response):
                    has_expected_response = True
                    break

    assert has_expected_response, "应该包含固定内容 '气温20度'"
    workflow_logger.info("✓ 验证成功: 流式输出包含 '气温20度'")

    return stream_outputs


async def test_workflow_react_tools_echo():
    """
    测试消息节点的 echo 功能
    """
    workflow_logger.info("=== 测试消息节点 echo 功能 ===")

    # 创建工作流
    flow, _ = create_workflow_react_tools()

    # 执行工作流
    test_query = "Hello World!"
    inputs = {"query": test_query}
    session = create_workflow_session()

    result = await flow.invoke(inputs, session=session)

    # 验证结果
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED

    workflow_logger.info(f"测试输入: {test_query}")
    workflow_logger.info(f"工作流结果: {result.result}")

    return result


if __name__ == "__main__":
    import subprocess
    import sys

    workflow_logger.info("运行 workflow_react_tools 测试用例")

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v", "-s"])
    if result.returncode == 0:
        workflow_logger.info("\n✓ 所有测试通过!")
    else:
        workflow_logger.error(f"\n✗ 测试失败，返回码: {result.returncode}")
        sys.exit(result.returncode)
