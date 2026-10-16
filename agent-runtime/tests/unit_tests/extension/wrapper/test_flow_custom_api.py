# coding: utf-8
# pylint: disable=protected-access
"""FlowCustomApi 工作流组件单元测试。

覆盖修改点 A19-A28：
- A19: _init_api() — 有 apiId 走 resource_mgr.get_tool
- A20: _init_api() — 无 apiId 走 _build_api_from_ir
- A21: invoke() — 正常执行返回 {"userFields": data}
- A22: invoke() — CommonJiuWenBaseException 异常处理+err_ignore
- A23: invoke() — 通用 Exception 异常处理+err_ignore
- A24: stream() — 流式执行+异常处理+err_ignore yield
- A25: _format_api_outputs() — errCode 105000-105999 区间校验
- A26: _format_api_outputs() — response 非空时 data 必须为 dict
- A27: _process_and_filter_answer() — answer 为 str 时 json.loads
- A28: get_auth_token() 返回 None
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.common.exception import JiuWenBaseException as CommonJiuWenBaseException
from jiuwen.extension.workflow_node.flow_api import (
    EXCEPTIONENABLE,
    EXCEPTIONSUPPRESSION,
    FlowApiStatusCode,
    OLD_IR_PLUGIN_RESPONSE,
)
from jiuwen.extension.workflow_node.flow_custom_api import FlowCustomApi
from jiuwen.extension.workflow_node.utils import JiuWenBaseException


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #

def _make_flow(api_mock, conf=None):
    """创建 FlowCustomApi 实例，跳过 __init__ 中的 init 链，手动设置字段。"""
    flow = FlowCustomApi(conf=None)
    flow._conf = conf or {}
    flow._api = api_mock
    flow._api_id = "test-api-id"
    flow._enable_validate = False
    flow._enable_confirm = False
    flow._outputs = []
    flow._user_fields = conf.get("userFields") if conf else None
    return flow


def _make_session():
    """创建 mock session。"""
    session = MagicMock()
    session.trace = AsyncMock()
    session.get_session_id = MagicMock(return_value="session-123")
    return session


# --------------------------------------------------------------------------- #
# A19: _init_api() — 有 apiId 走 resource_mgr.get_tool
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.workflow_node.flow_custom_api.Runner")
def test_init_api_with_api_id(mock_runner):
    """A19: 有 apiId 时走 Runner.resource_mgr.get_tool()。"""
    mock_tool = MagicMock()
    mock_runner.resource_mgr.get_tool.return_value = mock_tool

    conf = {"apiId": "registered-tool-id", "userFields": {"outputs": []}}
    flow = FlowCustomApi(conf=conf)

    mock_runner.resource_mgr.get_tool.assert_called_once_with("registered-tool-id")
    assert flow._api is mock_tool
    assert flow._api_id == "registered-tool-id"


# --------------------------------------------------------------------------- #
# A20: _init_api() — 无 apiId 走 _build_api_from_ir
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.workflow_node.flow_custom_api.convert_ir_to_custom_card")
@patch("jiuwen.extension.workflow_node.flow_custom_api.CustomPluginTool")
def test_init_api_without_api_id_builds_from_ir(mock_tool_cls, mock_convert):
    """A20: 无 apiId 时走 _build_api_from_ir()。"""
    mock_card = MagicMock()
    mock_convert.return_value = mock_card
    mock_tool = MagicMock()
    mock_tool_cls.return_value = mock_tool

    conf = {
        "id": "ir-built-id",
        "name": "test",
        "componentType": "custom.test",
        "userFields": {"outputs": []},
    }
    flow = FlowCustomApi(conf=conf)

    mock_convert.assert_called_once()
    mock_tool_cls.assert_called_once_with(mock_card)
    assert flow._api is mock_tool
    assert flow._api_id == "ir-built-id"


# --------------------------------------------------------------------------- #
# A21: invoke() — 正常执行
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_invoke_success():
    """A21: 正常调用返回 {"userFields": data}。"""
    mock_api = AsyncMock()
    mock_api.params = []
    mock_api.ainvoke = AsyncMock(return_value={"errCode": 0, "data": {"result": "ok"}})
    mock_api.response = []

    conf = {"userFields": {"outputs": []}}
    flow = _make_flow(mock_api, conf)

    inputs = {"userFields": {}, "validated": True, "confirmed": True}
    session = _make_session()
    context = MagicMock()

    result = await flow.invoke(inputs, session, context)

    assert "userFields" in result
    assert result["userFields"]["errCode"] == 0
    assert result["userFields"]["data"] == {"result": "ok"}


# --------------------------------------------------------------------------- #
# A22: invoke() — CommonJiuWenBaseException 异常处理
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_invoke_common_exception_with_err_ignore():
    """A22: CommonJiuWenBaseException + err_ignore → 返回抑制值。"""
    mock_api = AsyncMock()
    mock_api.params = []
    mock_api.ainvoke = AsyncMock(
        side_effect=CommonJiuWenBaseException(error_code=100001, message="common error")
    )
    mock_api.response = []

    conf = {
        "exceptionEnable": True,
        "exceptionSuppression": '{"default": "suppressed"}',
        "userFields": {"outputs": []},
    }
    flow = _make_flow(mock_api, conf)

    inputs = {"userFields": {}, "validated": True, "confirmed": True}
    session = _make_session()
    context = MagicMock()

    result = await flow.invoke(inputs, session, context)

    assert result["userFields"] == {"default": "suppressed"}


@pytest.mark.asyncio
async def test_invoke_common_exception_without_err_ignore():
    """A22: CommonJiuWenBaseException 无 err_ignore → 抛异常。"""
    mock_api = AsyncMock()
    mock_api.params = []
    mock_api.ainvoke = AsyncMock(
        side_effect=CommonJiuWenBaseException(error_code=100001, message="common error")
    )
    mock_api.response = []

    conf = {"userFields": {"outputs": []}}
    flow = _make_flow(mock_api, conf)

    inputs = {"userFields": {}, "validated": True, "confirmed": True}
    session = _make_session()
    context = MagicMock()

    with pytest.raises(JiuWenBaseException) as exc_info:
        await flow.invoke(inputs, session, context)

    assert exc_info.value.code == 100001


# --------------------------------------------------------------------------- #
# A23: invoke() — 通用 Exception 异常处理
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_invoke_generic_exception_with_err_ignore():
    """A23: 通用 Exception + err_ignore → 返回抑制值。"""
    mock_api = AsyncMock()
    mock_api.params = []
    mock_api.ainvoke = AsyncMock(side_effect=RuntimeError("unexpected"))
    mock_api.response = []

    conf = {
        "exceptionEnable": True,
        "exceptionSuppression": '{"fallback": "safe"}',
        "userFields": {"outputs": []},
    }
    flow = _make_flow(mock_api, conf)

    inputs = {"userFields": {}, "validated": True, "confirmed": True}
    session = _make_session()
    context = MagicMock()

    result = await flow.invoke(inputs, session, context)

    assert result["userFields"] == {"fallback": "safe"}


@pytest.mark.asyncio
async def test_invoke_generic_exception_without_err_ignore():
    """A23: 通用 Exception 无 err_ignore → 抛包装异常。"""
    mock_api = AsyncMock()
    mock_api.params = []
    mock_api.ainvoke = AsyncMock(side_effect=RuntimeError("unexpected"))
    mock_api.response = []

    conf = {"userFields": {"outputs": []}}
    flow = _make_flow(mock_api, conf)

    inputs = {"userFields": {}, "validated": True, "confirmed": True}
    session = _make_session()
    context = MagicMock()

    with pytest.raises(JiuWenBaseException) as exc_info:
        await flow.invoke(inputs, session, context)

    assert exc_info.value.code == FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR.value[0]


# --------------------------------------------------------------------------- #
# A24: stream() — 异常处理+err_ignore
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_stream_exception_with_err_ignore():
    """A24: stream 异常 + err_ignore → yield error OutputSchema。"""
    mock_api = MagicMock()
    mock_api.params = []
    mock_api.astream = MagicMock(
        side_effect=CommonJiuWenBaseException(error_code=100001, message="stream error")
    )

    conf = {
        "exceptionEnable": True,
        "exceptionSuppression": '{"default": "safe"}',
        "userFields": {"outputs": []},
    }
    flow = _make_flow(mock_api, conf)

    inputs = {"userFields": {}}
    session = _make_session()
    context = MagicMock()

    outputs = []
    with pytest.raises(Exception):
        async for out in flow.stream(inputs, session, context):
            outputs.append(out)

    assert len(outputs) >= 1
    assert outputs[0].type == "error"
    assert outputs[0].payload["userFields"] == {"default": "safe"}


# --------------------------------------------------------------------------- #
# A25: _format_api_outputs() — errCode 区间校验
# --------------------------------------------------------------------------- #

def test_format_outputs_error_code_in_range():
    """A25: errCode=105001 → 原样透传不包装。"""
    mock_api = MagicMock()
    mock_api.response = []
    flow = _make_flow(mock_api, {"userFields": {"outputs": []}})

    with pytest.raises(JiuWenBaseException) as exc_info:
        flow._format_api_outputs({"errCode": 105001, "errMessage": "plugin error"})

    assert exc_info.value.code == 105001
    assert "plugin error" in exc_info.value.message


def test_format_outputs_error_code_out_of_range():
    """A25: errCode=999 → 包装为 WORKFLOW_API_EXECUTE_ERROR。"""
    mock_api = MagicMock()
    mock_api.response = []
    flow = _make_flow(mock_api, {"userFields": {"outputs": []}})

    with pytest.raises(JiuWenBaseException) as exc_info:
        flow._format_api_outputs({"errCode": 999, "errMessage": "unknown"})

    assert exc_info.value.code == FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR.value[0]


# --------------------------------------------------------------------------- #
# A26: _format_api_outputs() — response 非空时 data 必须为 dict
# --------------------------------------------------------------------------- #

def test_format_outputs_data_not_dict_with_response():
    """A26: response 非空但 data 不是 dict → 抛异常。"""
    mock_api = MagicMock()
    mock_api.response = [MagicMock()]  # non-empty
    flow = _make_flow(mock_api, {"userFields": {"outputs": []}})

    with pytest.raises(JiuWenBaseException) as exc_info:
        flow._format_api_outputs({"errCode": 0, "data": "not a dict"})

    assert exc_info.value.code == FlowApiStatusCode.WORKFLOW_API_OUTPUTS_ERROR.value[0]


# --------------------------------------------------------------------------- #
# A27: _process_and_filter_answer() — answer 为 str 时 json.loads
# --------------------------------------------------------------------------- #

def test_process_answer_string_json():
    """A27: answer 为 JSON 字符串 → 解析为 dict。"""
    mock_api = MagicMock()
    flow = _make_flow(mock_api, {"userFields": {"outputs": []}})

    data = {"answer": '{"key": "val"}'}
    required_fields = {"key": True}
    result = flow._process_and_filter_answer(data, required_fields)

    assert result["answer"] == {"key": "val"}


def test_process_answer_string_invalid_json():
    """A27: answer 为非 JSON 字符串 → 包装为 OLD_IR_PLUGIN_RESPONSE。"""
    mock_api = MagicMock()
    flow = _make_flow(mock_api, {"userFields": {"outputs": []}})

    data = {"answer": "not json"}
    required_fields = {"some_field": True}
    result = flow._process_and_filter_answer(data, required_fields)

    assert OLD_IR_PLUGIN_RESPONSE in result["answer"]
    assert result["answer"][OLD_IR_PLUGIN_RESPONSE] == "not json"


# --------------------------------------------------------------------------- #
# A28: get_auth_token() 返回 None
# --------------------------------------------------------------------------- #

def test_get_auth_token_returns_none():
    """A28: get_auth_token() 返回 None。"""
    mock_api = MagicMock()
    flow = _make_flow(mock_api, {"userFields": {"outputs": []}})
    assert flow.get_auth_token() is None
