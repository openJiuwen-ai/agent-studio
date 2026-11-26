# -*- coding: UTF-8 -*-
"""issue #1755：请求级环境作用域随会话下发（能力探测 + 显式优先 + 空值不传）。"""
import pytest

from agent_runtime.common import trace_compat
from agent_runtime.context.request_context import RequestContext, _request_ctx


# 跨仓能力门控：Studio 独立 CI 可能安装旧版 Core（无 workspace_id/source_metadata 形参），
# 此时用例应跳过而非失败；与配对 Core 一起运行时仍执行。
_WF_SUPPORTS_SCOPE = trace_compat.supports_workflow_env_scope()
_AGENT_SUPPORTS_METADATA = trace_compat.supports_agent_source_metadata()

requires_wf_scope = pytest.mark.skipif(
    not _WF_SUPPORTS_SCOPE, reason="core 未提供工作流环境作用域形参（旧版 Core）")
requires_agent_metadata = pytest.mark.skipif(
    not _AGENT_SUPPORTS_METADATA, reason="core 未提供 source_metadata 形参（旧版 Core）")


@pytest.fixture
def scope_ctx():
    token = _request_ctx.set(RequestContext(
        project_id="p1", workspace_id="ws1", environment_id="env1",
    ))
    yield
    _request_ctx.reset(token)


@requires_wf_scope
def test_workflow_session_carries_env_scope(monkeypatch, scope_ctx):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(trace_compat, "_create_workflow_session", _fake)
    trace_compat.create_workflow_session_with_trace(session_id="s1")
    assert captured["workspace_id"] == "ws1"
    assert captured["environment_id"] == "env1"
    assert captured["project_id"] == "p1"


@requires_wf_scope
def test_workflow_session_explicit_value_wins(monkeypatch, scope_ctx):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(trace_compat, "_create_workflow_session", _fake)
    trace_compat.create_workflow_session_with_trace(session_id="s1", workspace_id="explicit")
    assert captured["workspace_id"] == "explicit"


@requires_agent_metadata
def test_agent_session_source_metadata_seeded(monkeypatch, scope_ctx):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(trace_compat, "_create_agent_session", _fake)
    trace_compat.create_agent_session_with_trace(session_id="s1", source_metadata={"user_id": "u1"})
    metadata = captured["source_metadata"]
    assert metadata["user_id"] == "u1"
    assert metadata["workspace_id"] == "ws1"
    assert metadata["environment_id"] == "env1"
    assert metadata["project_id"] == "p1"


@requires_agent_metadata
def test_agent_session_explicit_metadata_not_overridden(monkeypatch, scope_ctx):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(trace_compat, "_create_agent_session", _fake)
    trace_compat.create_agent_session_with_trace(
        session_id="s1", source_metadata={"workspace_id": "explicit"},
    )
    assert captured["source_metadata"]["workspace_id"] == "explicit"


def test_empty_scope_does_not_inject_keys(monkeypatch):
    token = _request_ctx.set(RequestContext())
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(trace_compat, "_create_workflow_session", _fake)
    monkeypatch.setattr(trace_compat, "_create_agent_session", _fake)
    try:
        trace_compat.create_workflow_session_with_trace(session_id="s1")
        assert "workspace_id" not in captured
        captured.clear()
        trace_compat.create_agent_session_with_trace(session_id="s1")
        assert "source_metadata" not in captured
    finally:
        _request_ctx.reset(token)
