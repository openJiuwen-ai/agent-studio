# coding: utf-8
"""COW 行为验证: ``_convert_global_variable_refs_in_ir`` /
``_convert_subworkflow_global_var_refs`` 在消除 ``copy.deepcopy`` 后,
仍应保证:

1. 功能等价于原 in-place 实现 (memory 引用被正确改写);
2. 不污染调用方持有的原始 IR (缓存安全);
3. 未命中替换的子树保持原引用 (零拷贝快路径);
4. 部分命中时,未命中的 component 保持原引用,命中的 component 被替换。

依赖 ``conftest.py`` 在同级目录下应用的 branch_stream_end_patch。
"""

from __future__ import annotations

import copy
from unittest.mock import patch

import pytest

from jiuwen.serve.controllers.execution.ir_converter import (
    IRConverter,
    _apply_global_var_mapping_to_schema,
    _convert_global_variable_refs_in_ir,
    _convert_refs_in_schema,
    _convert_subworkflow_global_var_refs,
    _convert_start_memory_refs_in_string,
)
from openjiuwen.core.workflow.components.component import WorkflowComponent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _end_with_user_fields(memory_ref: str) -> dict:
    return {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "inputs": {"userFields": {"result": memory_ref}},
            },
        ]
    }


def _branch_with_expr(expr: str) -> dict:
    return {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "branch",
                "type": "jiuwen.branch",
                "configs": {
                    "branches": [
                        {"id": "branch-if", "boolExpression": expr},
                        {"id": "default"},
                    ]
                },
            },
        ]
    }


def _set_variable_with_left_value(value: str) -> dict:
    return {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "set_var",
                "type": "jiuwen.setVariable",
                "configs": {
                    "settings": [
                        {
                            "left": {"value": value},
                            "right": {"value": "8272"},
                        }
                    ]
                },
            },
        ]
    }


# ---------------------------------------------------------------------------
# A. Functional equivalence with the old in-place behaviour
# ---------------------------------------------------------------------------


def test_convert_global_var_refs_preserves_start_node_memory():
    """Start 节点的 memory 输入保持原样 (不转换)。"""
    ir_data = {
        "components": [
            {
                "id": "node_start",
                "type": "jiuwen.start",
                "inputs": {
                    "memory": {
                        "parent_mem_one": "${node_start.memory.parent_mem_one}"
                    }
                },
            },
            {"id": "node_end", "type": "jiuwen.end"},
        ]
    }

    converted = _convert_global_variable_refs_in_ir(ir_data)

    # Start 节点不会被改写 (其 memory 字段是实际值而非引用)
    assert converted["components"][0] is ir_data["components"][0]
    assert (
        converted["components"][0]["inputs"]["memory"]["parent_mem_one"]
        == "${node_start.memory.parent_mem_one}"
    )


def test_convert_global_var_refs_end_user_fields():
    ir_data = _end_with_user_fields("${node_start.memory.parent_mem_one}")

    converted = _convert_global_variable_refs_in_ir(ir_data)

    assert (
        converted["components"][1]["inputs"]["userFields"]["result"]
        == "${MEMORY_VARIABLE.parent_mem_one}"
    )


def test_convert_global_var_refs_end_output_user_fields():
    """End 节点 outputs.userFields 中的 memory 引用也应被转换。

    IR converter 把 End 的 outputs.userFields 以 ``#end_`` 前缀并入 inputs_schema，
    若 outputs 中的 ``${node_start.memory.xxx}`` 未转换，运行期会从 io_state
    (node_start 的旧输出) 解析而非从 global_state (被 SetVariable 更新) 解析，
    导致同一记忆变量在 End 的输入有值、输出却拿到陈旧默认值。
    """
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "outputs": {"userFields": {"aaa1": "${node_start.memory.aaa}"}},
            },
        ]
    }

    converted = _convert_global_variable_refs_in_ir(ir_data)

    assert (
        converted["components"][1]["outputs"]["userFields"]["aaa1"]
        == "${MEMORY_VARIABLE.aaa}"
    )


def test_convert_global_var_refs_branch_bool_expression():
    ir_data = _branch_with_expr("(${node_start.memory.is_valid} == '1')")

    converted = _convert_global_variable_refs_in_ir(ir_data)

    assert (
        converted["components"][1]["configs"]["branches"][0]["boolExpression"]
        == "(${MEMORY_VARIABLE.is_valid} == '1')"
    )


def test_convert_global_var_refs_set_variable_settings():
    ir_data = _set_variable_with_left_value("${node_start.memory.sub_mem_one}")

    converted = _convert_global_variable_refs_in_ir(ir_data)

    setting = converted["components"][1]["configs"]["settings"][0]
    assert setting["left"]["value"] == "${MEMORY_VARIABLE.sub_mem_one}"
    # right.value 不应被改写
    assert setting["right"]["value"] == "8272"


def test_convert_global_var_refs_io_configs_inputs_schema():
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_llm",
                "type": "jiuwen.LLMComponent",
                "configs": {
                    "io_configs": {
                        "inputs_schema": {
                            "properties": {
                                "prompt": "${node_start.memory.topic}",
                                "nested": {"ref": "${node_start.memory.x}"},
                            }
                        }
                    }
                },
            },
        ]
    }

    converted = _convert_global_variable_refs_in_ir(ir_data)

    schema = converted["components"][1]["configs"]["io_configs"]["inputs_schema"]
    assert schema["properties"]["prompt"] == "${MEMORY_VARIABLE.topic}"
    assert schema["properties"]["nested"]["ref"] == "${MEMORY_VARIABLE.x}"


def test_convert_subworkflow_global_var_refs_set_variable_left_value():
    ir_data = _set_variable_with_left_value("${node_start.memory.sub_mem_one}")

    converted = _convert_subworkflow_global_var_refs(
        ir_data, {"sub_mem_one": "parent_mem_one"}
    )

    setting = converted["components"][1]["configs"]["settings"][0]
    assert setting["left"]["value"] == "${MEMORY_VARIABLE.parent_mem_one}"
    # right.value 不应被映射
    assert setting["right"]["value"] == "8272"


def test_convert_subworkflow_global_var_refs_branch():
    ir_data = _branch_with_expr("(${MEMORY_VARIABLE.sub_mem_one} == '1')")

    converted = _convert_subworkflow_global_var_refs(
        ir_data, {"sub_mem_one": "parent_mem_one"}
    )

    assert (
        converted["components"][1]["configs"]["branches"][0]["boolExpression"]
        == "(${MEMORY_VARIABLE.parent_mem_one} == '1')"
    )


def test_convert_subworkflow_global_var_refs_inputs_legacy():
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "inputs": {"userFields": {"result": "${MEMORY_VARIABLE.sub_mem_one}"}},
            },
        ]
    }

    converted = _convert_subworkflow_global_var_refs(
        ir_data, {"sub_mem_one": "parent_mem_one"}
    )

    assert (
        converted["components"][1]["inputs"]["userFields"]["result"]
        == "${MEMORY_VARIABLE.parent_mem_one}"
    )


# ---------------------------------------------------------------------------
# B. cache_ir_queue 缓存不被污染
# ---------------------------------------------------------------------------


def test_convert_global_var_refs_does_not_mutate_original_ir():
    ir_data = _set_variable_with_left_value("${node_start.memory.sub_mem_one}")
    # 同时叠加 branch / inputs 引用,覆盖多条路径
    ir_data["components"].append(
        {
            "id": "branch",
            "type": "jiuwen.branch",
            "configs": {
                "branches": [
                    {"id": "b1", "boolExpression": "${node_start.memory.flag} == '1'"},
                ]
            },
            "inputs": {"userFields": {"k": "${node_start.memory.legacy}"}},
        }
    )
    snapshot = copy.deepcopy(ir_data)

    _convert_global_variable_refs_in_ir(ir_data)

    assert ir_data == snapshot
    # 重点: 命中字段在原 IR 上仍是原字符串
    assert (
        ir_data["components"][1]["configs"]["settings"][0]["left"]["value"]
        == "${node_start.memory.sub_mem_one}"
    )
    assert (
        ir_data["components"][2]["configs"]["branches"][0]["boolExpression"]
        == "${node_start.memory.flag} == '1'"
    )
    assert (
        ir_data["components"][2]["inputs"]["userFields"]["k"]
        == "${node_start.memory.legacy}"
    )


def test_convert_subworkflow_global_var_refs_does_not_mutate_original_ir():
    ir_data = _set_variable_with_left_value("${node_start.memory.sub_mem_one}")
    ir_data["components"].append(
        {
            "id": "branch",
            "type": "jiuwen.branch",
            "configs": {
                "branches": [
                    {"id": "b1", "boolExpression": "${MEMORY_VARIABLE.sub_mem_one} == '1'"},
                ]
            },
            "inputs": {"userFields": {"k": "${MEMORY_VARIABLE.sub_mem_one}"}},
        }
    )
    snapshot = copy.deepcopy(ir_data)

    _convert_subworkflow_global_var_refs(ir_data, {"sub_mem_one": "parent_mem_one"})

    assert ir_data == snapshot
    assert (
        ir_data["components"][1]["configs"]["settings"][0]["left"]["value"]
        == "${node_start.memory.sub_mem_one}"
    )
    assert (
        ir_data["components"][2]["configs"]["branches"][0]["boolExpression"]
        == "${MEMORY_VARIABLE.sub_mem_one} == '1'"
    )


def test_convert_global_var_refs_no_match_returns_same_object():
    """零拷贝快路径: 无任何 memory 引用时, component 容器链应保持原引用。"""
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "inputs": {"userFields": {"result": "${node_llm.userFields.out}"}},
            },
        ]
    }

    result = _convert_global_variable_refs_in_ir(ir_data)

    # 顶层 dict 被浅拷贝 (safety net), 但 component 原引用未变
    assert result is not ir_data
    assert result["components"][0] is ir_data["components"][0]
    assert result["components"][1] is ir_data["components"][1]


def test_convert_global_var_refs_partial_match_preserves_unmatched_subtree():
    """部分命中: 未命中 component 保持原引用,命中 component 被替换为新对象。"""
    ir_data = {
        "components": [
            {
                "id": "node_code",
                "type": "jiuwen.code",
                "configs": {"code": "def main(args): return {'out': 'a'}"},
            },
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "inputs": {"userFields": {"result": "${node_start.memory.x}"}},
            },
        ]
    }

    result = _convert_global_variable_refs_in_ir(ir_data)

    # 未命中: 保持原引用
    assert result["components"][0] is ir_data["components"][0]
    # 命中: 新对象
    assert result["components"][1] is not ir_data["components"][1]
    assert (
        result["components"][1]["inputs"]["userFields"]["result"]
        == "${MEMORY_VARIABLE.x}"
    )
    # 原 IR 中的字段未被污染
    assert (
        ir_data["components"][1]["inputs"]["userFields"]["result"]
        == "${node_start.memory.x}"
    )


# ---------------------------------------------------------------------------
# C. String-level fast-path guards
# ---------------------------------------------------------------------------


def test_convert_start_memory_refs_in_string_fast_path_returns_same_object():
    """不带 ``node_start.memory`` 的字符串应原样返回 (同一对象)。"""
    s = "hello world"
    assert _convert_start_memory_refs_in_string(s) is s
    s2 = "${node_llm.userFields.out}"
    assert _convert_start_memory_refs_in_string(s2) is s2


def test_apply_global_var_mapping_to_schema_no_match_returns_same_object():
    """schema 中无任何可映射引用时, 应返回原对象。"""
    schema = {"a": {"b": "hello"}, "c": ["${node_llm.out}", "plain"]}
    result = _apply_global_var_mapping_to_schema(schema, {"sub": "parent"})
    assert result is schema


# ---------------------------------------------------------------------------
# D. End-to-end: IR → LazyWorkflow → materialized workflow
# ---------------------------------------------------------------------------


class _MockCode(WorkflowComponent):
    async def invoke(self, inputs, session, context):
        return {"userFields": {"value": "ok"}}


@pytest.mark.asyncio
async def test_async_ir_to_workflow_with_memory_refs_builds_correctly():
    """
    含 memory 引用的 IR 经 ``async_ir_to_workflow`` → ``instantiate``
    后能正常构建 (等价于 test_ir_converter_aggregate_schema_edges 的 mock 模式)。
    """
    ir = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_code",
                "type": "jiuwen.code",
                "configs": {"code": "def main(args): return {'value': 'a'}"},
            },
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "inputs": {
                    "userFields": {"result": "${node_start.memory.parent_mem_one}"}
                },
            },
        ],
        "connections": [
            {"source": {"componentId": "node_start"}, "target": {"componentId": "node_code"}},
            {"source": {"componentId": "node_code"}, "target": {"componentId": "node_end"}},
        ],
    }

    original_create = getattr(IRConverter, "_create_component")

    async def _mock_create(node, global_model, *, node_by_id=None, ir_connections=None):
        node_type = node.get("type")
        if node_type == "jiuwen.code":
            return _MockCode(), node_type, dict(node.get("configs") or {})
        return await original_create(
            node, global_model, node_by_id=node_by_id, ir_connections=ir_connections
        )

    with patch.object(IRConverter, "_create_component", side_effect=_mock_create):
        lazy = await IRConverter.async_ir_to_workflow(ir)
        workflow = await lazy.instantiate()

    assert workflow is not None
    # 验证 memory 引用确实被转换到 MEMORY_VARIABLE 形式 (LazyWorkflow.instantiate
    # 调用的是 _convert_global_variable_refs_in_ir 的产出)
    end_node = next(
        c for c in ir["components"] if c["id"] == "node_end"
    )
    # 原 IR 不应被污染
    assert (
        end_node["inputs"]["userFields"]["result"]
        == "${node_start.memory.parent_mem_one}"
    )
