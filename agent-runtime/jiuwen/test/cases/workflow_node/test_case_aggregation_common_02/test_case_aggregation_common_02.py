"""
聚合工作流 (Aggregation Workflow - 1组1参数)

完整流程：
开始 → 变量聚合 → 结束

使用 openjiuwen 工作流框架实现，基于 extension/workflow_node 组件。
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_aggregate import Aggregate
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

workflow_id = "4af0ad3e-fae7-4b0b-8618-d9f8bbffc61c"
agent_id = "mock-agent-id"


def create_aggregation_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建聚合工作流

    完整结构:
    start → aggregation → end

    Returns:
        Workflow: 聚合工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id, name="zcm0717", version="0.6.0", description="1"
    )
    workflow = Workflow(workflow_card)

    # 1. 开始节点
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "param1",
                    "default_value": "",
                    "id": "param1",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "param1",
                    "default_value": "",
                    "id": "param1",
                    "type": "string",
                    "required": True,
                }
            ],
        },
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
                            "description": "工作流对话ID",
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
                            "description": "工作流对话ID",
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
    start = Start(start_conf)
    workflow.set_start_comp("node_start", start, inputs_schema={"param1": ""})

    # 2. 变量聚合节点
    aggregation_conf = {
        "mode": "first-non-null",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "group1_1",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "",
                    "id": "group1",
                    "type": "string",
                    "required": True,
                }
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
        "groups": {"group1": ["group1_1"]},
    }
    aggregation = Aggregate(aggregation_conf)
    workflow.add_workflow_comp(
        "node_aggregation",
        aggregation,
        inputs_schema={"group1_1": "${node_start.userFields.param1}"},
    )

    # 3. 结束节点
    end_conf = {
        "responseMode": "directResponse",
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
        "responseTemplate": "变量聚合组件输出：{{result}}",
        "systemFields": {"inputs": [], "outputs": []},
        "isStreamOut": True,
    }
    end = End(end_conf)
    workflow.set_end_comp(
        "node_end",
        end,
        inputs_schema={"result": "${node_aggregation.userFields.group1}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 建立连接
    workflow.add_connection("node_start", "node_aggregation")
    workflow.add_connection("node_aggregation", "node_end")

    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_aggregation_workflow():
    """测试聚合工作流"""
    # 创建工作流
    workflow, workflow_id = create_aggregation_workflow()  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []
    async for chunk in workflow_wrapper.astream(
        query="你好",
        params={"global_variables": {"param1": "嗨"}},
        workflow_id=workflow_id,
        session_id="df461690-ee3c-4655-aba0-4d8e2c75c6c7",
        agent_id=agent_id,
    ):
        chunks_1.append(chunk)
        workflow_logger.info(chunk)
