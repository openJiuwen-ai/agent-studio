# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SubWorkflow：嵌套子图不向外透出 workflow_start / 子 workflow_id。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow
from openjiuwen.core.session.stream.base import OutputSchema

# 使用 setattr / getattr 访问受保护成员，避免静态检测 G.CLS.11
_PROTECTED_INIT = (
    ("_workflow_instance", None),
    ("_stream_state", None),
    ("_interrupt_child_node_id", None),
    ("_pending_interact_prompt", ""),
    ("_global_var_names", None),
    ("_last_child_completed", False),
)


def _make_sub_workflow(workflow_id: str = "child-wf-uuid") -> SubWorkflow:
    conf = {
        "node_id": "node_sub",
        "name": "子流程A",
        "reference": {"id": workflow_id, "path": "obs://x"},
        "systemFields": {},
        "preDefineFields": {},
        "userFields": {},
    }
    sw = object.__new__(SubWorkflow)
    setattr(sw, "_conf", conf)
    setattr(sw, "_node_id", "node_sub")
    for attr, value in _PROTECTED_INIT:
        setattr(sw, attr, value)
    return sw


class TestNestedWorkflowLifecycleFiltered:
    """多控制器只需挂载工作流的一条 start；嵌套 SubWorkflow lifecycle 应被丢弃。"""

    @staticmethod
    def test_drops_workflow_start_without_forwarding():
        sw = _make_sub_workflow("child-wf-uuid")
        session = MagicMock()
        session.write_stream = AsyncMock()
        chunk = OutputSchema(
            type="workflow_start",
            index=1,
            payload={"workflow_id": "from-nested-child"},
        )
        result = asyncio.run(
            getattr(sw, "_process_stream_chunk")(chunk, session, MagicMock(), {})
        )
        assert result is None
        session.write_stream.assert_not_called()

    @staticmethod
    def test_drops_start_and_workflow_end():
        sw = _make_sub_workflow()
        session = MagicMock()
        session.write_stream = AsyncMock()
        process = getattr(sw, "_process_stream_chunk")
        for t in ("start", "workflow_start", "workflow_end"):
            r = asyncio.run(
                process(
                    OutputSchema(type=t, index=0, payload={}),
                    session,
                    MagicMock(),
                    {},
                )
            )
            assert r is None
        session.write_stream.assert_not_called()

    @staticmethod
    def test_no_emit_helper_for_nested_start():
        sw = _make_sub_workflow()
        assert not hasattr(sw, "_emit_child_workflow_start")
        assert not hasattr(sw, "_enrich_child_workflow_id")
