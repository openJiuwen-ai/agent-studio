# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
升金有礼工作流实现

使用开源openjiuwen的工作流框架，基于mock输出实现升金有礼工作流。

参考 start_workflow.py 的结构，使用 Workflow 类的高级 API 来构建工作流。
"""

import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility
from openjiuwen.core.workflow.components.flow.branch_comp import (
    BranchComponent as Branch,
)

# 设置环境变量
os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")
os.environ.setdefault("LLM_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("LLM_VERIFY_SSL", "False")

# 工作流配置
workflow_id = "875aeb56-1cd4-404c-9ef9-220c073f2e30"
agent_id = "d4c90802-9243-4667-aaaa-e7ace9985b29"
workflow_name = "ShengjinyouliAgent517_1_1_1"


def create_shengjin_youli_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建升金有礼工作流

    code 组件已规避，使用消息节点模拟

    Returns:
        Workflow: 升金有礼工作流实例
        str: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="ShengjinyouliAgent517_1_1_1",
        version="0.6.0",
        description="升金有礼子agent-517_bgc",
    )
    workflow = Workflow(workflow_card)

    # 1. 配置开始节点
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "客户ID",
                    "default_value": "",
                    "id": "dataId",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "活动日期",
                    "default_value": "",
                    "id": "ActivityTime",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "xxx",
                    "default_value": "false",
                    "id": "continue",
                    "type": "boolean",
                    "required": True,
                },
            ]
        }
    }

    workflow.set_start_comp(
        "node_start",
        Start(start_conf),
        inputs_schema={
            "dataId": "test_data_id",
            "ActivityTime": "123",
            "continue": True,
        },
    )

    # 2. 配置判断节点
    branch_component = Branch()
    branch_component.add_branch(
        "${node_start.userFields.continue} == True",
        ["node_1747212048020"],
        "node_1747668528371-if",
    )
    branch_component.add_branch(
        "${node_start.userFields.continue} == False",
        ["node_1752722695722"],
        "node_1747668528371-default",
    )
    workflow.add_workflow_comp("node_1747668528371", branch_component, inputs_schema={})

    # 3. 配置开场白-首轮澄清（消息节点）
    message_conf_1 = {
        "template": "#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出"
        "升金有礼"
        "积分回馈活动，即日起至{{ActivityTime}}，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，我现在把活动短信发给您，好吗？",
        "name": "开场白-首轮澄清",
    }

    workflow.add_workflow_comp(
        "node_1747212048020",
        Message(message_conf_1),
        inputs_schema={"ActivityTime": "${node_start.userFields.ActivityTime}"},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 4. 配置开场白-提问器（提问者节点）
    questioner_conf = {
        "model_name": "mock_model",
        "model_type": "Mock",
        "hyper_parameters": {"temperature": 0.2},
        "question_content": "##",
        "with_chat_history": True,
        "extract_fields_from_response": False,
        "max_response": 3,
    }

    workflow.add_workflow_comp(
        "node_1747212899505", Questioner(questioner_conf), inputs_schema={"query": ""}
    )

    # 5. 配置意图识别
    intent_detection_conf = {
        "userFields": {"inputs": [], "outputs": []},
        "recallThreshold": 0.8,
        "chatHistoryMaxTurn": 0,
        "systemFields": {"inputs": [], "outputs": []},
        "enableKnowledge": False,
        "enableHistory": False,
        "overridable": False,
        "enableInput": True,
        "kg": {},
        "llm": {
            "model": {
                "modelName": "mock-model",
                "modelType": "Mock",
                "hyperParameters": {"temperature": 0.2},
                "extension": {
                    "api_key": "mock-api-key",
                    "api_base": "http://localhost:8080",
                },
            }
        },
        "branches": [
            {"catalog": "不确定，其他的意图", "id": "branch_0"},
            {"catalog": "感兴趣", "id": "branch_1"},
        ],
        "prompt": "你是一个功能分类器，你可以根据用户的请求提问，和相应的功能类别描述，选择正确的功能帮助用户解决问题。",
    }

    intent_component = IntentDetection(intent_detection_conf)
    intent_component.add_branch(
        "${node_1747637209846.classificationId} == 1",
        ["node_1747293876339"],
        "node_1747637209846_branch_1",
    )
    intent_component.add_branch(
        "${node_1747637209846.classificationId} == 0",
        ["node_1747293733349"],
        "node_1747637209846_branch_0",
    )

    workflow.add_workflow_comp(
        "node_1747637209846",
        intent_component,
        inputs_schema={"input": "${node_1747212899505.userFields.USER_RESPONSE}"},
    )

    # 6. 配置发短息（消息节点）
    message_conf_sms = {"template": " ##内部系统插件，发短信##", "name": "发短息"}

    workflow.add_workflow_comp(
        "node_1747293876339",
        Message(message_conf_sms),
        inputs_schema={"code": "${node_start.userFields.dataId}"},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 7. 配置成功结束（消息节点）
    message_conf_success = {
        "template": "#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！",
        "name": "成功结束",
    }

    workflow.add_workflow_comp(
        "node_1747293794534",
        Message(message_conf_success),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 8. 配置拒绝结束（消息节点）
    message_conf_reject = {
        "template": "#BDD#,#GD#/好的，如有需要，您可随时登录银行APP，关注其他活动。那就先不打扰您了，祝您生活愉快，再见！",
        "name": "拒绝结束",
    }

    workflow.add_workflow_comp(
        "node_1747293733349",
        Message(message_conf_reject),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 9. 代码节点1（使用消息节点模拟）
    message_conf_code1 = {"template": "代码执行: continue=True", "name": "代码"}

    workflow.add_workflow_comp(
        "node_1747668619198", Message(message_conf_code1), inputs_schema={}
    )

    # 10. 代码节点2（使用消息节点模拟）
    message_conf_code2 = {"template": "代码执行: continue=False", "name": "代码_2"}

    workflow.add_workflow_comp(
        "node_1752722695722", Message(message_conf_code2), inputs_schema={}
    )

    # 11. 代码节点3（使用消息节点模拟）
    message_conf_code3 = {
        "template": "代码执行: action_after_completion=Terminal",
        "name": "代码_1",
    }

    workflow.add_workflow_comp(
        "node_1752658921767", Message(message_conf_code3), inputs_schema={}
    )

    # 12. 配置结束节点
    end_conf = {
        "responseTemplate": "##升金结束continue: {{temp}}。action_after_completion：{{action_after_completion}}",
        "name": "结束",
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={
            "temp": False,
            "action_after_completion": "Terminal",
            "#end_continue": False,
            "#end_action_after_completion": "Terminal",
        },
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_1747668528371")
    workflow.add_connection("node_1747212048020", "node_1747212899505")
    workflow.add_connection("node_1747212899505", "node_1747637209846")
    workflow.add_connection("node_1747293876339", "node_1747293794534")
    workflow.add_connection("node_1747293794534", "node_1752658921767")
    workflow.add_connection("node_1747293733349", "node_1747668619198")
    workflow.add_connection("node_1747668619198", "node_1752722695722")
    workflow.add_connection("node_1752658921767", "node_1752722695722")
    workflow.add_connection("node_1752722695722", "node_end")

    # 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_shengjin_youli_workflow():
    """
    测试升金有礼工作流

    测试工作流的创建和基本功能
    """
    workflow, workflow_id = create_shengjin_youli_workflow(True)  # noqa: redefined-outer-name
    session_id = "11fdd50a-dd8a-43de-934c-1b2661f80fde"

    # ==================== 第一次请求：我要买升金 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：我要买升金")
    workflow_logger.info("=" * 50)

    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    # 模拟 Handler 的 prepare_workflow_params() 传入的参数：
    # conversation_history 由 Handler 从 context_manager 获取（包含 intent），CONTROLLER_MODE_SWITCH=True
    params_1 = {
        "global_variables": {
            "dataId": "test_data_id",
            "ActivityTime": "123",
            "continue": True,
            "sys": {
                "conversationHistory": [],
                "currentTime": "2024-01-01",
                "userId": "test_user",
                "conversationId": session_id,
            },
        },
        "conversation_history": [
            {"role": "user", "content": "我要买升金", "intent": [workflow_name]}
        ],
        "CONTROLLER_MODE_SWITCH": True,
    }

    async for chunk in workflow_wrapper.astream(
        query="我要买升金",
        params=params_1,
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
    ):
        chunks_1.append(chunk)
        workflow_logger.info(chunk)

    # 验证第一次请求结果：提问器应该中断
    assert len(chunks_1) > 0
    has_interrupt = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_1
    )
    workflow_logger.info(f"第一次请求是否中断: {has_interrupt}")
    assert has_interrupt is True

    # ==================== 第二次请求：升金感兴趣 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：升金感兴趣")
    workflow_logger.info("=" * 50)

    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []

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

    # 构建对话历史，包含第一次的交互（模拟 Handler 从 context_manager 获取的带 intent 历史）
    conversation_history = [
        {"role": "user", "content": "我要买升金", "intent": [workflow_name]},
        {
            "role": "assistant",
            "content": "#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出"
            "升金有礼"
            "积分回馈活动，即日起至123，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，我现在把活动短信发给您，好吗？",
            "intent": [workflow_name],
        },
        {"role": "assistant", "content": "##", "intent": [workflow_name]},
        {"role": "user", "content": "升金感兴趣", "intent": [workflow_name]},
    ]

    params_2 = {
        "global_variables": {
            "dataId": "test_data_id",
            "ActivityTime": "123",
            "continue": True,
            "sys": {
                "conversationHistory": conversation_history,
                "currentTime": "2024-01-01",
                "userId": "test_user",
                "conversationId": session_id,
            },
        },
        "conversation_history": conversation_history,
        "CONTROLLER_MODE_SWITCH": True,
    }

    # 构建中断恢复的 InteractiveInput，精确路由到中断节点
    resume_input = InteractiveInput()
    resume_input.update(interrupt_node_id, "升金感兴趣")

    async for chunk in workflow_wrapper_resume.astream(
        query=resume_input,
        params=params_2,
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
    ):
        chunks_2.append(chunk)
        workflow_logger.info(chunk)

    # 验证第二次请求结果
    assert len(chunks_2) > 0
    workflow_logger.info(f"第二次请求完成，共收到 {len(chunks_2)} 个chunk")

    return chunks_1, chunks_2


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_shengjin_youli_workflow())
