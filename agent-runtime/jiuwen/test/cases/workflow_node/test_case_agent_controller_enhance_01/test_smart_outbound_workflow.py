"""
智能外呼工作流 (Smart Outbound Calling Workflow)

流程：开始 → 产品介绍消息节点 → 结束

支撑联调的替代方案：意图识别组件不影响工作流的流式输出，所以可以直接将消息节点作为工作流出口，输出固定文本。
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

workflow_id = "5ffdcfdc-0afe-4e08-b8e8-c6206c01115e"
agent_id = "302a1137-9d59-4c17-b9b6-b6674843c83e"


def create_smart_outbound_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建智能外呼工作流（支撑联调替代方案）

    结构: start -> product_intro -> end
    跳过意图识别节点，直接输出固定文本

    Returns:
        Workflow: 智能外呼工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="RemoteBankingIntelligentOutboundCalling_subflow",
        version="0.6.0",
        description="智能客服-智能理财例外场景",
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

    # 2. 配置意图识别节点
    intent_conf = {
        "branches": [
            {"catalog": "不确定，其他的意图", "id": "branch_0"},
            {"catalog": "介绍什么/申请什么", "id": "branch_1"},
            {"catalog": "起购金额是多少", "id": "branch_2"},
            {"catalog": "赎回时间", "id": "branch_3"},
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
        "chatHistoryMaxTurn": 7,
        "enableKnowledge": False,
        "enableHistory": True,
        "overridable": False,
        "enableInput": True,
        "prompt": "",
    }
    # 意图识别分支连接
    intent_component = IntentDetection(intent_conf)
    intent_component.add_branch(
        "${node_intent_detection.classificationId} == branch_0",
        ["node_end"],
        "branch_0",
    )
    intent_component.add_branch(
        "${node_intent_detection.classificationId} == branch_1",
        ["node_product_intro"],
        "branch_1",
    )
    intent_component.add_branch(
        "${node_intent_detection.classificationId} == branch_2",
        ["node_purchase_amount"],
        "branch_2",
    )
    intent_component.add_branch(
        "${node_intent_detection.classificationId} == branch_3",
        ["node_redemption_time"],
        "branch_3",
    )

    # workflow.add_workflow_comp(
    #     "node_intent_detection",
    #     intent_component,
    #     inputs_schema={"input": "${node_start.systemFields.query}"}
    # )

    # 3. 配置消息节点 - 产品介绍
    workflow.add_workflow_comp(
        "node_product_intro",
        Message(
            {
                "template": "本次来电是邀请您体验我行闲钱管理服务'大天盈'的。收益每日计算，1分起购，赎回最快实时到账，让您的闲钱不闲置，详情给您发条短信，您有空的时候了解下，可以吗"
            }
        ),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 4. 配置消息节点 - 起购金额
    workflow.add_workflow_comp(
        "node_purchase_amount",
        Message({"template": '"天天盈"的起购金额是1分钱，低风险，用取都很灵活'}),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 5. 配置消息节点 - 赎回时间
    workflow.add_workflow_comp(
        "node_redemption_time",
        Message({"template": '"天天盈"单日单只最高赎回最高1万块'}),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 6. 配置结束节点
    end_conf = {
        "responseTemplate": "【理财】工作流执行结束",
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"result": "${node_start.systemFields.query}"},
        response_mode="streaming" if is_streaming else "direct",
    )

    # 7. 添加连接（简化版）
    # workflow.add_connection("node_start", "node_intent_detection")
    # # 消息节点到结束节点
    # workflow.add_connection("node_product_intro", "node_end")
    # workflow.add_connection("node_purchase_amount", "node_end")
    # workflow.add_connection("node_redemption_time", "node_end")
    workflow.add_connection("node_start", "node_product_intro")
    workflow.add_connection("node_product_intro", "node_end")
    # 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_smart_outbound_workflow():
    """
    测试智能外呼工作流
    """
    workflow, workflow_id = create_smart_outbound_workflow()  # noqa: redefined-outer-name

    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="理财是什么",
        workflow_id=workflow_id,
        session_id="cae2c07b-2a13-4107-8c2b-d75e9af55b5f",
        agent_id=agent_id,
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)
