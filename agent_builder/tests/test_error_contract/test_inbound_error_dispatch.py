# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""G.ERR.13 类型分派 + G.LOG.02 bootstrap logger 定向测试。

按《CodeCheck六项disable处置修改建议》§5.4/§7 验收不变量：
- 前置 JiuWenBaseException → canonical response（from_builder_exception，非 generic 500）
- 前置普通异常 → 13100004 internal response
- 业务异常只记录一次 ERROR + traceback
- SSE response.start 后异常边界（不构建第二个 HTTP Response）
- bootstrap logger 无全局注册、无 Handler 泄漏
"""

import logging
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from agent_builder.adapter.exception_bridge import JiuWenBaseException


def _n2l_body(cid):
    """构造合法 N2L 请求体。"""

    return {
        "query": "hello",
        "model": {"modelName": "test-model"},
        "conversationId": cid,
    }


def _make_app(monkeypatch, pre_exc=None, executor_raises=None):
    """构建真实 instance_app，可控制 load_environment_variables 前置抛异常 / Executor SSE 流后抛。"""
    import agent_builder.serve.server_fastapi as sf
    from agent_builder.serve.apis.n2l_api import builder_router
    from agent_builder.serve.server_fastapi import instance_app

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    monkeypatch.setattr(sf, "lifespan", _noop_lifespan)
    monkeypatch.setattr(sf, "apps_map", [builder_router])
    monkeypatch.setattr("agent_builder.nl_to_agent.nl2.parse_adapter_info", lambda: {})

    if pre_exc is not None:
        async def _raise_env(*a, **kw):
            raise pre_exc

        monkeypatch.setattr("common_utils.load_environment_variables", _raise_env)

    if executor_raises is not None:
        class _RaisingAsyncIterator:
            def __init__(self, message):
                self.message = message

            def __aiter__(self):
                return self

            async def __anext__(self):
                raise RuntimeError(self.message)

        class _MockExecutor:
            def __init__(self, *a, **kw):
                self.error_message = executor_raises

            def ainvoke(self, query):
                return _RaisingAsyncIterator(self.error_message)

        monkeypatch.setattr("agent_builder.nl_to_agent.nl2.Executor", _MockExecutor)

    return instance_app()


# === 1. 前置 JiuWenBaseException → canonical response ===

def test_pre_jiuwen_base_exception_canonical(monkeypatch):
    """call_next 前 load_environment_variables 抛 JiuWenBaseException → from_builder_exception canonical response。"""
    app = _make_app(
        monkeypatch,
        pre_exc=JiuWenBaseException(error_code=102155, message="llm pre fail"),
    )
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/proj1/agents/generator/conversations/conv-jbe/chat",
        json=_n2l_body("conv-jbe"),
        headers={"X-Request-Id": "rid-pre-jbe"},
    )
    # JiuWenBaseException(102155) → from_builder_exception → catalog 13100007/404
    # （非 generic 500，保 canonical code + request_id，G.ERR.13 类型分派正确）
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "openjiuwen.13100007"
    assert body["request_id"] == "rid-pre-jbe"
    # 不外泄原始异常 message
    assert "llm pre fail" not in resp.text


# === 2. 前置普通异常 → 13100004 internal ===

def test_pre_runtime_exception_internal(monkeypatch):
    """call_next 前 load_environment_variables 抛 RuntimeError → 13100004 internal response。"""
    app = _make_app(
        monkeypatch,
        pre_exc=RuntimeError("pre-runtime-secret"),
    )
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/proj1/agents/generator/conversations/conv-rt/chat",
        json=_n2l_body("conv-rt"),
        headers={"X-Request-Id": "rid-pre-rt"},
    )
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "openjiuwen.13100004"
    assert body["request_id"] == "rid-pre-rt"
    assert "pre-runtime-secret" not in resp.text


# === 3. 业务异常只记录一次 ERROR + traceback ===

def test_business_exception_logged_once(monkeypatch, caplog):
    """前置 JiuWenBaseException 在中间件 except 内只记录一次 ERROR + exc_info。"""
    caplog.set_level(logging.ERROR)
    app = _make_app(
        monkeypatch,
        pre_exc=JiuWenBaseException(error_code=102155, message="once-only"),
    )
    client = TestClient(app, raise_server_exceptions=False)
    client.post(
        "/v1/proj1/agents/generator/conversations/conv-once/chat",
        json=_n2l_body("conv-once"),
        headers={"X-Request-Id": "rid-once"},
    )
    error_stacks = [
        r for r in caplog.records
        if r.levelno >= logging.ERROR and r.exc_info is not None
    ]
    assert len(error_stacks) == 1, (
        f"business exception should log exactly one ERROR stack, got {len(error_stacks)}"
    )


# === 4. SSE response.start 后异常边界 ===

def test_sse_response_started_exception_boundary(monkeypatch):
    """SSE 流 response.start(200) 后 __anext__ 抛——不构建第二个 HTTP Response，流内收口 error。"""
    app = _make_app(monkeypatch, executor_raises="sse-secret-detail")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/proj1/agents/generator/conversations/conv-sse/chat",
        json=_n2l_body("conv-sse"),
        headers={"X-Request-Id": "rid-sse"},
    )
    # StreamingResponse response.start 已发送 200，不得重新构建 JSONResponse（无 500 重置）
    assert resp.status_code == 200
    # 流内应有 canonical error 帧
    assert b"error_code" in resp.content
    # 原始异常字符串不外泄
    assert b"sse-secret-detail" not in resp.content
    assert b"rid-sse" in resp.content


# === 5. bootstrap logger 无全局注册 + 无 Handler 泄漏 ===

def test_bootstrap_logger_no_global_registration():
    """_emit_failure_to_stderr 的隔离 Logger 不注册全局 loggerDict、不残留 Handler。"""
    from agent_builder.serve.common.logger.log_init import _emit_failure_to_stderr

    before = set(logging.Logger.manager.loggerDict.keys())
    root_handlers_before = list(logging.getLogger().handlers)

    _emit_failure_to_stderr()
    _emit_failure_to_stderr()  # 连续两次，验证不叠加

    after = set(logging.Logger.manager.loggerDict.keys())
    # bootstrap Logger 不注册到全局树
    assert "agent_builder.bootstrap" not in after
    assert before == after
    # root handler 数量不变（不传播、不叠加）
    assert logging.getLogger().handlers == root_handlers_before
