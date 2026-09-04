"""
FlowInput 子工作流测试

完整流程：
父工作流：开始 → 子工作流 → 结束
子工作流：开始 → FlowInput → 结束

测试 FlowInput 组件在子工作流中的功能：
1. 子工作流中的 FlowInput 中断处理
2. 子工作流与父工作流的交互通信
3. CustomSchema 在父子工作流间的传递
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_input import FlowInput
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow, WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

# 子工作流配置
sub_workflow_id = "sub_workflow_flow_input_test"
# 父工作流配置
parent_workflow_id = "parent_workflow_flow_input_test"
agent_id = "test_flow_input_sub_agent_id"


def create_sub_flow_input_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建包含 FlowInput 的子工作流

    完整结构:
    start -> flow_input -> end

    Returns:
        tuple[Workflow, str]: 子工作流实例和工作流ID
    """
    workflow_card = WorkflowCard(
        id=sub_workflow_id,
        name="sub_workflow_flow_input_test",
        version="0.6.0",
        description="包含 FlowInput 的子工作流",
    )
    workflow = Workflow(workflow_card)

    # 开始节点配置
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "订单ID",
                    "default_value": "",
                    "id": "order_id",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "订单ID",
                    "default_value": "",
                    "id": "order_id",
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
        "node_start", Start(start_conf), inputs_schema={"order_id": "", "query": ""}
    )

    # FlowInput 节点配置（在子工作流中）
    flow_input_conf = {
        "userFields": {
            "inputs": [
                {
                    "id": "product_name",
                    "type": "string",
                    "required": True,
                    "description": "商品名称",
                    "sourceType": "ref",
                },
                {
                    "id": "quantity",
                    "type": "number",
                    "required": True,
                    "description": "购买数量",
                    "sourceType": "ref",
                },
                {
                    "id": "remark",
                    "type": "string",
                    "required": False,
                    "description": "备注信息",
                    "sourceType": "ref",
                },
            ],
            "outputs": [
                {
                    "id": "product_name",
                    "type": "string",
                    "required": True,
                    "description": "商品名称",
                },
                {
                    "id": "quantity",
                    "type": "number",
                    "required": True,
                    "description": "购买数量",
                },
                {
                    "id": "remark",
                    "type": "string",
                    "required": False,
                    "description": "备注信息",
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
        "responseTemplate": "订单信息收集完成：订单ID={{order_id}}，商品={{product_name}}，数量={{quantity}}，备注={{remark}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "name": "结束",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "订单ID",
                    "id": "order_id",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "商品名称",
                    "id": "product_name",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "购买数量",
                    "id": "quantity",
                    "type": "number",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "备注信息",
                    "id": "remark",
                    "type": "string",
                    "required": False,
                },
            ],
            "outputs": [
                {
                    "sourceType": "ref",
                    "description": "订单结果",
                    "id": "responseContent",
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
        inputs_schema={
            "order_id": "${node_start.userFields.order_id}",
            "product_name": "${node_flow_input.userFields.product_name}",
            "quantity": "${node_flow_input.userFields.quantity}",
            "remark": "${node_flow_input.userFields.remark}",
        },
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 添加连接
    workflow.add_connection("node_start", "node_flow_input")
    workflow.add_connection("node_flow_input", "node_end")

    # 注册子工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, sub_workflow_id


def create_parent_flow_input_workflow(
    is_streaming: bool = True, sub_workflow_instance=None
) -> tuple[Workflow, str]:
    """
    创建包含子工作流的父工作流

    流程结构:
    start → workflowComposite (子工作流) → end

    Args:
        is_streaming: 是否启用流式输出
        sub_workflow_instance: 子工作流实例

    Returns:
        tuple[Workflow, str]: 父工作流实例和工作流ID
    """
    workflow_card = WorkflowCard(
        id=parent_workflow_id,
        name="parent_workflow_flow_input_test",
        version="0.6.0",
        description="包含 FlowInput 子工作流的父工作流",
    )
    workflow = Workflow(workflow_card)

    # 开始节点配置
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "id": "order_id",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                }
            ],
            "outputs": [
                {
                    "id": "order_id",
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
        "node_start", Start(start_conf), inputs_schema={"order_id": "", "query": ""}
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
                    "id": "order_id",
                    "type": "String",
                    "description": "订单ID",
                    "sourceType": "ref",
                }
            ]
        },
        "preDefineFields": {"outputs": [{"id": "responseContent", "type": "String"}]},
        "reference": {
            "id": sub_workflow_id,
            "path": "sub_workflow_flow_input_test.json",
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
            "userFields": {"order_id": "${node_start.userFields.order_id}"},
        },
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    # 结束节点配置
    end_conf = {
        "responseTemplate": "父工作流执行完成：{{end_input}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
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

    # 注册父工作流
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, parent_workflow_id


@pytest.mark.asyncio
async def test_flow_input_sub_workflow():
    """
    测试 FlowInput 在子工作流中的功能

    测试流程：
    1. 第一次请求：启动父工作流，子工作流中的 FlowInput 应该中断等待用户输入
    2. 第二次请求：提供用户输入（商品名称、数量、备注），工作流继续执行完成
    """
    # 先创建子工作流
    sub_workflow, sub_wf_id = create_sub_flow_input_workflow(True)
    # 再创建父工作流，将子工作流实例传递给它
    workflow, workflow_id = create_parent_flow_input_workflow(True, sub_workflow)

    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：启动父工作流，子工作流中 FlowInput 中断等待输入")
    workflow_logger.info("=" * 50)

    # 第一次请求：启动工作流，子工作流中的 FlowInput 应该中断
    async for chunk in workflow_wrapper.astream(
        query="查询订单信息",
        params={
            "global_variables": {
                "order_id": "ORD001",
                "query": "查询订单信息",
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
    assert has_interrupt is True, "子工作流中的 FlowInput 应该中断等待用户输入"

    # ==================== 第二次请求：提供用户输入 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：提供用户输入")
    workflow_logger.info("=" * 50)

    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []

    # 构建对话历史
    conversation_history = [
        {"role": "user", "content": "查询订单信息"},
        {
            "role": "assistant",
            "content": '{"inputs": [{"name": "product_name", "actualType": "string", "required": true, "description": "商品名称"}, {"name": "quantity", "actualType": "number", "required": true, "description": "购买数量"}, {"name": "remark", "actualType": "string", "required": false, "description": "备注信息"}]}',
        },
    ]

    params_2 = {
        "global_variables": {
            "order_id": "ORD001",
            "query": '{"product_name": "笔记本电脑", "quantity": 2, "remark": "加急发货"}',
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
            if chunk.data.get("parentNodeId"):
                interrupt_node_id = (
                    chunk.data.get("parentNodeId") + "." + interrupt_node_id
                )
                break
    assert interrupt_node_id is not None, "未找到中断节点的 node_id"

    # 构建中断恢复的 InteractiveInput
    user_response = (
        '{"product_name": "笔记本电脑", "quantity": 2, "remark": "加急发货"}'
    )
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
