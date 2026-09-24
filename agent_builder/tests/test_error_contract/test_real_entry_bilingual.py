"""COM-03 §8/#7: Builder 真实入口双语测试。

通过真实 FastAPI establish_inbound_context 中间件建立 ContextVar,
验证 x-language=en-us 时 N2L SSE error 输出英文,不是中文。

本文件含两类测试:
- test_builder_real_app_bilingual_*: 使用真实 instance_app() + 真实 N2L 路由 +
  真实 _generate build_sse_error_event 路径,证明三者已在真实框架注册链中串联。
- test_builder_middleware_* / test_builder_sse_*: 合成中间件测试,证明单组件行为。
"""

import json
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from agent_builder.adapter.request_context_bridge import (
    ContextSource,
    RequestContext,
    _request_ctx,
)
from agent_builder.serve.common.inbound_context import (
    apply_platform_headers,
    select_ids,
    write_x_request_id,
)


def _make_app_with_middleware():
    """创建测试 FastAPI app,使用真实 establish_inbound_context 逻辑。"""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def establish_context(request, call_next):
        from agent_builder.adapter.logger_bridge import reset_session_id, set_session_id
        request_id, trace_id, _, _ = select_ids(request.headers)
        ctx = RequestContext(request_id=request_id, source=ContextSource.FASTAPI_MOUNT)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request_token = _request_ctx.set(ctx)
        try:
            trace_token = set_session_id(trace_id)
        except Exception:
            _request_ctx.reset(request_token)
            raise
        try:
            apply_platform_headers(ctx, request.headers)
            response = await call_next(request)
            write_x_request_id(response, request_id)
            return response
        except Exception as exc:
            from agent_builder.serve.common.error_response import (
                build_unhandled_error_response,
            )
            err_response = build_unhandled_error_response(request, exc)
            write_x_request_id(err_response, request_id)
            return err_response
        finally:
            try:
                reset_session_id(trace_token)
            finally:
                _request_ctx.reset(request_token)

    return app


@pytest.mark.asyncio
async def test_builder_middleware_saves_x_language():
    """§6/#7: 真实中间件保存 x-language 到 ContextVar。"""
    app = _make_app_with_middleware()

    @app.get("/test-lang")
    async def test_lang():
        ctx = _request_ctx.get()
        return {"lang": ctx.headers.get("x-language", "missing")}

    client = TestClient(app, raise_server_exceptions=False)

    # English
    resp = client.get(
        "/test-lang",
        headers={"X-Request-Id": "r1", "x-language": "en-us"})
    assert resp.json()["lang"] == "en-us"

    # Chinese
    resp = client.get(
        "/test-lang",
        headers={"X-Request-Id": "r2", "x-language": "zh-cn"})
    assert resp.json()["lang"] == "zh-cn"

    # Missing → default zh-cn
    resp = client.get("/test-lang", headers={"X-Request-Id": "r3"})
    assert resp.json()["lang"] == "zh-cn"


def test_builder_sse_error_english_locale():
    """§7: x-language=en-us 时 N2L SSE error 输出英文。"""
    from agent_builder.common.error_contract import factory
    from agent_builder.common.error_contract.stream_state import SseTerminalGuard

    app = _make_app_with_middleware()

    @app.get("/sse-error")
    async def sse_error():
        ctx = _request_ctx.get()
        guard = SseTerminalGuard()
        guard.begin_streaming()
        event = factory.build_sse_error_event(
            ctx.request_id or None,
            RuntimeError("secret-detail"),
            ctx.headers.get("x-language", "zh-cn"),
            guard,
        )
        if event:
            return PlainTextResponse(event)
        return PlainTextResponse("no event")

    client = TestClient(app, raise_server_exceptions=False)

    # English request
    resp = client.get(
        "/sse-error",
        headers={"X-Request-Id": "r-en", "x-language": "en-us"})
    body = resp.text
    assert "error_code" in body
    assert "Internal server error" in body or "error" in body
    # Should NOT contain Chinese text when en-us is requested
    assert "服务内部错误" not in body, "English request should not return Chinese"

    # Chinese request
    resp_zh = client.get(
        "/sse-error",
        headers={"X-Request-Id": "r-zh", "x-language": "zh-cn"})
    body_zh = resp_zh.text
    # Chinese should be different from English
    assert body != body_zh, "zh-cn and en-us should produce different text"

    # request_id not unknown
    assert "r-en" in body, "request_id should be in output"


def test_builder_sse_error_default_locale_when_missing():
    """§7: 缺失 x-language 时默认 zh-cn。"""
    from agent_builder.common.error_contract import factory
    from agent_builder.common.error_contract.stream_state import SseTerminalGuard

    app = _make_app_with_middleware()

    @app.get("/sse-default")
    async def sse_default():
        ctx = _request_ctx.get()
        guard = SseTerminalGuard()
        guard.begin_streaming()
        event = factory.build_sse_error_event(
            ctx.request_id or None,
            RuntimeError("boom"),
            ctx.headers.get("x-language", "zh-cn"),
            guard,
        )
        if event:
            return PlainTextResponse(event)
        return PlainTextResponse("none")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/sse-default", headers={"X-Request-Id": "r-default"})
    body = resp.text
    # Default zh-cn should contain Chinese
    assert "服务内部错误" in body or "错误" in body, (
        "default locale should be zh-cn (Chinese)")
    assert "r-default" in body


# ---------------------------------------------------------------------------
# 真实 instance_app() 入口测试 — 证明三组件在真实框架注册链中已串联
# ---------------------------------------------------------------------------

def _real_app(monkeypatch):
    """构建真实 instance_app(),仅包含 builder_router(排除 Flask mount 和
    model_service_router),lifespan 替换为 no-op,Executor 替换为抛异常的 mock。

    这保证测试走的是真实 establish_inbound_context 中间件 → 真实 builder_router
    → 真实 _chat → 真实 _generate build_sse_error_event 路径。
    """
    import agent_builder.serve.server_fastapi as sf
    from agent_builder.serve.apis.n2l_api import builder_router
    from agent_builder.serve.server_fastapi import instance_app

    # 1. no-op lifespan(跳过 Redis/S3/prompt-store 初始化)
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    monkeypatch.setattr(sf, "lifespan", _noop_lifespan)

    # 2. apps_map 只含 builder_router(排除 Flask mount + model_service_router)
    monkeypatch.setattr(sf, "apps_map", [builder_router])

    # 3. Executor mock:ainvoke 返回首个 __anext__ 抛 RuntimeError 的 async gen
    class _RaisingAsyncIterator:
        def __init__(self, message):
            self.message = message

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError(self.message)

    class _MockExecutor:
        def __init__(self, *args, **kwargs):
            self.error_message = "secret-gen-detail"

        def ainvoke(self, query):
            return _RaisingAsyncIterator(self.error_message)

    monkeypatch.setattr(
        "agent_builder.nl_to_agent.nl2.Executor", _MockExecutor)
    monkeypatch.setattr(
        "agent_builder.nl_to_agent.nl2.parse_adapter_info", lambda: {})

    return instance_app()


def _n2l_body(cid="conv-real-001"):
    """构造合法 N2L 请求体。"""
    return {
        "query": "hello",
        "model": {"modelName": "test-model"},
        "conversationId": cid,
    }


def test_builder_real_app_bilingual_english(monkeypatch):
    """§6.2: 真实 app + x-language=en-us → SSE error 输出英文,含完整五字段,
    request_id 来自真实中间件 ContextVar,不回显异常 str。
    """
    app = _real_app(monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/v1/proj1/agents/generator/conversations/conv-en-001/chat",
        json=_n2l_body("conv-en-001"),
        headers={"X-Request-Id": "req-real-en", "x-language": "en-us"},
    )
    assert resp.status_code == 200  # StreamingResponse 总是 200

    events = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass

    # START 事件存在(首帧保留)
    assert any(e.get("event") == "START" for e in events), "START event must exist"

    # error 事件存在且唯一
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 1, f"exactly one error event, got {len(error_events)}"

    # 无 END(error 是唯一终态)
    assert not any(
        e.get("event") == "END" for e in events
    ), "no END after error terminal"

    err_data = error_events[0].get("data", {})
    _fields = (
        "error_code", "error_msg", "error_reason",
        "error_suggestion", "request_id",
    )
    for f in _fields:
        assert err_data.get(f), f"error field '{f}' must be non-empty"

    # request_id 来自真实中间件 ContextVar
    assert err_data["request_id"] == "req-real-en"

    # 英文:不含中文文案
    assert "服务内部错误" not in resp.text, "en-us request must not return Chinese"
    # 不回显异常 str(fail-closed)
    assert "secret-gen-detail" not in resp.text, "must not leak exception str"


def test_builder_real_app_bilingual_chinese(monkeypatch):
    """§6.2: 真实 app + x-language=zh-cn → SSE error 输出中文,与英文不同。"""
    app = _real_app(monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/v1/proj1/agents/generator/conversations/conv-zh-001/chat",
        json=_n2l_body("conv-zh-001"),
        headers={"X-Request-Id": "req-real-zh", "x-language": "zh-cn"},
    )
    assert resp.status_code == 200

    # 中文请求应含中文文案
    assert "服务内部错误" in resp.text, "zh-cn request should return Chinese"
    assert "req-real-zh" in resp.text, "request_id from real middleware ContextVar"

    # X-Request-Id 回写(真实中间件)
    assert resp.headers.get("x-request-id") == "req-real-zh"


def test_builder_real_app_default_locale_missing(monkeypatch):
    """§6.2: 真实 app + 无 x-language → 默认 zh-cn。"""
    app = _real_app(monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/v1/proj1/agents/generator/conversations/conv-def-001/chat",
        json=_n2l_body("conv-def-001"),
        headers={"X-Request-Id": "req-real-def"},
    )
    assert resp.status_code == 200
    # 默认 zh-cn
    assert "服务内部错误" in resp.text, "missing x-language should default to zh-cn"
    assert "req-real-def" in resp.text
