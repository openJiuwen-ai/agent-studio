"""
转账工作流

完整流程：
开始 → flow_api → 结束

使用 FlowApi 组件替代原始的 plugin 组件，调用转账的 API。
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

workflow_id = "workflow_plugin_transfer"
agent_id = "test_agent_id"


def create_transfer_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建转账工作流

    完整结构:
    start -> flow_api -> end

    Returns:
        Workflow: 转账工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="workflow_plugin_transfer",
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
                    "description": "转出账户",
                    "default_value": "",
                    "id": "from_account",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "转入账户",
                    "default_value": "",
                    "id": "to_account",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "转账金额",
                    "default_value": 0.0,
                    "id": "amount",
                    "type": "number",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "转出账户",
                    "default_value": "",
                    "id": "from_account",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "转入账户",
                    "default_value": "",
                    "id": "to_account",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "转账金额",
                    "default_value": 0.0,
                    "id": "amount",
                    "type": "number",
                    "required": True,
                },
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
        "node_start",
        Start(start_conf),
        inputs_schema={
            "from_account": "",
            "to_account": "",
            "amount": 0.0,
            "query": "",
        },
    )

    # FlowApi 节点配置（替代原始的 plugin 组件）
    flow_api_conf = {
        "id": "plugin11112",
        "name": "plugin_transfer",
        "description": "plugin_transfer",
        "url": "http://fakeIp:5003/transfer2",
        "method": "POST",
        "auth": {},
        "arguments": [
            {
                "name": "from_account",
                "description": "转出账户",
                "type": "String",
                "method": "Body",
                "required": True,
                "defaultValue": "",
            },
            {
                "name": "to_account",
                "description": "转入账户",
                "type": "String",
                "method": "Body",
                "required": True,
                "defaultValue": "",
            },
            {
                "name": "amount",
                "description": "转账金额",
                "type": "Number",
                "method": "Body",
                "required": True,
                "defaultValue": "",
            },
        ],
        "pluginDependency": {
            "paramsWrapper": {"inputList": False, "outputList": False},
            "hook_function": {},
        },
        "response": [],
        "userFields": {
            "inputs": [
                {
                    "id": "from_account",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                },
                {
                    "id": "to_account",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                },
                {
                    "id": "amount",
                    "type": "number",
                    "required": True,
                    "sourceType": "ref",
                },
            ],
            "outputs": [
                {
                    "id": "data",
                    "type": "Object",
                    "description": "是否成功",
                    "schema": [
                        {"id": "status", "type": "String", "description": "是否成功"}
                    ],
                }
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
        "exceptionEnable": True,
        "exceptionSuppression": '{"data": {"status": "success"}}',
    }

    workflow.add_workflow_comp(
        "node_plugin",
        FlowApi(flow_api_conf),
        inputs_schema={
            "from_account": "${node_start.userFields.from_account}",
            "to_account": "${node_start.userFields.to_account}",
            "amount": "${node_start.userFields.amount}",
        },
    )

    # 结束节点配置
    end_conf = {
        "responseTemplate": "转账成功：{{status}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "是否成功",
                    "id": "status",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "是否成功",
                    "id": "status",
                    "type": "string",
                    "required": True,
                }
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"status": "${node_plugin.userFields.data.status}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_plugin")
    workflow.add_connection("node_plugin", "node_end")

    # 注册工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_transfer_workflow():
    """
    测试转账工作流
    """
    workflow, workflow_id = create_transfer_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []
    workflow_logger.info("=" * 50)
    workflow_logger.info("请求：转账")
    workflow_logger.info("=" * 50)

    async for chunk in workflow_wrapper.astream(
        query="根据账户余额是否充足，选择执行转账或还款操作",
        params={
            "global_variables": {
                "from_account": "555444",
                "to_account": "999888",
                "amount": 200.0,
                "query": "转账",
                "sys": {
                    "conversationHistory": [
                        {
                            "role": "user",
                            "content": "帮我还一下信用卡，信用卡ID是123456",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": None,
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "assistant",
                            "content": "[STEP_DONE]",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": None,
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "user",
                            "content": "账户ID是777666",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": [
                                "workflow_plugin_query_account",
                                "workflow_plugin_transfer",
                            ],
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "tool",
                            "content": "账户id为：777666，账户余额为：200.0",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": ["workflow_plugin_query_account"],
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "assistant",
                            "content": "[STEP_DONE]",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": None,
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "assistant",
                            "content": "转账成功：success",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": None,
                            "enable_history": True,
                            "agent_id": None,
                        },
                    ],
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
