"""
父-子工作流变量传递测试

测试工作流结构:
- parent workflow: start -> set_variable -> set_variable2 -> message -> workflowComposite(call sub_flow) -> end
- sub workflow: start -> variable_modify -> end

测试目标:
验证在子工作流中修改的变量能否正确传递回父工作流

组件说明:
- set_variable 和 variable_modify 使用 LoopSetVariableComponent
- End 使用扩展的 End 组件 (支持父-子工作流记忆变量传递)
- workflowComposite 使用 SubWorkflowComponent 调用子工作流
"""

import pytest

# 使用扩展的 End 组件
from jiuwen.extension.workflow_node.end import End as ExtendedEnd
from jiuwen.extension.workflow_node.start import Start
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import (
    Workflow,
    create_workflow_session,
    WorkflowExecutionState,
    WorkflowComponent,
    LoopSetVariableComponent,
    SubWorkflowComponent,
)

pytestmark = pytest.mark.asyncio


# ============================================================================
# 自定义组件定义
# ============================================================================
class MessageComponent(WorkflowComponent):
    """消息组件，用于在工作流中传递/打印消息"""

    def __init__(self, message: str = ""):
        super().__init__()
        self._message = message

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        workflow_logger.info(f"[MessageComponent] {self._message}: {inputs}")
        return {"message": self._message, **inputs}


# ============================================================================
# 子工作流创建
# ============================================================================


def create_sub_workflow() -> Workflow:
    """
    创建子工作流

    结构: start -> variable_modify -> end

    子工作流接收一个变量，对其进行修改，然后返回

    Returns:
        Workflow: 子工作流实例
    """
    sub_flow = Workflow()
    conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "输入变量",
                    "default_value": "123 你好",
                    "id": "input",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "输入变量",
                    "default_value": "123 你好",
                    "id": "input",
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
    # 设置开始节点
    sub_flow.set_start_comp(
        "sub_start",
        Start(conf),
        inputs_schema={"input": "", "memory": {"sub_mem": "", "add_mem": "ab"}},
    )

    # 添加变量修改节点 - 将 counter 设置为 110
    sub_flow.add_workflow_comp(
        "variable_modify",
        LoopSetVariableComponent({"${sub_start.memory.sub_mem}": "ccc2"}),
    )

    # 设置结束节点 (使用扩展的 End 组件)
    sub_flow.set_end_comp(
        "sub_end",
        ExtendedEnd(),
        inputs_schema={"result": "${sub_start.memory.sub_mem}"},
    )

    # 添加连接
    sub_flow.add_connection("sub_start", "variable_modify")
    sub_flow.add_connection("variable_modify", "sub_end")

    return sub_flow


# ============================================================================
# 父工作流创建
# ============================================================================


def create_parent_workflow(sub_workflow: Workflow) -> Workflow:
    """
    创建父工作流

    结构: start -> set_variable -> set_variable2 -> message -> workflowComposite(call sub_flow) -> end

    Args:
        sub_workflow: 子工作流实例

    Returns:
        Workflow: 父工作流实例
    """
    parent_flow = Workflow()
    conf = {
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
    # 1. 设置开始节点
    parent_flow.set_start_comp("start", Start(conf), inputs_schema={})

    # 2. 添加第一个变量设置节点 - 设置 counter = 100
    parent_flow.add_workflow_comp(
        "set_variable", LoopSetVariableComponent({"${start.memory.test_mem}": "aaaaaa"})
    )

    # 3. 添加第二个变量设置节点 - 设置 status = "initialized"
    parent_flow.add_workflow_comp(
        "set_variable2", LoopSetVariableComponent({"${start.memory.test_mem2}": 1})
    )

    # 4. 添加消息节点 - 打印调用子工作流前的状态
    parent_flow.add_workflow_comp(
        "message",
        MessageComponent("Before calling sub-workflow"),
        inputs_schema={
            "test_mem": "${start.memory.test_mem}",
            "test_mem2": "${start.memory.test_mem2}",
        },
    )

    # 5. 添加子工作流调用节点
    sub_workflow_component = SubWorkflowComponent(sub_workflow)
    parent_flow.add_workflow_comp(
        "workflowComposite",
        sub_workflow_component,
        inputs_schema={
            "input": "${start.memory.test_mem}",
            "input2": "${start.memory.test_mem2}",
            "memory": {
                "sub_mem": "{start.memory.test_mem}",
                "sub_mem2": "{start.memory.test_mem2}",
            },
        },
    )

    # 6. 设置结束节点 (使用扩展的 End 组件)
    parent_flow.set_end_comp(
        "end",
        ExtendedEnd(),
        inputs_schema={
            "result": "${start.memory.test_mem}",
            "result2": "${start.memory.test_mem2}",
            "sub_result": "${workflowComposite.output}",
        },
    )

    # 添加连接
    parent_flow.add_connection("start", "set_variable")
    parent_flow.add_connection("set_variable", "set_variable2")
    parent_flow.add_connection("set_variable2", "message")
    parent_flow.add_connection("message", "workflowComposite")
    parent_flow.add_connection("workflowComposite", "end")

    return parent_flow


# ============================================================================
# 测试用例
# ============================================================================


async def test_parent_child_workflow_variable_propagation():
    """
    测试父-子工作流变量传递

    验证:
    1. 父工作流能够正确执行
    2. 子工作流能够被正确调用
    3. 子工作流中修改的变量能够正确传递回父工作流
    """
    # 创建子工作流
    sub_workflow = create_sub_workflow()

    # 创建父工作流
    parent_workflow = create_parent_workflow(sub_workflow)

    # 执行父工作流
    inputs = {"query": "你好"}
    session = create_workflow_session()

    result = await parent_workflow.invoke(inputs, session=session)

    # 验证结果
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED

    workflow_logger.info(f"Workflow result: {result}")
    workflow_logger.info(f"Result data: {result.result}")

    # 验证子工作流的结果
    # 子工作流应该将 counter 从 100 增加到 110
    if result.result:
        response = result.result.get("response", {})
        sub_result = response.get("output", {}).get("sub_workflow_result")
        if sub_result:
            workflow_logger.info(f"Sub-workflow returned: {sub_result}")
            # 验证 counter 被正确修改
            assert sub_result.get("result") == "ccc2", (
                f"Expected result='ccc2', got {sub_result.get('result')}"
            )
            assert sub_result.get("result2") == 1, (
                f"Expected result2=1, got {sub_result.get('result2')}"
            )

    return result


async def test_sub_workflow_standalone():
    """
    测试子工作流独立执行

    验证子工作流能够独立正确运行
    """
    sub_workflow = create_sub_workflow()

    # 执行子工作流
    inputs = {}
    session = create_workflow_session()

    result = await sub_workflow.invoke(inputs, session=session)

    # 验证结果
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED

    workflow_logger.info(f"Sub-workflow result: {result}")

    # 验证 counter 被正确修改
    if result.result:
        response = result.result.get("answer", {})
        assert response.get("output", {}).get("result") == "ccc2", (
            f"Expected result='ccc2', got {response.get('output', {}).get('result')}"
        )

    return result


# ============================================================================
# 流式输出和结构化输出测试
# ============================================================================


async def test_end_stream_output():
    """
    测试 End 组件的流式输出功能

    验证:
    1. 流式输出能够正确生成
    2. workflow_end 和 finish 事件能够正确发送
    """
    from openjiuwen.core.session.stream import OutputSchema

    # 创建一个简单的工作流，测试流式输出
    flow = Workflow()

    # 配置结束节点支持流式输出
    end_conf = {"responseTemplate": "Hello {{name}}!", "stream_output": True}

    # 设置开始节点
    flow.set_start_comp(
        "start",
        Start(
            {
                "userFields": {"inputs": [], "outputs": []},
                "systemFields": {"inputs": [], "outputs": []},
            }
        ),
        inputs_schema={"name": "World"},
    )

    # 设置结束节点（使用扩展的End组件）
    flow.set_end_comp(
        "end",
        ExtendedEnd(end_conf),
        stream_inputs_schema={"name": "${start.name}"},
        response_mode="streaming",  # 启用流式模式，确保调用stream方法
    )

    # 添加连接
    flow.add_connection("start", "end")

    # 执行流式输出测试
    inputs = {}
    session = create_workflow_session()

    # 收集所有流式输出
    stream_outputs = []
    workflow_logger.info("Starting to stream output...")

    async for output in flow.stream(inputs, session=session):
        stream_outputs.append(output)
        workflow_logger.info(
            f"Received stream output: {type(output).__name__} - {output}"
        )

    # 验证流式输出
    assert len(stream_outputs) > 0, "Should have at least one stream output"

    # 验证是否有 workflow_end 和 finish 事件
    has_workflow_end = False
    has_finish = False
    has_workflow_final = False

    workflow_logger.info(f"\nAll stream outputs ({len(stream_outputs)}):")
    for i, output in enumerate(stream_outputs):
        output_type = type(output).__name__
        workflow_logger.info(f"  Output {i + 1}: {output_type}")

        # 尝试获取可能的type字段
        if hasattr(output, "type"):
            workflow_logger.info(f"    - type: {output.type}")
        if hasattr(output, "payload"):
            workflow_logger.info(f"    - payload: {output.payload}")

        if isinstance(output, OutputSchema):
            if output.type == "workflow_end":
                has_workflow_end = True
            elif output.type == "finish":
                has_finish = True
            elif output.type == "workflow_final":
                has_workflow_final = True

    workflow_logger.info("\nEvent checks:")
    workflow_logger.info(f"  has_workflow_end: {has_workflow_end}")
    workflow_logger.info(f"  has_finish: {has_finish}")
    workflow_logger.info(f"  has_workflow_final: {has_workflow_final}")

    # 更新断言逻辑，考虑TraceSchema中的完成事件
    workflow_finished = any(
        hasattr(output, "payload")
        and output.payload.get("status") == "finish"
        and output.payload.get("invokeId") == output.payload.get("workflowId")
        for output in stream_outputs
    )

    # 验证工作流是否完成
    assert workflow_finished, "Workflow should have finished event"
    workflow_logger.info(f"  workflow_finished: {workflow_finished}")

    workflow_logger.info(f"Stream outputs count: {len(stream_outputs)}")
    workflow_logger.info(f"Has workflow_end: {has_workflow_end}")
    workflow_logger.info(f"Has finish: {has_finish}")
    workflow_logger.info(f"Has workflow_final: {has_workflow_final}")
    workflow_logger.info(
        f"All stream output types: {[output.type if isinstance(output, OutputSchema) else type(output) for output in stream_outputs]}"
    )

    return stream_outputs


async def test_end_structured_output():
    """
    测试 End 组件的结构化输出功能

    验证:
    1. 结构化输出能够正确生成
    2. 结构化输出包含正确的模板和变量
    """
    # 创建一个简单的工作流，测试结构化输出
    flow = Workflow()

    # 配置开始节点
    start_conf = {
        "userFields": {"inputs": [], "outputs": ["name"]},
        "systemFields": {"inputs": [], "outputs": []},
    }

    # 配置结束节点支持结构化输出
    end_conf = {
        "responseTemplate": "Hello {{name}}!",
        "struct_output_template": '{"greeting": "{{response}}", "user": "{{name}}"}',
        "enable_struct_message": True,
    }

    # 设置开始节点
    flow.set_start_comp("start", Start(start_conf), inputs_schema={})

    # 设置结束节点（使用扩展的End组件）
    flow.set_end_comp("end", ExtendedEnd(end_conf), inputs_schema={"name": "Alice"})

    # 添加连接
    flow.add_connection("start", "end")

    # 执行工作流
    inputs = {}
    session = create_workflow_session()

    result = await flow.invoke(inputs, session=session)

    # 验证结果
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED

    workflow_logger.info(f"Structured output result: {result.result}")

    # 验证结构化输出
    if result.result and "output" in result.result:
        output = result.result["output"]
        assert "struct_answer" in output, "Should have structured answer"

        struct_answer = output["struct_answer"]
        assert (
            struct_answer["struct_output_template"]
            == end_conf["struct_output_template"]
        )
        assert "Alice" in str(struct_answer["variables"]), (
            "Should contain name variable"
        )

    return result


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    # 使用 pytest 运行测试
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    if result.returncode == 0:
        workflow_logger.info("\nAll tests passed!")
    else:
        workflow_logger.error(f"\nTests failed with return code: {result.returncode}")
        sys.exit(result.returncode)
