# -*- coding: UTF-8 -*-
"""issue 1754 复审：非流式执行必须与流式共用同一 execution_id。

- three runners: run_blocking 必须把 execution_id 透传给 run_streaming；
- orchestration：按能力探测组装 run_blocking 关键字，旧替身不传不报错；
- 登记/读取/清理必须使用同一个执行键（本单核心不变量）。
"""
from types import SimpleNamespace

import pytest

from agent_runtime.common import otel_trace_context as otc
from agent_runtime.runner.controller_runner import ControllerRunner
from agent_runtime.runner.react_agent_runner import ReActAgentRunner
from agent_runtime.runner.workflow_runner import WorkflowRunner
from agent_runtime.serve.apis import orchestration as orch

EXEC_ID = "a" * 32
OTHER_EXEC_ID = "b" * 32
TRACE_ID = "f" * 32
SPAN_ID = "0" * 16


class _StreamRecorder:
    """记录 run_streaming 收到的 execution_id，并产出空流。"""

    def __init__(self):
        self.received = []

    def __call__(self, req, execution_id=None, env_scope=None):
        self.received.append(execution_id)
        return self._empty()

    async def _empty(self):
        if False:  # pragma: no cover - 保持异步生成器语义
            yield None


@pytest.mark.parametrize("runner_cls", [WorkflowRunner, ReActAgentRunner, ControllerRunner])
@pytest.mark.asyncio
async def test_run_blocking_passes_execution_id_to_streaming(runner_cls):
    runner = object.__new__(runner_cls)
    recorder = _StreamRecorder()
    object.__setattr__(runner, "run_streaming", recorder)

    result = await runner.run_blocking(SimpleNamespace(conversation_id="c1"), execution_id=EXEC_ID)

    assert result == ""
    assert recorder.received == [EXEC_ID]


class _NewRunner:
    async def run_blocking(self, req, execution_id=None, env_scope=None):
        return ""


class _VarKwargsRunner:
    async def run_blocking(self, req, **kwargs):
        return ""


class _OldRunnerWithScope:
    async def run_blocking(self, req, env_scope=None):
        return ""


class _OldRunner:
    async def run_blocking(self, req):
        return ""


def test_blocking_kwargs_include_execution_id_for_new_runner():
    kwargs = orch._blocking_kwargs_for(_NewRunner(), EXEC_ID, {"workspace_id": "w1"})

    assert kwargs["execution_id"] == EXEC_ID
    assert kwargs["env_scope"] == {"workspace_id": "w1"}


def test_blocking_kwargs_support_var_keyword_runner():
    kwargs = orch._blocking_kwargs_for(_VarKwargsRunner(), EXEC_ID, {})

    assert kwargs == {"execution_id": EXEC_ID, "env_scope": {}}


def test_blocking_kwargs_skip_execution_id_for_legacy_runner():
    kwargs = orch._blocking_kwargs_for(_OldRunnerWithScope(), EXEC_ID, {})

    assert "execution_id" not in kwargs
    assert "env_scope" in kwargs
    assert orch._blocking_kwargs_for(_OldRunner(), EXEC_ID, {}) == {}


@pytest.mark.asyncio
async def test_nonstream_registry_read_and_clear_use_same_execution_id():
    """登记键 == 精确读取键 == 清理键；其他执行读不到，清理后不残留。"""
    conv = "c-same-exec"

    class _RegisterRunner:
        async def run_blocking(self, req, execution_id=None, env_scope=None):
            otc.register_session_trace(
                req.conversation_id, TRACE_ID, SPAN_ID, execution_id=execution_id)
            return "ok"

    otc.clear_session_trace(conv)
    runner = _RegisterRunner()
    kwargs = orch._blocking_kwargs_for(runner, EXEC_ID, {})
    await runner.run_blocking(SimpleNamespace(conversation_id=conv), **kwargs)

    assert otc.get_session_trace(conv, EXEC_ID) is not None
    assert otc.get_session_trace(conv, OTHER_EXEC_ID) is None

    otc.clear_session_trace(conv, EXEC_ID)
    assert otc.get_session_trace(conv, EXEC_ID) is None
