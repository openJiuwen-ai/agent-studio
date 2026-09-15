"""
理财开始工作流 (Start Workflow - 多级)

完整流程：
开始 → 消息 → 结束
"""

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

workflow_id = "32964224-6644-4483-94ae-40d1c8532c52"
agent_id = "e21b261d-3792-4942-873b-b3b6fef29537"


def create_start_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建理财开始工作流

    完整结构：
    start → message → end

    Returns:
        Workflow: 理财开始工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="ssq_start_1",
        version="0.6.0",
        description="开始工作流-多级",
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
        "preDefinedFields": {
            "inputs": [
                {
                    "schema": [],
                    "sourceType": "null",
                    "description": None,
                    "id": "memory",
                    "type": "object",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "schema": [],
                    "sourceType": "null",
                    "description": None,
                    "id": "memory",
                    "type": "object",
                    "required": True,
                }
            ],
        },
    }

    workflow.set_start_comp("node_start", Start(start_conf), inputs_schema={})

    message_conf = {
        "template": "【开始工作流】{{query}}\n开始工作流开始",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "",
                    "id": "name",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.add_workflow_comp(
        "node_1747275741185",
        Message(message_conf),
        inputs_schema={
            "userFields": {"query": "${node_start.systemFields.query}", "name": "None"}
        },
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    end_conf = {
        "response_mode": "directResponse",
        "response_template": "【开始工作流-结束节点】{{result}}",
        "is_stream_out": True,
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
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"result": "${node_start.systemFields.query}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    workflow.add_connection("node_start", "node_1747275741185")
    workflow.add_connection("node_1747275741185", "node_end")

    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_start_workflow():
    """
    测试理财开始工作流
    """
    workflow, workflow_id = create_start_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="测试开始工作流",
        params={
            "global_variables": {
                "sys": {
                    "conversationHistory": [],
                    "currentTime": "2026-04-23",
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
