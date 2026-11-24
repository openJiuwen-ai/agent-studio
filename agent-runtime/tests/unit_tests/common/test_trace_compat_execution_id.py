# -*- coding: UTF-8 -*-
"""issue 1753: execution_id 建会话透传（新 Core 透传 / 旧 Core 降级）。"""
import pytest

import agent_runtime.common.trace_compat as tc


@pytest.mark.asyncio
async def test_execution_id_forwarded_when_core_supports(monkeypatch):
    captured = {}

    def _fake_create(session_id=None, **kwargs):
        captured.update(kwargs)
        return {"session_id": session_id, **kwargs}

    monkeypatch.setattr(tc, "_create_workflow_session", _fake_create)
    monkeypatch.setattr(tc, "_wf_accepts_execution_id", True)
    monkeypatch.setattr(tc, "_wf_accepts_trace_id", True)

    tc.create_workflow_session_with_trace(
        session_id="cid", trace_id="req-1", execution_id="exec-1"
    )
    assert captured["execution_id"] == "exec-1"
    assert captured["trace_id"] == "req-1"


@pytest.mark.asyncio
async def test_execution_id_skipped_when_old_core(monkeypatch):
    captured = {}

    def _fake_create(session_id=None, **kwargs):
        captured.update(kwargs)
        return {"session_id": session_id, **kwargs}

    monkeypatch.setattr(tc, "_create_workflow_session", _fake_create)
    monkeypatch.setattr(tc, "_wf_accepts_execution_id", False)
    monkeypatch.setattr(tc, "_wf_accepts_trace_id", False)
    monkeypatch.setattr(tc, "get_x_request_id", lambda: "req-2")

    result = tc.create_workflow_session_with_trace(session_id="cid", execution_id="exec-2")
    assert "execution_id" not in captured
    assert "trace_id" not in captured
    assert result["session_id"] == "cid"