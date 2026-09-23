"""COM-03 §3.4: Runtime 真实生产 SSE 出口测试。

驱动 orchestration.py stream_response 的真实异常路径,断言:
- 首帧后失败只发 error,之后无 done
- request_id 来自请求上下文,不等于 execution_id
- cause 不在 error 输出中
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_runtime.context.request_context import RequestContext, _request_ctx


def _set_request_ctx(request_id: str):
    """设置 COM-05 请求上下文（带 request_id 和 headers）。"""
    ctx = RequestContext(
        request_id=request_id,
        headers={"x-language": "zh-cn"},
    )
    return _request_ctx.set(ctx)


async def _collect_events(gen):
    """收集 async generator 的所有 yield 值。"""
    events = []
    async for chunk in gen:
        events.append(chunk)
    return events


class _BoomAfterFirstChunk:
    """模拟 runner:先发一个 chunk,再抛异常。"""

    async def run_streaming(self, req, execution_id):
        yield b'data: {"type": "start"}\n\n'
        raise RuntimeError("runner exploded mid-stream")


@pytest.fixture(autouse=True)
def _mock_execution_registry(monkeypatch):
    """隔离 ExecutionRegistry（sync_01 新业务；老分支 stream_response 无注册）。

    COM-03 SSE 出口测试只验证 SSE error 帧/guard/cause 隔离；注册/注销行为在
    test_cancel_execution.py 覆盖。req 用 MagicMock 提供 conversation_id 等。
    """
    registry = MagicMock()
    registry.register = AsyncMock()
    registry.unregister = AsyncMock()
    registry.clear_suspension = AsyncMock()
    monkeypatch.setattr(
        "agent_runtime.serve.apis.orchestration.get_execution_registry",
        lambda: registry,
    )
    return registry


@pytest.mark.asyncio
async def test_first_frame_after_failure_only_error_no_done():
    """§3.1: 首帧后失败只发 error,之后无 done。"""
    from agent_runtime.serve.apis.orchestration import stream_response

    token = _set_request_ctx("req-real-001")
    try:
        runner = _BoomAfterFirstChunk()
        events = await _collect_events(
            stream_response(req=MagicMock(), execution_id="exec-different-001", runner=runner))

        # 解析所有事件
        parsed = []
        for e in events:
            if isinstance(e, bytes):
                text = e.decode("utf-8").strip()
            else:
                text = str(e).strip()
            if text.startswith("data: "):
                parsed.append(json.loads(text[len("data: "):]))

        # 有 error 事件
        error_events = [p for p in parsed if p.get("event") == "error"]
        assert len(error_events) == 1, f"expected 1 error, got {len(error_events)}"

        # 没有 done 事件（error 是唯一终态）
        done_events = [p for p in parsed if p.get("event") == "done" or p.get("type") == "done"]
        assert len(done_events) == 0, "error 后不得再发 done"

        # error 的 request_id 来自上下文,不等于 execution_id
        error_data = error_events[0]["data"]
        assert error_data["request_id"] == "req-real-001"
        assert error_data["request_id"] != "exec-different-001"
    finally:
        _request_ctx.reset(token)


@pytest.mark.asyncio
async def test_before_first_frame_failure_raises_http():
    """§3.4: 首帧前失败不产生 SSE,直接 raise（走 HTTP handler）。"""

    class _BoomBeforeFirstChunk:
        async def run_streaming(self, req, execution_id):
            raise RuntimeError("runner exploded before first frame")
            yield  # make it a generator (unreachable)

    from agent_runtime.serve.apis.orchestration import stream_response

    token = _set_request_ctx("req-real-002")
    try:
        runner = _BoomBeforeFirstChunk()
        with pytest.raises(RuntimeError, match="before first frame"):
            await _collect_events(
                stream_response(req=MagicMock(), execution_id="exec-002", runner=runner))
    finally:
        _request_ctx.reset(token)


@pytest.mark.asyncio
async def test_cause_not_in_error_output():
    """§3.4: error 输出不泄漏 cause。"""

    class _BoomWithSecret:
        async def run_streaming(self, req, execution_id):
            yield b'data: {"type": "start"}\n\n'
            raise ValueError("secret-internal-detail")

    from agent_runtime.serve.apis.orchestration import stream_response

    token = _set_request_ctx("req-real-003")
    try:
        events = await _collect_events(
            stream_response(req=MagicMock(), execution_id="exec-003", runner=_BoomWithSecret()))
        all_text = " ".join(e.decode("utf-8") if isinstance(e, bytes) else str(e) for e in events)
        assert "secret-internal-detail" not in all_text
    finally:
        _request_ctx.reset(token)
