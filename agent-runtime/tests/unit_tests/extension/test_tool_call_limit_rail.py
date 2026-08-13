# -*- coding: UTF-8 -*-
"""ToolCallLimitRail unit tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent_runtime.extension.workflow_node.tool_call_limit_rail import ToolCallLimitRail


def _make_ctx(tool_calls):
    ctx = MagicMock()
    ctx.inputs = SimpleNamespace(response=SimpleNamespace(tool_calls=tool_calls))
    ctx.extra = {}
    ctx.request_force_finish = MagicMock()
    return ctx


class TestToolCallLimitRail:
    @pytest.mark.asyncio
    async def test_parallel_tool_calls_count_as_one_round(self):
        rail = ToolCallLimitRail(max_tool_call_rounds=2)
        ctx = _make_ctx([MagicMock(), MagicMock()])

        await rail.after_model_call(ctx)

        assert list(ctx.extra.values()) == [1]
        ctx.request_force_finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_final_answer_does_not_consume_round(self):
        rail = ToolCallLimitRail(max_tool_call_rounds=1)
        ctx = _make_ctx([])

        await rail.after_model_call(ctx)

        assert ctx.extra == {}
        ctx.request_force_finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_next_tool_round_is_stopped_before_execution(self):
        rail = ToolCallLimitRail(max_tool_call_rounds=1)
        ctx = _make_ctx([MagicMock()])

        await rail.after_model_call(ctx)
        await rail.after_model_call(ctx)

        assert list(ctx.extra.values()) == [1]
        ctx.request_force_finish.assert_called_once_with(
            result={
                "output": "Max iterations reached without completion",
                "result_type": "error",
            }
        )
