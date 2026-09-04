"""
意图识别工作流 (Intent Identification Workflow)

根据文档说明，code 组件在开源版本中不可用，所以使用简化版本：
node_start → node_end
intent_id 固定为 0
"""

import pytest
from jiuwen.extension.workflow_node.end import End
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

workflow_id = "966cbaa3-e693-4cd4-be18-44747329df9e"
agent_id = "302a1137-9d59-4c17-b9b6-b6674843c83e"


def create_intent_detection_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建意图识别工作流

    结构: start -> end

    Returns:
        Workflow: 意图识别工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="qzp_intent_identifier_2",
        version="0.6.0",
        description="斯蒂芬",
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

    # 2. 配置结束节点，intent_id 固定为 0
    end_conf = {
        "responseTemplate": "{{intent_id}}",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "intent_id",
                    "id": "intent_id",
                    "type": "integer",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "intent_id",
                    "id": "intent_id",
                    "type": "integer",
                    "required": True,
                }
            ],
        },
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"intent_id": 0},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 3. 添加连接
    workflow.add_connection("node_start", "node_end")

    # 4. 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_intent_detection_workflow():
    """
    测试意图识别工作流
    """
    workflow, workflow_id = create_intent_detection_workflow()  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="0",
        workflow_id=workflow_id,
        session_id="cae2c07b-2a13-4107-8c2b-d75e9af55b5f",
        agent_id=agent_id,
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)
    # 执行工作流
    inputs = {
        "query": "测试查询",
        "sys": {
            "conversationHistory": [],
            "currentTime": "2024-01-01",
            "userId": "test_user",
            "conversationId": "test_conv",
        },
    }
    session = create_workflow_session()

    result = await workflow.invoke(inputs, session=session)

    # 验证结果
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED

    return result
