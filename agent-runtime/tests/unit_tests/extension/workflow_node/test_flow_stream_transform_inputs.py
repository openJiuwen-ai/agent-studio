# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""
验证 FlowStreamTransform 对一次性整体值输入（str/dict/list）的兜底支持。

覆盖 BUG2026102704532：流式消息参数为 object 类型（整体 dict/list）时，
原先直接抛 101171 input invalid；修复后与 str 一致包装为单元素异步生成器，
复用统一流式管线输出渲染结果。

测试覆盖范围:
1. invoke 整体 str 输入：包装为单帧正常输出（回归）
2. invoke 整体 dict 输入：不再报错，输出渲染后的整体对象
3. invoke 整体 list 输入：不再被丢弃，输出渲染后的数组
4. invoke 整体 object 且模板按路径取字段：正常嵌套渲染
5. 非 str/dict/list 类型（如 int）仍抛 INPUT_INVALID（不超范围扩展）
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from jiuwen.extension.workflow_node.flow_stream_transform import (
    STREAM_TYPE_MESSAGE_END,
    FlowStreamTransform,
)
from jiuwen.extension.workflow_node.flow_stream_transform import (
    USER_FIELDS as ST_USER_FIELDS,
)
from jiuwen.extension.workflow_node.utils import WorkflowMetadata
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.workflow.components import Session


def _make_mock_session() -> MagicMock:
    """创建 FlowStreamTransform 测试用的 mock Session"""
    session = MagicMock(spec=Session)
    session.get_component_id = MagicMock(return_value="st_comp")
    session.get_workflow_id = MagicMock(return_value="test_wf")
    session.get_session_id = MagicMock(return_value="test_sess")
    session.write_stream = AsyncMock()
    session.write_custom_stream = AsyncMock()
    session.get_env = MagicMock(return_value=0.2)
    session.get_global_state = MagicMock(return_value=None)
    return session


def _make_mock_context() -> MagicMock:
    return MagicMock(spec=ModelContext)


def _make_metadata() -> WorkflowMetadata:
    return WorkflowMetadata(
        node_id="st_node",
        node_type="StreamTransform",
        node_name="Test ST",
        should_interrupt=False,
    )


def _make_comp(configs: dict) -> FlowStreamTransform:
    """创建 FlowStreamTransform，输入参数 id 固定为 raw_output"""
    conf = {
        "transformer": configs,
        "userFields": {
            "inputs": [{"id": "raw_output", "type": "object", "required": True}],
            "outputs": [],
        },
    }
    return FlowStreamTransform(conf, _make_metadata())


def _answer_of(session: MagicMock) -> Any:
    """提取最后一次 write_stream 的 answer（MESSAGE_END 帧）"""
    written = [c.args[0] for c in session.write_stream.call_args_list]
    end_frames = [w for w in written if w.type == STREAM_TYPE_MESSAGE_END]
    return end_frames[-1].payload.get("answer")


class TestFlowStreamTransformOverallInput:
    @pytest.mark.asyncio
    async def test_invoke_str_input_outputs_frame(self):
        """整体 str 输入（回归）：包装为单帧并输出渲染结果"""
        comp = _make_comp(
            {
                "variables": [{"name": "raw_output", "src_path": "raw_output", "concat": False}],
                "frame_template": {"raw_output": "{{raw_output}}"},
                "add_is_last": False,
            }
        )
        session = _make_mock_session()
        result = await comp.invoke(
            {ST_USER_FIELDS: {"raw_output": "hello"}}, session, _make_mock_context()
        )
        assert result == {ST_USER_FIELDS: {"raw_output": {"answer": "hello"}}}
        assert _answer_of(session) == '{"answer": "hello"}'

    @pytest.mark.asyncio
    async def test_invoke_dict_input_no_longer_raises(self):
        """整体 dict 输入（object 参数）：不再抛 101171，输出渲染后的整体对象"""
        comp = _make_comp(
            {
                "variables": [{"name": "raw_output", "src_path": "raw_output", "concat": False}],
                "frame_template": {"raw_output": "{{raw_output}}"},
                "add_is_last": False,
            }
        )
        session = _make_mock_session()
        result = await comp.invoke(
            {ST_USER_FIELDS: {"raw_output": {"data": {"a": 1}}}},
            session,
            _make_mock_context(),
        )
        assert result == {ST_USER_FIELDS: {"raw_output": {"data": {"a": 1}}}}
        assert _answer_of(session) == '{"data": {"a": 1}}'

    @pytest.mark.asyncio
    async def test_invoke_list_input_not_dropped(self):
        """整体 list 输入：不再被 _iter_dict_frames 丢弃，输出渲染后的数组"""
        comp = _make_comp(
            {
                "variables": [{"name": "raw_output", "src_path": "raw_output", "concat": False}],
                "frame_template": {"raw_output": "{{raw_output}}"},
                "add_is_last": False,
            }
        )
        session = _make_mock_session()
        result = await comp.invoke(
            {ST_USER_FIELDS: {"raw_output": [{"a": 1}, {"b": 2}]}},
            session,
            _make_mock_context(),
        )
        assert result == {ST_USER_FIELDS: {"raw_output": [{"a": 1}, {"b": 2}]}}
        assert _answer_of(session) == '[{"a": 1}, {"b": 2}]'

    @pytest.mark.asyncio
    async def test_invoke_object_input_with_path_render(self):
        """整体 object 输入按模板路径取字段：正常嵌套渲染"""
        comp = _make_comp(
            {
                "variables": [{"name": "ref_1", "src_path": "data", "concat": False}],
                "frame_template": {"content": "{{ref_1}}"},
                "add_is_last": False,
            }
        )
        session = _make_mock_session()
        await comp.invoke(
            {ST_USER_FIELDS: {"raw_output": {"data": {"a": 1}}}},
            session,
            _make_mock_context(),
        )
        assert _answer_of(session) == '{"content": {"a": 1}}'

    @pytest.mark.asyncio
    async def test_invoke_number_inputs_rendered_like_str(self):
        """数字/布尔（int/float/bool）与 str 同步兜底：不再报错，数字/布尔作为整体帧输出"""
        cases = [
            (123, {ST_USER_FIELDS: {"raw_output": 123}}),
            (3.14, {ST_USER_FIELDS: {"raw_output": 3.14}}),
            (True, {ST_USER_FIELDS: {"raw_output": True}}),
        ]
        for raw, expected in cases:
            comp = _make_comp(
                {
                    "variables": [{"name": "raw_output", "src_path": "raw_output", "concat": False}],
                    "frame_template": {"raw_output": "{{raw_output}}"},
                    "add_is_last": False,
                }
            )
            session = _make_mock_session()
            result = await comp.invoke(
                {ST_USER_FIELDS: {"raw_output": raw}}, session, _make_mock_context()
            )
            assert result == expected
            assert _answer_of(session) is not None

    @pytest.mark.asyncio
    async def test_invoke_unsupported_type_still_raises(self):
        """非支持的输入类型（如 set）仍抛 INPUT_INVALID，不超范围扩展"""
        comp = _make_comp(
            {
                "variables": [{"name": "raw_output", "src_path": "raw_output", "concat": False}],
                "frame_template": {"raw_output": "{{raw_output}}"},
                "add_is_last": False,
            }
        )
        session = _make_mock_session()
        with pytest.raises(Exception) as exc_info:
            await comp.invoke(
                {ST_USER_FIELDS: {"raw_output": {1, 2}}}, session, _make_mock_context()
            )
        assert "must be an async iterable, string, dict, list or number" in str(exc_info.value)