# coding: utf-8
"""EI.http 单节点调试输入组装 UT（MR 检视意见 #1 的后半段修复）。

create_single_component 已把 inputs_schema 重排（query→query_parameters、
userFields 平铺、auth 并入）；本文件验证 SingleComponentDebugWrapper._preprocess_inputs
对 EI.http 按 HTTPRequestExecutable 的货架契约组装 invoke inputs，并叠加调试面板覆盖：
- 面板空框（'{}' 字符串）/缺省 → 货架与重排 schema 一致（含 auth 头）；
- query / headers 框并入对应货架，同名键框优先、节点配置与 auth 保留；
- 其余用户字段框值叠加到顶层同名键（MR 检视意见 #1 后续轮），组件保留键
  与未声明键不叠加；嵌套 userFields 形态（API 直调）同样接受；
- dict 形态输入（直接 API 调用）同样接受；
- 非法 JSON / 非对象 JSON / 其余非 str/dict 形态（list/number/bool，API 直调）
  → COMPONENT_STEP_DEBUG_ERROR，不静默吞输入；
- 覆盖不写回 inputs_schema（deepcopy 底座，实例可复用）。

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/extension/wrapper/test_single_component_http_debug_inputs.py -v
"""

# pylint: disable=protected-access  # 单测需直接调用内部方法 _preprocess_inputs

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


@pytest.mark.parametrize("bad", [[1, 2], 5, True])
def test_non_str_non_dict_box_raises_debug_error(bad):
    # API 直调传 list/number/bool 形态按约定报错，不得静默忽略调试覆盖
    # （dict 是合法形态，见 test_dict_inputs_accepted）
    with pytest.raises(JiuWenBaseException):
        _make_wrapper()._preprocess_inputs({"query": bad})


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


# ─── MR 检视意见 #1（后续轮）：其余用户字段框值必须叠加到 base ──────────


def test_user_field_box_overlaid():
    # 节点测试对话框按 nodeInfo.inputs 条目逐键发送：query/headers 是 JSON 框，
    # 用户字段（如 uid）是普通输入框，值必须叠加到顶层供 {{uid}} 占位符解析
    out = _make_wrapper()._preprocess_inputs(
        {"query": "{}", "headers": "{}", "uid": "99"}
    )
    assert out["uid"] == "99"
    # 货架不受影响
    assert out["query_parameters"] == {"page": "1"}
    assert out["headers"]["X-Api-Key"] == "secret123"


def test_user_field_declared_without_default_overlaid():
    # base（重排 schema）里没有该字段默认值，但 configs.userFields.inputs 声明过
    # → 对齐通用分支的声明口径，同样叠加
    wrapper = _make_wrapper(
        inputs_schema={"query_parameters": {}, "headers": {}},
        configs={"userFields": {"inputs": [{"id": "city", "sourceType": "input"}]}},
    )
    out = wrapper._preprocess_inputs({"city": "shanghai"})
    assert out["city"] == "shanghai"


def test_nested_user_fields_dict_overlaid():
    # API 直调传嵌套 userFields 形态同样接受
    out = _make_wrapper()._preprocess_inputs({"userFields": {"uid": "7"}})
    assert out["uid"] == "7"


def test_flat_key_wins_over_nested():
    out = _make_wrapper()._preprocess_inputs(
        {"userFields": {"uid": "7"}, "uid": "8"}
    )
    assert out["uid"] == "8"


def test_reserved_and_undeclared_keys_not_overlaid():
    # 组件保留键与未声明键不得经调试输入改变节点控制配置
    out = _make_wrapper()._preprocess_inputs(
        {"method": "DELETE", "body": "evil", "authentication": "x", "unknown": "1"}
    )
    assert "method" not in out
    assert "body" not in out
    assert "authentication" not in out
    assert "unknown" not in out
    assert out["query_parameters"] == {"page": "1"}


def test_declared_field_with_reserved_name_blocked():
    # 用户字段声明成保留键名（重排侧已避让）→ 叠加侧同样拦截
    wrapper = _make_wrapper(
        inputs_schema={"query_parameters": {}, "headers": {}},
        configs={"userFields": {"inputs": [{"id": "body", "sourceType": "input"}]}},
    )
    out = wrapper._preprocess_inputs({"body": "evil"})
    assert "body" not in out
