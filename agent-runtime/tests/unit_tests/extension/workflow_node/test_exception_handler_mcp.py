# coding: utf-8
"""exception_handler.py 单元测试 — MCP 异常处理相关改动。

重点覆盖：
1. _merge_dicts — Bug #4 修复：MCP 节点 outputs_schema 为空时保留 default_outputs 所有 key
2. _handle_default_outputs — MCP 路径（outputs_schema={}）vs Plugin 路径
3. _handle_error_branch — 返回结构正确性
4. _format_inner_exception — JiuWenBaseException vs 通用 Exception

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/extension/workflow_node/test_exception_handler_mcp.py -v
"""

from types import SimpleNamespace

from jiuwen.extension.workflow_node.exception_handler import (
    _format_inner_exception,
    _handle_default_outputs,
    _handle_error_branch,
)
from jiuwen.extension.workflow_node.utils import JiuWenBaseException


# ─── helpers ──────────────────────────────────────────────────────────


def _make_exception_config(
    *,
    handle_type="defaultOutputs",
    outputs_schema=None,
    default_outputs=None,
    _node_type="jiuwen.mcp",
    **extra,
):
    """构造 ExceptionConfig 替身（SimpleNamespace，与 Pydantic extra=allow 行为一致）。"""
    return SimpleNamespace(
        handle_type=handle_type,
        outputs_schema=outputs_schema if outputs_schema is not None else {},
        default_outputs=default_outputs if default_outputs is not None else {},
        _node_type=_node_type,
        **extra,
    )


def _make_jiuwen_error(msg="test error", code=105001):
    return JiuWenBaseException(error_code=code, message=msg)


def _make_generic_error():
    return ValueError("something broke")


def _merge_via_handler(base, default):
    """构造配置 → 调用 _handle_default_outputs → 提取 merge 结果（去掉 isSuccess/errorBody）。"""
    config = _make_exception_config(
        outputs_schema=base,
        default_outputs=default,
    )
    result = _handle_default_outputs(_make_generic_error(), config, None)
    # 剥掉异常追加字段，只看 merge 结果
    result.pop("isSuccess", None)
    result.pop("errorBody", None)
    return result


# ─── _format_inner_exception ──────────────────────────────────────────


def test_format_jiuwen_exception():
    """JiuWenBaseException 提取 message/errorCode。"""
    result = _format_inner_exception(_make_jiuwen_error("timeout", 100101))
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorMessage"] == "timeout"
    assert result["errorBody"]["errorCode"] == 100101


def test_format_generic_exception():
    """通用异常用 repr。"""
    result = _format_inner_exception(_make_generic_error())
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorCode"] == -1
    assert "ValueError" in result["errorBody"]["errorMessage"]


def test_format_none_error():
    """极端情况：传入 None 不应崩溃。"""
    result = _format_inner_exception(None)
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorCode"] == -1


# ─── _merge_dicts（Bug #4 修复核心）──────────────────────────────────


def test_merge_empty_base_preserves_all_default_keys():
    """Bug #4 核心：MCP 节点 outputs_schema={} 时，default_outputs 的所有 key 都保留。"""
    default = {
        "content": [{"type": "text", "text": "默认值"}],
        "isError": True,
    }
    result = _merge_via_handler({}, default)
    assert result["content"] == [{"type": "text", "text": "默认值"}]
    assert result["isError"] is True


def test_merge_overlapping_keys_default_wins():
    """key 冲突时，default 的值覆盖 base。"""
    base = {"output": "base_value", "extra": "keep"}
    default = {"output": "default_value"}
    result = _merge_via_handler(base, default)
    assert result["output"] == "default_value"
    assert result["extra"] == "keep"


def test_merge_nested_dict():
    """嵌套 dict 递归合并。"""
    base = {"data": {"field1": "base1", "field2": "base2"}}
    default = {"data": {"field1": "default1", "field3": "default3"}}
    result = _merge_via_handler(base, default)
    assert result["data"]["field1"] == "default1"
    assert result["data"]["field2"] == "base2"
    assert result["data"]["field3"] == "default3"


def test_merge_default_has_extra_keys_not_in_base():
    """default 中有 base 没有的 key → 保留（MCP 场景）。"""
    base = {"content": []}
    default = {"content": [{"type": "text", "text": "ok"}], "isError": True, "custom_field": "value"}
    result = _merge_via_handler(base, default)
    assert result["isError"] is True
    assert result["custom_field"] == "value"


def test_merge_both_empty():
    """两个空 dict → 返回空。"""
    assert _merge_via_handler({}, {}) == {}


# ─── _handle_default_outputs ─────────────────────────────────────────


def test_default_outputs_mcp_path_empty_schema():
    """MCP 节点：outputs_schema={}，default_outputs 直接透传 + 异常信息追加。"""
    config = _make_exception_config(
        outputs_schema={},
        default_outputs={
            "content": [{"type": "text", "text": "超时默认值"}],
            "isError": True,
        },
        _node_type="jiuwen.mcp",
    )
    error = _make_jiuwen_error("MCP 执行超时", 100101)
    result = _handle_default_outputs(error, config, session=None)

    # 用户默认值保留
    assert result["content"] == [{"type": "text", "text": "超时默认值"}]
    assert result["isError"] is True
    # 异常信息追加
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorMessage"] == "MCP 执行超时"
    assert result["errorBody"]["errorCode"] == 100101


def test_default_outputs_plugin_path_with_schema():
    """Plugin 节点：outputs_schema 有值，merge 后保留 schema 中的 base key。"""
    config = _make_exception_config(
        outputs_schema={"result": "", "status": ""},
        default_outputs={"result": "默认结果", "extra": "额外字段"},
        _node_type="jiuwen.plugin",
    )
    error = _make_generic_error()
    result = _handle_default_outputs(error, config, session=None)

    # base 的 status 保留（值来自 outputs_schema）
    assert result["status"] == ""
    # default 的 result 覆盖 base
    assert result["result"] == "默认结果"
    # default 独有的 extra 保留（Bug #4 修复）
    assert result["extra"] == "额外字段"
    # 异常信息
    assert result["isSuccess"] is False


def test_default_outputs_none_schema_treated_as_empty():
    """outputs_schema=None 时等同于 {}（防御性）。"""
    config = _make_exception_config(
        outputs_schema=None,
        default_outputs={"key": "value"},
    )
    result = _handle_default_outputs(_make_generic_error(), config, session=None)
    assert result["key"] == "value"
    assert result["isSuccess"] is False


def test_default_outputs_error_body_does_not_overwrite_user_fields():
    """isSuccess/errorBody 由异常信息追加，不与用户 default_outputs 冲突。"""
    config = _make_exception_config(
        default_outputs={"isSuccess": True, "errorBody": "user_value"},
    )
    result = _handle_default_outputs(_make_jiuwen_error(), config, session=None)
    # _format_inner_exception 的结果通过 update 覆盖
    assert result["isSuccess"] is False
    assert isinstance(result["errorBody"], dict)


# ─── _handle_error_branch ────────────────────────────────────────────


def test_error_branch_jiuwen_exception():
    result = _handle_error_branch(_make_jiuwen_error("节点失败", 105001))
    assert result["result"] == "1"
    assert result["classificationId"] == -1
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorMessage"] == "节点失败"
    assert result["errorBody"]["errorCode"] == 105001


def test_error_branch_generic_exception():
    result = _handle_error_branch(_make_generic_error())
    assert result["result"] == "1"
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorCode"] == -1
    assert "ValueError" in result["errorBody"]["errorMessage"]


def test_error_branch_result_is_string_one_not_int():
    """result 必须是字符串 '1'，不是整数 1（下游用字符串比较）。"""
    result = _handle_error_branch(_make_generic_error())
    assert result["result"] == "1"
    assert isinstance(result["result"], str)
