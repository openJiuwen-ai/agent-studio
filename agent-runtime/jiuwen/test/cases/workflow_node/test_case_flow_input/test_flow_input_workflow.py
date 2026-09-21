"""
FlowInput 工作流测试（无子工作流）

完整流程：
开始 → FlowInput → 结束

测试 FlowInput 组件的基本功能：
1. 收集用户输入参数
2. 支持工作流中断等待用户输入
3. 验证输入字段的完整性
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_input import FlowInput
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow, WorkflowCard

workflow_id = "workflow_flow_input_test"
agent_id = "test_flow_input_agent_id"


def create_flow_input_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建 FlowInput 工作流（无子工作流）

    完整结构:
    start -> flow_input -> end

    Returns:
        Workflow: FlowInput 工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="workflow_flow_input_test",
        version="0.6.0",
        description="FlowInput 组件测试工作流",
    )
    workflow = Workflow(workflow_card)

    # 开始节点配置
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "查询内容",
                    "default_value": "",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "查询内容",
                    "default_value": "",
                    "id": "query",
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
        "node_start", Start(start_conf), inputs_schema={"query": ""}
    )

    # FlowInput 节点配置
    flow_input_conf = {
        "userFields": {
            "inputs": [
                {
                    "id": "name",
                    "type": "string",
                    "required": True,
                    "description": "用户姓名",
                    "sourceType": "ref",
                },
                {
                    "id": "age",
                    "type": "number",
                    "required": False,
                    "description": "用户年龄",
                    "sourceType": "ref",
                },
                {
                    "id": "email",
                    "type": "string",
                    "required": True,
                    "description": "用户邮箱",
                    "sourceType": "ref",
                },
            ],
            "outputs": [
                {
                    "id": "name",
                    "type": "string",
                    "required": True,
                    "description": "用户姓名",
                },
                {
                    "id": "age",
                    "type": "number",
                    "required": False,
                    "description": "用户年龄",
                },
                {
                    "id": "email",
                    "type": "string",
                    "required": True,
                    "description": "用户邮箱",
                },
            ],
        },
        "systemFields": {"inputs": [], "outputs": []},
        "name": "输入",
    }

    workflow.add_workflow_comp(
        "node_flow_input", FlowInput(flow_input_conf), inputs_schema={}
    )

    # 结束节点配置
    end_conf = {
        "responseTemplate": "用户信息收集完成：姓名={{name}}，年龄={{age}}，邮箱={{email}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "用户姓名",
                    "id": "name",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "用户年龄",
                    "id": "age",
                    "type": "number",
                    "required": False,
                },
                {
                    "sourceType": "ref",
                    "description": "用户邮箱",
                    "id": "email",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={
            "name": "${node_flow_input.userFields.name}",
            "age": "${node_flow_input.userFields.age}",
            "email": "${node_flow_input.userFields.email}",
        },
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_flow_input")
    workflow.add_connection("node_flow_input", "node_end")

    # 注册工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_flow_input_workflow():
    """
    测试 FlowInput 工作流（无子工作流）

    测试流程：
    1. 第一次请求：启动工作流，FlowInput 应该中断等待用户输入
    2. 第二次请求：提供用户输入（姓名、年龄、邮箱），工作流继续执行完成
    """
    workflow, workflow_id = create_flow_input_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：启动工作流，FlowInput 中断等待输入")
    workflow_logger.info("=" * 50)

    # 第一次请求：启动工作流，FlowInput 应该中断
    async for chunk in workflow_wrapper.astream(
        query="请填写用户信息",
        params={
            "global_variables": {
                "query": "请填写用户信息",
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

    # 验证第一次请求结果：FlowInput 应该中断
    assert len(chunks_1) > 0
    has_interrupt = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_1
    )
    workflow_logger.info(f"第一次请求是否中断: {has_interrupt}")
    assert has_interrupt is True, "FlowInput 应该中断等待用户输入"

    # ==================== 第二次请求：提供用户输入 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：提供用户输入")
    workflow_logger.info("=" * 50)

    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []

    # 构建对话历史
    conversation_history = [
        {"role": "user", "content": "请填写用户信息"},
        {
            "role": "assistant",
            "content": '{"inputs": [{"name": "name", "actualType": "string", "required": true, "description": "用户姓名"}, {"name": "age", "actualType": "number", "required": false, "description": "用户年龄"}, {"name": "email", "actualType": "string", "required": true, "description": "用户邮箱"}]}',
        },
    ]

    params_2 = {
        "global_variables": {
            "query": '{"name": "张三", "age": 25, "email": "zhangsan@example.com"}',
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

    # 构建中断恢复的 InteractiveInput
    user_response = '{"name": "张三", "age": 25, "email": "zhangsan@example.com"}'
    resume_input = InteractiveInput()
    resume_input.update(interrupt_node_id, user_response)

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
