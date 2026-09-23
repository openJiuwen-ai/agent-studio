"""COM-03 §10.2: Runtime 真实 ir_execute 多场景测试补充。"""

import json
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_runtime.context.request_context import RequestContext, _request_ctx
from agent_runtime.serve.apis.orchestration import execution_app
from jiuwen.common.exception.base import JiuWenBaseException


def _make_app(request_id="req-real-ir-001", lang="zh-cn"):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def _set_ctx(request, call_next):
        ctx = RequestContext(request_id=request_id, headers={"x-language": lang})
        token = _request_ctx.set(ctx)
        try:
            return await call_next(request)
        finally:
            _request_ctx.reset(token)

    app.include_router(execution_app)
    return app


def _patch_deps(monkeypatch, runner_cls):
    async def _mock_ir_load(path):
        return {"configs": {"mode": "workflow"}}
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.async_ir_load", _mock_ir_load)
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration._get_runner_by_type",
        lambda mode: runner_cls())
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.init_moderation_from_ir",
        lambda ir_json: None)
    mock_cfg = MagicMock()
    mock_cfg.enabled = False
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.get_config",
        lambda: mock_cfg)
    # 隔离 ExecutionRegistry（sync_01 新业务；老分支 stream_response 无注册）
    registry = MagicMock()
    registry.register = AsyncMock()
    registry.unregister = AsyncMock()
    registry.clear_suspension = AsyncMock()
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.get_execution_registry",
        lambda: registry)


def _parse_sse_events(text):
    """解析 SSE 文本为 event dict 列表,每个 {event, data}。"""
    events = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):].strip()
        try:
            obj = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            continue
        evt = obj.get("event")
        data = obj.get("data", obj)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                pass
        events.append({"event": evt, "data": data})
    return events


class _BoomRunner:
    async def run_streaming(self, req, execution_id):
        raise RuntimeError("runner exploded before first event")
        yield


class _BoomAfterFirstRunner:
    async def run_streaming(self, req, execution_id):
        yield b'data: {"event": "start", "data": ""}\n\n'
        raise RuntimeError("runner exploded after first event")


class _NormalRunner:
    async def run_streaming(self, req, execution_id):
        yield b'data: {"event": "start", "data": ""}\n\n'
        yield b'data: {"event": "message", "data": {"answer": "hello"}}\n\n'
        yield b'data: {"event": "done", "data": {"answer": "hello"}}\n\n'


_VALID_BODY = {
    "conversationId": "conv-test-001",
    "irPath": "test-ir-path",
    "query": "test query",
    "responseMode": "streaming",
}


def test_invalid_body_zh_cn(monkeypatch):
    """§10.2.1: 非法 body(zh-cn) → 400 JSON 五字段。"""
    _patch_deps(monkeypatch, _NormalRunner)
    app = _make_app("req-invalid-zh", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json={})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "openjiuwen.12100001"
    for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[f], f"{f} non-empty"
    assert body["request_id"] == "req-invalid-zh"


def test_invalid_body_en_us(monkeypatch):
    """§10.2.2: 非法 body(en-us) → 400 JSON,文案为英文。"""
    _patch_deps(monkeypatch, _NormalRunner)
    app = _make_app("req-invalid-en", "en-us")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json={})
    body = resp.json()
    assert resp.status_code == 400
    # 英文文案验证(与中文不同)
    en_msg = body["error_msg"]
    assert "请求参数校验失败" not in en_msg


def test_ir_load_failure(monkeypatch):
    """§10.2.3: IR 加载失败 → 500,不回显 str(e)。"""
    async def _boom_ir(path):
        raise RuntimeError("secret-ir-load-failure")
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.async_ir_load", _boom_ir)
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration._get_runner_by_type",
        lambda m: _NormalRunner())
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.init_moderation_from_ir",
        lambda ir: None)
    app = _make_app("req-ir-fail", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "openjiuwen.12100004"
    assert "secret-ir-load-failure" not in resp.text
    assert body["request_id"] == "req-ir-fail"


def test_normal_flow_exact_events(monkeypatch):
    """§10.2.4: 正常流 → start→message→done,done 唯一,顺序正确。"""
    _patch_deps(monkeypatch, _NormalRunner)
    app = _make_app("req-normal", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    events = _parse_sse_events(resp.text)
    assert len(events) == 3, f"expected 3 events, got {len(events)}"

    seq = [e["event"] for e in events]
    assert seq == ["start", "message", "done"], (
        f"event order must be start→message→done, got {seq}")

    done_count = sum(1 for e in events if e["event"] == "done")
    assert done_count == 1, "exactly one done event"
    assert events[0]["event"] == "start", "first event must be start"


def test_midstream_failure_exact(monkeypatch):
    """§10.2.5: 首帧后失败 → 1 start + 1 error,无 done。

    error 五字段非空,request_id 来自上下文。
    """
    _patch_deps(monkeypatch, _BoomAfterFirstRunner)
    app = _make_app("req-mid-fail", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    assert "application/json" not in resp.headers.get("content-type", "")

    events = _parse_sse_events(resp.text)
    assert len(events) == 2, f"expected start+error, got {len(events)}: {events}"
    assert events[0].get("event") == "start", "first event must be start (首帧保留)"

    error_evt = events[1]
    assert error_evt.get("event") == "error", "second event must be error"

    err_data = error_evt.get("data", {})
    _fields = (
        "error_code", "error_msg", "error_reason",
        "error_suggestion", "request_id",
    )
    for f in _fields:
        assert err_data.get(f), f"error field '{f}' must be non-empty"
    assert err_data["request_id"] == "req-mid-fail", "request_id must come from context"
    assert err_data.get("error_code") == "openjiuwen.12100004"

    # error 后无 message
    msg_count = sum(1 for e in events if e.get("event") == "message")
    assert msg_count == 0, "no message event after error terminal"
    done_count = sum(1 for e in events if e.get("event") == "done")
    assert done_count == 0, "no done after error terminal"


def test_request_id_from_context(monkeypatch):
    """§10.2: request_id 来自上下文,不为 unknown。"""
    _patch_deps(monkeypatch, _BoomRunner)
    app = _make_app("req-rid-unique", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    body = resp.json()
    assert body["request_id"] == "req-rid-unique"
    assert body["request_id"] != "unknown"
    assert resp.headers.get("x-request-id") == "req-rid-unique"


# ---------------------------------------------------------------------------
# 复审6 §9.4: pending done, aclose, cancel, log-count
# ---------------------------------------------------------------------------

class _DoneThenBoomRunner:
    """Runner that yields a done event then raises (no start sent)."""
    async def run_streaming(self, req, execution_id):
        yield b'data: {"event": "done", "data": {"answer": "early"}}\n\n'
        raise RuntimeError("runner exploded after done")


class _StartDoneBoomRunner:
    """Runner that yields start, then done (pending), then raises."""
    async def run_streaming(self, req, execution_id):
        yield b'data: {"event": "start", "data": ""}\n\n'
        yield b'data: {"event": "done", "data": {"answer": "early"}}\n\n'
        raise RuntimeError("runner exploded after pending done")


class _Plugin105015AfterFirstRunner:
    """模拟 _process_exception 包成形态：首帧后抛 plain JiuWenBaseException(105015)。

    真实链路：restfulapi raise PluginCommonException(105015) → bpmn_workflow
    _process_exception 包成 plain JiuWenBaseException(error_code=105015)（有
    .error_code、无 .code）→ 不被 run_streaming 的 except ExecutionError/BaseError
    捕获 → 传播到 stream_response except Exception → from_plugin_exception。
    """
    async def run_streaming(self, req, execution_id):
        yield b'data: {"event": "start", "data": ""}\n\n'
        raise JiuWenBaseException(
            error_code=105015, message="SECRET-PLUGIN-RESPONSE-NOT-LIST")


def test_pending_done_before_start_returns_http_error(monkeypatch):
    """§5.1: done 在首帧前被暂存,异常→首帧前 HTTP 500 JSON 五字段,0 SSE。"""
    _patch_deps(monkeypatch, _DoneThenBoomRunner)
    app = _make_app("req-done-pre-start", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    # 首帧前失败 → HTTP 500 JSON
    assert resp.status_code == 500
    assert "application/json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["error_code"] == "openjiuwen.12100004"
    for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[f], f"{f} non-empty"
    assert body["request_id"] == "req-done-pre-start"


def test_pending_done_after_start_returns_sse_error(monkeypatch):
    """§5.1: start→done(pending)→exception → start + error,无 done。"""
    _patch_deps(monkeypatch, _StartDoneBoomRunner)
    app = _make_app("req-done-post-start", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    events = _parse_sse_events(resp.text)
    # start + error,无 done
    assert len(events) == 2
    assert events[0].get("event") == "start"
    assert events[1].get("event") == "error"
    done_count = sum(1 for e in events if e.get("event") == "done")
    assert done_count == 0, "no done after error terminal"
    err_data = events[1].get("data", {})
    _fields = (
        "error_code", "error_msg", "error_reason",
        "error_suggestion", "request_id",
    )
    for f in _fields:
        assert err_data.get(f), f"error field '{f}' must be non-empty"
    assert err_data["request_id"] == "req-done-post-start"


def test_midstream_plugin_105015_maps_to_12100006(monkeypatch):
    """P5-R3 决策 A 端到端：流式 mid-stream JiuWenBaseException(105015)（_process_exception
    包成形态，有 .error_code 无 .code）→ stream_response except Exception →
    from_plugin_exception(.error_code==105015) → SSE error event openjiuwen.12100006。
    决策 A：105015 不发布 + sentinel 不泄漏。"""
    _patch_deps(monkeypatch, _Plugin105015AfterFirstRunner)
    app = _make_app("req-pfmt", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    events = _parse_sse_events(resp.text)
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 1, f"expected 1 error event, got {len(error_events)}"
    err_data = error_events[0].get("data", {})
    # 决策 A: 105015 → canonical 12100006（不外露 105015）
    assert err_data["error_code"] == "openjiuwen.12100006"
    assert err_data.get("request_id") == "req-pfmt"
    for f in ("error_msg", "error_reason", "error_suggestion"):
        assert err_data.get(f), f"error field '{f}' non-empty"
    # sentinel + 105015 canonical 不泄漏
    assert "SECRET-PLUGIN-RESPONSE-NOT-LIST" not in resp.text
    assert "openjiuwen.105015" not in resp.text


class _WrappedPlugin105015AfterFirstRunner:
    """模拟引擎包装形态：首帧后抛 ExecutionError(cause=JiuWenBaseException(105015))。

    真实链路（P5-R3a，审视 §1.2）：restfulapi raise PluginCommonException(105015)
    → _process_exception 包成 plain JiuWenBaseException(105015)（Exception 子类）
    → openjiuwen graph/vertex.py ``except Exception`` 再包成
    build_error(WORKFLOW_COMPONENT_EXECUTION_ERROR, cause=原异常)（ExecutionError）
    → run_streaming except ExecutionError 分支 guard re-raise → 传播到
    stream_response except → from_plugin_exception（认 __cause__ 链）。
    此处以伪 runner 直接 re-raise 同形态异常，验证 catch 端 wire。
    """

    async def run_streaming(self, req, execution_id):
        from openjiuwen.core.common.exception.codes import StatusCode
        from openjiuwen.core.common.exception.errors import ExecutionError
        yield b'data: {"event": "start", "data": ""}\n\n'
        raise ExecutionError(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            cause=JiuWenBaseException(
                error_code=105015, message="SECRET-PLUGIN-RESPONSE-NOT-LIST"))


def test_midstream_wrapped_plugin_105015_maps_to_12100006(monkeypatch):
    """P5-R3a：流式包装路径（ExecutionError cause=105015）→ catch 端
    from_plugin_exception 认 __cause__ 链 → SSE error openjiuwen.12100006。

    修复前：from_plugin_exception 只判 exc.error_code（ExecutionError 为引擎码）
    → 12100004；更早版本 runner 层直接 yield data.code=105015 裸码。
    """
    _patch_deps(monkeypatch, _WrappedPlugin105015AfterFirstRunner)
    app = _make_app("req-pfmt-wrapped", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    events = _parse_sse_events(resp.text)
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 1, f"expected 1 error event, got {len(error_events)}"
    err_data = error_events[0].get("data", {})
    assert err_data["error_code"] == "openjiuwen.12100006"
    assert err_data.get("request_id") == "req-pfmt-wrapped"
    for f in ("error_msg", "error_reason", "error_suggestion"):
        assert err_data.get(f), f"error field '{f}' non-empty"
    # 唯一终态：error 后无 done
    done_count = sum(1 for e in events if e.get("event") == "done")
    assert done_count == 0, "error 是唯一终态,不得再有 done"
    # 裸 105015 + sentinel 不泄漏
    assert "SECRET-PLUGIN-RESPONSE-NOT-LIST" not in resp.text
    assert "105015" not in resp.text


class _WrappedNon105015AfterFirstRunner:
    """反证：ExecutionError(cause=105001) 由伪 runner 转成 error event（基线行为，
    模拟 runner 层 guard 判非后的 yield）→ catch 端按普通 error 事件透传。"""

    async def run_streaming(self, req, execution_id):
        yield (
            b'data: {"event": "error", "data": {"code": 105001, '
            b'"message": "[105001] biz"}}\n\n'
        )
        yield b'data: {"event": "done", "data": {}}\n\n'


def test_midstream_wrapped_non_105015_keeps_error_event(monkeypatch):
    """反证：非 105015 业务码（105001）经包装路径 → runner 层保原 yield
    error event（原码透传）+ done 终态——不被 guard 误改/吞掉。"""
    _patch_deps(monkeypatch, _WrappedNon105015AfterFirstRunner)
    app = _make_app("req-pfmt-non", "zh-cn")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/orchestration/ir/execute", json=_VALID_BODY)
    events = _parse_sse_events(resp.text)
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 1
    assert str(error_events[0].get("data", {}).get("code")) == "105001"
    done_count = sum(1 for e in events if e.get("event") == "done")
    assert done_count == 1, "非 105015 保基线 error→done 终态"


def test_prefetched_stream_calls_aclose_on_early_termination():
    """§9.4: _prefetched_stream 在消费者提前停止时调 aclose。"""
    import asyncio
    from agent_runtime.serve.apis.orchestration import _prefetched_stream

    aclose_called = []

    class _MockGen:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            aclose_called.append(True)

    async def _consume_one():
        gen = _prefetched_stream(b"first", _MockGen())
        async for chunk in gen:
            break  # 只取第一个就停

    asyncio.run(_consume_one())
    assert aclose_called, "aclose must be called on early termination"


def test_prefetched_stream_aclose_failure_does_not_propagate():
    """§9.4: aclose 自身失败时不抛,不崩溃。"""
    import asyncio
    from agent_runtime.serve.apis.orchestration import _prefetched_stream

    class _BoomCloseGen:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            raise RuntimeError("aclose boom")

    async def _consume_all():
        gen = _prefetched_stream(b"first", _BoomCloseGen())
        async for chunk in gen:
            pass  # consume first + rest

    # 不应抛异常
    asyncio.run(_consume_all())


def test_prefetched_stream_yields_first_then_rest():
    """§9.4: _prefetched_stream 先输出预取首事件,再透传剩余。"""
    import asyncio
    from agent_runtime.serve.apis.orchestration import _prefetched_stream

    class _MultiGen:
        def __aiter__(self):
            return self

        async def __anext__(self):
            if not hasattr(self, "_count"):
                self._count = 0
            self._count += 1
            if self._count == 1:
                return b"second"
            if self._count == 2:
                return b"third"
            raise StopAsyncIteration

        async def aclose(self):
            pass

    async def _consume():
        gen = _prefetched_stream(b"first", _MultiGen())
        return [chunk async for chunk in gen]

    chunks = asyncio.run(_consume())
    assert chunks == [b"first", b"second", b"third"]


def test_client_cancel_closes_generator_no_error_no_done():
    """§5.3: 客户端取消(CancelledError)→原生成器关闭,无 SSE error,无 done。"""
    import asyncio
    from agent_runtime.serve.apis.orchestration import _prefetched_stream

    closed = []

    class _SlowGen:
        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.sleep(10)  # 模拟慢响应
            return b"data\n\n"

        async def aclose(self):
            closed.append(True)

    async def _cancel_after_first():
        gen = _prefetched_stream(b"first", _SlowGen())
        iterator = gen.__aiter__()
        await iterator.__anext__()  # 取第一个
        # 取第二个时取消——模拟客户端断连
        task = asyncio.create_task(iterator.__anext__())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass

    asyncio.run(_cancel_after_first())
    assert closed, "generator must be closed on client cancel"


def test_aclose_failure_does_not_leak_to_client():
    """§5.3: _prefetched_stream aclose 失败时不泄漏到客户端(已有 except: pass)。

    项目策略：aclose 清理异常被安全吞掉,不追加 done 或 error。
    若未来改为记录安全诊断日志,此测试应同步更新。
    """
    import asyncio
    from agent_runtime.serve.apis.orchestration import _prefetched_stream

    class _BoomCloseGen:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            raise RuntimeError("aclose cleanup boom")

    async def _consume():
        gen = _prefetched_stream(b"first", _BoomCloseGen())
        return [chunk async for chunk in gen]

    # 不抛异常——清理失败被安全吞掉
    chunks = asyncio.run(_consume())
    assert chunks == [b"first"]


def test_first_frame_after_error_logged_once(monkeypatch, caplog):
    """§9.4: 首帧后异常完整栈恰好记录一次。"""
    import logging
    _patch_deps(monkeypatch, _BoomAfterFirstRunner)
    app = _make_app("req-log-once", "zh-cn")

    with caplog.at_level(logging.ERROR, logger="workflow"):
        client = TestClient(app, raise_server_exceptions=False)
        client.post(
            "/v1/orchestration/ir/execute", json=_VALID_BODY)

    stream_fail_logs = [
        r for r in caplog.records
        if "Stream failure" in r.getMessage()
    ]
    assert len(stream_fail_logs) == 1, (
        f"stream failure must be logged exactly once, "
        f"got {len(stream_fail_logs)}")
    # 验证完整异常栈（exc_info 非空）
    assert stream_fail_logs[0].exc_info is not None, (
        "log record must contain full exception traceback (exc_info)")
    # 验证日志消息含异常类型
    assert "RuntimeError" in stream_fail_logs[0].getMessage()
