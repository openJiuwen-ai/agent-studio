"""
信用卡还款工作流

完整流程：
开始 → 提问器 → flow_api → 结束

使用 FlowApi 组件替代原始的 plugin 组件，调用信用卡还款的 API。
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

workflow_id = "workflow_plugin_repay_credit"
agent_id = "test_agent_id"


def create_repay_credit_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建信用卡还款工作流

    完整结构:
    start -> questioner -> flow_api -> end

    Returns:
        Workflow: 信用卡还款工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="workflow_plugin_repay_credit",
        version="0.6.0",
        description="信用卡还款",
    )
    workflow = Workflow(workflow_card)

    # 开始节点配置
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "信用卡ID",
                    "default_value": "",
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "信用卡ID",
                    "default_value": "",
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                }
            ],
        },
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
        },
    }

    workflow.set_start_comp(
        "node_start", Start(start_conf), inputs_schema={"card_id": "", "query": ""}
    )

    # 提问器节点配置
    questioner_conf = {
        "model_name": "mock_model",
        "model_type": "Mock",
        "name": "提问器",
        "question_content": "确认还款嘛？",
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
        "node_questioner", Questioner(questioner_conf), inputs_schema={}
    )

    # FlowApi 节点配置（替代原始的 plugin 组件）
    flow_api_conf = {
        "id": "plugin11112",
        "name": "plugin_repay_credit",
        "description": "plugin_repay_credit",
        "url": "http://fakeIp:5003/repay_credit",
        "method": "POST",
        "auth": {},
        "arguments": [
            {
                "name": "card_id",
                "description": "信用卡ID",
                "type": "String",
                "method": "Body",
                "required": True,
                "defaultValue": "",
            }
        ],
        "pluginDependency": {
            "paramsWrapper": {"inputList": False, "outputList": False},
            "hook_function": {},
        },
        "response": [],
        "userFields": {
            "inputs": [
                {
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                }
            ],
            "outputs": [
                {
                    "id": "data",
                    "type": "Object",
                    "description": "还款结果",
                    "schema": [
                        {"id": "card_id", "type": "String", "description": "还款id"},
                        {"id": "status", "type": "String", "description": "还款结果"},
                    ],
                }
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
        "exceptionEnable": True,
        "exceptionSuppression": '{"data": {"card_id": "777666", "status": "success"}}',
    }

    workflow.add_workflow_comp(
        "node_plugin", FlowApi(flow_api_conf), inputs_schema={"card_id": "777666"}
    )

    # 结束节点配置
    end_conf = {
        "responseTemplate": "还款成功：{{status}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "信用卡ID",
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "是否成功",
                    "id": "status",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "信用卡ID",
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "是否成功",
                    "id": "status",
                    "type": "string",
                    "required": True,
                },
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={
            "card_id": "${node_plugin.userFields.data.card_id}",
            "status": "${node_plugin.userFields.data.status}",
        },
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_questioner")
    workflow.add_connection("node_questioner", "node_plugin")
    workflow.add_connection("node_plugin", "node_end")

    # 注册工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_repay_credit_workflow():
    """
    测试信用卡还款工作流
    """
    workflow, workflow_id = create_repay_credit_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []
    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：启动工作流")
    workflow_logger.info("=" * 50)

    # 第一次请求：启动工作流，应该触发提问器
    async for chunk in workflow_wrapper.astream(
        query="",
        params={
            "global_variables": {
                "card_id": "777666",
                "query": "还款",
                "sys": {
                    "conversationHistory": [],
                    "currentTime": "2024-01-01",
                    "userId": "test_user",
                    "conversationId": "test_conversation_id",
                },
            }
        },
        workflow_id=workflow_id,
        session_id="test_session_id",
        agent_id=agent_id,
    ):
        chunks_1.append(chunk)
        workflow_logger.info(chunk)

    # 验证第一次请求结果：提问器应该中断
    assert len(chunks_1) > 0
    # 检查是否有中断信号
    has_interrupt = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_1
    )
    workflow_logger.info(f"第一次请求是否中断: {has_interrupt}")
    assert has_interrupt is True

    # ==================== 第二次请求：确认还款 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：确认还款")
    workflow_logger.info("=" * 50)

    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []

    # 构建对话历史
    conversation_history = [
        {"role": "user", "content": "还款", "intent": [workflow_id]},
        {"role": "assistant", "content": "确认还款嘛？", "intent": [workflow_id]},
    ]

    params_2 = {
        "global_variables": {
            "card_id": "777666",
            "query": "确认",
            "sys": {
                "conversationHistory": conversation_history,
                "currentTime": "2024-01-01",
                "userId": "test_user",
                "conversationId": "test_conversation_id",
            },
        },
        "conversation_history": conversation_history,
        "CONTROLLER_MODE_SWITCH": True,
    }

    # 从第一次请求的中断 chunk 中提取 node_id
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
    resume_input.update(interrupt_node_id, "确认")

    async for chunk in workflow_wrapper_resume.astream(
        query=resume_input,
        params=params_2,
        workflow_id=workflow_id,
        session_id="test_session_id",
        agent_id=agent_id,
    ):
        chunks_2.append(chunk)
        workflow_logger.info(chunk)

    # 验证第二次请求结果：工作流应该完成
    assert len(chunks_2) > 0
    workflow_logger.info(f"第二次请求完成，共收到 {len(chunks_2)} 个chunk")

    return chunks_1, chunks_2
