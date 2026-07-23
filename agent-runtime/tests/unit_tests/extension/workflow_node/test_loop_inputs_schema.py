#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2025

"""验证 loop 节点注册的 inputs_schema 为 dict 且结构正确。

背景: IRConverter 在 jiuwen.loop 节点上注册的 inputs_schema 原本是自定义
callable (_loop_inputs_transformer)，运行时从绝对根作用域解析 ${...} 引用。
但在子工作流上下文中，子节点输出按 parent_id 嵌套在 subWorkflow 节点子树下，
callable 从根解析会取不到同级子节点输出，导致 arrLoopVar 落地为字面量字符串
而触发 "Expected list/tuple ... got str"。

修复后: loop 节点直接以 dict 作为 inputs_schema，交由 core 标准路径
state.get_inputs → io_state.get_by_prefix(schema, parent_id) → get_by_schema
按 parent_id 作用域解析，与所有其他节点一致。${...} 引用原样保留在 dict 中，
由 core 在运行时解析。

测试覆盖:
1. inputs_schema 是 dict 而非 callable。
2. numLoop: loop_type="number"，loop_number 取自 numLoopVar。
3. arrayLoop: loop_type="array"，loop_array 以 arrLoopVar.item 为键，
   ${...} 引用原样保留（不在注册时解析）。
4. intermediateLoopVar: intermediate_var 以 intermediateLoopVar 为键，值原样保留。
5. 三者同时存在时结构正确。
"""

from unittest.mock import MagicMock

import pytest

from jiuwen.serve.controllers.execution import ir_converter as ir_conv_module
from jiuwen.serve.controllers.execution.ir_converter import IRConverter


pytestmark = pytest.mark.asyncio


class _FakeLoopComponent:
    """替代真实 LoopComponent，避免 check_validate 校验空 LoopGroup。

    测试聚焦 inputs_schema 结构，不依赖 LoopGroup 内部结构。
    """

    def __init__(self, loop_group, output_schema=None):
        self.loop_group = loop_group
        self.output_schema = output_schema


def _build_loop_node(node_id="node_loop_1", loop_type="numLoop",
                     num_var=3, arr_var=None, intermediate_var=None):
    """构造一个最小的 loop IR 节点 dict。"""
    inputs = {}
    if loop_type == "numLoop":
        inputs["numLoopVar"] = num_var
    if arr_var is not None:
        inputs["arrLoopVar"] = arr_var
    if intermediate_var is not None:
        inputs["intermediateLoopVar"] = intermediate_var
    return {
        "id": node_id,
        "name": "loop node",
        "type": "jiuwen.loop",
        "configs": {"loopType": loop_type, "loopBody": []},
        "inputs": inputs,
        "outputs": {},
    }


async def _capture_loop_inputs_schema(node):
    """通过 IRConverter._add_component 真实路径注册 loop 节点，
    截获传给 workflow.add_workflow_comp 的 inputs_schema。

    monkey-patch LoopComponent 为 _FakeLoopComponent，绕过空 LoopGroup 校验。
    """
    captured = {}

    def fake_add_workflow_comp(comp_id, component, **kwargs):
        captured["comp_id"] = comp_id
        captured["inputs_schema"] = kwargs.get("inputs_schema")

    workflow = MagicMock()
    workflow.add_workflow_comp.side_effect = fake_add_workflow_comp

    original = ir_conv_module.LoopComponent
    ir_conv_module.LoopComponent = _FakeLoopComponent
    try:
        _add_component = getattr(IRConverter, "_add_component")
        await _add_component(
            workflow,
            node,
            global_model=None,
            node_by_id={node["id"]: node},
            ir_connections=[],
        )
    finally:
        ir_conv_module.LoopComponent = original

    inputs_schema = captured.get("inputs_schema")
    assert isinstance(inputs_schema, dict), \
        f"inputs_schema should be a dict, got {type(inputs_schema).__name__}: {inputs_schema!r}"
    return inputs_schema


async def test_loop_inputs_schema_is_dict_not_callable():
    """loop 节点注册的 inputs_schema 应为 dict（修复后不再用 callable transformer）。"""
    inputs_schema = await _capture_loop_inputs_schema(_build_loop_node())
    assert isinstance(inputs_schema, dict)
    assert not callable(inputs_schema)


async def test_num_loop_inputs_schema():
    """numLoop: loop_type="number"，loop_number 取自 numLoopVar。"""
    inputs_schema = await _capture_loop_inputs_schema(_build_loop_node(num_var=5))
    assert inputs_schema["loop_type"] == "number"
    assert inputs_schema["loop_number"] == 5
    assert "loop_array" not in inputs_schema


async def test_array_loop_inputs_schema_preserves_ref():
    """arrayLoop: loop_array 以 arrLoopVar.item 为键，${...} 引用原样保留供 core 运行时解析。"""
    arr_ref = "${node_code_1.userFields.key0}"
    inputs_schema = await _capture_loop_inputs_schema(
        _build_loop_node(loop_type="arrayLoop", arr_var=arr_ref)
    )
    assert inputs_schema["loop_type"] == "array"
    assert inputs_schema["loop_array"] == {"arrLoopVar.item": arr_ref}
    # 引用必须原样保留，不能在注册阶段被解析成值或字面量
    assert inputs_schema["loop_array"]["arrLoopVar.item"] == arr_ref


async def test_intermediate_var_inputs_schema():
    """intermediateLoopVar: intermediate_var 以 intermediateLoopVar 为键，值原样保留。"""
    inter = {"tmp": "10"}
    inputs_schema = await _capture_loop_inputs_schema(
        _build_loop_node(loop_type="arrayLoop", arr_var="${node_x.y}", intermediate_var=inter)
    )
    assert inputs_schema["intermediate_var"] == {"intermediateLoopVar": inter}


async def test_combined_loop_inputs_schema():
    """三者同时存在时结构正确。"""
    inputs_schema = await _capture_loop_inputs_schema(
        _build_loop_node(
            loop_type="arrayLoop",
            arr_var="${node_code_1.userFields.list}",
            intermediate_var={"tmp": "${node_loop_1.intermediateLoopVar.tmp}"},
        )
    )
    assert inputs_schema["loop_type"] == "array"
    assert inputs_schema["loop_array"] == {"arrLoopVar.item": "${node_code_1.userFields.list}"}
    assert inputs_schema["intermediate_var"] == {
        "intermediateLoopVar": {"tmp": "${node_loop_1.intermediateLoopVar.tmp}"}
    }
