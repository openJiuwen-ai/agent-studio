"""
融e借工作流 (Rong Yi Jie Workflow)

流程：开始 → 提问器 → 意图识别 → (分支) → 消息节点 → 结束
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine.context.context import SessionModelContext
from openjiuwen.core.context_engine.schema.config import ContextEngineConfig
from openjiuwen.core.foundation.llm import BaseMessage
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

workflow_id = "666aea41-bec1-47a9-af29-590f19bc01dd"
agent_id = "302a1137-9d59-4c17-b9b6-b6674843c83e"


def _create_test_model_context(
    messages: list[BaseMessage] = None,
) -> SessionModelContext:
    """创建测试用的 ModelContext"""
    config = ContextEngineConfig(
        max_context_message_num=100,
        default_window_message_num=50,
    )
    return SessionModelContext(
        context_id="test-context",
        session_id="test-session",
        config=config,
        history_messages=messages or [],
        processors=[],
    )


def _mock_getenv(key: str, default=None):
    """Mock getenv 函数"""
    env_map = {
        "LLM_PROVIDER": "OpenAI",
        "LLM_API_KEY": "test-api-key",
        "LLM_API_BASE": "https://api.test.com",
        "LLM_MODEL_NAME": "test_model",
        "LLM_VERIFY_SSL": "False",
    }
    return env_map.get(key, default)


def create_rongEjie_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建融e借工作流

    结构: start -> questioner -> intent_detection -> (branch) -> message -> end

    Returns:
        Workflow: 融e借工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="ssq_ryj_1",
        version="0.6.0",
        description="融e借产品推荐，解决用户有关贷款的需求",
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

    # 2. 配置提问器节点
    questioner_conf = {
        "model_name": "mock_model_name",
        "model_type": "llm_SiliconFlow",
        "response_type": "reply_directly",
        "extract_fields_from_response": False,
        "with_chat_history": True,
        "chat_history_max_rounds": 0,
        "extra_prompt_for_fields_extraction": "",
        "question_content": "关注到您近期有用款需求，我行融e借个人信用贷款...不知道您是否感兴趣？\n我把产品信息及办理方式以短信形式发送给您？",
        "question_construction_method": "rule_based",
        "cn_fields_name": {},
        "max_response": 10,
        "option_content": [],
        "key_fields": [],
        "input_complement": False,
        "type_complement": "",
        "hyper_parameters": {"top_p": 0.5, "temperature": 0.2},
        "extension": {
            "deploymentId": "customer_chat_llm2.5-72b",
            "api_key": "mock-api-key-for-testing",
            "api_base": "https://api.siliconflow.cn/v1",
            "verify_ssl": False,
        },
        "prompt_template": None,
        "example_content": "",
        "rails_config": {},
        "accept_language": "zh",
    }

    workflow.add_workflow_comp(
        "node_questioner", Questioner(questioner_conf), inputs_schema={}
    )

    # 3. 配置意图识别节点
    intent_conf = {
        "branches": [
            {"catalog": "不确定，其他的意图", "id": "branch_0"},
            {"catalog": "用户表示感兴趣，有同意、动心等意向", "id": "branch_1"},
            {"catalog": "用户表示不感兴趣，有拒绝或排斥等倾向", "id": "branch_2"},
        ],
        "llm": {
            "model": {
                "modelName": "mock_model_name",
                "extension": {
                    "deploymentId": "customer_chat_llm2.5-72b",
                    "api_key": "mock-api-key-for-testing",
                    "api_base": "https://api.siliconflow.cn/v1",
                    "verify_ssl": False,
                },
                "hyperParameters": {"top_p": 0.5, "temperature": 0.5},
                "modelType": "OpenAI",
            }
        },
        "kg": {},
        "memory": {},
        "chatHistoryMaxTurn": 0,
        "enableKnowledge": False,
        "enableHistory": False,
        "overridable": False,
        "enableInput": True,
        "prompt": "",
    }

    intent_component = IntentDetection(intent_conf)
    intent_component.add_branch(
        "0 == ${node_intent_detection['classificationId']}",
        ["node_message_other"],
        "branch_0",
    )
    intent_component.add_branch(
        "1 == ${node_intent_detection['classificationId']}",
        ["node_message_interest"],
        "branch_1",
    )
    intent_component.add_branch(
        "2 == ${node_intent_detection['classificationId']}",
        ["node_message_not_interest"],
        "branch_2",
    )

    workflow.add_workflow_comp(
        "node_intent_detection",
        intent_component,
        inputs_schema={"input": "${node_questioner.user_response}"},
    )

    # 4. 配置消息节点 - 用户感兴趣
    workflow.add_workflow_comp(
        "node_message_interest",
        Message({"template": "好的，感谢您的信任！祝您生活愉快，再见。"}),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 5. 配置消息节点 - 用户不感兴趣
    workflow.add_workflow_comp(
        "node_message_not_interest",
        Message({"template": "抱歉打扰您了，祝您生活愉快，再见。"}),
        inputs_schema={},
    )

    # 6. 配置消息节点 - 不确定/其他意图
    workflow.add_workflow_comp(
        "node_message_other",
        Message({"template": "谁说用户没有其他意图"}),
        inputs_schema={},
    )

    # 7. 配置结束节点
    end_conf = {
        "responseTemplate": "ssq_融e借产品推荐_1--结束",
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={},
        response_mode="streaming" if is_streaming else "direct",
    )

    # 8. 添加连接
    workflow.add_connection("node_start", "node_questioner")
    workflow.add_connection("node_questioner", "node_intent_detection")

    # 消息节点到结束节点
    workflow.add_connection("node_message_interest", "node_end")
    workflow.add_connection("node_message_not_interest", "node_end")
    workflow.add_connection("node_message_other", "node_end")

    # 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
@patch("jiuwen.extension.workflow_node.questioner.Model")
@patch("jiuwen.extension.workflow_node.questioner.os.getenv")
@patch.object(IntentDetection, "_get_llm_instance")
async def test_rongyijie_workflow_with_wrapper(
    mock_get_llm_instance, mock_getenv, mock_model_class
):
    """
    测试融e借工作流（使用 WorkflowWrapper）

    使用真实 Questioner，Mock LLM 让意图识别组件识别为 branch_0（不确定，其他的意图）
    """
    mock_getenv.side_effect = _mock_getenv

    mock_questioner_model = AsyncMock()
    mock_questioner_result = MagicMock()
    mock_questioner_result.content = '{"user_response": "我不知道你在说什么"}'
    mock_questioner_result.usage_metadata = None
    mock_questioner_model.invoke = AsyncMock(return_value=mock_questioner_result)
    mock_model_class.return_value = mock_questioner_model

    mock_intent_llm = AsyncMock()
    mock_intent_result = MagicMock()
    mock_intent_result.content = (
        '{"class": "分类0", "reason": "用户表示不确定，属于其他意图"}'
    )
    mock_intent_result.usage_metadata = None
    mock_intent_llm.invoke = AsyncMock(return_value=mock_intent_result)
    mock_get_llm_instance.return_value = mock_intent_llm

    workflow, workflow_id = create_rongEjie_workflow()  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="我不知道你在说什么",
        workflow_id=workflow_id,
        session_id="cae2c07b-2a13-4107-8c2b-d75e9af55b5f",
        agent_id=agent_id,
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)

    assert len(chunks) > 0
