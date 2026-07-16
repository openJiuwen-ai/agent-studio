#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2025

"""验证 loop 节点 _loop_inputs_transformer 跳过 deepcopy 的行为。

背景: IRConverter 在 jiuwen.loop 节点上注册的 inputs_schema 是一个 callable
(_loop_inputs_transformer)。运行时 Vertex._pre_invoke 通过
state.get_inputs_by_transformer → InMemoryCommitState.get_by_transformer →
transformer(self._state) 调用它，传入的 self._state 是 InMemoryStateLike
实例（不是 dict）。原实现里 `data = getter()` 命中
InMemoryStateLike.get_state() 默认 copied=True，每次循环迭代都对整个
io_state 做一次 deepcopy，开销偏大。

修复后: transformer 优先 getter(copied=False) 拿原始 dict 引用，跳过 deepcopy。
由于 transformer 内部仅调用 get_by_schema（纯只读，无写入），返回值是新建
dict/list，不会回写 io_state，因此跳过 deepcopy 是安全的。

测试覆盖:
1. 传入 InMemoryStateLike 实例时，transformer 调用前后内部 _state 的 id 不变
   （即未被 deepcopy），且 transformer 不会修改 io_state 内容。
2. 传入 dict 时（已为 dict，不调 get_state），transformer 正常解析。
3. 传入不支持 copied 关键字的 get_state 实现时，兜底分支能正常工作。
4. 通过 IRConverter._add_component 真实路径构造 loop 节点，截获注册的
   inputs_schema callable，验证它收到 copied=False。
"""

from unittest.mock import MagicMock

import pytest

from openjiuwen.core.session.state.base import InMemoryStateLike
from jiuwen.serve.controllers.execution import ir_converter as ir_conv_module
from jiuwen.serve.controllers.execution.ir_converter import IRConverter


pytestmark = pytest.mark.asyncio


class _MockStateWithCopiedParam:
    """Mock state that supports copied parameter to avoid deepcopy."""

    def __init__(self, state_dict):
        self._state = state_dict

    def get_state(self, copied=True):
        import copy
        if copied:
            return copy.deepcopy(self._state)
        return self._state


class _FakeLoopComponent:
    """替代真实 LoopComponent，避免 check_validate 校验空 LoopGroup。

    测试聚焦 transformer 行为，不依赖 LoopGroup 内部结构。
    """

    def __init__(self, loop_group, output_schema=None):
        self.loop_group = loop_group
        self.output_schema = output_schema


def _build_loop_node(node_id="node_loop_1", loop_type="numLoop", num_var=3):
    """构造一个最小的 loop IR 节点 dict。"""
    return {
        "id": node_id,
        "name": "loop node",
        "type": "jiuwen.loop",
        "configs": {
            "loopType": loop_type,
            "loopBody": [],
        },
        "inputs": {"numLoopVar": num_var} if loop_type == "numLoop" else {},
        "outputs": {},
    }


async def _capture_loop_transformer(node):
    """通过 IRConverter._add_component 真实路径注册 loop 节点，
    截获传给 workflow.add_workflow_comp 的 inputs_schema callable。

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

    transformer = captured.get("inputs_schema")
    assert callable(transformer), f"inputs_schema should be callable, got {transformer!r}"
    return transformer


async def test_loop_inputs_transformer_does_not_deepcopy_inmemory_state(monkeypatch):
    """transformer 接收支持 copied 参数的 state 实例时不应 deepcopy 内部 _state。

    通过 spy copy.deepcopy 计数验证：transformer 调用期间 deepcopy 应被 0 次调用
    （原 bug 是 state.get_state() 默认 copied=True 触发 deepcopy）。

    同时验证:
    - 调用后 state._state 内容未被修改（只读保证）
    - transformer 返回的 dict 中 loop_type/loop_number 正确
    """
    import copy as _copy

    deepcopy_calls = []
    original_deepcopy = _copy.deepcopy

    def _spy_deepcopy(obj, *args, **kwargs):
        deepcopy_calls.append(obj)
        return original_deepcopy(obj, *args, **kwargs)

    monkeypatch.setattr(_copy, "deepcopy", _spy_deepcopy)

    io_state_dict = {
        "node_start": {"userFields": {"query": "hello world"}},
        "node_llm_1": {"raw_output": "llm result"},
        "_big_field": [{"k": i} for i in range(50)],
    }
    state_like = _MockStateWithCopiedParam(io_state_dict)
    original_state_content = state_like.get_state(copied=False)

    transformer = await _capture_loop_transformer(_build_loop_node())

    deepcopy_calls.clear()
    result = transformer(state_like)

    # 1. transformer 调用期间 deepcopy 应被 0 次（核心断言）
    assert len(deepcopy_calls) == 0, \
        f"transformer should not trigger deepcopy, but got {len(deepcopy_calls)} calls"

    # 2. _state 内容未被修改（只读保证）
    assert state_like.get_state(copied=False) == original_state_content, \
        "transformer should not modify io_state content"

    # 3. 返回值是 dict，包含 loop_type 等字段（numLoop → number）
    assert isinstance(result, dict)
    assert result.get("loop_type") == "number"
    assert result.get("loop_number") == 3


async def test_loop_inputs_transformer_resolves_dict_state():
    """transformer 接收 dict 时（已是 dict，不调 get_state），正常返回。"""
    transformer = await _capture_loop_transformer(_build_loop_node())

    io_state = {"node_start": {"userFields": {"query": "hi"}}}
    result = transformer(io_state)
    assert isinstance(result, dict)
    assert result["loop_type"] == "number"
    assert result["loop_number"] == 3


async def test_loop_inputs_transformer_fallback_for_unsupported_copied_kw():
    """当 state.get_state 不接受 copied 关键字时，兜底分支应正常工作。"""
    transformer = await _capture_loop_transformer(_build_loop_node())

    class LegacyState:
        def __init__(self, data):
            self._data = data

        def get_state(self):  # 不接受 copied 关键字
            return self._data

    legacy = LegacyState({"node_start": {"userFields": {"query": "legacy"}}})
    # 不应抛 TypeError，应走兜底分支
    result = transformer(legacy)
    assert isinstance(result, dict)
    assert result["loop_type"] == "number"


async def test_loop_inputs_transformer_uses_copied_false_when_supported():
    """当 state.get_state 支持 copied 关键字时，应传 copied=False 跳过 deepcopy。"""
    transformer = await _capture_loop_transformer(_build_loop_node())

    call_kwargs_log = []

    class TracingState(InMemoryStateLike):
        def get_state(self, **kwargs):
            call_kwargs_log.append(dict(kwargs))
            return super().get_state(**kwargs)

    tracing = TracingState()
    tracing.set_state({"node_start": {"userFields": {"query": "trace"}}})

    _ = transformer(tracing)
    assert call_kwargs_log, "get_state should be called at least once"
    assert any(kw.get("copied") is False for kw in call_kwargs_log), \
        f"expected copied=False in get_state calls, got {call_kwargs_log}"
