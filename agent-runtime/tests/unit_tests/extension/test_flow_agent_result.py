# -*- coding: UTF-8 -*-
"""FlowAgent result compatibility tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.extension.workflow_node.flow_agent import FlowAgent, FlowAgentConfig


@pytest.mark.asyncio
async def test_invoke_preserves_react_result_type():
    react_agent = MagicMock()
    react_agent.register_rail = AsyncMock()
    react_agent.invoke = AsyncMock(
        return_value={
            "output": "Max iterations reached without completion",
            "result_type": "error",
        }
    )

    with patch(
        "jiuwen.extension.workflow_node.flow_agent.ReActAgent",
        return_value=react_agent,
    ):
        agent = FlowAgent(FlowAgentConfig(max_iteration=1))
        result = await agent.invoke({"query": "test"}, session=None, context=None)

    react_config = react_agent.configure.call_args.args[0]
    assert react_config.max_iterations == 2
    assert result == {
        "userFields": {
            "output": "Max iterations reached without completion",
            "result_type": "error",
        }
    }
