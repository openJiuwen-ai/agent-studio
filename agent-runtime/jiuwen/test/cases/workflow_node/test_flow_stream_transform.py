# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowStreamTransform 组件测试用例

测试覆盖范围:
- 初始化 / 配置校验
- 核心执行路径（invoke）
- 流式输出测试
- 错误处理测试
- 各种输入格式处理（dict/StreamData/JSON字符串/bytes）
"""

import json
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from jiuwen.extension.workflow_node.flow_stream_transform import (
    FlowStreamTransform,
    FlowStreamTransformStatusCode,
    build_flow_stream_transform_error,
    get_data_of_streaming_with_metadata,
    USER_FIELDS,
    STREAM_TYPE_PARTIAL_CONTENT,
    STREAM_TYPE_MESSAGE_END,
)
from jiuwen.extension.workflow_node.utils import (
    WorkflowMetadata,
    JiuWenBaseException,
)
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream import OutputSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent

USER_FIELDS = "userFields"


def create_mock_session() -> MagicMock:
    """创建模拟的 Session 对象"""
    session = MagicMock(spec=Session)
    session.get_component_id = MagicMock(return_value="test_node_id")
    session.get_component_type = MagicMock(return_value="StreamTransform")
    session.get_workflow_id = MagicMock(return_value="test_workflow_id")
    session.get_session_id = MagicMock(return_value="test_session_id")
    session.write_stream = AsyncMock()
    return session


def create_mock_context() -> MagicMock:
    """创建模拟的 ModelContext 对象"""
    context = MagicMock(spec=ModelContext)
    return context


def create_test_metadata() -> WorkflowMetadata:
    """创建测试用的 WorkflowMetadata"""
    return WorkflowMetadata(
        node_id="test_node_id",
        node_type="StreamTransform",
        node_name="Test Stream Transform",
        should_interrupt=False,
    )


async def async_generator(items: list) -> AsyncIterator:
    """创建异步生成器"""
    for item in items:
        yield item


class TestFlowStreamTransformInit:
    """初始化和配置校验测试"""

    def test_init_with_valid_config(self):
        """测试使用有效配置初始化"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }
        metadata = create_test_metadata()

        component = FlowStreamTransform(conf, metadata)

        assert component._conf == conf
        assert component.metadata == metadata
        assert component._parse_json_strings is True
        assert component._source_field == "_input"
        assert component._output_field == ""
        assert component._direct_assign_output is True

    def test_init_with_user_fields_config(self):
        """测试使用 userFields 配置初始化"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "userFields": {
                "inputs": [{"id": "custom_input"}],
                "outputs": [{"id": "custom_output"}],
            },
        }
        metadata = create_test_metadata()

        component = FlowStreamTransform(conf, metadata)

        assert component._source_field == "custom_input"
        assert component._output_field == "custom_output"
        assert component._direct_assign_output is False

    def test_init_with_invalid_transformer_config(self):
        """测试使用无效的 transformer 配置"""
        conf = {
            "transformer": "not_a_dict",
        }
        metadata = create_test_metadata()

        with pytest.raises(JiuWenBaseException) as exc_info:
            FlowStreamTransform(conf, metadata)

        assert (
            exc_info.value.error_code == FlowStreamTransformStatusCode.CONFIG_ERROR[0]
        )

    def test_init_with_empty_transformer_conf(self):
        """测试 transformer 配置为空字典（初始化不报错，执行时报错）"""
        conf = {}
        metadata = create_test_metadata()

        component = FlowStreamTransform(conf, metadata)
        assert component._transformer_conf == {}


class TestFlowStreamTransformInvoke:
    """核心执行路径测试"""

    @pytest.mark.asyncio
    async def test_invoke_with_none_stream(self):
        """测试输入流为 None 的情况"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()
        inputs = {USER_FIELDS: {}}

        result = await component.invoke(inputs, session, context)

        assert result == {USER_FIELDS: None}
        session.write_stream.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoke_with_non_async_iterable(self):
        """测试输入不是异步可迭代对象"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()
        inputs = {USER_FIELDS: {"_input": "not_async_iterable"}}

        with pytest.raises(JiuWenBaseException) as exc_info:
            await component.invoke(inputs, session, context)

        assert (
            exc_info.value.error_code == FlowStreamTransformStatusCode.INPUT_INVALID[0]
        )

    @pytest.mark.asyncio
    async def test_invoke_with_valid_stream(self):
        """测试使用有效输入流"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test1"}
            yield {"input": "test2"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result
        assert session.write_stream.call_count == 2


class TestFlowStreamTransformStreaming:
    """流式输出测试"""

    @pytest.mark.asyncio
    async def test_streaming_output_format(self):
        """测试流式输出格式"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test1"}
            yield {"input": "test2"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        await component.invoke(inputs, session, context)

        calls = session.write_stream.call_args_list
        assert len(calls) == 2

        first_call = calls[0][0][0]
        assert isinstance(first_call, OutputSchema)
        assert first_call.type == STREAM_TYPE_PARTIAL_CONTENT
        assert first_call.index == 0

        second_call = calls[1][0][0]
        assert isinstance(second_call, OutputSchema)
        assert second_call.type == STREAM_TYPE_MESSAGE_END
        assert second_call.index == 1

    @pytest.mark.asyncio
    async def test_streaming_with_metadata(self):
        """测试流式输出包含元数据"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = WorkflowMetadata(
            node_id="custom_node_id",
            node_type="CustomType",
            node_name="Custom Node",
            should_interrupt=False,
        )
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        await component.invoke(inputs, session, context)

        call = session.write_stream.call_args_list[0][0][0]
        payload = call.payload

        assert payload["node_id"] == "custom_node_id"
        assert payload["node_type"] == "CustomType"
        assert payload["node_name"] == "Custom Node"


class TestFlowStreamTransformInputFormats:
    """各种输入格式处理测试"""

    @pytest.mark.asyncio
    async def test_dict_input_format(self):
        """测试字典输入格式"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test_value"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result

    @pytest.mark.asyncio
    async def test_json_string_input_format(self):
        """测试 JSON 字符串输入格式"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield json.dumps({"input": "test_value"})

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result

    @pytest.mark.asyncio
    async def test_sse_format_input(self):
        """测试 SSE 格式输入（data: 前缀）"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield "data: " + json.dumps({"input": "test_value"})

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result

    @pytest.mark.asyncio
    async def test_bytes_input_format(self):
        """测试 bytes 输入格式"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield json.dumps({"input": "test_value"}).encode("utf-8")

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result

    @pytest.mark.asyncio
    async def test_parse_json_strings_disabled(self):
        """测试禁用 JSON 字符串解析"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": False,
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield json.dumps({"input": "test_value"})

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert result == {USER_FIELDS: None}
        session.write_stream.assert_not_called()


class TestFlowStreamTransformErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_transformer_config_error(self):
        """测试无效的 transformer 配置错误"""
        conf = {
            "transformer": {
                "frame_template": None,
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        with pytest.raises(JiuWenBaseException) as exc_info:
            await component.invoke(inputs, session, context)

        assert (
            exc_info.value.error_code
            == FlowStreamTransformStatusCode.TRANSFORMER_CONFIG_ERROR[0]
        )


class TestGetDataOfStreamingWithMetadata:
    """get_data_of_streaming_with_metadata 函数测试"""

    def test_basic_output(self):
        """测试基本输出"""
        metadata = create_test_metadata()
        result = get_data_of_streaming_with_metadata(
            answer="test_answer",
            metadata=metadata,
        )

        assert result["answer"] == "test_answer"
        assert result["node_id"] == "test_node_id"
        assert result["node_type"] == "StreamTransform"
        assert result["node_name"] == "Test Stream Transform"
        assert result["should_interrupt"] is False
        assert "outputs" not in result

    def test_output_with_outputs(self):
        """测试带 outputs 的输出"""
        metadata = create_test_metadata()
        result = get_data_of_streaming_with_metadata(
            answer="test_answer",
            metadata=metadata,
            outputs={"key": "value"},
        )

        assert "outputs" in result
        assert result["outputs"][USER_FIELDS] == {"key": "value"}

    def test_dict_answer(self):
        """测试字典类型的 answer"""
        metadata = create_test_metadata()
        result = get_data_of_streaming_with_metadata(
            answer={"key": "value"},
            metadata=metadata,
        )

        assert result["answer"] == {"key": "value"}


class TestBuildFlowStreamTransformError:
    """build_flow_stream_transform_error 函数测试"""

    def test_error_creation(self):
        """测试错误创建"""
        error = build_flow_stream_transform_error(
            error_code=FlowStreamTransformStatusCode.CONFIG_ERROR[0],
            message="Test error message",
        )

        assert isinstance(error, JiuWenBaseException)
        assert error.error_code == FlowStreamTransformStatusCode.CONFIG_ERROR[0]
        assert "Test error message" in error.message


class TestFlowStreamTransformOutputField:
    """输出字段配置测试"""

    @pytest.mark.asyncio
    async def test_direct_assign_output(self):
        """测试直接分配输出"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result
        assert isinstance(result[USER_FIELDS], dict)

    @pytest.mark.asyncio
    async def test_output_field_assignment(self):
        """测试指定输出字段"""
        conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "userFields": {
                "outputs": [{"id": "custom_output"}],
            },
        }
        metadata = create_test_metadata()
        component = FlowStreamTransform(conf, metadata)

        session = create_mock_session()
        context = create_mock_context()

        async def test_stream():
            yield {"input": "test"}

        inputs = {USER_FIELDS: {"_input": test_stream()}}

        result = await component.invoke(inputs, session, context)

        assert USER_FIELDS in result
        assert "custom_output" in result[USER_FIELDS]


# ============================================================================
# 辅助组件定义
# ============================================================================


class StreamGenerator(WorkflowComponent):
    """流式数据生成组件，用于生成测试用的异步流"""

    def __init__(self, items: list):
        super().__init__()
        self._items = items

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        async def async_gen():
            for item in self._items:
                yield item

        return {USER_FIELDS: {"_input": async_gen()}}


class StreamCollector(WorkflowComponent):
    """流式数据收集组件，用于收集并验证流式输出"""

    def __init__(self):
        super().__init__()
        self.collected_data = []

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        user_fields = (inputs or {}).get(USER_FIELDS, {}) or {}
        self.collected_data.append(user_fields)
        return {"collected": True, "data": user_fields}


# ============================================================================
# 整体 Workflow 集成测试
# ============================================================================


class TestFlowStreamTransformWorkflowIntegration:
    """
    FlowStreamTransform 组件整体 Workflow 集成测试

    由于 openjiuwen 工作流引擎会对状态进行 pickle 序列化，
    而 async_generator 对象无法被序列化，因此使用直接调用组件的方式
    来模拟工作流执行流程。

    测试场景:
    - 组件间协作
    - 流式数据传递
    - 完整执行流程
    """

    @pytest.mark.asyncio
    async def test_component_chain_integration(self):
        """测试组件链式调用集成

        模拟工作流: StreamGenerator -> FlowStreamTransform -> StreamCollector
        """

        stream_items = [
            {"input": "hello"},
            {"input": "world"},
            {"input": "test"},
        ]

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert USER_FIELDS in transform_result
        assert transform_result[USER_FIELDS] is not None

        collector = StreamCollector()
        final_result = await collector.invoke(transform_result, session, context)

        assert final_result.get("collected") is True

    @pytest.mark.asyncio
    async def test_component_chain_with_json_string_input(self):
        """测试 JSON 字符串输入的组件链式调用"""

        stream_items = [
            json.dumps({"input": "test1"}),
            json.dumps({"input": "test2"}),
        ]

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert USER_FIELDS in transform_result

    @pytest.mark.asyncio
    async def test_component_chain_with_custom_fields(self):
        """测试自定义输入输出字段的组件链式调用"""

        stream_items = [
            {"data": "item1"},
            {"data": "item2"},
        ]

        session = create_mock_session()
        context = create_mock_context()

        async def custom_async_gen():
            for item in stream_items:
                yield item

        gen_result = {USER_FIELDS: {"custom_input": custom_async_gen()}}

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "data"}],
            },
            "userFields": {
                "inputs": [{"id": "custom_input"}],
                "outputs": [{"id": "custom_output"}],
            },
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert USER_FIELDS in transform_result
        assert "custom_output" in transform_result[USER_FIELDS]

    @pytest.mark.asyncio
    async def test_component_chain_empty_stream(self):
        """测试空流的组件链式调用"""

        stream_items = []

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert USER_FIELDS in transform_result
        assert transform_result[USER_FIELDS] is None

    @pytest.mark.asyncio
    async def test_component_chain_streaming_output(self):
        """测试流式输出的组件链式调用"""

        stream_items = [
            {"input": "chunk1"},
            {"input": "chunk2"},
            {"input": "chunk3"},
        ]

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert session.write_stream.call_count == 3

        calls = session.write_stream.call_args_list
        assert calls[0][0][0].type == STREAM_TYPE_PARTIAL_CONTENT
        assert calls[1][0][0].type == STREAM_TYPE_PARTIAL_CONTENT
        assert calls[2][0][0].type == STREAM_TYPE_MESSAGE_END

    @pytest.mark.asyncio
    async def test_component_chain_with_metadata_propagation(self):
        """测试元数据在组件链中的传递"""

        stream_items = [
            {"input": "test"},
        ]

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="custom_node_id",
            node_type="CustomType",
            node_name="Custom Node Name",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        await transformer.invoke(gen_result, session, context)

        call = session.write_stream.call_args_list[0][0][0]
        payload = call.payload

        assert payload["node_id"] == "custom_node_id"
        assert payload["node_type"] == "CustomType"
        assert payload["node_name"] == "Custom Node Name"

    @pytest.mark.asyncio
    async def test_component_chain_with_sse_format_input(self):
        """测试 SSE 格式输入的组件链式调用"""

        stream_items = [
            "data: " + json.dumps({"input": "test1"}),
            "data: " + json.dumps({"input": "test2"}),
        ]

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert USER_FIELDS in transform_result

    @pytest.mark.asyncio
    async def test_component_chain_with_bytes_input(self):
        """测试 bytes 输入的组件链式调用"""

        stream_items = [
            json.dumps({"input": "test1"}).encode("utf-8"),
            json.dumps({"input": "test2"}).encode("utf-8"),
        ]

        session = create_mock_session()
        context = create_mock_context()

        generator = StreamGenerator(stream_items)
        gen_result = await generator.invoke({}, session, context)

        metadata = WorkflowMetadata(
            node_id="flow_stream_transform",
            node_type="FlowStreamTransform",
            node_name="Test Flow Stream Transform",
            should_interrupt=False,
        )

        transform_conf = {
            "transformer": {
                "frame_template": {"result": "{{value}}"},
                "variables": [{"name": "value", "src_path": "input"}],
            },
            "parse_json_strings": True,
        }

        transformer = FlowStreamTransform(transform_conf, metadata)
        transform_result = await transformer.invoke(gen_result, session, context)

        assert USER_FIELDS in transform_result


# ============================================================================
# 主函数
# ============================================================================


if __name__ == "__main__":
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    if result.returncode == 0:
        print("\nAll tests passed!")
    else:
        print(f"\nTests failed with return code: {result.returncode}")
        sys.exit(result.returncode)
