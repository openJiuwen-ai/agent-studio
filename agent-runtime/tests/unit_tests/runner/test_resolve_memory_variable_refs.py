# -*- coding: UTF-8 -*-
"""resolve_memory_variable_refs 回归：空数组下标记忆引用不得写回 None 删除。

背景：Start→End 直连，End 引用 ${MEMORY_VARIABLE.a[0].b}，memory.a=[] 时
get_global 返回 None。旧逻辑 update_global({'a[0].b': None}) 触发
update_dict 删除语义 → root_to_path 穿越空数组失败 →
TypeError: argument of type 'NoneType' is not iterable。
"""

from agent_runtime.runner.workflow_stream_data_wrapper import (
    resolve_memory_variable_refs,
)


class _FakeState:
    def __init__(self, values: dict):
        self._values = values

    def get_global(self, key):
        return self._values.get(key)


def test_resolve_memory_ref_miss_fills_inputs_without_global_write():
    """缺失的 MEMORY_VARIABLE.a[0].b 只进 inputs，不产生可触发删除的回写。"""
    schema = {"b": "${MEMORY_VARIABLE.a[0].b}", "c": "literal"}
    inputs = {"b": "${MEMORY_VARIABLE.a[0].b}", "c": "c"}
    state = _FakeState({"MEMORY_VARIABLE.a": []})  # 无 a[0].b

    resolve_memory_variable_refs(schema, inputs, state)

    assert inputs["b"] is None
    assert inputs["c"] == "c"
    # 权威 global 仍是空数组，未被 None 删除污染
    assert state._values == {"MEMORY_VARIABLE.a": []}


def test_resolve_memory_ref_hit_fills_inputs():
    schema = {"b": "${MEMORY_VARIABLE.a[0].b}"}
    inputs = {}
    state = _FakeState({"MEMORY_VARIABLE.a[0].b": "from_mem"})

    resolve_memory_variable_refs(schema, inputs, state)

    assert inputs["b"] == "from_mem"


def test_resolve_nested_schema():
    schema = {"userFields": {"b": "${MEMORY_VARIABLE.a[0].b}"}}
    inputs = {}
    state = _FakeState({})

    resolve_memory_variable_refs(schema, inputs, state)

    assert inputs["userFields"]["b"] is None
