# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
父工作流 - 查询账单

根据 workflow/parent_workflow_query_bill.json 配置实现的父工作流，
使用 openjiuwen 工作流框架。

流程：
开始 → 子工作流 → 结束
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.test.cases.workflow_node.test_case_controller_plan_execute_common_01.test_query_bill_workflow import (
    create_query_bill_workflow,
)
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow, WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

workflow_id = "parent_workflow_plugin_query_bill"
agent_id = "parent_workflow_plugin_query_bill_agent"


def create_parent_query_bill_workflow(
    is_streaming: bool = True, sub_workflow_instance=None
) -> tuple[Workflow, str]:
    """
    创建父工作流 - 查询账单

    流程结构:
    start → workflowComposite → end

    Args:
        is_streaming: 是否启用流式输出
        sub_workflow_instance: 子工作流实例

    Returns:
        tuple[Workflow, str]: 工作流实例和工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="parent_workflow_plugin_query_bill",
        version="0.6.0",
        description="父工作流 - 查询账单",
    )
    workflow = Workflow(workflow_card)
    sub_workflow_instance, _ = create_query_bill_workflow(True)
    # 开始节点配置
    start_conf = {
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
                    "id": "card_id",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                }
            ],
        },
        "systemFields": {
            "inputs": [
                {"id": "query", "type": "string", "required": True, "sourceType": "ref"}
            ],
            "outputs": [{"id": "query", "type": "string", "description": "用户输入"}],
        },
    }

    workflow.set_start_comp(
        "node_start", Start(start_conf), inputs_schema={"card_id": "", "query": ""}
    )

    # 子工作流节点配置
    sub_workflow_conf = {
        "systemFields": {
            "inputs": [
                {
                    "id": "query",
                    "type": "String",
                    "description": "用户Query",
                    "sourceType": "ref",
                }
            ]
        },
        "userFields": {
            "inputs": [
                {
                    "id": "card_id",
                    "type": "String",
                    "description": "用户Query",
                    "sourceType": "ref",
                }
            ]
        },
        "preDefineFields": {"outputs": [{"id": "responseContent", "type": "String"}]},
        "reference": {
            "id": "workflow_plugin_query_bill",
            "path": "workflow_query_bill.json",
        },
        "node_id": "node_workflowComposite",
    }

    # 创建 SubWorkflow 组件
    sub_workflow_component = SubWorkflow(sub_workflow_conf, sub_workflow_instance)

    workflow.add_workflow_comp(
        "node_workflowComposite",
        sub_workflow_component,
        inputs_schema={
            "systemFields": {"query": "${node_start.systemFields.query}"},
            "userFields": {"card_id": "${node_start.userFields.card_id}"},
        },
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 结束节点配置
    end_conf = {
        "responseTemplate": "{{end_input}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
        "userFields": {
            "inputs": [
                {
                    "id": "end_input",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                }
            ],
            "outputs": [],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"end_input": "${node_workflowComposite.responseContent}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_workflowComposite")
    workflow.add_connection("node_workflowComposite", "node_end")

    # 注册工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_parent_query_bill_workflow():
    """
    测试父工作流 - 查询账单
    """
    # 先创建子工作流
    sub_workflow, sub_workflow_id = create_query_bill_workflow(True)
    # 再创建父工作流，将子工作流实例传递给它
    workflow, workflow_id = create_parent_query_bill_workflow(True, sub_workflow)  # noqa: redefined-outer-name

    workflow_wrapper = WorkflowWrapper()
    chunks = []

    workflow_logger.info("=" * 50)
    workflow_logger.info("测试父工作流 - 查询账单")
    workflow_logger.info("=" * 50)

    # 测试父工作流
    async for chunk in workflow_wrapper.astream(
        query="调用 query_bill 工具查询信用卡ID为123456的账单",
        params={
            "global_variables": {
                "sys": {
                    "conversationHistory": [
                        {
                            "role": "user",
                            "content": "帮我还一下信用卡，信用卡ID是123456",
                        },
                        {
                            "role": "user",
                            "content": "调用 query_bill 工具查询信用卡ID为123456的账单",
                        },
                        {
                            "role": "assistant",
                            "content": "信用卡账单金额为：500.0，信用卡id为：",
                        },
                    ],
                    "currentTime": "2024-01-01",
                    "userId": "test_user",
                    "conversationId": "test_conversation_id",
                }
            }
        },
        workflow_id=workflow_id,
        session_id="test_session_id",
        agent_id="parent_workflow_plugin_query_bill_agent",
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)

    # 验证请求结果
    assert len(chunks) > 0
    workflow_logger.info(f"父工作流测试完成，共收到 {len(chunks)} 个chunk")

    return chunks
