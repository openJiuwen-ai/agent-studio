# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for WorkflowRunner exception handling (WorkflowAbortException vs other ExecutionError)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.workflow_runner import WorkflowRunner


def _make_mock_req(conversation_id="conv-1", query="test"):
    """Create a minimal ExecutionRequest mock."""
    req = MagicMock()
    req.conversation_id = conversation_id
    req.ir_path = "workflow/ir/test/test.json"
    req.query = query
    req.resume_input = None
    req.user_id = "testUser"
    req.params = MagicMock()
    req.params.is_debug = False
    req.params.model_dump = MagicMock(return_value={})
    req.params.conversation_history = []
    req.params.enable_memory_extract = False
    return req


class TestWorkflowRunnerAbortException:
    """Test WorkflowRunner behavior for WorkflowAbortException vs other ExecutionError.

    These tests patch the infrastructure layer of run_streaming() to isolate
    just the exception-handling try/except block.
    """

    @pytest.mark.asyncio
    async def test_abort_exception_done_event_uses_exception_node_info(self):
        """When WorkflowAbortException is raised, done event should use exception
        node's node_id/node_name/node_type, not the last normal node's."""
        from jiuwen.extension.workflow_node.utils import WorkflowAbortException

        abort_exc = WorkflowAbortException(
            data={"error_code": "10025"},
            node_id="node_exception",
            node_name="异常",
            node_type="jiuwen.exception",
        )
        events = await self._run_exception_path(abort_exc)

        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) == 1
        assert done_events[0]["data"]["node_id"] == "node_exception"
        assert done_events[0]["data"]["node_name"] == "异常"
        assert done_events[0]["data"]["node_type"] == "jiuwen.exception"

    @pytest.mark.asyncio
    async def test_abort_exception_no_error_event(self):
        """WorkflowAbortException should NOT emit an error event (exception already sent via stream)."""
        from jiuwen.extension.workflow_node.utils import WorkflowAbortException

        abort_exc = WorkflowAbortException(
            data={"error_code": "10025"},
            node_id="node_exception",
            node_name="异常",
            node_type="jiuwen.exception",
        )
        events = await self._run_exception_path(abort_exc)

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 0

    @pytest.mark.asyncio
    async def test_other_execution_error_emits_error_event(self):
        """Non-WorkflowAbortException ExecutionError should still emit error event."""
        from openjiuwen.core.common.exception.codes import StatusCode
        from openjiuwen.core.common.exception.errors import ExecutionError

        other_exc = ExecutionError(StatusCode.ERROR, message="something broke")
        events = await self._run_exception_path(other_exc)

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1

    @pytest.mark.asyncio
    async def test_abort_exception_clears_execution_id_store(self):
        """WorkflowAbortException should clear ExecutionIdStore so next run is independent."""
        from jiuwen.extension.workflow_node.utils import WorkflowAbortException

        abort_exc = WorkflowAbortException(
            data={"error_code": "10025"},
            node_id="node_exception",
            node_name="异常",
            node_type="jiuwen.exception",
        )

        with patch(
            "agent_runtime.runner.workflow_runner.ExecutionIdStore"
        ) as mock_store:
            mock_store.delete = AsyncMock()
            await self._run_exception_path(abort_exc)
            mock_store.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_other_execution_error_does_not_clear_execution_id_store(self):
        """Non-WorkflowAbortException should NOT clear ExecutionIdStore."""
        from openjiuwen.core.common.exception.codes import StatusCode
        from openjiuwen.core.common.exception.errors import ExecutionError

        other_exc = ExecutionError(StatusCode.ERROR, message="something broke")

        with patch(
            "agent_runtime.runner.workflow_runner.ExecutionIdStore"
        ) as mock_store:
            mock_store.delete = AsyncMock()
            await self._run_exception_path(other_exc)
            mock_store.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_abort_exception_missing_node_id_uses_last_node(self):
        """When WorkflowAbortException has no node_id (SubWorkflow case),
        done event should fallback to last_node and log a warning."""
        from jiuwen.extension.workflow_node.utils import WorkflowAbortException

        abort_exc = WorkflowAbortException(
            data={"error_code": "10025"},
            # No node_id, node_name, node_type — simulates SubWorkflow propagation
        )
        events = await self._run_exception_path(
            abort_exc, last_node={"node_id": "node_msg", "node_type": "jiuwen.message"}
        )

        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) == 1
        # Falls back to last_node since e.node_id is None
        assert done_events[0]["data"]["node_id"] == "node_msg"

    # ── Helpers ──────────────────────────────────────────────────

    async def _run_exception_path(self, exception, last_node=None):
        """Run the exception-handling path of WorkflowRunner.run_streaming().

        Patches all infrastructure to isolate just the try/except block.
        Returns the list of yielded events from the except handler.
        """
        from agent_runtime.runner.workflow_stream_data_wrapper import (
            WorkflowStreamDataWrapper,
        )

        runner = WorkflowRunner(api_key="test-key")

        req = _make_mock_req()

        # Mock the wrapper — return a controllable last_node
        mock_wrapper = MagicMock(spec=WorkflowStreamDataWrapper)
        mock_wrapper.get_last_node.return_value = last_node or {
            "node_id": "node_msg",
            "node_type": "jiuwen.message",
        }
        mock_wrapper.wrap_stream_data = MagicMock(return_value=[])

        ir_json = {
            "workflowId": "wf-test",
            "workflowName": "TestWorkflow",
        }

        # Create a mock workflow that raises the exception immediately
        mock_workflow = MagicMock()

        async def _stream_raising(*args, **kwargs):
            raise exception
            yield  # make this an async generator

        mock_workflow.stream = _stream_raising

        # Patch all the infrastructure
        mock_checkpointer = MagicMock()
        mock_checkpointer.session_exists = AsyncMock(return_value=False)

        with patch(
            "agent_runtime.runner.workflow_runner.async_ir_load",
            new_callable=AsyncMock,
            return_value=ir_json,
        ), patch(
            "agent_runtime.runner.workflow_runner.IRConverter.extract_node_defs",
            new_callable=AsyncMock,
            return_value={"wf-test": {"node_msg": {"node_name": "消息", "node_type": "jiuwen.message"}}},
        ), patch.object(
            runner._ir_converter,
            "async_ir_to_workflow",
            new_callable=AsyncMock,
            return_value=mock_workflow,
        ), patch(
            "agent_runtime.runner.workflow_runner.create_conversation_context",
        ), patch(
            "agent_runtime.runner.workflow_runner.create_workflow_session_with_trace",
        ), patch(
            "agent_runtime.runner.workflow_runner.CheckpointerFactory.get_checkpointer",
            return_value=mock_checkpointer,
        ), patch(
            "agent_runtime.runner.workflow_runner.WorkflowStreamDataWrapper",
            return_value=mock_wrapper,
        ), patch(
            "agent_runtime.runner.workflow_runner.ExecutionIdStore.save",
            new_callable=AsyncMock,
        ), patch(
            "agent_runtime.runner.workflow_runner.ExecutionIdStore.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "agent_runtime.runner.workflow_runner._resolve_node_name",
            side_effect=lambda defs, wf_id, nid: nid,
        ):
            events = []
            async for event in runner.run_streaming(req, execution_id="exec-1"):
                events.append(event)
            return events
