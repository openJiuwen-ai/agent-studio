# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""异常恢复（defaultOutputs/errorBranch）标红回调单测。

验证 handle_error_recovery 在交付恢复数据前先 session.trace_error(error)
（真实错误已发生只被降级接管：错误标红进 trace，流程不受影响）。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from openjiuwen.core.runner import Runner

import jiuwen.extension.workflow_node.exception_handler as eh


class FakeFramework:
    def __init__(self):
        self.handlers = {}

    def on(self, event, priority=100):
        def deco(fn):
            self.handlers.setdefault(event, []).append(fn)
            return fn

        return deco


def _fire_default_outputs(fw, error):
    handler = fw.handlers["component_error_recovery"][0]
    session = MagicMock()
    session.trace_error = AsyncMock()
    exc_config = MagicMock(
        handle_type="defaultOutputs",
        _node_type="jiuwen.http",
        default_outputs={},
        outputs_schema={},
    )
    result = asyncio.run(
        handler(error=error, session=session, node_id="n", exception_config=exc_config)
    )
    return session, result


def test_default_outputs_recovery_marks_error_before_handoff():
    fw = FakeFramework()
    with patch.object(Runner, "callback_framework", fw), patch.object(eh, "_HANDLER_REGISTERED", False):
        eh.register_error_recovery_handler()

    error = RuntimeError("recoverable failure")
    session, result = _fire_default_outputs(fw, error)

    session.trace_error.assert_awaited_once_with(error)
    assert result["isSuccess"] is False
    assert result["errorBody"]["errorCode"] == -1


def test_error_branch_recovery_marks_error_before_handoff():
    fw = FakeFramework()
    with patch.object(Runner, "callback_framework", fw), patch.object(eh, "_HANDLER_REGISTERED", False):
        eh.register_error_recovery_handler()

    error = RuntimeError("switch to error branch")
    handler = fw.handlers["component_error_recovery"][0]
    session = MagicMock()
    session.trace_error = AsyncMock()
    exc_config = MagicMock(handle_type="errorBranch", _node_type="jiuwen.http")
    result = asyncio.run(
        handler(error=error, session=session, node_id="n", exception_config=exc_config)
    )

    session.trace_error.assert_awaited_once_with(error)
    assert result["result"] == "1"