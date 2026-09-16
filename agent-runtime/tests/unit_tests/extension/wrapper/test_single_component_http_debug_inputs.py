# coding: utf-8
"""EI.http 单节点调试输入组装 UT（MR 检视意见 #1 的后半段修复）。

create_single_component 已把 inputs_schema 重排（query→query_parameters、
userFields 平铺、auth 并入）；本文件验证 SingleComponentDebugWrapper._preprocess_inputs
对 EI.http 按 HTTPRequestExecutable 的货架契约组装 invoke inputs，并叠加调试面板覆盖：
- 面板空框（'{}' 字符串）/缺省 → 货架与重排 schema 一致（含 auth 头）；
- query / headers 框并入对应货架，同名键框优先、节点配置与 auth 保留；
- dict 形态输入（直接 API 调用）同样接受；
- 非法 JSON / 非对象 JSON → COMPONENT_STEP_DEBUG_ERROR，不静默吞输入；
- 覆盖不写回 inputs_schema（deepcopy 底座，实例可复用）。

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/extension/wrapper/test_single_component_http_debug_inputs.py -v
"""

import pytest

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.extension.wrapper.single_component_debug_wrapper import (
    SingleComponentDebugWrapper,
    SingleComponentInfo,
)
from jiuwen.serve.controllers.execution.ir_converter import (
    _remap_http_inputs_schema,
)

# 重排后的货架底座：query→query_parameters、auth 并入 headers、userFields 平铺
REMAPPED_SCHEMA = _remap_http_inputs_schema(
    {
        "query": {"page": "1"},
        "headers": {"X-A": "1"},
        "userFields": {"uid": "42"},
    },
    {"auth": {"scope": "SERVICE", "headers": {"X-Api-Key": "secret123"}, "query": {}}},
)


def _make_wrapper(inputs_schema=None, configs=None):
    info = SingleComponentInfo(
        component=object(),
        node_id="node_http_1",
        node_type="EI.http",
        configs=configs or {},
        inputs_schema=REMAPPED_SCHEMA if inputs_schema is None else inputs_schema,
        node_name="HTTP请求_1",
    )
    return SingleComponentDebugWrapper(component_info=info, execution_id="exec_test")


def test_empty_string_boxes_use_schema_shelves():
    # 前端 Monaco 默认值 '{}'：完全按节点配置执行
    out = _make_wrapper()._preprocess_inputs({"query": "{}", "headers": "{}"})
    assert out["query_parameters"] == {"page": "1"}
    assert out["headers"] == {"X-A": "1", "X-Api-Key": "secret123"}
    # G2：用户字段平铺顶层，{{uid}} 占位符可解析
    assert out["uid"] == "42"
    # 不得收缩成 {userFields: {...}} 嵌套（组件读不到）
    assert "userFields" not in out


def test_missing_boxes_use_schema_shelves():
    out = _make_wrapper()._preprocess_inputs({})
    assert out["query_parameters"] == {"page": "1"}
    assert out["headers"]["X-Api-Key"] == "secret123"


def test_box_overrides_merge_into_shelves():
    out = _make_wrapper()._preprocess_inputs(
        {"query": '{"page": "2", "demo": "9"}', "headers": '{"X-Debug": "1"}'}
    )
    # 同名键框优先；新增键并入；节点配置行与 auth 保留
    assert out["query_parameters"] == {"page": "2", "demo": "9"}
    assert out["headers"] == {"X-A": "1", "X-Api-Key": "secret123", "X-Debug": "1"}


def test_dict_inputs_accepted():
    # 直接 API 调用传 dict 形态同样生效
    out = _make_wrapper()._preprocess_inputs({"query": {"demo": "9"}, "headers": {}})
    assert out["query_parameters"] == {"page": "1", "demo": "9"}
    assert out["headers"]["X-Api-Key"] == "secret123"


def test_invalid_json_box_raises_debug_error():
    with pytest.raises(JiuWenBaseException):
        _make_wrapper()._preprocess_inputs({"query": "{not json"})


def test_non_object_json_box_raises_debug_error():
    with pytest.raises(JiuWenBaseException):
        _make_wrapper()._preprocess_inputs({"headers": "[1, 2]"})


def test_override_does_not_pollute_schema():
    wrapper = _make_wrapper()
    wrapper._preprocess_inputs({"query": '{"page": "9"}'})
    # deepcopy 底座：覆盖不得写回 inputs_schema（同实例多次调试可复用）
    assert REMAPPED_SCHEMA["query_parameters"] == {"page": "1"}


def test_non_http_node_still_uses_userfields_branch():
    # 回归：非 HTTP 节点保持通用 userFields 预处理，不被新分支影响
    info = SingleComponentInfo(
        component=object(),
        node_id="node_code_1",
        node_type="jiuwen.code",
        configs={"userFields": {"inputs": [{"id": "x", "sourceType": "input"}], "x": "1"}},
        inputs_schema={},
        node_name="代码_1",
    )
    wrapper = SingleComponentDebugWrapper(component_info=info, execution_id="exec_test")
    out = wrapper._preprocess_inputs({})
    assert out == {"userFields": {"x": "1"}}
