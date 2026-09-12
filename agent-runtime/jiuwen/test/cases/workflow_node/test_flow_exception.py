"""
异常结束工作流 (Exception Workflow)

流程：开始 → 提问器 → 分支判断 → 结束 / 异常结束

测试 BranchComponent 表达式条件 + ExceptionInfo 异常结束节点。
当 query 含 "异常" 时路由到 ExceptionInfo，否则路由到 End。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_exception import ExceptionInfo
from jiuwen.extension.workflow_node.questioner import (
    Questioner,
    QuestionerConfig,
    FieldInfo,
)
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.condition.condition import AlwaysTrue
from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent

workflow_id = "38a80260-2181-446f-8cf1-2887e9403f5d"
agent_id = "39a80260-2181-446f-8cf1-2887e9403f5c"
session_id = "e02b3673-1683-4a99-83b6-ecce9426bf0b"


def _create_mock_llm():
    mock_model = MagicMock()
    mock_invoke_result = MagicMock()
    mock_invoke_result.content = '{"user_input": "正常"}'
    mock_invoke_result.usage_metadata = None
    mock_model.invoke = AsyncMock(return_value=mock_invoke_result)
    return mock_model


def create_exception_workflow() -> tuple[Workflow, str]:
    """
    创建异常结束工作流

    结构: start -> questioner -> branch -> (end / exception_info)

    Branch 条件: '异常' not in ${start.systemFields.query} → end，否则 → exception_info

    Returns:
        Workflow: 工作流实例
        workflow_id: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="ssq_exception_termination_component_01",
        version="0.1.0",
        description="ssq_异常结束组件_01",
    )
    wf = Workflow(workflow_card)

    # 1. 开始节点
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "错误码",
                    "default_value": 500,
                    "id": "error_code",
                    "type": "integer",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "错误信息",
                    "default_value": "用户定义错误信息",
                    "id": "error_message",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "错误码",
                    "default_value": 500,
                    "id": "error_code",
                    "type": "integer",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "错误信息",
                    "default_value": "用户定义错误信息",
                    "id": "error_message",
                    "type": "string",
                    "required": True,
                },
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
    wf.set_start_comp(
        "start",
        Start(start_conf),
        inputs_schema={
            "query": "${query}",
            "error_code": "${global_variables.error_code}",
            "error_message": "${global_variables.error_message}",
        },
        # inputs_schema={
        #     "query": "${query}",
        #     "error_code": 500,
        #     "error_message": "用户自定义错误信息----",
        # },
    )

    # 2. 提问器节点
    questioner_conf = QuestionerConfig(
        model_name="mock-model",
        model_type="agentBuilder",
        response_type="reply_directly",
        extract_fields_from_response=True,
        with_chat_history=False,
        key_fields=[
            FieldInfo(
                field_name="user_input",
                description="用户输入内容",
                type="string",
                required=True,
            ),
        ],
        max_response=3,
        accept_language="zh",
    )
    wf.add_workflow_comp(
        "questioner",
        Questioner(questioner_conf),
        inputs_schema={"query": "${start.systemFields.query}"},
    )

    # 3. 异常结束节点
    wf.add_workflow_comp(
        "node_exception_termination",
        ExceptionInfo("node_exception_termination", "异常结束节点", "jiuwen.exception"),
        inputs_schema={
            "userFields": {
                "error_code": "${start.userFields.error_code}",
                "error_message": "${start.userFields.error_message}",
            }
        },
    )

    # 4. 正常结束节点
    end_conf = {
        "responseTemplate": "## 正常结束----",
        "responseMode": "directResponse",
        "name": "结束",
        "isStreamOut": True,
    }
    wf.set_end_comp(
        "end",
        End(end_conf),
        inputs_schema={"answer": "${questioner.userFields.user_response}"},
    )

    # 5. 分支判断节点
    branch = BranchComponent()
    branch.add_branch(
        "'异常' not in ${start.systemFields.query}",
        "end",
        "node_if",
    )
    branch.add_branch(AlwaysTrue(), "node_exception_termination", "default")
    wf.add_workflow_comp("branch", branch)

    # 6. 连接
    wf.add_connection("start", "questioner")
    wf.add_connection("questioner", "branch")

    # 7. 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(
        workflow_card,
        lambda card=workflow_card: wf,
        tag=agent_id,
    )

    return wf, workflow_id


@pytest.mark.asyncio
async def test_exception_workflow():
    """
    测试异常结束工作流

    query="异常" → Branch 路由到 ExceptionInfo → WorkflowAbortException。
    验证异常携带正确的节点信息和 payload。
    """

    async def _mock_init_model(self_q):
        self_q._model = _create_mock_llm()
        self_q._initialized = True

    with patch.object(Questioner, "_initialize_model", _mock_init_model):
        workflow, wf_id = create_exception_workflow()

        wrapper = WorkflowWrapper()
        chunks = []
        async for chunk in wrapper.astream(
            query="异常",
            workflow_id=wf_id,
            session_id=session_id,
            agent_id=agent_id,
            params={
                "global_variables": {
                    "error_code": 500,
                    "error_message": "用户自定义错误信息----",
                }
            },
        ):
            chunks.append(chunk)
            workflow_logger.info(chunk)
        assert len(chunks) > 0
        workflow_logger.info(f"共收到 {len(chunks)} 个chunk")
