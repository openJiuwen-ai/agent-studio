#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单测需直接调用内部方法 _prepare_child_inputs

from unittest.mock import MagicMock

import pytest
from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow
from jiuwen.serve.controllers.execution.ir_converter import (
    _convert_global_variable_refs_in_ir,
    _convert_subworkflow_global_var_refs,
)


def test_parent_start_userfields_memory_refs_convert_to_memory_variable():
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "inputs": {
                    "userFields": {
                        "result": "${node_start.memory.parent_mem_one}"
                    }
                },
            },
        ]
    }

    converted = _convert_global_variable_refs_in_ir(ir_data)

    assert (
        converted["components"][1]["inputs"]["userFields"]["result"]
        == "${MEMORY_VARIABLE.parent_mem_one}"
    )


def test_parent_branch_memory_refs_convert_to_memory_variable():
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "branch",
                "type": "jiuwen.branch",
                "configs": {
                    "branches": [
                        {
                            "id": "branch-if",
                            "boolExpression": "(${node_start.memory.is_valid} == '1')",
                        },
                        {"id": "default"},
                    ]
                },
            },
        ]
    }

    converted = _convert_global_variable_refs_in_ir(ir_data)

    assert (
        converted["components"][1]["configs"]["branches"][0]["boolExpression"]
        == "(${MEMORY_VARIABLE.is_valid} == '1')"
    )


def test_child_memory_refs_are_mapped_to_parent_memory_variable():
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "set_var",
                "type": "jiuwen.setVariable",
                "configs": {
                    "settings": [
                        {
                            "left": {
                                "value": "${node_start.memory.sub_mem_one}"
                            },
                            "right": {"value": "8272"},
                        }
                    ]
                },
                "inputs": {
                    "userFields": {
                        "sub_mem_one": "${node_start.memory.sub_mem_one}"
                    }
                },
            },
        ]
    }

    converted = _convert_subworkflow_global_var_refs(
        ir_data, {"sub_mem_one": "parent_mem_one"}
    )

    setting = converted["components"][1]["configs"]["settings"][0]
    assert setting["left"]["value"] == "${MEMORY_VARIABLE.parent_mem_one}"
    assert (
        converted["components"][1]["inputs"]["userFields"]["sub_mem_one"]
        == "${MEMORY_VARIABLE.parent_mem_one}"
    )


def test_child_branch_memory_refs_are_mapped_to_parent_memory_variable():
    ir_data = {
        "components": [
            {"id": "node_start", "type": "jiuwen.start"},
            {
                "id": "branch",
                "type": "jiuwen.branch",
                "configs": {
                    "branches": [
                        {
                            "id": "branch-if",
                            "boolExpression": "(${MEMORY_VARIABLE.sub_mem_one} == '1')",
                        },
                        {"id": "default"},
                    ]
                },
            },
        ]
    }

    converted = _convert_subworkflow_global_var_refs(
        ir_data, {"sub_mem_one": "parent_mem_one"}
    )

    assert (
        converted["components"][1]["configs"]["branches"][0]["boolExpression"]
        == "(${MEMORY_VARIABLE.parent_mem_one} == '1')"
    )


@pytest.mark.asyncio
async def test_subworkflow_passes_memory_mapping_values_to_child_global_variables():
    component = SubWorkflow(
        {
            "node_id": "sub_node",
            "userFields": {"inputs": [], "outputs": []},
            "systemFields": {"inputs": [], "outputs": []},
            "preDefineFields": {},
            "reference": {"id": "child", "path": "child.json"},
        }
    )
    session = MagicMock()
    session.get_env.return_value = None
    session.dump_state.return_value = {"comp_state": {}}
    session.get_state.return_value = {}
    session.get_global_state.return_value = {
        "conversationId": "conv-1",
        "userId": "user-1",
    }

    child_inputs = await component._prepare_child_inputs(
        {
            "systemFields": {"query": "hello"},
            "userFields": {},
            "memory": {"sub_mem_one": "parent-value"},
        },
        session,
        None,
        for_stream=True,
    )

    assert child_inputs["global_variables"]["sub_mem_one"] == "parent-value"
    assert child_inputs["global_variables"]["userId"] == "user-1"


@pytest.mark.asyncio
async def test_subworkflow_user_fields_override_same_named_memory_fields():
    component = SubWorkflow(
        {
            "node_id": "sub_node",
            "userFields": {"inputs": [], "outputs": []},
            "systemFields": {"inputs": [], "outputs": []},
            "preDefineFields": {},
            "reference": {"id": "child", "path": "child.json"},
        }
    )
    session = MagicMock()
    session.get_env.return_value = None
    session.dump_state.return_value = {"comp_state": {}}
    session.get_state.return_value = {}
    session.get_global_state.return_value = {
        "conversationId": "conv-1",
        "userId": "user-1",
    }

    child_inputs = await component._prepare_child_inputs(
        {
            "systemFields": {"query": "hello"},
            "userFields": {"amount": "100", "currency": "CNY"},
            "memory": {"amount": None, "is_valid": None, "currency": None},
        },
        session,
        None,
        for_stream=True,
    )

    assert child_inputs["amount"] == "100"
    assert child_inputs["currency"] == "CNY"
    assert child_inputs["is_valid"] is None
    assert child_inputs["global_variables"]["amount"] == "100"
    assert child_inputs["global_variables"]["currency"] == "CNY"
    assert child_inputs["global_variables"]["is_valid"] is None


def test_subworkflow_collects_updated_memory_from_memory_variable_global_key():
    component = SubWorkflow(
        {
            "node_id": "sub_node",
            "userFields": {"inputs": [], "outputs": []},
            "systemFields": {"inputs": [], "outputs": []},
            "preDefineFields": {},
            "reference": {"id": "child", "path": "child.json"},
        }
    )

    session = MagicMock()
    values = {"MEMORY_VARIABLE.parent_mem_one": "8272", "parent_mem_one": None}
    session.get_global_state.side_effect = lambda key=None: values.get(key)

    # 变量名经参数传递（`_global_var_names` 已局部化，不再落组件实例属性）
    assert component._collect_updated_memory(session, ["parent_mem_one"]) == {
        "parent_mem_one": "8272"
    }
