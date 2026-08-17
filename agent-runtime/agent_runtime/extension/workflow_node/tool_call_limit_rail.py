# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Limit ReAct by tool-call rounds instead of total model iterations."""

from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.single_agent.rail.base import AgentCallbackContext, AgentRail


class ToolCallLimitRail(AgentRail):
    """Stop before executing a tool-call round beyond the configured limit.

    One model response containing one or more parallel tool calls counts as one
    round. The counter is stored in the per-invocation callback context so a
    reused workflow component does not leak state between conversations.
    """

    _COUNT_KEY = "flow_agent_tool_call_rounds"

    def __init__(self, max_tool_call_rounds: int):
        self.max_tool_call_rounds = max_tool_call_rounds

    async def after_model_call(self, ctx: AgentCallbackContext) -> None:
        response = getattr(ctx.inputs, "response", None)
        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            return

        completed_rounds = int(ctx.extra.get(self._COUNT_KEY, 0))
        if completed_rounds >= self.max_tool_call_rounds:
            workflow_logger.warning(
                "FlowAgent maximum tool-call rounds reached: "
                f"{self.max_tool_call_rounds}"
            )
            ctx.request_force_finish(
                result={
                    "output": "Max iterations reached without completion",
                    "result_type": "error",
                }
            )
            return

        ctx.extra[self._COUNT_KEY] = completed_rounds + 1
