# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
父工作流 - 信用卡还款

根据 workflow/parent_workflow_repay_credit.json 配置实现的父工作流，
使用 openjiuwen 工作流框架。

流程：
开始 → 子工作流 → 结束
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.test.cases.workflow_node.test_case_controller_plan_execute_common_01.test_repay_credit_workflow import (
    create_repay_credit_workflow,
)
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow, WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

workflow_id = "parent_workflow_plugin_repay_credit"
agent_id = "parent_workflow_plugin_repay_credit_agent"


def create_parent_repay_credit_workflow(
    is_streaming: bool = True, sub_workflow_instance=None
) -> tuple[Workflow, str]:
    """
    创建父工作流 - 信用卡还款

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
        name="parent_workflow_plugin_repay_credit",
        version="0.6.0",
        description="父工作流 - 信用卡还款",
    )
    workflow = Workflow(workflow_card)
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
            "id": "workflow_plugin_repay_credit",
            "path": "workflow_repay_credit.json",
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
        stream_inputs_schema={"end_input": "${node_workflowComposite.responseContent}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_workflowComposite")
    workflow.add_stream_connection("node_workflowComposite", "node_end")

    # 注册工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_parent_repay_credit_workflow():
    """
    测试父工作流 - 信用卡还款
    """
    # 先创建子工作流
    sub_workflow, sub_workflow_id = create_repay_credit_workflow(True)
    # 再创建父工作流，将子工作流实例传递给它
    workflow, workflow_id = create_parent_repay_credit_workflow(True, sub_workflow)  # noqa: redefined-outer-name

    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    workflow_logger.info("=" * 50)
    workflow_logger.info("测试父工作流 - 信用卡还款")
    workflow_logger.info("=" * 50)

    # 测试父工作流
    async for chunk in workflow_wrapper.astream(
        query="执行还款操作",
        params={
            "global_variables": {
                "card_id": "",
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
                                "parent_workflow_plugin_repay_credit",
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
                            "role": "tool",
                            "content": "转账成功：success",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": ["workflow_plugin_transfer"],
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "assistant",
                            "content": "余额不足，转账完成[STEP_DONE]",
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
                            "content": "执行还款操作",
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
                            "content": "确认还款嘛？",
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
        agent_id="parent_workflow_plugin_repay_credit_agent",
    ):
        chunks_1.append(chunk)
        workflow_logger.info(chunk)

    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：确认还款")
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
            if chunk.data.get("parentNodeId"):
                interrupt_node_id = (
                    chunk.data.get("parentNodeId") + "." + interrupt_node_id
                )
                break
    assert interrupt_node_id is not None, "未找到中断节点的 node_id"
    # 构建中断恢复的 InteractiveInput，精确路由到中断节点
    resume_input = InteractiveInput()
    resume_input.update(interrupt_node_id, "确认还款")
    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []
    async for chunk in workflow_wrapper_resume.astream(
        query=resume_input,
        params={
            "global_variables": {
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
                            "role": "assistant",
                            "content": "余额不足，转账完成[STEP_DONE]",
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
                            "content": "确认还款",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": ["parent_workflow_plugin_repay_credit"],
                            "enable_history": True,
                            "agent_id": None,
                        },
                        {
                            "role": "assistant",
                            "content": "还款成功：success",
                            "files": None,
                            "name": None,
                            "tool_call_id": None,
                            "function_call": None,
                            "intent": None,
                            "enable_history": True,
                            "agent_id": None,
                        },
                    ],
                    "currentTime": "2025-01-01",
                    "userId": "test_user",
                    "conversationId": "test-conversation-id",
                }
            }
        },
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
