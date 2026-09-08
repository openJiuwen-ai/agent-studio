# coding: utf-8
"""消息节点纯 batch guard 验证。

背景：LLM 节点 stream:true 时，上游 LLM 会被识别为流式源（ir_stream_source_ids），
``jiuwen.message`` 属于 ``_STREAM_INPUT_CAPABLE_TARGET_TYPES``，原本会被无条件
注册为流式组件（stream_inputs_schema）→ 消息节点所有 ``${batch_ref}`` 被
StreamProcessor 包成等流的 generator 饿死 → 渲染全空、默认值消失。

修复（2026-09-07，纯 batch guard）：消息节点 inputs 若只引用 batch 值
（start userFields / 记忆变量），即使上游有 stream LLM，也不加入
``stream_input_target_ids``、``_is_stream_connection`` 返回 False → 走普通
INVOKE 路径（batch 注册，从 state 读默认值）。

本文件覆盖：
1. ``_message_schema_has_stream_ref`` 判定（单元）
2. ``_is_stream_connection`` 对纯 batch 消息节点的 guard（单元）
3. ``async_ir_to_workflow`` 集成构建：LLM stream + 消息纯 batch 引用 → 消息
   以 batch 注册（stream_inputs_schema 为空）；对照：消息引用 LLM 输出 →
   仍走流式注册。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.workflow.components.base import ComponentAbility
from openjiuwen.core.workflow.components.component import WorkflowComponent


# ---------------------------------------------------------------------------
# _message_schema_has_stream_ref — 单元判定
# ---------------------------------------------------------------------------


class TestMessageSchemaHasStreamRef:
    """消息节点 inputs schema 中是否含流式源引用的判定。"""

    def test_batch_only_refs_return_false(self):
        node = {
            "id": "node_msg",
            "type": "jiuwen.message",
            "inputs": {
                "userFields": {"query": "${node_start.userFields.query}"},
                "systemFields": {},
            },
        }
        assert IRConverter._message_schema_has_stream_ref(node, {"node_llm"}) is False

    def test_memory_variable_ref_is_batch(self):
        # 记忆变量在 IR 转换时变 ${MEMORY_VARIABLE.xxx}，不属于任何流式源
        node = {
            "id": "node_msg",
            "type": "jiuwen.message",
            "inputs": {"userFields": {"mem": "${MEMORY_VARIABLE.flag}"}},
        }
        assert IRConverter._message_schema_has_stream_ref(node, {"node_llm"}) is False

    def test_stream_ref_returns_true(self):
        node = {
            "id": "node_msg",
            "type": "jiuwen.message",
            "inputs": {"userFields": {"content": "${node_llm.raw_output}"}},
        }
        assert IRConverter._message_schema_has_stream_ref(node, {"node_llm"}) is True

    def test_mixed_refs_return_true(self):
        node = {
            "id": "node_msg",
            "type": "jiuwen.message",
            "inputs": {
                "userFields": {
                    "query": "${node_start.userFields.query}",
                    "content": "${node_llm.raw_output}",
                }
            },
        }
        assert IRConverter._message_schema_has_stream_ref(node, {"node_llm"}) is True

    def test_empty_inputs_return_false(self):
        assert IRConverter._message_schema_has_stream_ref({"id": "m", "inputs": {}}, {"node_llm"}) is False
        assert IRConverter._message_schema_has_stream_ref({"id": "m"}, {"node_llm"}) is False


# ---------------------------------------------------------------------------
# _is_stream_connection — guard 使纯 batch 消息节点走普通边
# ---------------------------------------------------------------------------


class TestIsStreamConnectionGuard:
    """_is_stream_connection 对 jiuwen.message 的纯 batch guard。"""

    @staticmethod
    def _components(batch_only: bool) -> list[dict]:
        msg_inputs = (
            {"userFields": {"query": "${node_start.userFields.query}"}}
            if batch_only
            else {"userFields": {"content": "${node_llm.raw_output}"}}
        )
        return [
            {"id": "node_start", "type": "jiuwen.start"},
            {"id": "node_llm", "type": "jiuwen.llm", "configs": {"stream": True}},
            {"id": "node_msg", "type": "jiuwen.message", "inputs": msg_inputs},
        ]

    def test_batch_only_message_uses_regular_edge(self):
        comps = self._components(batch_only=True)
        assert (
            IRConverter._is_stream_connection(comps, "node_llm", "node_msg", {"node_llm"})
            is False
        )

    def test_stream_ref_message_keeps_stream_edge(self):
        comps = self._components(batch_only=False)
        assert (
            IRConverter._is_stream_connection(comps, "node_llm", "node_msg", {"node_llm"})
            is True
        )

    def test_non_message_target_unaffected(self):
        comps = [
            {"id": "node_llm", "type": "jiuwen.llm", "configs": {"stream": True}},
            {
                "id": "node_stream_transform",
                "type": "jiuwen.streamTransform",
                "inputs": {"userFields": {"_input": "${node_llm.raw_output}"}},
            },
        ]
        assert (
            IRConverter._is_stream_connection(
                comps, "node_llm", "node_stream_transform", {"node_llm"}
            )
            is True
        )


# ---------------------------------------------------------------------------
# 集成构建：LLM stream 上游 + 消息节点
# ---------------------------------------------------------------------------


class _MockLLM(WorkflowComponent):
    """替换 _create_component 中 jiuwen.llm 创建的假组件（构建用）。"""

    async def invoke(self, inputs, session, context):
        return {"result": "mock"}


def _build_ir(msg_ref: str) -> dict:
    """构造 start → llm(stream) → msg → end 的 IR。

    msg_ref 决定消息节点引用 batch（start userFields）还是 LLM 流式输出。
    """
    return {
        "components": [
            {
                "id": "node_start",
                "type": "jiuwen.start",
                "inputs": {
                    "userFields": {"query": "hello"},
                    "systemFields": {"query": "", "sys": {}},
                },
                "configs": {
                    "userFields": {
                        "inputs": [
                            {
                                "id": "query",
                                "type": "string",
                                "sourceType": "input",
                                "defaultValue": "hello",
                                "required": True,
                            }
                        ],
                        "outputs": [],
                    }
                },
            },
            {
                "id": "node_llm",
                "type": "jiuwen.llm",
                "configs": {"stream": True, "responseFormat": {"type": "text"}},
                "inputs": {"userFields": {"query": "${node_start.userFields.query}"}},
            },
            {
                "id": "node_msg",
                "type": "jiuwen.message",
                "configs": {"template": "query: {{query}}"},
                "inputs": {"userFields": {"query": msg_ref}},
            },
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "configs": {
                    "responseTemplate": "{{result}}",
                    "isStreamOut": False,
                },
                "inputs": {"userFields": {"result": "${node_msg.result}"}},
            },
        ],
        "connections": [
            {"source": {"componentId": "node_start"}, "target": {"componentId": "node_llm"}},
            {"source": {"componentId": "node_start"}, "target": {"componentId": "node_msg"}},
            {"source": {"componentId": "node_llm"}, "target": {"componentId": "node_msg"}},
            {"source": {"componentId": "node_msg"}, "target": {"componentId": "node_end"}},
        ],
    }


def _get_message_node_spec(workflow) -> "tuple[object, object]":
    """从构建好的 workflow 中取出 (node_msg NodeSpec, WorkflowSpec)。"""
    internal = getattr(workflow, "_internal", workflow)
    internal = getattr(internal, "_wrapped", internal)
    internal = getattr(internal, "_internal", internal)
    workflow_config = internal.config()
    node_spec = workflow_config.spec.comp_configs.get("node_msg")
    assert node_spec is not None, "node_msg 未注册到 workflow"
    return node_spec, workflow_config.spec


@pytest.mark.asyncio
async def test_batch_only_message_registered_as_batch():
    """纯 batch 引用的消息节点在 LLM stream 上游下仍走 batch 注册。"""
    ir = _build_ir(msg_ref="${node_start.userFields.query}")
    original_create = getattr(IRConverter, "_create_component")

    async def _mock_create(node, global_model, *, node_by_id=None, ir_connections=None):
        if node.get("type") == "jiuwen.llm":
            return _MockLLM(), "jiuwen.llm", dict(node.get("configs") or {})
        return await original_create(
            node, global_model, node_by_id=node_by_id, ir_connections=ir_connections
        )

    with patch.object(IRConverter, "_create_component", side_effect=_mock_create):
        lazy = await IRConverter.async_ir_to_workflow(ir)
        workflow = await lazy.instantiate()

    node_spec, spec = _get_message_node_spec(workflow)
    stream_schema = (
        node_spec.stream_io_configs.inputs_schema
        if node_spec.stream_io_configs is not None
        else None
    )
    assert stream_schema is None, "纯 batch 引用的消息节点不应以流式 schema 注册"
    assert node_spec.io_configs is not None
    assert node_spec.io_configs.inputs_schema is not None
    # 无 llm → msg 流边；llm → msg 是普通边
    assert "node_msg" not in (spec.stream_edges.get("node_llm") or []), (
        "纯 batch 引用的消息节点不应有上游流边"
    )
    assert "node_msg" in (spec.edges.get("node_llm") or [])


@pytest.mark.asyncio
async def test_stream_ref_message_still_registered_as_stream():
    """引用 LLM 流式输出的消息节点仍走流式注册（混合场景不受影响）。"""
    ir = _build_ir(msg_ref="${node_llm.raw_output}")
    original_create = getattr(IRConverter, "_create_component")

    async def _mock_create(node, global_model, *, node_by_id=None, ir_connections=None):
        if node.get("type") == "jiuwen.llm":
            return _MockLLM(), "jiuwen.llm", dict(node.get("configs") or {})
        return await original_create(
            node, global_model, node_by_id=node_by_id, ir_connections=ir_connections
        )

    with patch.object(IRConverter, "_create_component", side_effect=_mock_create):
        lazy = await IRConverter.async_ir_to_workflow(ir)
        workflow = await lazy.instantiate()

    node_spec, spec = _get_message_node_spec(workflow)
    stream_schema = (
        node_spec.stream_io_configs.inputs_schema
        if node_spec.stream_io_configs is not None
        else None
    )
    assert stream_schema is not None, "引用 LLM 流式输出的消息节点仍应走流式注册"
    assert "node_msg" in (spec.stream_edges.get("node_llm") or [])


# ---------------------------------------------------------------------------
# 并行 fork/join：消息节点作为 join 汇聚点（is_stream_join_edge 同步 guard）
# ---------------------------------------------------------------------------
# 背景：parallel_stream_done_inputs 的 is_stream_join_edge（ir_converter 1727）
# 原本只判「source ∈ 流式源」+「target ∈ _STREAM_INPUT_CAPABLE_TARGET_TYPES」，
# 没有同步消息节点纯 batch guard。修复前：并行两条 lane（流式 LLM / 普通代码）
# 汇聚到只引用 batch 值的消息节点时，lane-done 注册为 TRANSFORM
# （_ParallelTransformLaneDoneComponent），但 phase 2 因 _is_stream_connection
# 返回 False 用普通边连接 → 运行期既无流式入边也不执行 INVOKE →
# GRAPH_VERTEX_STREAM_CALL_ERROR（no stream data in）。
# 同步 guard 后：batch-only 消息的 lane-done 注册为 INVOKE（普通边一致）；
# 引用 LLM 输出的消息 lane-done 仍为 TRANSFORM（流边一致）。


def _build_parallel_join_ir(msg_ref: str) -> dict:
    """构造并行 fork/join IR：start 并行分叉到 llm(stream)/code，再汇聚到消息节点。"""
    return {
        "components": [
            {
                "id": "node_start",
                "type": "jiuwen.start",
                "inputs": {
                    "userFields": {"query": "hello"},
                    "systemFields": {"query": "", "sys": {}},
                },
                "configs": {
                    "userFields": {
                        "inputs": [
                            {
                                "id": "query",
                                "type": "string",
                                "sourceType": "input",
                                "defaultValue": "hello",
                                "required": True,
                            }
                        ],
                        "outputs": [],
                    }
                },
            },
            {
                "id": "node_llm",
                "type": "jiuwen.llm",
                "configs": {"stream": True, "responseFormat": {"type": "text"}},
                "inputs": {"userFields": {"query": "${node_start.userFields.query}"}},
            },
            {
                "id": "node_code",
                "type": "jiuwen.code",
                "configs": {"code": "def main(args): return {'value': 'x'}"},
                "inputs": {"userFields": {"_input": "${node_start.userFields.query}"}},
            },
            {
                "id": "node_msg",
                "type": "jiuwen.message",
                "configs": {"template": "query: {{query}}"},
                "inputs": {"userFields": {"query": msg_ref}},
            },
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "configs": {
                    "responseTemplate": "{{result}}",
                    "isStreamOut": False,
                },
                "inputs": {"userFields": {"result": "${node_msg.result}"}},
            },
        ],
        "connections": [
            {
                "source": {"componentId": "node_start", "parallelBranchId": "P1"},
                "target": {"componentId": "node_llm"},
            },
            {
                "source": {"componentId": "node_start", "parallelBranchId": "P1"},
                "target": {"componentId": "node_code"},
            },
            {
                "source": {"componentId": "node_llm"},
                "target": {"componentId": "node_msg", "parallelBranchId": "P1"},
            },
            {
                "source": {"componentId": "node_code"},
                "target": {"componentId": "node_msg", "parallelBranchId": "P1"},
            },
            {
                "source": {"componentId": "node_msg"},
                "target": {"componentId": "node_end"},
            },
        ],
    }


DONE_LLM = "_parallel_done__P1__node_msg__node_llm"
DONE_CODE = "_parallel_done__P1__node_msg__node_code"


def _mock_llm_create(original_create):
    async def _mock_create(node, global_model, *, node_by_id=None, ir_connections=None):
        if node.get("type") == "jiuwen.llm":
            return _MockLLM(), "jiuwen.llm", dict(node.get("configs") or {})
        return await original_create(
            node, global_model, node_by_id=node_by_id, ir_connections=ir_connections
        )

    return _mock_create


async def _build_parallel_join_workflow(msg_ref: str):
    """构建并行 join IR 并实例化 workflow。"""
    ir = _build_parallel_join_ir(msg_ref)
    original_create = getattr(IRConverter, "_create_component")
    with patch.object(
        IRConverter, "_create_component", side_effect=_mock_llm_create(original_create)
    ):
        lazy = await IRConverter.async_ir_to_workflow(ir)
        workflow = await lazy.instantiate()
    return workflow


def _get_done_node_spec(workflow, done_id: str):
    """从构建好的 workflow 中取出 done 节点 NodeSpec 与 WorkflowSpec。"""
    internal = getattr(workflow, "_internal", workflow)
    internal = getattr(internal, "_wrapped", internal)
    internal = getattr(internal, "_internal", internal)
    workflow_config = internal.config()
    node_spec = workflow_config.spec.comp_configs.get(done_id)
    assert node_spec is not None, f"{done_id} 未注册到 workflow"
    return node_spec, workflow_config.spec


@pytest.mark.asyncio
async def test_parallel_join_batch_message_done_is_invoke():
    """并行 join 汇聚到纯 batch 引用的消息节点：lane-done 注册为 INVOKE + 普通边。"""
    workflow = await _build_parallel_join_workflow(
        msg_ref="${node_start.userFields.query}"
    )
    for done_id in (DONE_LLM, DONE_CODE):
        done_spec, spec = _get_done_node_spec(workflow, done_id)
        stream_schema = (
            done_spec.stream_io_configs.inputs_schema
            if done_spec.stream_io_configs is not None
            else None
        )
        assert stream_schema is None, (
            f"{done_id} 不应以流式 schema 注册（修复前注册 _ParallelTransformLaneDoneComponent）"
        )
        assert ComponentAbility.TRANSFORM not in done_spec.abilities, (
            f"{done_id} 不应具备 TRANSFORM 能力，否则运行期会触发 GRAPH_VERTEX_STREAM_CALL_ERROR"
        )
        assert done_id not in (spec.stream_edges.get("node_llm") or [])
    assert DONE_LLM in (spec.edges.get("node_llm") or []), "llm → lane-done 应为普通边"
    assert DONE_CODE in (spec.edges.get("node_code") or []), "code → lane-done 应为普通边"


@pytest.mark.asyncio
async def test_parallel_join_stream_ref_message_done_keeps_transform():
    """并行 join 汇聚到引用 LLM 输出的消息节点：LLM 的 lane-done 保持 TRANSFORM + 流边。"""
    workflow = await _build_parallel_join_workflow(msg_ref="${node_llm.raw_output}")
    done_spec, spec = _get_done_node_spec(workflow, DONE_LLM)
    stream_schema = (
        done_spec.stream_io_configs.inputs_schema
        if done_spec.stream_io_configs is not None
        else None
    )
    assert stream_schema is not None, "引用 LLM 输出的消息节点 lane-done 仍应注册 TRANSFORM"
    assert ComponentAbility.TRANSFORM in done_spec.abilities
    assert DONE_LLM in (spec.stream_edges.get("node_llm") or [])
    # code 是非流式源，其 lane-done 始终为 INVOKE
    code_spec, _ = _get_done_node_spec(workflow, DONE_CODE)
    code_stream_schema = (
        code_spec.stream_io_configs.inputs_schema
        if code_spec.stream_io_configs is not None
        else None
    )
    assert code_stream_schema is None, "非流式 lane 的 done 节点不应注册 TRANSFORM"
    assert ComponentAbility.TRANSFORM not in code_spec.abilities
