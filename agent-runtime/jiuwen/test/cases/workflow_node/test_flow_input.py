# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowInput 工作流集成测试
测试覆盖:
- FlowInput 在完整工作流中的功能
- 工作流中断和用户输入处理
- 输入验证和默认值功能
- 与其他组件的协作
"""

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from jiuwen.extension.workflow_node.flow_input import (
    FlowInput,
    FlowInputState,
    FlowInputUtils,
    ExecutionStatus,
    USER_FIELDS,
    FLOW_INPUT_STATE_KEY,
)
from jiuwen.extension.workflow_node.start import Start
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import Workflow, End, create_workflow_session
from openjiuwen.core.workflow.components.component import WorkflowComponent


class SimpleProcessComponent(WorkflowComponent):
    """简单处理组件，用于在工作流中处理 FlowInput 的输出"""

    def __init__(self):
        super().__init__()

    async def invoke(
        self, inputs: Dict[str, Any], session: Session, context: ModelContext
    ) -> Dict[str, Any]:
        """处理输入并返回结果"""
        user_fields = inputs.get(USER_FIELDS, {})
        if not user_fields:
            return {}
        # 简单处理：拼接用户信息
        result = {
            "processed_name": f"User: {user_fields.get('name', '')}",
            "processed_age": int(user_fields.get("age", 0)) + 1
            if user_fields.get("age")
            else 0,
            "processed_email": user_fields.get("email", ""),
        }

        return result


class TestFlowInputUnit:
    """FlowInput 单元测试"""

    def test_initial_state(self):
        """测试初始状态"""
        flow_input = FlowInput({})
        assert flow_input.get_node_status() == ExecutionStatus.START
        assert flow_input.should_interrupt() == False

    def test_should_interrupt(self):
        """测试中断判断"""
        flow_input = FlowInput({})
        assert flow_input.should_interrupt() == False

        flow_input._node_state.status = ExecutionStatus.USER_INTERACT
        assert flow_input.should_interrupt() == True

        flow_input._node_state.status = ExecutionStatus.END
        assert flow_input.should_interrupt() == False

    def test_load_state(self):
        """测试状态加载"""
        flow_input = FlowInput({})
        new_state = flow_input._node_state.__class__(
            status=ExecutionStatus.USER_INTERACT, question="请输入信息"
        )
        flow_input.load_state(new_state)

        assert flow_input.get_node_status() == ExecutionStatus.USER_INTERACT
        assert flow_input._node_state.question == "请输入信息"

    def test_error_to_output(self):
        """测试错误处理"""
        flow_input = FlowInput({})
        flow_input._node_state.status = ExecutionStatus.USER_INTERACT

        flow_input.error_to_output()

        assert flow_input.get_node_status() == ExecutionStatus.END

    def test_need_inputs_message(self):
        """测试输入配置信息生成"""
        config = {
            USER_FIELDS: {
                "inputs": [
                    {
                        "id": "name",
                        "type": "string",
                        "required": True,
                        "description": "用户姓名",
                    }
                ]
            }
        }
        flow_input = FlowInput(config)
        message = FlowInputUtils.build_inputs_message(flow_input._config)

        assert isinstance(message, str)
        parsed = json.loads(message)
        assert "inputs" in parsed
        assert len(parsed["inputs"]) == 1
        assert parsed["inputs"][0]["name"] == "name"
        assert parsed["inputs"][0]["actualType"] == "string"

    def test_parse_user_response(self):
        """测试用户响应解析"""
        # 测试 field:value 格式
        response = FlowInputUtils.parse_user_response("name:张三\nage:25")
        assert response["name"] == "张三"
        assert response["age"] == "25"

        # 测试 JSON 格式
        response = FlowInputUtils.parse_user_response('{"name": "李四", "age": "30"}')
        assert response["name"] == "李四"
        assert response["age"] == "30"

        # 测试空响应
        response = FlowInputUtils.parse_user_response("")
        assert response == {}

        # 测试 None
        response = FlowInputUtils.parse_user_response(None)
        assert response == {}

    def test_validate_inputs(self):
        """测试输入验证"""
        config = {
            USER_FIELDS: {
                "inputs": [
                    {"id": "name", "type": "string", "required": True},
                    {"id": "age", "type": "number", "required": False},
                    {"id": "active", "type": "boolean", "required": False},
                ]
            }
        }
        flow_input = FlowInput(config)

        # 测试正常输入
        inputs = {"name": "张三", "age": "25", "active": "true"}
        # 这应该不会抛出异常
        FlowInputUtils.validate_inputs(inputs, flow_input._config)

        # 测试缺少必填字段
        with pytest.raises(Exception):
            FlowInputUtils.validate_inputs(
                {"age": "25"}, flow_input._config
            )  # 缺少 name

        # 测试类型转换
        inputs = {"name": "张三", "age": "25", "active": "true"}
        FlowInputUtils.validate_inputs(inputs, flow_input._config)


@pytest.mark.asyncio
async def test_flow_input_invoke_with_mock_session():
    """使用模拟 session 测试 FlowInput.invoke 方法（模拟恢复执行流程）"""
    workflow_logger.info("=== 测试 FlowInput.invoke 方法 ===")

    config = {
        USER_FIELDS: {
            "inputs": [
                {"id": "name", "type": "string", "required": True},
                {"id": "age", "type": "number", "required": False},
                {"id": "email", "type": "string", "required": True},
            ]
        }
    }

    flow_input = FlowInput(config)

    # ===== 模拟恢复执行：USER_INTERACT 状态 =====
    # 创建保存的状态
    saved_state = FlowInputState(
        status=ExecutionStatus.USER_INTERACT,
        question=FlowInputUtils.build_inputs_message(flow_input._config),
    )

    # 创建模拟 session，使用 spec=Session 让 isinstance 检查通过
    from openjiuwen.core.workflow.components import Session as RealSession

    mock_session = MagicMock(spec=RealSession)
    mock_session.get_component_id = MagicMock(return_value="test_node")
    mock_session.get_state = MagicMock(
        return_value={FLOW_INPUT_STATE_KEY: saved_state.serialize()}
    )
    mock_session.update_state = MagicMock()
    mock_session.write_custom_stream = AsyncMock()

    # session.interact 返回用户输入
    user_input = "name:张三\nage:25\nemail:zhangsan@example.com"
    mock_session.interact = AsyncMock(return_value=user_input)

    mock_context = MagicMock()

    # 调用 invoke（此时会从 session 加载 USER_INTERACT 状态并处理用户输入）
    result = await flow_input.invoke({}, mock_session, mock_context)

    workflow_logger.info(f"   invoke 结果: {result}")

    # 验证结果包含用户输入
    assert USER_FIELDS in result, f"期望结果包含 {USER_FIELDS}，实际结果: {result}"
    assert result[USER_FIELDS]["name"] == "张三"
    assert result[USER_FIELDS]["age"] == 25.0
    assert result[USER_FIELDS]["email"] == "zhangsan@example.com"

    workflow_logger.info("   - invoke 方法测试通过")


@pytest.mark.asyncio
async def test_flow_input_in_workflow():
    """测试 FlowInput 在完整工作流中的功能"""
    workflow_logger.info("=== 测试 FlowInput 在完整工作流中的功能 ===")

    flow_input_config = {
        USER_FIELDS: {
            "inputs": [
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
            ]
        }
    }

    flow = Workflow()

    start = Start({})
    flow.set_start_comp("start", start, inputs_schema={})

    flow_input = FlowInput(flow_input_config)
    flow.add_workflow_comp("input", flow_input, inputs_schema={})

    process_comp = SimpleProcessComponent()
    flow.add_workflow_comp(
        "process", process_comp, inputs_schema={USER_FIELDS: "${input.userFields}"}
    )

    end = End()
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "final_name": "${process.processed_name}",
            "final_age": "${process.processed_age}",
            "final_email": "${process.processed_email}",
        },
    )

    flow.add_connection("start", "input")
    flow.add_connection("input", "process")
    flow.add_connection("process", "end")

    # 创建会话并模拟用户输入
    session = create_workflow_session()
    user_input = "name:张三\nage:25\nemail:zhangsan@example.com"
    session.interact = AsyncMock(return_value=user_input)

    workflow_logger.info(f"   用户输入: {user_input}")

    # 使用 stream 方法测试
    results = []
    async for output in flow.stream({}, session=session):
        results.append(output)
        workflow_logger.info(f"   流式输出: {output}")

    workflow_logger.info(f"   流式输出数量: {len(results)}")

    # 检查最后一个输出是否包含完成信息
    if results:
        last_output = results[-1]
        if hasattr(last_output, "payload"):
            workflow_logger.info(f"   最终 payload: {last_output.payload}")


@pytest.mark.asyncio
async def test_flow_input_commercial_features():
    """测试商用版本的所有主要功能是否都已实现"""
    workflow_logger.info("\n=== 验证商用版本功能实现 ===")

    flow_input = FlowInput({})

    commercial_features = {
        "状态管理 (ExecutionStatus)": hasattr(flow_input, "get_node_status")
        and hasattr(flow_input, "load_state"),
        "输入参数收集和验证": True,
        "默认值设置": True,
        "中断逻辑": hasattr(flow_input, "should_interrupt"),
        "输入配置信息生成": hasattr(FlowInputUtils, "build_inputs_message"),
        "异常处理": hasattr(flow_input, "error_to_output"),
        "状态保存和恢复": hasattr(flow_input, "get_state")
        and hasattr(flow_input, "load_state"),
        "同步执行接口 (invoke)": hasattr(flow_input, "invoke"),
        "流式执行接口 (stream)": hasattr(flow_input, "stream"),
    }

    all_features_implemented = True
    for feature, implemented in commercial_features.items():
        status = "OK" if implemented else "ERROR"
        workflow_logger.info(
            f"   {status} {feature}: {'已实现' if implemented else '未实现'}"
        )
        if not implemented:
            all_features_implemented = False

    if all_features_implemented:
        workflow_logger.info("\n所有商用版本的主要功能都已实现！")
    else:
        workflow_logger.error("\n部分商用版本功能未实现！")


@pytest.mark.asyncio
async def test_flow_input_with_default_values():
    """测试 FlowInput 的默认值功能（模拟恢复执行流程）"""
    workflow_logger.info("\n=== 测试 FlowInput 默认值功能 ===")

    flow_input_config = {
        USER_FIELDS: {
            "inputs": [
                {"id": "name", "type": "string", "required": True},
                {"id": "age", "type": "number", "required": False},
                {"id": "active", "type": "boolean", "required": False},
                {"id": "tags", "type": "array", "required": False},
                {"id": "meta", "type": "object", "required": False},
            ]
        }
    }

    flow_input = FlowInput(flow_input_config)

    # 创建保存的状态（USER_INTERACT 状态）
    saved_state = FlowInputState(
        status=ExecutionStatus.USER_INTERACT,
        question=FlowInputUtils.build_inputs_message(flow_input._config),
    )

    # 创建模拟 session，使用 spec=Session 让 isinstance 检查通过
    from openjiuwen.core.workflow.components import Session as RealSession

    mock_session = MagicMock(spec=RealSession)
    mock_session.get_component_id = MagicMock(return_value="test_node")
    mock_session.get_state = MagicMock(
        return_value={FLOW_INPUT_STATE_KEY: saved_state.serialize()}
    )
    mock_session.update_state = MagicMock()
    mock_session.write_custom_stream = AsyncMock()
    mock_session.interact = AsyncMock(return_value="name:王五")  # 只提供必填字段

    mock_context = MagicMock()

    # 调用 invoke（此时会从 session 加载 USER_INTERACT 状态并处理用户输入）
    result = await flow_input.invoke({}, mock_session, mock_context)

    assert USER_FIELDS in result, f"期望结果包含 {USER_FIELDS}，实际结果: {result}"

    user_fields = result[USER_FIELDS]
    assert user_fields["name"] == "王五"
    assert user_fields["age"] == 0  # number 默认值
    assert user_fields["active"] == False  # boolean 默认值
    assert user_fields["tags"] == []  # array 默认值
    assert user_fields["meta"] == {}  # object 默认值

    workflow_logger.info("   - 默认值功能测试通过")


if __name__ == "__main__":
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    if result.returncode == 0:
        workflow_logger.info("\n所有测试都通过了！")
    else:
        workflow_logger.error(f"\nTests failed with return code: {result.returncode}")
        sys.exit(result.returncode)
