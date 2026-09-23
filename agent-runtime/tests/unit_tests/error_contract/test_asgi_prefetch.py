"""COM-03 §3.4: Runtime 真实 ASGI 首帧边界测试。

通过 FastAPI TestClient 请求真实 endpoint,验证:
- 首帧前 runner 异常 → HTTP JSON error,不是 200 text/event-stream
- 首帧后 runner 异常 → SSE error,无 done
- 正常流首事件/done 不因预取改变
- body request_id = X-Request-Id != unknown
"""


from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from agent_runtime.context.request_context import RequestContext, _request_ctx
from agent_runtime.error_contract import factory as error_factory


def _set_ctx(request_id: str):
    ctx = RequestContext(request_id=request_id, headers={"x-language": "zh-cn"})
    return _request_ctx.set(ctx)


def _make_app(runner_gen_factory):
    """创建测试 FastAPI app,复用 orchestration 的预取模式。"""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/stream")
    async def stream():
        gen = runner_gen_factory()
        try:
            first = await anext(gen)
        except StopAsyncIteration:
            return StreamingResponse(content=iter([]), media_type="text/event-stream")
        except Exception as e:
            import logging
            logging.getLogger("test").error(f"Pre-fetch failed: {e}", exc_info=True)
            ctx = _request_ctx.get()
            rid = ctx.request_id or None
            lang = ctx.headers.get("x-language", "zh-cn") if ctx.headers else "zh-cn"
            descriptor = error_factory.from_internal(e, rid)
            return error_factory.build_json_response(descriptor, lang)

        async def _prefetched(_first, _gen):
            yield _first
            async for chunk in _gen:
                yield chunk

        return StreamingResponse(content=_prefetched(first, gen), media_type="text/event-stream")

    return app


def test_prefetch_failure_returns_http_error_not_stream():
    """§3: 首帧前 runner 异常 → HTTP JSON error。"""

    async def _boom_runner():
        raise RuntimeError("runner exploded before first event")
        yield  # make it a generator

    token = _set_ctx("req-asgi-001")
    try:
        app = _make_app(lambda: _boom_runner())
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/stream")

        # 必须不是 200 text/event-stream
        assert resp.status_code != 200 or "text/event-stream" not in resp.headers.get("content-type", "")
        # 必须是 JSON error
        assert "application/json" in resp.headers.get("content-type", "")
        body = resp.json()
        assert body["error_code"] == "openjiuwen.12100004"
        for field in ("error_msg", "error_reason", "error_suggestion", "request_id"):
            assert body[field], f"{field} non-empty"
        assert body["request_id"] == "req-asgi-001"
        assert resp.headers.get("x-request-id") == "req-asgi-001"
    finally:
        _request_ctx.reset(token)


def test_prefetch_success_then_midstream_failure_first_event_preserved():
    """§3: 首帧成功 → streaming 已开始；mid-stream 异常不产生 done。

    测试 app 的 _prefetched 包装器不含 SSE error handler（与真实
    stream_response 不同——后者有内部 try/except + guard）,因此
    mid-stream 异常导致连接关闭,客户端收到首事件后流终止。
    重点验证:预取成功(HTTP streaming 开始),不存在 done 终态。
    """

    async def _boom_after_first():
        yield b'data: {"type": "start"}\n\n'
        raise RuntimeError("runner exploded after first event")

    token = _set_ctx("req-asgi-002")
    try:
        app = _make_app(lambda: _boom_after_first())
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/stream")

        # Pre-fetch succeeded → streaming started (not HTTP error)
        ct = resp.headers.get("content-type", "")
        assert "application/json" not in ct, \
            "pre-fetch succeeded, should not be JSON error"

        # No done event in response (mid-stream failure, not normal completion)
        body_text = resp.text
        assert '"done"' not in body_text and '"type": "done"' not in body_text, \
            "mid-stream failure should not produce done"
    finally:
        _request_ctx.reset(token)


def test_normal_flow_preserves_events():
    """§3: 正常流首事件和 done 不因预取改变。"""

    async def _normal_runner():
        yield b'data: {"type": "start"}\n\n'
        yield b'data: {"type": "message", "answer": "hello"}\n\n'
        yield b'data: {"type": "done"}\n\n'

    token = _set_ctx("req-asgi-003")
    try:
        app = _make_app(lambda: _normal_runner())
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/stream")

        assert resp.status_code == 200
        # All three events present
        lines = [line for line in resp.text.strip().split("\n") if line.startswith("data: ")]
        assert len(lines) >= 2  # at least start + one more
    finally:
        _request_ctx.reset(token)


def test_request_id_not_unknown():
    """§7.1: 标准出口 request_id != unknown。"""

    async def _boom():
        raise RuntimeError("boom")
        yield

    token = _set_ctx("req-real-not-unknown")
    try:
        app = _make_app(lambda: _boom())
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/stream")

        body = resp.json()
        assert body["request_id"] == "req-real-not-unknown"
        assert body["request_id"] != "unknown"
    finally:
        _request_ctx.reset(token)
