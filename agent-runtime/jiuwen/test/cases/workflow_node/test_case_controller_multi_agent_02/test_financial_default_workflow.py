"""
理财默认工作流

完整流程:
开始 → 消息 → 结束
"""

import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")
os.environ.setdefault("LLM_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("LLM_VERIFY_SSL", "False")

workflow_id = "33d0e157-318d-4b35-96a3-0674a48c9a9f"
agent_id = "e21b261d-3792-4942-873b-b3b6fef29537"


def create_financial_default_workflow(
    is_streaming: bool = True,
) -> tuple[Workflow, str]:
    """
    创建理财默认工作流

    完整结构:
    start → message → end

    Returns:
        Workflow: 理财默认工作流实例
        str: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="baixin_default_1",
        version="0.6.0",
        description="默认工作流",
    )
    workflow = Workflow(workflow_card)

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

    message_conf = {
        "template": "这是默认工作流",
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.add_workflow_comp(
        "node_1746876027294",
        Message(message_conf),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    end_conf = {
        "responseTemplate": "默认工作流结束",
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    workflow.add_connection("node_start", "node_1746876027294")
    workflow.add_connection("node_1746876027294", "node_end")

    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_financial_default_workflow():
    """
    测试理财默认工作流
    """
    workflow, workflow_id = create_financial_default_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="默认流程",
        params={
            "global_variables": {
                "sys": {
                    "conversationHistory": [],
                    "currentTime": "2025-01-01",
                    "userId": "test_user",
                    "conversationId": "test-conversation-id",
                }
            }
        },
        workflow_id=workflow_id,
        session_id="test-session-id",
        agent_id=agent_id,
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)

    assert len(chunks) > 0, "应该收到至少一个输出chunk"
    workflow_logger.info(f"测试完成，共收到 {len(chunks)} 个chunks")
