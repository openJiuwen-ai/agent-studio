"""
查询信用卡账单工作流

完整流程：
开始 → flow_api → 结束

使用 FlowApi 组件替代原始的 plugin 组件，调用查询信用卡账单的 API。
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

workflow_id = "workflow_plugin_query_bill"
agent_id = "test_agent_id"


def create_query_bill_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建查询信用卡账单工作流

    完整结构:
    start -> flow_api -> end

    Returns:
        Workflow: 查询信用卡账单工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="workflow_plugin_query_bill",
        version="0.6.0",
        description="查询信用卡账单",
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

    # FlowApi 节点配置（替代原始的 plugin 组件）
    flow_api_conf = {
        "id": "plugin11112",
        "name": "plugin_query_bill",
        "description": "plugin_query_bill",
        "url": "http://fakeIp:5003/query_bill",
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
                    "description": "欠款",
                    "schema": [
                        {"id": "bill_id", "type": "String", "description": "账单ID"},
                        {"id": "amount", "type": "String", "description": "欠款"},
                        {"id": "due_date", "type": "String", "description": "逾期时间"},
                    ],
                }
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
        "exceptionEnable": True,
        "exceptionSuppression": '{"data": {"bill_id": "123456", "amount": "5000.00", "due_date": "2026-05-31"}}',
    }

    workflow.add_workflow_comp(
        "node_plugin",
        FlowApi(flow_api_conf),
        inputs_schema={"card_id": "${node_start.userFields.card_id}"},
    )

    # 结束节点配置
    end_conf = {
        "responseTemplate": "信用卡账单金额为：{{amount}}，信用卡id为：{{card_id}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "账单ID",
                    "id": "bill_id",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "欠款",
                    "id": "amount",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "逾期时间",
                    "id": "due_date",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "信用卡ID",
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "账单ID",
                    "id": "bill_id",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "信用卡账单",
                    "id": "amount",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "逾期时间",
                    "id": "due_date",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "信用卡ID",
                    "id": "card_id",
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
            "bill_id": "${node_plugin.userFields.data.bill_id}",
            "amount": "${node_plugin.userFields.data.amount}",
            "due_date": "${node_plugin.userFields.data.due_date}",
            "card_id": "${node_start.userFields.card_id}",
        },
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_plugin")
    workflow.add_connection("node_plugin", "node_end")

    # 注册工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_query_bill_workflow():
    """
    测试查询信用卡账单工作流
    """
    workflow, workflow_id = create_query_bill_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []
    workflow_logger.info("=" * 50)
    workflow_logger.info("请求：查询信用卡账单")
    workflow_logger.info("=" * 50)

    async for chunk in workflow_wrapper.astream(
        query="",
        params={
            "global_variables": {
                "card_id": "777666",
                "query": "查询信用卡账单",
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
        chunks.append(chunk)
        workflow_logger.info(chunk)

    # 验证请求结果：工作流应该完成
    assert len(chunks) > 0
    workflow_logger.info(f"请求完成，共收到 {len(chunks)} 个chunk")

    return chunks
