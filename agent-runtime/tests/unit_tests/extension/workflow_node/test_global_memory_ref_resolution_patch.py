# -*- coding: UTF-8 -*-
"""global_memory_ref_resolution_patch 单元测试。

验证 CommitState.get_inputs 对 ${MEMORY_VARIABLE.xxx} 引用的 global_state 兜底：
- 循环体内写入的记忆变量，循环外节点输入解析可取到（核心缺陷场景）
- 未命中时维持原结果，不影响未执行分支保护
- 非记忆变量引用行为零变化
- io_state 已有实际值时不覆盖（fill-when-missing）
"""

from jiuwen.extension.patches.global_memory_ref_resolution_patch import (
    GLOBAL_REF_PREFIX,
    _patched_commit_state_get_inputs,
    _resolve_memory_leaves,
    apply_global_memory_ref_resolution_patch,
)

# 幂等应用：无论生产代码（ir_converter / sub_workflow 导入时）是否已先行应用，
# 均确保本测试进程内补丁生效；返回 True/False 均为正常路径
apply_global_memory_ref_resolution_patch()

from openjiuwen.core.session import NodeSession, SubWorkflowSession, WorkflowSession  # noqa: E402
from openjiuwen.core.session.state.workflow_state import CommitState, InMemoryState  # noqa: E402


def test_patch_hooked_on_commit_state():
    """补丁必须真正挂载到 CommitState.get_inputs（状态断言，不依赖 apply 返回值）。"""
    assert CommitState.get_inputs is _patched_commit_state_get_inputs


GLOBAL_REF = "${" + GLOBAL_REF_PREFIX + "mem_counter}"


def _build_loop_scenario():
    """还原真实执行会话层级：工作流 → 循环节点 → SubWorkflowSession → 循环体。

    返回 (wf_session, sub_wf_session)。
    """
    wf_session = WorkflowSession(workflow_id="main_wf", parent=None)
    wf_session._state = InMemoryState()  # pylint: disable=protected-access
    loop_node_session = NodeSession(wf_session, "node_loop_1")
    sub_wf_session = SubWorkflowSession(loop_node_session, "loop_body_wf")
    return wf_session, sub_wf_session


def _write_memory_inside_loop(sub_wf_session, var_name, value):
    """模拟循环体内 LoopSetVariable 写记忆变量（root_session.update_global）。"""
    set_var_inner = NodeSession(sub_wf_session, "node_set_var")
    root_session = set_var_inner.parent()
    root_session.state().update_global({f"{GLOBAL_REF_PREFIX}{var_name}": value})
    root_session.state().commit()


def test_memory_ref_resolves_outside_loop():
    """核心场景：循环内写入 → 循环外 get_inputs 解析到值（修复前为 None）。"""
    wf_session, sub_wf_session = _build_loop_scenario()
    _write_memory_inside_loop(sub_wf_session, "mem_counter", "loop_value_1")

    after_loop = NodeSession(wf_session, "node_after_loop")
    schema = {"userFields": {"result": GLOBAL_REF}}
    resolved = after_loop.state().get_inputs(schema)
    assert resolved["userFields"]["result"] == "loop_value_1"


def test_end_node_style_ref_not_blank():
    """End 节点 #end_ 前缀映射场景：引用可解析，不再被 sanitize 置空的前提成立。"""
    wf_session, sub_wf_session = _build_loop_scenario()
    _write_memory_inside_loop(sub_wf_session, "answer", "from_loop")

    end_node = NodeSession(wf_session, "node_end")
    schema = {"userFields": {"#end_result": "${" + GLOBAL_REF_PREFIX + "answer}"}}
    resolved = end_node.state().get_inputs(schema)
    assert resolved["userFields"]["#end_result"] == "from_loop"


def test_unresolved_memory_ref_stays_none():
    """global_state 也无该变量时维持 None（交由既有保护逻辑，不新增行为）。"""
    wf_session, _ = _build_loop_scenario()
    node = NodeSession(wf_session, "node_x")
    schema = {"userFields": {"result": "${" + GLOBAL_REF_PREFIX + "never_set}"}}
    resolved = node.state().get_inputs(schema)
    assert resolved["userFields"]["result"] is None


def test_non_memory_refs_unaffected():
    """非 MEMORY_VARIABLE 引用仍走 io_state，行为零变化。"""
    wf_session, _ = _build_loop_scenario()
    start = NodeSession(wf_session, "node_start")
    start.state().set_outputs({"systemFields": {"query": "hello"}})
    start.state().commit()

    node = NodeSession(wf_session, "node_y")
    schema = {"userFields": {"q": "${node_start.systemFields.query}"}}
    resolved = node.state().get_inputs(schema)
    assert resolved["userFields"]["q"] == "hello"

    # io_state 中不存在的节点引用仍为 None（不会被误兜底）
    schema2 = {"userFields": {"x": "${node_missing.out}"}}
    resolved2 = node.state().get_inputs(schema2)
    assert resolved2["userFields"]["x"] is None


def test_io_state_value_not_overridden():
    """io_state 已解析出实际值时不覆盖（fill-when-missing）。"""
    wf_session, _ = _build_loop_scenario()
    # global_state 写入该记忆变量
    seed = NodeSession(wf_session, "node_seed")
    seed.state().update_global({f"{GLOBAL_REF_PREFIX}dup": "from_global"})
    seed.state().commit()
    # 向 io_state 写入同路径的值（模拟异常场景）
    io_state = wf_session.state()._io_state  # pylint: disable=protected-access
    io_state.update_by_id_and_commit("MEMORY_VARIABLE", {"MEMORY_VARIABLE": {"dup": "from_io"}})

    node = NodeSession(wf_session, "node_z")
    schema = {"userFields": {"v": "${" + GLOBAL_REF_PREFIX + "dup}"}}
    resolved = node.state().get_inputs(schema)
    assert resolved["userFields"]["v"] == "from_io"


def test_string_schema_memory_ref():
    """schema 为纯字符串引用时同样兜底。"""
    wf_session, sub_wf_session = _build_loop_scenario()
    _write_memory_inside_loop(sub_wf_session, "plain", "plain_value")

    node = NodeSession(wf_session, "node_s")
    resolved = node.state().get_inputs("${" + GLOBAL_REF_PREFIX + "plain}")
    assert resolved == "plain_value"


def test_list_schema_memory_ref():
    """schema 为列表结构时逐项兜底。"""
    wf_session, sub_wf_session = _build_loop_scenario()
    _write_memory_inside_loop(sub_wf_session, "list_var", [1, 2])

    node = NodeSession(wf_session, "node_l")
    schema = {"items": ["${" + GLOBAL_REF_PREFIX + "list_var}"]}
    resolved = node.state().get_inputs(schema)
    assert resolved["items"] == [[1, 2]]


def test_patch_apply_idempotent():
    """重复 apply 返回 False，不重复包装。"""
    assert apply_global_memory_ref_resolution_patch() is False


def test_resolve_memory_leaves_cow_no_hit():
    """无命中时返回原对象（COW 零拷贝路径）。"""
    schema = {"a": {"b": "${node_x.y}"}}
    result = {"a": {"b": None}}
    assert _resolve_memory_leaves(schema, result, None) is result


def test_resolve_memory_leaves_mismatched_shapes():
    """schema 与 result 结构不一致时安全返回原 result。"""
    assert _resolve_memory_leaves({"a": 1}, "not-a-dict", None) == "not-a-dict"
    assert _resolve_memory_leaves(["x"], "not-a-list", None) == "not-a-list"


def test_resolve_memory_leaves_result_shorter_than_schema():
    """result 短于 schema 时仅在既有槽位内兜底，不越界、不虚构槽位。"""
    wf_session, _ = _build_loop_scenario()
    seed = NodeSession(wf_session, "node_seed")
    seed.state().update_global({f"{GLOBAL_REF_PREFIX}v": "vv"})
    seed.state().commit()
    gs = wf_session.state()._global_state  # pylint: disable=protected-access

    ref = "${" + GLOBAL_REF_PREFIX + "v}"
    # 越界尾项为可命中引用 → 不得 IndexError，原样返回
    assert _resolve_memory_leaves([ref], [], gs) == []
    # 越界项之前存在命中项 → 既有槽位修正、越界槽位忽略（长度不变）
    schema = [ref, "literal", ref]
    assert _resolve_memory_leaves(schema, [None], gs) == ["vv"]


def test_interpolate_embedded_ref_in_composite_string():
    """复合字符串中的内嵌引用在原解析未命中时做插值。"""
    wf_session, _ = _build_loop_scenario()
    seed = NodeSession(wf_session, "node_seed")
    seed.state().update_global({f"{GLOBAL_REF_PREFIX}city": "深圳"})
    seed.state().commit()
    gs = wf_session.state()._global_state  # pylint: disable=protected-access

    schema = "当前城市：${" + GLOBAL_REF_PREFIX + "city}，请确认"
    # 引擎对复合串取首个引用路径查询 → None，插值后应得到完整文本
    assert _resolve_memory_leaves(schema, None, gs) == "当前城市：深圳，请确认"


def test_interpolate_leaves_unresolved_refs_untouched():
    """未命中的内嵌引用保持原样，不伪造空值。"""
    wf_session, _ = _build_loop_scenario()
    seed = NodeSession(wf_session, "node_seed")
    seed.state().update_global({f"{GLOBAL_REF_PREFIX}hit": "H"})
    seed.state().commit()
    gs = wf_session.state()._global_state  # pylint: disable=protected-access

    schema = "${" + GLOBAL_REF_PREFIX + "hit}/${" + GLOBAL_REF_PREFIX + "miss}"
    assert _resolve_memory_leaves(schema, None, gs) == "H/${" + GLOBAL_REF_PREFIX + "miss}"


def test_interpolate_dict_value_as_json():
    """内嵌引用命中 dict/list 时以 JSON 表示。"""
    wf_session, _ = _build_loop_scenario()
    seed = NodeSession(wf_session, "node_seed")
    seed.state().update_global({f"{GLOBAL_REF_PREFIX}obj": {"k": "v"}})
    seed.state().commit()
    gs = wf_session.state()._global_state  # pylint: disable=protected-access

    schema = "data=${" + GLOBAL_REF_PREFIX + "obj}"
    assert _resolve_memory_leaves(schema, None, gs) == 'data={"k": "v"}'


def test_interpolate_skipped_when_resolved_or_no_marker():
    """已解析出实际值、或不含 MEMORY_VARIABLE 标记的串不做插值。"""
    # 已有实际值 → 不覆盖
    schema = "prefix ${" + GLOBAL_REF_PREFIX + "x} suffix"
    assert _resolve_memory_leaves(schema, "already", None) == "already"
    # 含 ${} 但不含标记 → 不进入插值
    assert _resolve_memory_leaves("${node_a.b}", None, None) is None


def test_global_get_isolates_mutable_values():
    """global_state 命中可变容器时返回拷贝，原地修改不污染权威存储。"""
    wf_session, _ = _build_loop_scenario()
    seed = NodeSession(wf_session, "node_seed")
    seed.state().update_global({f"{GLOBAL_REF_PREFIX}cfg": {"k": [1]}})
    seed.state().commit()
    gs = wf_session.state()._global_state  # pylint: disable=protected-access

    from jiuwen.extension.patches.global_memory_ref_resolution_patch import (
        _global_get,
    )

    value = _global_get(gs, f"{GLOBAL_REF_PREFIX}cfg")
    value["k"].append(999)
    value["new"] = 1
    again = _global_get(gs, f"{GLOBAL_REF_PREFIX}cfg")
    assert again == {"k": [1]}
