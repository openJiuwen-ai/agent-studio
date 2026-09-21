"""
结束工作流 (End Workflow)

流程：开始 → 结束

最简单的工作流，用于测试结束节点的流式输出。
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

workflow_id = "8f9ac059-0b15-4b11-baf2-18d10665c38c"
agent_id = "d4c90802-9243-4667-aaaa-e7ace9985b29"


def create_end_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建结束工作流

    结构: start -> end

    Returns:
        Workflow: 结束工作流实例
        workflow_id: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="end_workflow",
        version="0.6.0",
        description="结束工作流测试",
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

    # 2. 配置结束节点
    end_conf = {
        "responseTemplate": "## 流程结束",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 3. 添加连接
    workflow.add_connection("node_start", "node_end")

    # 4. 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_end_workflow():
    """
    测试结束工作流

    验证输出包含以下 StreamData 序列：
    1. code=3000 (WORKFLOW_START) - 工作流开始
    2. code=1206 (PARTIAL_CONTENT) - 结束节点输出
    3. code=5000 (MESSAGE_END) - 消息结束
    4. code=7000 (CONTROLLER_INTERMEDIATE_MESSAGE) - 中间消息
    5. code=4000 (WORKFLOW_END) - 工作流结束
    6. code=0 (FINISH) - 完成
    """
    workflow, workflow_id = create_end_workflow()  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in workflow_wrapper.astream(
        query="升金感兴趣",
        workflow_id=workflow_id,
        session_id="ea437b21-be2d-4dce-a25c-4b82662cda40",
        agent_id=agent_id,
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)

    # 验证输出数量
    assert len(chunks) >= 6, f"Expected at least 6 chunks, got {len(chunks)}"
