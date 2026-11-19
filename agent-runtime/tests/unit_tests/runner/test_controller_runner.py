# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单测需直接验证内部函数与成员
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
ControllerRunner.run_blocking 单元测试

Controller 正常流产出 SSE bytes("data: {...}\\n\\n"),错误流(adapt_error)产出 dict;
run_blocking 必须同时支持两类输入,并按"完整终态优先、delta 兜底"裁决,
保证答案恰好一份(不重复 ×4、不空 ×0)。
"""

# pylint: disable=no-self-use

import json
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime.runner.controller_runner import ControllerRunner
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

import agent_runtime.runner.controller_runner as controller_runner_mod
from agent_runtime.runner.controller_runner import (
    _bind_request_span,
    _mark_span_error,
)
from agent_runtime.schemas.orchestration_mgr import ExecutionRequest


def _sse(event: str, data: dict | None = None) -> bytes:
    """构造 Controller run_streaming 正常流产出的 SSE bytes帧。"""
    payload = {"event": event, "data": data or {}}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


class TestControllerRunBlocking:
    """以真实 SSE bytes 为主输入,精确断言,不允许空结果蒙混通过。"""

    @pytest.mark.asyncio
    async def test_real_reproduction_sequence_exactly_one_copy(self):
        """真实复现序列:message delta×2 + message_end + workflow_end + done → 恰好一份。"""
        answer = "🔧【技术·child-B】已接单: 我需要技术支持"
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message", {"answer": "🔧【技术·child-B】已接单: "})
            yield _sse("message", {"answer": "我需要技术支持"})
            yield _sse("message_end", {"answer": answer})     # 完整快照
            yield _sse("workflow_end", {"answer": answer})    # 完整快照(权威源)
            yield _sse("done", {"answer": answer})            # done#1 带 answer,应忽略

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == answer  # 精确一份,不是 answer×2 或 answer×4

    @pytest.mark.asyncio
    async def test_workflow_end_only(self):
        """终态唯一:只有 workflow_end → 返回 workflow_end 答案。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("start", {})
            yield _sse("workflow_end", {"answer": "完整答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "完整答案"

    @pytest.mark.asyncio
    async def test_message_end_only(self):
        """message_end 唯一:返回 message_end 答案。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message_end", {"answer": "终态答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "终态答案"

    @pytest.mark.asyncio
    async def test_delta_only_no_terminal(self):
        """仅 delta:message×N 无终态 → 正确拼接 delta。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message", {"answer": "foo"})
            yield _sse("message", {"answer": "bar"})
            yield _sse("done", {})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "foobar"

    @pytest.mark.asyncio
    async def test_cumulative_message_with_terminal_no_duplication(self):
        """累计 message:A、AB + 终态 AB → 返回 AB,不能 AAB。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message", {"answer": "A"})
            yield _sse("message", {"answer": "AB"})
            yield _sse("message_end", {"answer": "AB"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "AB"  # 终态优先,不受累积 message 影响

    @pytest.mark.asyncio
    async def test_dict_chunks_compatible_with_bytes(self):
        """dict 兼容(错误路径 adapt_error 产 dict):与 bytes 结果一致。"""
        answer = "dict 路径答案"
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "dict "}}
            yield {"event": "message", "data": {"answer": "路径答案"}}
            yield {"event": "workflow_end", "data": {"answer": answer}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == answer

    @pytest.mark.asyncio
    async def test_output_fallback(self):
        """data.output 非空(无 answer)→ 正确返回 output。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("workflow_end", {"output": "output 答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "output 答案"

    @pytest.mark.asyncio
    async def test_empty_and_non_data_frames_skipped(self):
        """空帧:None、空 answer、非 data: 帧 → 跳过且不影响有效结果。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield None
            yield _sse("message", {"answer": ""})   # 空 answer,跳过
            yield b"keep-alive\n\n"                 # 非 data: 帧,跳过
            yield _sse("workflow_end", {"answer": "有效答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "有效答案"

    @pytest.mark.asyncio
    async def test_invalid_input_does_not_crash(self):
        """非法输入:非法 UTF-8/JSON/不支持类型 → 有日志、不崩溃、返回空。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield b"\xff\xfe not utf-8"            # 非法 UTF-8 → 逐帧吞
            yield _sse("message", {"answer": "x"})  # 有效帧
            yield "data: {not json}\n\n".encode("utf-8")  # JSONDecodeError → 跳过
            yield 12345                                # 不支持类型 → 跳过

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        # 不崩溃;唯一有效帧是 message "x",无终态 → delta 兜底
        assert result == "x"


@pytest.fixture
def sdk_tracer():
    """内存 tracer：span 结束即同步导出到内存 exporter（无网络、无真实 exporter）。"""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield provider.get_tracer("ut-controller-runner"), exporter
    provider.shutdown()


def _request() -> ExecutionRequest:
    return ExecutionRequest(conversationId="conv-ut-1", query="你好", ir_path="ir://ut")


class TestBindRequestSpan:
    """_bind_request_span：把 IR 身份写回请求级根 span。"""

    @staticmethod
    def test_sets_name_and_agent_attributes(sdk_tracer):
        """有 agentName/agentId：span 名改为 invoke_agent {name}，并写 gen_ai.agent.name/id。"""
        tracer, exporter = sdk_tracer
        span = tracer.start_span("invoke_agent")

        _bind_request_span(span, {"agentName": "客服助手", "agentId": "agent-42"})
        span.end()

        finished = exporter.get_finished_spans()[0]
        assert finished.name == "invoke_agent 客服助手"
        assert finished.attributes["gen_ai.agent.name"] == "客服助手"
        assert finished.attributes["gen_ai.agent.id"] == "agent-42"

    @staticmethod
    def test_agent_name_only_does_not_set_agent_id(sdk_tracer):
        """只有 agentName：只改名与 name 属性，不写 gen_ai.agent.id。"""
        tracer, exporter = sdk_tracer
        span = tracer.start_span("invoke_agent")

        _bind_request_span(span, {"agentName": "写作助手"})
        span.end()

        finished = exporter.get_finished_spans()[0]
        assert finished.name == "invoke_agent 写作助手"
        assert finished.attributes["gen_ai.agent.name"] == "写作助手"
        assert "gen_ai.agent.id" not in finished.attributes

    @staticmethod
    def test_agent_id_only_keeps_original_name(sdk_tracer):
        """只有 agentId：保留原始 span 名，仅补 gen_ai.agent.id。"""
        tracer, exporter = sdk_tracer
        span = tracer.start_span("invoke_agent")

        _bind_request_span(span, {"agentId": "agent-7"})
        span.end()

        finished = exporter.get_finished_spans()[0]
        assert finished.name == "invoke_agent"
        assert finished.attributes["gen_ai.agent.id"] == "agent-7"
        assert "gen_ai.agent.name" not in finished.attributes

    @pytest.mark.parametrize("ir_json", [None, [], "agent-decl", 42], ids=["none", "list", "str", "int"])
    def test_non_mapping_ir_json_does_not_touch_span(self, sdk_tracer, ir_json):
        """IR 不是 dict（加载异常/结构异常）：不调用 span 任何写方法。"""
        tracer, _ = sdk_tracer
        span = MagicMock()

        _bind_request_span(span, ir_json)

        span.update_name.assert_not_called()
        span.set_attribute.assert_not_called()

    @staticmethod
    def test_none_span_is_noop():
        """span 为 None（OTel 关闭）：不抛异常。"""
        _bind_request_span(None, {"agentName": "x", "agentId": "y"})

    @staticmethod
    def test_swallows_span_exception_and_still_sets_id():
        """改名失败（span 已结束等）被吞掉，后续属性写入仍执行，避免打断主流程。"""
        span = MagicMock()
        span.update_name.side_effect = RuntimeError("span already ended")

        _bind_request_span(span, {"agentName": "客服助手", "agentId": "agent-42"})

        span.update_name.assert_called_once_with("invoke_agent 客服助手")
        # try 块内异常会终止后续属性写入（仅改名失败，不写任何 gen_ai.* 属性）
        span.set_attribute.assert_not_called()


class TestMarkSpanError:
    """_mark_span_error：按调用方实际收到的错误标记根 span。"""

    @staticmethod
    def test_sets_error_status_and_truncates_message_to_256(sdk_tracer):
        """超长错误信息截断到 256 字符，状态为 ERROR。"""
        tracer, exporter = sdk_tracer
        span = tracer.start_span("invoke_agent")

        _mark_span_error(span, "E" * 300)
        span.end()

        finished = exporter.get_finished_spans()[0]
        assert finished.status.status_code is StatusCode.ERROR
        assert finished.status.description == "E" * 256
        assert len(finished.status.description) == 256

    @staticmethod
    def test_none_span_is_noop_and_span_failure_is_swallowed():
        """span 为 None 或 set_status 抛异常时都不上抛，且入参是 ERROR 状态对象。"""
        _mark_span_error(None, "boom")

        broken_span = MagicMock()
        broken_span.set_status.side_effect = RuntimeError("span closed")
        _mark_span_error(broken_span, "IR load failed: timeout")

        broken_span.set_status.assert_called_once()
        status = broken_span.set_status.call_args[0][0]
        assert status.status_code is StatusCode.ERROR
        assert status.description == "IR load failed: timeout"


class TestRunStreamingRequestRootSpan:
    """run_streaming 请求级根 span 生命周期。"""

    @pytest.mark.asyncio
    async def test_ok_path_marks_ok_and_ends_span(self, sdk_tracer, monkeypatch):
        """正常流：根 span 名/属性正确、状态 OK、结束导出一次，且 context 已 detach。"""
        tracer, exporter = sdk_tracer
        monkeypatch.setattr(controller_runner_mod, "setup_otel_tracer", lambda: tracer)
        runner = ControllerRunner(api_key="test")
        captured = {}

        async def fake_stream(self, req, execution_id=None, span=None, error_state=None):
            captured["span"] = span
            captured["execution_id"] = execution_id
            captured["error_state"] = error_state
            yield b"chunk-1"
            yield b"chunk-2"

        with patch.object(ControllerRunner, "_run_streaming", fake_stream):
            chunks = [c async for c in runner.run_streaming(_request(), "exec-9")]

        assert chunks == [b"chunk-1", b"chunk-2"]
        assert captured["execution_id"] == "exec-9"

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        root = spans[0]
        assert root.name == "invoke_agent"
        assert root.attributes["gen_ai.operation.name"] == "invoke_agent"
        assert root.attributes["openjiuwen.session.id"] == "conv-ut-1"
        assert root.status.status_code is StatusCode.OK
        # 传给 _run_streaming 的必须是同一个根 span（子 span 才能挂上去）
        assert captured["span"].get_span_context().trace_id == root.context.trace_id
        # 第 4 个参数必须是共享的 error_state 且初值为未出错
        assert captured["error_state"] == {"has_error": False}
        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.asyncio
    async def test_error_path_marks_error_and_reraises(self, sdk_tracer, monkeypatch):
        """实现抛异常：根 span 置 ERROR（含异常名）、正常 end，异常继续上抛。"""
        tracer, exporter = sdk_tracer
        monkeypatch.setattr(controller_runner_mod, "setup_otel_tracer", lambda: tracer)
        runner = ControllerRunner(api_key="test")

        async def failing_stream(self, req, execution_id=None, span=None, error_state=None):
            if not error_state:  # pragma: no cover
                yield b"never"
            raise ValueError("boom")

        with patch.object(ControllerRunner, "_run_streaming", failing_stream):
            with pytest.raises(ValueError, match="boom"):
                async for _ in runner.run_streaming(_request(), "exec-err"):
                    pass

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        root = spans[0]
        assert root.status.status_code is StatusCode.ERROR
        assert root.status.description == "ValueError: boom"
        assert root.end_time is not None
        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.asyncio
    async def test_without_tracer_passes_chunks_through(self, monkeypatch):
        """setup_otel_tracer 返回 None（OTel 关闭）：不建 span，chunk 原样透传。"""
        monkeypatch.setattr(controller_runner_mod, "setup_otel_tracer", lambda: None)
        runner = ControllerRunner(api_key="test")
        captured = {}

        async def fake_stream(self, req, execution_id=None, span=None, error_state=None):
            captured["span"] = span
            yield b"data: {}\n\n"

        with patch.object(ControllerRunner, "_run_streaming", fake_stream):
            chunks = [c async for c in runner.run_streaming(_request())]

        assert chunks == [b"data: {}\n\n"]
        assert captured["span"] is None
        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.asyncio
    async def test_early_return_error_state_keeps_span_error(self, sdk_tracer, monkeypatch):
        """早退错误分支：_run_streaming 内部标记 ERROR 后正常结束，根 span 终态仍是 ERROR。

        早退分支（IR 加载失败/建 group 失败等）只 yield 错误帧后 return，不抛异常；
        若外层只按"是否抛异常"决定终态，会把已标记的 ERROR 覆盖成 OK。
        """
        tracer, exporter = sdk_tracer
        monkeypatch.setattr(controller_runner_mod, "setup_otel_tracer", lambda: tracer)
        runner = ControllerRunner(api_key="test")
        captured = {}

        async def early_return_stream(self, req, execution_id=None, span=None, error_state=None):
            captured["span"] = span
            captured["error_state"] = error_state
            _mark_span_error(span, "IR load failed: boom", error_state)
            yield b"data: {\"event\": \"error\"}\n\n"
            return  # 早退：不抛异常

        with patch.object(ControllerRunner, "_run_streaming", early_return_stream):
            chunks = [c async for c in runner.run_streaming(_request(), "exec-early")]

        assert chunks == [b"data: {\"event\": \"error\"}\n\n"]
        # error_state 被 _mark_span_error 置位，证明共享的是同一个 dict
        assert captured["error_state"] == {"has_error": True}
        root = exporter.get_finished_spans()[0]
        assert root.status.status_code is StatusCode.ERROR
        assert root.status.description == "IR load failed: boom"
        assert root.end_time is not None
        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.asyncio
    async def test_span_creation_failure_falls_back_to_none(self, monkeypatch):
        """start_span/set_attribute 抛异常：回落 span=None/token=None，chunk 仍可透传。"""
        broken_tracer = MagicMock()
        broken_tracer.start_span.side_effect = RuntimeError("exporter broken")
        monkeypatch.setattr(
            controller_runner_mod, "setup_otel_tracer", lambda: broken_tracer
        )
        runner = ControllerRunner(api_key="test")
        captured = {}

        async def fake_stream(self, req, execution_id=None, span=None, error_state=None):
            captured["span"] = span
            captured["error_state"] = error_state
            yield b"chunk-ok"

        with patch.object(ControllerRunner, "_run_streaming", fake_stream):
            chunks = [c async for c in runner.run_streaming(_request())]

        assert chunks == [b"chunk-ok"]
        assert captured["span"] is None
        assert captured["error_state"] == {"has_error": False}
        broken_tracer.start_span.assert_called_once_with("invoke_agent")
        # span 未创建，也无残留上下文
        assert otel_trace.get_current_span().get_span_context().is_valid is False


class TestRunStreamingEarlyErrorBranches:
    """_run_streaming 三个早退错误分支：标记 error_state 后 return，外层不得覆盖为 OK。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("stage", "expected_description"),
        [
            ("ir_load", "IR load failed: ir boom"),
            ("build_input", "build_agent_input failed: input boom"),
            ("agent_group", "agent group creation failed: group boom"),
        ],
    )
    async def test_early_branch_marks_error_status_and_yields_one_error_frame(
        self, sdk_tracer, monkeypatch, stage, expected_description
    ):
        """每个早退分支：只 yield 一帧 error，根 span 终态 ERROR（不被 OK 覆盖）。"""
        tracer, exporter = sdk_tracer
        monkeypatch.setattr(controller_runner_mod, "setup_otel_tracer", lambda: tracer)

        async def ok_ir_load(path):
            return {"agentName": "客服助手"}

        async def boom_ir_load(path):
            raise RuntimeError("ir boom")

        async def ok_build_agent_input(req):
            return MagicMock(), MagicMock(), MagicMock()

        async def boom_build_agent_input(req):
            raise RuntimeError("input boom")

        async def boom_ir_to_agent_group(*args, **kwargs):
            raise RuntimeError("group boom")

        if stage == "ir_load":
            monkeypatch.setattr(controller_runner_mod, "async_ir_load", boom_ir_load)
        elif stage == "build_input":
            monkeypatch.setattr(controller_runner_mod, "async_ir_load", ok_ir_load)
            monkeypatch.setattr(
                controller_runner_mod, "build_agent_input", boom_build_agent_input
            )
        else:
            monkeypatch.setattr(controller_runner_mod, "async_ir_load", ok_ir_load)
            monkeypatch.setattr(
                controller_runner_mod, "build_agent_input", ok_build_agent_input
            )
            monkeypatch.setattr(
                controller_runner_mod.IRConverter,
                "ir_to_agent_group",
                boom_ir_to_agent_group,
            )

        runner = ControllerRunner(api_key="test")
        chunks = [
            chunk async for chunk in runner.run_streaming(_request(), "exec-early")
        ]

        assert len(chunks) == 1
        assert chunks[0]["event"] == "error"
        root = exporter.get_finished_spans()[0]
        assert root.status.status_code is StatusCode.ERROR
        assert root.status.description == expected_description
        assert root.end_time is not None
        # 早退路径同样要把请求级上下文清干净
        assert otel_trace.get_current_span().get_span_context().is_valid is False


    @pytest.mark.asyncio
    async def test_streaming_exception_branch_marks_error_and_yields_frame(
        self, sdk_tracer, monkeypatch
    ):
        """第 4 个错误点：成员流执行抛异常 → 根 span ERROR，且只 yield 一帧 error。

        该分支不经过 run_streaming 的 except（_run_streaming 内部捕获后 return），
        因此必须由 error_state 保证终态不被覆盖成 OK。
        """
        tracer, exporter = sdk_tracer
        monkeypatch.setattr(controller_runner_mod, "setup_otel_tracer", lambda: tracer)

        async def ok_ir_load(path):
            return {}

        async def ok_build_agent_input(req):
            return MagicMock(), MagicMock(), MagicMock()

        async def ok_ir_to_agent_group(*args, **kwargs):
            return MagicMock()

        def boom_create_session(**kwargs):
            raise RuntimeError("session boom")

        class _StateManager:
            async def delete_state(self, session_id):
                return None

        monkeypatch.setattr(controller_runner_mod, "async_ir_load", ok_ir_load)
        monkeypatch.setattr(
            controller_runner_mod, "build_agent_input", ok_build_agent_input
        )
        monkeypatch.setattr(
            controller_runner_mod.IRConverter,
            "ir_to_agent_group",
            ok_ir_to_agent_group,
        )
        monkeypatch.setattr(
            controller_runner_mod,
            "create_agent_session_with_trace",
            boom_create_session,
        )
        monkeypatch.setattr(controller_runner_mod, "AsyncStateManager", _StateManager)

        runner = ControllerRunner(api_key="test")
        chunks = [
            chunk async for chunk in runner.run_streaming(_request(), "exec-stream-err")
        ]

        assert len(chunks) == 1
        assert chunks[0]["event"] == "error"
        root = exporter.get_finished_spans()[0]
        assert root.status.status_code is StatusCode.ERROR
        assert root.status.description == "agent execution failed: session boom"
        assert root.end_time is not None
        assert otel_trace.get_current_span().get_span_context().is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

