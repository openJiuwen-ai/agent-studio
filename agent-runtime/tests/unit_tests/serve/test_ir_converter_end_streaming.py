# coding: utf-8
# pylint: disable=protected-access  # Tests inspect generated openJiuwen graph specs.

import asyncio

import pytest
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import WorkflowComponent, create_workflow_session
from openjiuwen.core.workflow.components.base import ComponentAbility


def _stream_llm(node_id: str) -> dict:
    return {
        "id": node_id,
        "type": "jiuwen.LLMComponent",
        "configs": {
            "stream": True,
            "deployMode": "workflow",
            "templateContent": [],
            "responseFormat": {"type": "text"},
            "enableHistory": False,
            "userFields": {"inputs": [], "outputs": []},
            "model": {
                "modelName": "test-model",
                "modelType": "LLM",
                "hyperParameters": {},
                "extension": {},
            },
        },
        "inputs": {},
        "outputs": {"userFields": {"raw_output": ""}},
    }


def _branch_end_ir(*, take_first_branch: bool = True) -> dict:
    return {
        "workflowId": "branch-end-streaming",
        "workflowName": "branch-end-streaming",
        "components": [
            {
                "id": "node_start",
                "type": "jiuwen.start",
                "configs": {},
                "inputs": {},
                "outputs": {},
            },
            {
                "id": "node_branch",
                "type": "jiuwen.branch",
                "configs": {
                    "branches": [
                        {
                            "id": "node_branch-if",
                            "boolExpression": str(take_first_branch),
                        },
                        {"id": "default"},
                    ]
                },
                "inputs": {},
                "outputs": {},
            },
            _stream_llm("node_llm_1"),
            {
                "id": "node_message",
                "type": "jiuwen.message",
                "configs": {"template": "消息节点输出：{{content}}"},
                "inputs": {
                    "userFields": {
                        "content": "${node_llm_1.userFields.raw_output}"
                    }
                },
                "outputs": {},
            },
            _stream_llm("node_llm_2"),
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "configs": {
                    "isStreamOut": True,
                    "responseTemplate": "结束节点输出：{{result1}}，{{result2}}",
                },
                "inputs": {
                    "userFields": {
                        "result1": "${node_llm_1.userFields.raw_output}",
                        "result2": "${node_llm_2.userFields.raw_output}",
                    }
                },
                "outputs": {},
            },
        ],
        "connections": [
            {
                "source": {"componentId": "node_start"},
                "target": {"componentId": "node_branch"},
            },
            {
                "source": {
                    "componentId": "node_branch",
                    "branchId": "node_branch-if",
                },
                "target": {"componentId": "node_llm_1"},
            },
            {
                "source": {
                    "componentId": "node_branch",
                    "branchId": "node_branch-default",
                },
                "target": {"componentId": "node_llm_2"},
            },
            {
                "source": {"componentId": "node_llm_1"},
                "target": {"componentId": "node_message"},
            },
            {
                "source": {"componentId": "node_message"},
                "target": {"componentId": "node_end"},
            },
            {
                "source": {"componentId": "node_llm_2"},
                "target": {"componentId": "node_end"},
            },
        ],
    }


def _branch_batch_end_ir(*, take_stream_branch: bool = True) -> dict:
    ir = _branch_end_ir(take_first_branch=take_stream_branch)
    ir["components"] = [
        node for node in ir["components"] if node["id"] != "node_message"
    ]
    batch_node = next(
        node for node in ir["components"] if node["id"] == "node_llm_2"
    )
    batch_node["type"] = "jiuwen.code"
    batch_node["configs"] = {"code": "def main(args): return {'key0': 'result2'}"}
    batch_node["outputs"] = {"userFields": {"key0": ""}}
    end_node = next(node for node in ir["components"] if node["id"] == "node_end")
    end_node["inputs"]["userFields"] = {
        "result1": "${node_llm_1.userFields.raw_output}",
        "result2": "${node_llm_2.userFields.key0}",
    }
    connections = []
    for connection in ir["connections"]:
        source_id = connection["source"]["componentId"]
        target_id = connection["target"]["componentId"]
        if source_id != "node_message" and target_id != "node_message":
            connections.append(connection)
    ir["connections"] = connections
    ir["connections"].append(
        {
            "source": {"componentId": "node_llm_1"},
            "target": {"componentId": "node_end"},
        }
    )
    return ir


def _direct_stream_with_context_ir() -> dict:
    ir = _branch_end_ir()
    ir["components"] = [
        node
        for node in ir["components"]
        if node["id"] in {"node_start", "node_llm_1", "node_end"}
    ]
    end_node = next(node for node in ir["components"] if node["id"] == "node_end")
    end_node["configs"]["responseTemplate"] = "{{query}}：{{result1}}"
    end_node["inputs"]["userFields"] = {
        "query": "${node_start.userFields.query}",
        "result1": "${node_llm_1.userFields.raw_output}",
    }
    ir["connections"] = [
        {
            "source": {"componentId": "node_start"},
            "target": {"componentId": "node_llm_1"},
        },
        {
            "source": {"componentId": "node_llm_1"},
            "target": {"componentId": "node_end"},
        },
    ]
    return ir


@pytest.mark.asyncio
async def test_end_stream_inputs_follow_explicit_control_lanes():
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(_branch_end_ir())
    spec = workflow._internal._workflow_spec
    end_spec = spec.comp_configs["node_end"]

    assert end_spec.io_configs.inputs_schema is None
    assert end_spec.stream_io_configs.inputs_schema == {
        "userFields": {
            "result1": (
                "${__end_stream_lane__node_end__node_message.userFields.result1}"
            ),
            "result2": "${node_llm_2.userFields.raw_output}",
        }
    }
    assert end_spec.abilities == [ComponentAbility.TRANSFORM]


@pytest.mark.asyncio
async def test_indirect_ref_uses_control_lane_instead_of_bypassing_message():
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(_branch_end_ir())
    workflow._internal.auto_complete_abilities()
    spec = workflow._internal._workflow_spec
    lane_id = "__end_stream_lane__node_end__node_message"

    assert "node_end" not in spec.stream_edges.get("node_llm_1", [])
    assert lane_id in spec.edges["node_message"]
    assert "node_end" in spec.stream_edges[lane_id]
    assert "node_end" in spec.stream_edges["node_llm_2"]
    assert spec.stream_source_groups["node_end"] == [
        [f"{lane_id}-stream", "node_llm_2-stream"]
    ]


@pytest.mark.asyncio
async def test_batch_branch_is_normalized_to_one_frame_stream_lane():
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(
        _branch_batch_end_ir()
    )
    workflow._internal.auto_complete_abilities()
    spec = workflow._internal._workflow_spec
    lane_id = "__end_stream_lane__node_end__node_llm_2"

    assert lane_id in spec.edges["node_llm_2"]
    assert "node_end" in spec.stream_edges[lane_id]
    assert "node_end" in spec.stream_edges["node_llm_1"]
    assert len(spec.stream_source_groups["node_end"]) == 1
    assert set(spec.stream_source_groups["node_end"][0]) == {
        "node_llm_1-stream",
        f"{lane_id}-stream",
    }
    assert spec.comp_configs["node_end"].stream_io_configs.inputs_schema == {
        "userFields": {
            "result1": "${node_llm_1.userFields.raw_output}",
            "result2": f"${{{lane_id}.userFields.result2}}",
        }
    }


@pytest.mark.asyncio
async def test_non_stream_end_keeps_regular_batch_connections():
    ir = _branch_batch_end_ir()
    ir["components"] = [
        node
        for node in ir["components"]
        if node["id"] in {"node_start", "node_llm_2", "node_end"}
    ]
    end_node = next(node for node in ir["components"] if node["id"] == "node_end")
    end_node["configs"]["isStreamOut"] = False
    end_node["inputs"]["userFields"] = {
        "result2": "${node_llm_2.userFields.key0}"
    }
    ir["connections"] = [
        {
            "source": {"componentId": "node_start"},
            "target": {"componentId": "node_llm_2"},
        },
        {
            "source": {"componentId": "node_llm_2"},
            "target": {"componentId": "node_end"},
        },
    ]

    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(ir)
    workflow._internal.auto_complete_abilities()
    spec = workflow._internal._workflow_spec

    assert "node_end" in spec.edges["node_llm_2"]
    assert not any(
        node_id.startswith("__end_stream_lane__") for node_id in spec.comp_configs
    )
    assert spec.comp_configs["node_end"].stream_io_configs.inputs_schema is None


@pytest.mark.asyncio
async def test_direct_stream_stays_native_when_end_also_reads_upstream_context():
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(
        _direct_stream_with_context_ir()
    )
    workflow._internal.auto_complete_abilities()
    spec = workflow._internal._workflow_spec

    assert "node_end" in spec.stream_edges["node_llm_1"]
    assert not any(
        node_id.startswith("__end_stream_lane__") for node_id in spec.comp_configs
    )
    assert spec.comp_configs["node_end"].stream_io_configs.inputs_schema == {
        "userFields": {
            "query": "${node_start.userFields.query}",
            "result1": "${node_llm_1.userFields.raw_output}",
        }
    }


class _FakeStreamingLLM(WorkflowComponent):
    def __init__(self, value: str):
        super().__init__()
        self._value = value
        self._stream_final_output: Output | None = None

    def get_stream_output(self) -> Output | None:
        """Match LLMChain's contract for downstream refs after stream completion."""
        return self._stream_final_output

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        for chunk in self._value:
            await asyncio.sleep(0)
            yield {"userFields": {"raw_output": chunk}}
        self._stream_final_output = {"userFields": {"raw_output": self._value}}


class _FakeBatchCode(WorkflowComponent):
    async def invoke(self, inputs: Input, session: Session, context: ModelContext):
        return {"userFields": {"key0": "result2"}}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("take_first_branch", "expected_content", "expected_message_ends", "expected_order"),
    [
        (
            True,
            "消息节点输出：result1结束节点输出：result1，",
            2,
            ["message", "end"],
        ),
        (False, "结束节点输出：，result2", 1, ["end"]),
    ],
)
async def test_message_and_end_emit_distinct_messages_in_control_order(
    monkeypatch,
    take_first_branch,
    expected_content,
    expected_message_ends,
    expected_order,
):
    original_create_component = IRConverter._create_component

    async def create_component(node, global_model, **kwargs):
        if node.get("type") == "jiuwen.LLMComponent":
            value = "result1" if node["id"] == "node_llm_1" else "result2"
            return _FakeStreamingLLM(value), node["type"], node.get("configs") or {}
        return await original_create_component(node, global_model, **kwargs)

    monkeypatch.setattr(
        IRConverter, "_create_component", staticmethod(create_component)
    )
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(
        _branch_end_ir(take_first_branch=take_first_branch)
    )

    async def collect_visible_content() -> tuple[str, int, list[str]]:
        content = []
        message_end_count = 0
        source_order: list[str] = []
        async for chunk in workflow.stream({}, session=create_workflow_session()):
            chunk_type = getattr(chunk, "type", None)
            if chunk_type == "end node stream":
                payload = getattr(chunk, "payload", None)
                if isinstance(payload, dict):
                    content.append(str(payload.get("answer", "")))
                    source_order.append("end")
            elif chunk_type == "partial_content":
                data = getattr(chunk, "data", None)
                if isinstance(data, dict):
                    content.append(str(data.get("answer", "")))
                    source_order.append("message")
            elif chunk_type == "message_end":
                message_end_count += 1
        collapsed_order = [
            source
            for index, source in enumerate(source_order)
            if index == 0 or source != source_order[index - 1]
        ]
        return "".join(content), message_end_count, collapsed_order

    assert await asyncio.wait_for(collect_visible_content(), timeout=1.0) == (
        expected_content,
        expected_message_ends,
        expected_order,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("take_stream_branch", "expected"),
    [
        (True, "结束节点输出：result1，"),
        (False, "结束节点输出：，result2"),
    ],
)
async def test_stream_and_batch_branches_render_without_waiting_for_inactive_lane(
    monkeypatch, take_stream_branch, expected
):
    original_create_component = IRConverter._create_component

    async def create_component(node, global_model, **kwargs):
        if node.get("type") == "jiuwen.LLMComponent":
            return _FakeStreamingLLM("result1"), node["type"], node.get("configs") or {}
        if node.get("type") == "jiuwen.code":
            return _FakeBatchCode(), node["type"], node.get("configs") or {}
        return await original_create_component(node, global_model, **kwargs)

    monkeypatch.setattr(
        IRConverter, "_create_component", staticmethod(create_component)
    )
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(
        _branch_batch_end_ir(take_stream_branch=take_stream_branch)
    )

    async def collect_end_content() -> str:
        content = []
        async for chunk in workflow.stream({}, session=create_workflow_session()):
            if getattr(chunk, "type", None) != "end node stream":
                continue
            payload = getattr(chunk, "payload", None)
            if isinstance(payload, dict):
                content.append(str(payload.get("answer", "")))
        return "".join(content)

    assert await asyncio.wait_for(collect_end_content(), timeout=1.0) == expected
