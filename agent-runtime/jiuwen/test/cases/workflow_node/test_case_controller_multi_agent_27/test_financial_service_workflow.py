"""
理财服务工作流 (Financial Service Workflow)

完整流程：
开始 → 提问器 → 消息 → 结束
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

workflow_id = "ad21cfff-e864-4af8-be97-2e3fe605322c"
agent_id = "e21b261d-3792-4942-873b-b3b6fef29537"


def create_financial_service_workflow(
    is_streaming: bool = True,
) -> tuple[Workflow, str]:
    """
    创建理财服务工作流

    完整结构：
    start → questioner → message → end

    Returns:
        Workflow: 理财服务工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="test_finacial",
        version="0.6.0",
        description="test_finacial",
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

    questioner_conf = {
        "question_content": "请问你要赎回哪一笔理财？1.xxx 2.xxx\n",
        "model_name": "mock_model",
        "model_type": "Mock",
        "with_chat_history": True,
        "extra_prompt_for_fields_extraction": "",
        "input_complement": False,
        "type_complement": "",
        "example_content": "",
        "rails_config": {},
        "extract_fields_from_response": False,
        "max_response": 10,
        "hyper_parameters": {"temperature": 0.2},
    }

    workflow.add_workflow_comp(
        "node_1756177438288", Questioner(questioner_conf), inputs_schema={}
    )

    message_conf = {
        "template": "好的，赎回成功，已实时到账。\n\n\n",
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.add_workflow_comp(
        "node_1756177475544",
        Message(message_conf),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    end_conf = {
        "response_mode": "directResponse",
        "response_template": " ",
        "is_stream_out": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    workflow.add_connection("node_start", "node_1756177438288")
    workflow.add_connection("node_1756177438288", "node_1756177475544")
    workflow.add_connection("node_1756177475544", "node_end")

    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_financial_service_workflow():
    """
    测试理财服务工作流
    """
    workflow, workflow_id = create_financial_service_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    async for chunk in workflow_wrapper.astream(
        query="我要赎回理财",
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
        chunks_1.append(chunk)
        workflow_logger.info(chunk)

    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：序号1")
    workflow_logger.info("=" * 50)
    # 从第一次请求的 chunks 中提取中断节点的 node_id
    interrupt_node_id = None
    for chunk in chunks_1:
        if (
            hasattr(chunk, "data")
            and isinstance(chunk.data, dict)
            and chunk.data.get("should_interrupt", False)
        ):
            interrupt_node_id = chunk.data.get("node_id")
            break
    assert interrupt_node_id is not None, "未找到中断节点的 node_id"

    # 构建中断恢复的 InteractiveInput，精确路由到中断节点
    resume_input = InteractiveInput()
    resume_input.update(interrupt_node_id, "序号1")
    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []
    async for chunk in workflow_wrapper_resume.astream(
        query=resume_input,
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
        chunks_2.append(chunk)
        workflow_logger.info(chunk)

    # 验证第二次请求结果：工作流应该完成
    assert len(chunks_2) > 0
    workflow_logger.info(f"第二次请求完成，共收到 {len(chunks_2)} 个chunk")

    return chunks_1, chunks_2
