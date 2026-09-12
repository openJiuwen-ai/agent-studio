# coding: utf-8
"""Tests for parallel-branch join detection in IRConverter."""

import json
from pathlib import Path

import pytest

from jiuwen.serve.controllers.execution.ir_parallel_utils import (
    collect_parallel_join_nodes,
)


_IR_PATH = (
    Path(__file__).resolve().parents[5]
    / "test_ir"
    / "test_flow_aggregation_parallel_ir.json"
)


def test_collect_parallel_join_nodes_from_aggregation_parallel_ir():
    with _IR_PATH.open(encoding="utf-8") as f:
        ir = json.load(f)
    join_nodes = collect_parallel_join_nodes(ir["connections"])
    assert "node_1780556289681" in join_nodes


def test_collect_parallel_join_nodes_ignores_single_incoming_parallel_edge():
    connections = [
        {
            "source": {"componentId": "a", "parallelBranchId": "p1"},
            "target": {"componentId": "b"},
        },
        {
            "source": {"componentId": "x"},
            "target": {"componentId": "join", "parallelBranchId": "p1"},
        },
    ]
    assert collect_parallel_join_nodes(connections) == frozenset()


def test_collect_parallel_join_nodes_detects_two_branch_convergence():
    connections = [
        {
            "source": {"componentId": "llm"},
            "target": {"componentId": "agg", "parallelBranchId": "p1"},
        },
        {
            "source": {"componentId": "msg"},
            "target": {"componentId": "agg", "parallelBranchId": "p1"},
        },
    ]
    assert collect_parallel_join_nodes(connections) == frozenset({"agg"})


def test_collect_parallel_join_nodes_keeps_parallel_join_before_loop():
    connections = [
        {
            "source": {"componentId": "branch_a"},
            "target": {"componentId": "loop", "parallelBranchId": "p1"},
        },
        {
            "source": {"componentId": "branch_b"},
            "target": {"componentId": "loop", "parallelBranchId": "p1"},
        },
        {
            "source": {"componentId": "loop"},
            "target": {"componentId": "end"},
        },
    ]
    node_by_id = {"loop": {"id": "loop", "type": "jiuwen.loop"}}
    assert collect_parallel_join_nodes(connections, node_by_id) == frozenset({"loop"})


def test_collect_parallel_join_nodes_ignores_loop_cyclic_parallel_source():
    connections = [
        {
            "source": {"componentId": "entry"},
            "target": {"componentId": "loop", "parallelBranchId": "p1"},
        },
        {
            "source": {"componentId": "body"},
            "target": {"componentId": "loop", "parallelBranchId": "p1"},
        },
        {
            "source": {"componentId": "loop_input"},
            "target": {"componentId": "body"},
        },
        {
            "source": {"componentId": "body"},
            "target": {"componentId": "loop_output"},
        },
    ]
    node_by_id = {"loop": {"id": "loop", "type": "jiuwen.loop"}}
    assert collect_parallel_join_nodes(connections, node_by_id) == frozenset()


def test_llm_to_aggregate_uses_batch_edge_not_stream():
    pytest.importorskip("openjiuwen.core.workflow.workflow_config")
    try:
        from openjiuwen.core.workflow.workflow_config import ExceptionConfig  # noqa: F401
    except ImportError:
        pytest.skip("ExceptionConfig unavailable in installed openjiuwen")
    from jiuwen.serve.controllers.execution.ir_converter import IRConverter

    stream_source_ids = {"node_1780556908427"}
    components = [
        {
            "id": "node_1780556908427",
            "type": "jiuwen.LLMComponent",
            "configs": {"stream": True},
        },
        {
            "id": "node_1780556289681",
            "type": "jiuwen.aggregation",
            "inputs": {
                "userFields": {
                    "group1_1": "${node_1780556908427.userFields.raw_output}",
                }
            },
        },
    ]
    assert (
        IRConverter._is_stream_connection(
            components,
            "node_1780556908427",
            "node_1780556289681",
            stream_source_ids,
        )
        is False
    )
