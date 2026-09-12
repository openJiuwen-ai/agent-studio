"""
理财开始工作流

完整流程:
开始 → 提问器 → 结束
"""

import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")
os.environ.setdefault("LLM_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("LLM_VERIFY_SSL", "False")

workflow_id = "c85266d9-8605-4ecb-9f47-473075196366"
agent_id = "e21b261d-3792-4942-873b-b3b6fef29537"


def create_financial_start_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建理财开始工作流

    完整结构:
    start → questioner → end

    Returns:
        Workflow: 理财开始工作流实例
        str: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="ssq_start_1_1",
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
    }

    workflow.set_start_comp("node_start", Start(start_conf), inputs_schema={})

    questioner_conf = {
        "model_name": "mock_model",
        "model_type": "Mock",
        "hyper_parameters": {"top_p": 0.5, "max_tokens": 2048, "temperature": 0.2},
        "question_content": "请问是本人吗",
        "with_chat_history": True,
        "extract_fields_from_response": True,
        "max_response": 10,
    }

    workflow.add_workflow_comp(
        "node_1756539749802", Questioner(questioner_conf), inputs_schema={}
    )

    end_conf = {
        "responseTemplate": "【开始工作流-结束节点】{{result}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"result": "${node_start.systemFields.query}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    workflow.add_connection("node_start", "node_1756539749802")
    workflow.add_connection("node_1756539749802", "node_end")

    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_financial_start_workflow():
    """
    测试理财开始工作流
    """
    workflow, workflow_id = create_financial_start_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks1 = []
    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：我要赎回理财")
    workflow_logger.info("=" * 50)
    async for chunk in workflow_wrapper.astream(
        query="我要赎回理财",
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
        chunks1.append(chunk)
        workflow_logger.info(chunk)

    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：是本人")
    workflow_logger.info("=" * 50)
    # 从第一次请求的中断 chunk 中提取 node_id
    interrupt_node_id = None
    for chunk in chunks1:
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
    resume_input.update(interrupt_node_id, "是本人")
    workflow_wrapper_resume = WorkflowWrapper()
    chunks2 = []
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
        chunks2.append(chunk)
        workflow_logger.info(chunk)

    # 验证第二次请求结果：工作流应该完成
    assert len(chunks2) > 0
    workflow_logger.info(f"第二次请求完成，共收到 {len(chunks2)} 个chunk")
