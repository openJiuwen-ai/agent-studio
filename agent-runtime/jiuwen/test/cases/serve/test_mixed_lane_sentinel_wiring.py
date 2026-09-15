# coding: utf-8
"""Wiring-level tests for mixed-lane sentinel insertion in IRConverter.

``test_mixed_lane_sentinel.py`` covers the pure detection function; these
tests build a full Workflow from a minimal mixed-lane IR (LLM + Code behind a
conditional branch, two parallel lanes into END) and assert the converter
actually:

  * registers a ``_lane_sentinel__*`` STREAM component for each non-stream
    terminal, and
  * wires ``terminal -> sentinel`` (batch) and ``sentinel -> lane-done``
    (stream) so the lane-done's stream source group becomes the CNF OR-group
    ``{LLM, sentinel}`` -- the fix for 112052 "no stream data in" when the
    non-stream branch executes.

The LLM model is stubbed so the build never touches a model service; we only
inspect the built ``WorkflowSpec`` / ``stream_edges``.
"""
# pylint: disable=protected-access
#   White-box tests inspect ``workflow._internal`` / ``_workflow_spec``.
import pytest

pytest.importorskip("openjiuwen.core.workflow.workflow_config")

from jiuwen.serve.controllers.execution.ir_converter import IRConverter  # noqa: E402


def _mixed_lane_ir() -> dict:
    """Two parallel lanes from node_start into node_end; each lane is a branch
    that routes conditionally to an LLM (stream) or a Code node (non-stream).
    Both lanes are mixed -> both Code terminals get a sentinel."""
    branch_cond = "(length(${node_start.systemFields.query}) > 0)"
    return {
        "workflowId": "wf_mix",
        "workflowName": "mixed_lane",
        "schemaVersion": "0.6.0",
        "configs": {"model": {"modelName": "m", "modelType": "LLM",
                              "extension": {}, "hyperParameters": {}}},
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "name": "开始",
             "configs": {"userFields": {"inputs": [], "outputs": []},
                         "systemFields": {"inputs": [
                             {"id": "query", "type": "string", "required": True,
                              "sourceType": "input", "description": "user input"}],
                             "outputs": []}},
             "inputs": {"userFields": {}, "systemFields": {"query": "", "sys": {}}},
             "outputs": {"userFields": {}, "systemFields": {"query": "", "sys": {}}}},
            {"id": "b1", "type": "jiuwen.branch", "name": "判断1",
             "configs": {"branches": [
                 {"boolExpression": branch_cond, "id": "b1-if"},
                 {"id": "default"}]}},
            {"id": "b2", "type": "jiuwen.branch", "name": "判断2",
             "configs": {"branches": [
                 {"boolExpression": branch_cond, "id": "b2-if"},
                 {"id": "default"}]}},
            {"id": "llm1", "type": "jiuwen.LLMComponent", "name": "大模型1",
             "configs": {"stream": True, "deployMode": "workflow",
                         "userFields": {"inputs": [
                             {"id": "query", "type": "string", "required": True,
                              "sourceType": "ref", "value": "${node_start.systemFields.query}"}],
                             "outputs": [{"id": "raw_output", "type": "string",
                                          "required": True, "sourceType": "input"}]},
                         "templateContent": [{"role": "user", "content": "{{query}}"}],
                         "model": {"modelName": "m", "modelType": "LLM",
                                   "extension": {}, "hyperParameters": {}},
                         "memory": {"enable": False}, "enableHistory": False,
                         "responseFormat": {"type": "text"}, "historySize": 3},
             "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
             "outputs": {"userFields": {"raw_output": ""}}},
            {"id": "llm2", "type": "jiuwen.LLMComponent", "name": "大模型2",
             "configs": {"stream": True, "deployMode": "workflow",
                         "userFields": {"inputs": [
                             {"id": "query", "type": "string", "required": True,
                              "sourceType": "ref", "value": "${node_start.systemFields.query}"}],
                             "outputs": [{"id": "raw_output", "type": "string",
                                          "required": True, "sourceType": "input"}]},
                         "templateContent": [{"role": "user", "content": "{{query}}"}],
                         "model": {"modelName": "m", "modelType": "LLM",
                                   "extension": {}, "hyperParameters": {}},
                         "memory": {"enable": False}, "enableHistory": False,
                         "responseFormat": {"type": "text"}, "historySize": 3},
             "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
             "outputs": {"userFields": {"raw_output": ""}}},
            {"id": "code1", "type": "jiuwen.code", "name": "代码1",
             "configs": {"userFields": {"inputs": [], "outputs": [
                 {"id": "key0", "type": "string", "required": True,
                  "sourceType": "null", "description": ""}]},
                         "code": "def main(args):\n    return {'key0': 'c1'}",
                         "exec_env": "sandbox", "fg_id": "", "fg_urn": "",
                         "fg_url": "", "template_version": "",
                         "systemFields": {"inputs": [], "outputs": []}},
             "inputs": {"userFields": {}},
             "outputs": {"userFields": {"key0": ""}}},
            {"id": "code2", "type": "jiuwen.code", "name": "代码2",
             "configs": {"userFields": {"inputs": [], "outputs": [
                 {"id": "key0", "type": "string", "required": True,
                  "sourceType": "null", "description": ""}]},
                         "code": "def main(args):\n    return {'key0': 'c2'}",
                         "exec_env": "sandbox", "fg_id": "", "fg_urn": "",
                         "fg_url": "", "template_version": "",
                         "systemFields": {"inputs": [], "outputs": []}},
             "inputs": {"userFields": {}},
             "outputs": {"userFields": {"key0": ""}}},
            {"id": "node_end", "type": "jiuwen.end", "name": "结束",
             "configs": {"responseMode": "directResponse", "isStreamOut": True,
                         "enable_history": False, "isStructMessage": False,
                         "responseTemplate": "{{a}}\n{{b}}\n{{c}}\n{{d}}",
                         "userFields": {
                             "inputs": [
                                 {"id": "a", "type": "string", "required": True,
                                  "sourceType": "ref", "value": "${llm1.userFields.raw_output}"},
                                 {"id": "b", "type": "string", "required": True,
                                  "sourceType": "ref", "value": "${code1.userFields.key0}"},
                                 {"id": "c", "type": "string", "required": True,
                                  "sourceType": "ref", "value": "${llm2.userFields.raw_output}"},
                                 {"id": "d", "type": "string", "required": True,
                                  "sourceType": "ref", "value": "${code2.userFields.key0}"}],
                             "outputs": []},
                         "systemFields": {"inputs": [], "outputs": []}},
             "inputs": {"userFields": {
                 "a": "${llm1.userFields.raw_output}",
                 "b": "${code1.userFields.key0}",
                 "c": "${llm2.userFields.raw_output}",
                 "d": "${code2.userFields.key0}"}},
             "outputs": {"userFields": {}, "responseContent": ""}},
        ],
        "connections": [
            {"source": {"componentId": "node_start", "parallelBranchId": "p1"},
             "target": {"componentId": "b1"}},
            {"source": {"componentId": "node_start", "parallelBranchId": "p1"},
             "target": {"componentId": "b2"}},
            {"source": {"branchId": "b1-if", "componentId": "b1"},
             "target": {"componentId": "llm1"}},
            {"source": {"branchId": "b1-default", "componentId": "b1"},
             "target": {"componentId": "code1"}},
            {"source": {"branchId": "b2-if", "componentId": "b2"},
             "target": {"componentId": "code2"}},
            {"source": {"branchId": "b2-default", "componentId": "b2"},
             "target": {"componentId": "llm2"}},
            {"source": {"componentId": "llm1"},
             "target": {"componentId": "node_end", "parallelBranchId": "p1"}},
            {"source": {"componentId": "code1"},
             "target": {"componentId": "node_end", "parallelBranchId": "p1"}},
            {"source": {"componentId": "llm2"},
             "target": {"componentId": "node_end", "parallelBranchId": "p1"}},
            {"source": {"componentId": "code2"},
             "target": {"componentId": "node_end", "parallelBranchId": "p1"}},
        ],
    }


def _spec(workflow):
    return workflow._internal._workflow_spec


@pytest.mark.asyncio
async def test_mixed_lane_inserts_sentinel_components_and_stream_edge(monkeypatch):
    """Building a mixed-lane IR must insert a sentinel STREAM component per
    non-stream terminal and wire sentinel -> lane-done as a stream edge."""
    # Stub model creation so the build never touches a model service.
    monkeypatch.setattr(IRConverter, "_create_llm_model",
                        staticmethod(lambda *a, **k: object()))

    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(_mixed_lane_ir())
    # stream_source_groups are populated at compile time (auto_complete_abilities),
    # not during build -- invoke it explicitly to verify OR-group resolution.
    workflow._internal.auto_complete_abilities()
    spec = _spec(workflow)

    # 1. Two sentinel components registered, both STREAM ability.
    sentinel_ids = [c for c in spec.comp_configs if c.startswith("_lane_sentinel__")]
    assert len(sentinel_ids) == 2, f"expected 2 sentinels, got {sentinel_ids}"

    # 2. Each non-stream terminal (code1, code2) has a batch edge into its sentinel.
    edges = spec.edges
    code_terminals = ("code1", "code2")
    sentinel_targets = {t for s in code_terminals for t in edges.get(s, [])}
    assert all(t.startswith("_lane_sentinel__") for t in sentinel_targets), (
        f"code terminals must connect to sentinels, got {sentinel_targets}")

    # 3. Each sentinel has a STREAM edge into its lane-done node.
    stream_edges = spec.stream_edges
    sentinel_stream_targets = {t for sid in sentinel_ids for t in stream_edges.get(sid, [])}
    assert sentinel_stream_targets, "sentinel must have a stream edge to lane-done"
    assert all(t.startswith("_parallel_done__") for t in sentinel_stream_targets), (
        f"sentinel stream edge must target a lane-done, got {sentinel_stream_targets}")

    # 4. The lane-done's stream source group is an OR-group {LLM, sentinel}
    #    (len > 1), so either branch firing satisfies it -> no 112052.
    for done_node in sentinel_stream_targets:
        groups = spec.stream_source_groups.get(done_node, [])
        assert groups, f"lane-done {done_node} must have stream source groups"
        or_groups = [g for g in groups if len(g) > 1]
        assert or_groups, (
            f"lane-done {done_node} must have an OR-group (LLM+sentinel), "
            f"got {groups}")


@pytest.mark.asyncio
async def test_pure_stream_lane_has_no_sentinel(monkeypatch):
    """A lane whose terminals are all streaming (no non-stream sibling) must
    NOT get a sentinel -- it is not mixed."""
    monkeypatch.setattr(IRConverter, "_create_llm_model",
                        staticmethod(lambda *a, **k: object()))
    ir = _mixed_lane_ir()
    # Convert code1/code2 into LLMs so every terminal streams.
    for c in ir["components"]:
        if c["id"] in ("code1", "code2"):
            c["type"] = "jiuwen.LLMComponent"
            c["configs"] = ir["components"][3]["configs"]  # mirror llm1 config
            c["outputs"] = {"userFields": {"raw_output": ""}}
            c["inputs"] = {"userFields": {"query": "${node_start.systemFields.query}"}}
    workflow = await IRConverter.build_openjiuwen_workflow_from_ir(ir)
    spec = _spec(workflow)
    sentinel_ids = [c for c in spec.comp_configs if c.startswith("_lane_sentinel__")]
    assert sentinel_ids == [], (
        f"pure-stream lanes must not get sentinels, got {sentinel_ids}")
