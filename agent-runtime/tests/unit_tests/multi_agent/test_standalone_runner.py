# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单测需直接验证内部函数与成员
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""StandaloneRunner 跨任务 OTel 上下文传播单测。

背景：成员处理任务运行在 AgentRunSpace 的后台事件循环里，``asyncio.create_task``
只复制创建时的 contextvars，成员 span 会各自成为新 trace 的根。修复方式是把
发送方当前 span 序列化成 W3C traceparent 放进信封 metadata，处理任务创建前
attach、创建后立即 detach。

覆盖点：
1. ``_current_traceparent`` 格式（32 位 trace_id / 16 位 span_id / 2 位 flags）与降级返回空串；
2. ``_attach_envelope_context`` / ``_detach_context`` 的恢复与清理；
3. ``send_message`` 有 span 写入 traceparent、无 span 不写 metadata；
4. 信封 metadata 序列化 round-trip 后 traceparent 仍可 extract 出相同 trace_id；
5. ``_process_next``（SendMessage / Response 两个分支）任务内 trace_id 与信封一致，且外层不残留；
6. ``_create_processing_task`` 无 metadata 时的行为。

全部使用内存 TracerProvider + InMemorySpanExporter，不产生网络/exporter 副作用。
"""

import asyncio
import re
from unittest.mock import MagicMock

import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

import jiuwen.multi_agent.core.runner.standalone_runner as sr
from jiuwen.multi_agent.core.common.message_type import (
    EnvelopeMetadata,
    MessageEnvelope,
    ResponseMessageEnvelope,
    SendMessageEnvelope,
)
from jiuwen.multi_agent.core.enums import ProcessStatus
from jiuwen.multi_agent.core.runner.standalone_runner import StandaloneRunner

# W3C traceparent 合法样例（来自 W3C 规范示例）
_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
_SPAN_ID = "00f067aa0ba902b7"
_TRACEPARENT = f"00-{_TRACE_ID}-{_SPAN_ID}-01"


@pytest.fixture
def tracer():
    """内存 tracer：span 结束即同步导出，无网络、无真实 exporter。"""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    yield provider.get_tracer("ut-standalone-runner")
    provider.shutdown()


class _CaptureQueue:
    """替代 AgentMessageQueue：捕获入队的信封并立即完成其 future。"""

    def __init__(self) -> None:
        self.envelopes = []

    async def put(self, envelope) -> None:
        self.envelopes.append(envelope)
        if envelope.future is not None and not envelope.future.done():
            envelope.future.set_result(["done"])


class _NextQueue:
    """替代 AgentMessageQueue：只提供 get_next_for_processing。"""

    def __init__(self, envelope) -> None:
        self._envelope = envelope
        self._served = False

    async def get_next_for_processing(self):
        if self._served:
            return None
        self._served = True
        return self._envelope


def _send_envelope(traceparent: str | None, future=None) -> SendMessageEnvelope:
    metadata = (
        EnvelopeMetadata(extra={"traceparent": traceparent}) if traceparent else None
    )
    return SendMessageEnvelope(
        message="payload",
        sender="agent-a",
        recipient="agent-b",
        future=future,
        metadata=metadata,
    )


class TestCurrentTraceparent:
    """_current_traceparent 序列化与降级。"""

    @staticmethod
    def test_format_matches_w3c_traceparent_with_active_span(tracer):
        """有活动 span 时输出 00-<32hex>-<16hex>-<2hex>，且与 span 上下文逐段一致。"""
        with tracer.start_as_current_span("controller.send") as span:
            traceparent = sr._current_traceparent()
            ctx = span.get_span_context()
            expected = (
                f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-"
                f"{int(ctx.trace_flags):02x}"
            )

        assert traceparent == expected
        assert re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}", traceparent)
        _, trace_id_hex, span_id_hex, flags = traceparent.split("-")
        assert len(trace_id_hex) == 32
        assert len(span_id_hex) == 16
        assert len(flags) == 2
        assert int(flags, 16) & 1 == 1  # 采样位必须置位，否则子 span 会被下游丢弃

    @staticmethod
    def test_returns_empty_string_when_no_active_span():
        """无活动 span（上下文里的 span 无效）时返回空串，调用方据此不写 metadata。"""
        assert otel_trace.get_current_span().get_span_context().is_valid is False
        assert sr._current_traceparent() == ""

    @staticmethod
    def test_returns_empty_string_when_otel_not_installed(monkeypatch):
        """OTel 缺失（模块级 otel_trace 为 None）时降级返回空串，不抛异常。"""
        monkeypatch.setattr(sr, "otel_trace", None)
        assert sr._current_traceparent() == ""

    @staticmethod
    def test_returns_empty_string_when_otel_api_raises(monkeypatch):
        """读取当前 span 抛异常时不得影响消息发送，返回空串。"""
        broken_trace = MagicMock()
        broken_trace.get_current_span.side_effect = RuntimeError("context store broken")
        monkeypatch.setattr(sr, "otel_trace", broken_trace)

        assert sr._current_traceparent() == ""
        broken_trace.get_current_span.assert_called_once_with()


class TestAttachDetachEnvelopeContext:
    """信封上下文恢复/清理。"""

    @staticmethod
    def test_attach_restores_sender_trace_and_detach_clears_it():
        """attach 后当前 span 的 trace_id/span_id 与信封 traceparent 完全一致；detach 后清空。"""
        envelope = _send_envelope(_TRACEPARENT)

        token = sr._attach_envelope_context(envelope)
        try:
            assert token is not None
            ctx = otel_trace.get_current_span().get_span_context()
            assert ctx.is_valid is True
            assert f"{ctx.trace_id:032x}" == _TRACE_ID
            assert f"{ctx.span_id:016x}" == _SPAN_ID
        finally:
            sr._detach_context(token)

        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.parametrize(
        "metadata",
        [
            None,
            EnvelopeMetadata(),
            EnvelopeMetadata(extra={"traceparent": ""}),
            EnvelopeMetadata(extra={"other": "value"}),
        ],
        ids=["no-metadata", "empty-extra", "empty-traceparent", "other-key"],
    )
    def test_attach_returns_none_without_traceparent(self, metadata):
        """无 metadata / 无 traceparent / traceparent 为空串时返回 None（不 attach）。"""
        envelope = SendMessageEnvelope(
            message="payload",
            sender="agent-a",
            recipient="agent-b",
            metadata=metadata,
        )

        assert sr._attach_envelope_context(envelope) is None

    @staticmethod
    def test_attach_returns_none_when_extract_raises(monkeypatch):
        """propagator 解析异常被吞掉并返回 None，避免坏信封中断消息循环。"""
        class _BrokenPropagator:
            @staticmethod
            def extract(carrier):
                raise RuntimeError("invalid carrier")

        monkeypatch.setattr(sr, "TraceContextTextMapPropagator", _BrokenPropagator)

        assert sr._attach_envelope_context(_send_envelope(_TRACEPARENT)) is None

    @staticmethod
    def test_detach_context_calls_detach_once_and_swallows_errors(monkeypatch):
        """detach 异常不得上抛（否则会打断消息循环），且必须以同一 token 调用一次。"""
        broken_detach = MagicMock(side_effect=RuntimeError("token already detached"))
        monkeypatch.setattr(sr.otel_context, "detach", broken_detach)
        token = object()

        sr._detach_context(token)
        sr._detach_context(None)  # None token 必须早退，不再调用 detach

        broken_detach.assert_called_once_with(token)


class TestSendMessageTracepropagation:
    """send_message 写入 traceparent。"""

    @pytest.mark.asyncio
    async def test_writes_traceparent_of_active_span_into_metadata(self, tracer):
        """有活动 span 时信封 metadata.extra['traceparent'] 等于该 span 的 W3C 串。"""
        runner = StandaloneRunner()
        runner._run_state = MagicMock()
        queue = _CaptureQueue()
        runner._message_queue = queue

        with tracer.start_as_current_span("controller.send") as span:
            result = await runner.send_message("hello", "agent-b", sender="agent-a")
            ctx = span.get_span_context()
            expected = (
                f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-"
                f"{int(ctx.trace_flags):02x}"
            )

        assert result == ["done"]
        assert len(queue.envelopes) == 1
        envelope = queue.envelopes[0]
        assert isinstance(envelope, SendMessageEnvelope)
        assert envelope.sender == "agent-a"
        assert envelope.recipient == "agent-b"
        assert envelope.message == "hello"
        assert envelope.metadata is not None
        assert envelope.metadata.extra == {"traceparent": expected}

    @pytest.mark.asyncio
    async def test_omits_metadata_when_no_active_span(self):
        """无 span 时不写 metadata（避免空 traceparent 污染状态序列化）。"""
        runner = StandaloneRunner()
        runner._run_state = MagicMock()
        queue = _CaptureQueue()
        runner._message_queue = queue
        assert otel_trace.get_current_span().get_span_context().is_valid is False

        await runner.send_message("hello", "agent-b", sender="agent-a")

        envelope = queue.envelopes[0]
        assert envelope.metadata is None


class TestEnvelopeMetadataRoundTrip:
    """信封序列化 round-trip 后 traceparent 仍可用。"""

    @staticmethod
    def test_roundtrip_keeps_extractable_traceparent():
        """to_dict → from_dict 后 traceparent 不变，extract 出的 trace_id/span_id 一致。"""
        envelope = SendMessageEnvelope(
            message={"k": "v"},
            sender="agent-a",
            recipient="agent-b",
            metadata=EnvelopeMetadata(extra={"traceparent": _TRACEPARENT}),
        )

        data = envelope.to_dict()
        assert data["metadata"]["extra"]["traceparent"] == _TRACEPARENT

        restored = SendMessageEnvelope.from_dict(data)
        assert restored.metadata.extra["traceparent"] == _TRACEPARENT

        ctx = TraceContextTextMapPropagator().extract(
            {"traceparent": restored.metadata.extra["traceparent"]}
        )
        extracted = otel_trace.get_current_span(ctx).get_span_context()
        assert extracted.is_valid is True
        assert f"{extracted.trace_id:032x}" == _TRACE_ID
        assert f"{extracted.span_id:016x}" == _SPAN_ID


class TestProcessingTaskContext:
    """处理任务的上下文继承与清理。"""

    @pytest.mark.asyncio
    async def test_process_next_send_envelope_inherits_trace_id(self):
        """SendMessage 分支：任务内当前 span 的 trace_id 等于信封 traceparent 的 trace_id。"""
        runner = StandaloneRunner()
        runner._message_queue = _NextQueue(_send_envelope(_TRACEPARENT))
        seen = {}

        async def fake_handler(envelope):
            await asyncio.sleep(0)
            seen["ctx"] = otel_trace.get_current_span().get_span_context()
            return "handled"

        runner._process_send_message = fake_handler

        result = await runner._process_next()
        assert result.status is ProcessStatus.COMPLETED

        tasks = list(runner._running_tasks)
        assert len(tasks) == 1
        assert await asyncio.gather(*tasks) == ["handled"]

        assert seen["ctx"].is_valid is True
        assert seen["ctx"].trace_id == int(_TRACE_ID, 16)
        # 外层消息循环上下文不得残留信封上下文
        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.asyncio
    async def test_process_next_response_envelope_inherits_trace_id(self):
        """ResponseMessage 分支：同样按信封 traceparent 继承 trace_id 并清理外层上下文。"""
        runner = StandaloneRunner()
        envelope = ResponseMessageEnvelope(
            message=[],
            sender="agent-b",
            recipient="agent-a",
            original_message_id="msg-1",
            future=None,
            metadata=EnvelopeMetadata(extra={"traceparent": _TRACEPARENT}),
        )
        runner._message_queue = _NextQueue(envelope)
        seen = {}

        async def fake_handler(env):
            seen["trace_id"] = otel_trace.get_current_span().get_span_context().trace_id
            return "response-handled"

        runner._process_response_message = fake_handler

        result = await runner._process_next()
        assert result.status is ProcessStatus.COMPLETED
        assert await asyncio.gather(*list(runner._running_tasks)) == ["response-handled"]

        assert seen["trace_id"] == int(_TRACE_ID, 16)
        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.asyncio
    async def test_create_processing_task_without_metadata_keeps_context_clean(self):
        """无 metadata 时任务在调用方上下文执行，且不产生有效 span。"""
        runner = StandaloneRunner()
        envelope = _send_envelope(None)
        seen = {}

        async def handler(env):
            seen["ctx"] = otel_trace.get_current_span().get_span_context()
            return "plain"

        task = runner._create_processing_task(envelope, handler)

        assert await task == "plain"
        assert seen["ctx"].is_valid is False
        assert otel_trace.get_current_span().get_span_context().is_valid is False


class TestRunnerGuards:
    """消息循环的早退/异常分支（保证 trace 改动不改变原有控制流）。"""

    @pytest.mark.asyncio
    async def test_send_message_requires_started_runner(self):
        """未 start：抛 JiuWenBaseException，不构造任何信封（不会写 traceparent）。"""
        runner = StandaloneRunner()
        runner._run_state = None

        with pytest.raises(sr.JiuWenBaseException) as exc_info:
            await runner.send_message("hello", "agent-b", sender="agent-a")

        assert exc_info.value.error_code == sr.StatusCode.MULTI_AGENT_RUNNER_NOT_STARTED.code

    @pytest.mark.asyncio
    async def test_process_next_returns_interrupted_when_stopped(self):
        """已 stop：返回 INTERRUPTED，不再取消息、不创建任务。"""
        runner = StandaloneRunner()
        runner._stopped.set()

        result = await runner._process_next()

        assert result.status is ProcessStatus.INTERRUPTED
        assert result.error_message == "Runner has been stopped"
        assert runner._running_tasks == set()

    @pytest.mark.asyncio
    async def test_process_next_returns_no_messages_when_queue_empty(self):
        """队列为空：返回 NO_MESSAGES，不创建任务。"""
        runner = StandaloneRunner()
        runner._message_queue = _NextQueue(None)

        result = await runner._process_next()

        assert result.status is ProcessStatus.NO_MESSAGES
        assert runner._running_tasks == set()

    @pytest.mark.asyncio
    async def test_process_next_returns_error_for_unknown_envelope_type(self):
        """未知信封类型：返回 ERROR 并带类型信息，不创建任务。"""
        runner = StandaloneRunner()
        unknown = SendMessageEnvelope(message="m", sender="a", recipient="b")
        unknown.__class__ = MessageEnvelope
        runner._message_queue = _NextQueue(unknown)

        result = await runner._process_next()

        assert result.status is ProcessStatus.ERROR
        assert "Unknown message envelope type" in result.error_message
        assert runner._running_tasks == set()


class TestTraceMetadata:
    """_trace_metadata：把当前活动 span 包成信封 metadata（无有效 span 返回 None）。"""

    @staticmethod
    def test_returns_none_when_no_active_span():
        """无活动 span：返回 None，避免空 traceparent 进入状态序列化。"""
        assert otel_trace.get_current_span().get_span_context().is_valid is False
        assert sr._trace_metadata() is None

    @staticmethod
    def test_extra_carries_current_span_traceparent(tracer):
        """有活动 span：extra 只含 traceparent，且可 extract 回同一 trace/span。"""
        with tracer.start_as_current_span("controller.invoke") as span:
            metadata = sr._trace_metadata()
            expected = sr._current_traceparent()
            ctx = span.get_span_context()
            assert expected == (
                f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-"
                f"{int(ctx.trace_flags):02x}"
            )

        assert isinstance(metadata, EnvelopeMetadata)
        assert metadata.extra == {"traceparent": expected}

        extracted = otel_trace.get_current_span(
            TraceContextTextMapPropagator().extract(
                {"traceparent": metadata.extra["traceparent"]}
            )
        ).get_span_context()
        assert extracted.is_valid is True
        assert extracted.trace_id == ctx.trace_id
        assert extracted.span_id == ctx.span_id


class TestAttachEnvelopeContextTraceValidation:
    """_attach_envelope_context 的两道新校验：span context 必须有效、trace_id 必须一致。"""

    @staticmethod
    def test_returns_none_when_envelope_trace_differs_from_current(tracer):
        """信封 trace_id 与当前活动 span 不一致（中断恢复的旧信封）→ 不 attach，上下文不变。"""
        with tracer.start_as_current_span("controller.invoke") as current:
            current_ctx = current.get_span_context()
            envelope = _send_envelope(_TRACEPARENT)
            # 前提：两者确实不是同一条 trace（否则本用例无意义）
            assert f"{current_ctx.trace_id:032x}" != _TRACE_ID

            token = sr._attach_envelope_context(envelope)

            assert token is None
            after = otel_trace.get_current_span().get_span_context()
            assert after.trace_id == current_ctx.trace_id
            assert after.span_id == current_ctx.span_id

        assert otel_trace.get_current_span().get_span_context().is_valid is False

    @pytest.mark.parametrize(
        "traceparent",
        [
            "garbage",
            "00-00000000000000000000000000000000-0000000000000000-01",
            f"00-{_TRACE_ID}-0000000000000000-01",
        ],
        ids=["garbage", "all-zero", "zero-span-id"],
    )
    def test_returns_none_for_unusable_traceparent_and_keeps_context(
        self, tracer, traceparent
    ):
        """traceparent 非法/无法 extract 出有效 span context → 返回 None，当前上下文不变。"""
        with tracer.start_as_current_span("controller.invoke") as current:
            current_ctx = current.get_span_context()

            token = sr._attach_envelope_context(_send_envelope(traceparent))

            assert token is None
            after = otel_trace.get_current_span().get_span_context()
            assert after.trace_id == current_ctx.trace_id
            assert after.span_id == current_ctx.span_id

    @staticmethod
    def test_attaches_when_trace_id_matches_current(tracer):
        """trace_id 一致（同一请求内的成员消息）→ attach 成功，任务内 trace_id 等于信封 trace_id。"""
        with tracer.start_as_current_span("controller.invoke") as current:
            ctx = current.get_span_context()
            same_trace = (
                f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-"
                f"{int(ctx.trace_flags):02x}"
            )

            token = sr._attach_envelope_context(_send_envelope(same_trace))
            try:
                assert token is not None
                inside = otel_trace.get_current_span().get_span_context()
                assert inside.is_valid is True
                assert inside.trace_id == int(f"{ctx.trace_id:032x}", 16)
                assert inside.span_id == int(f"{ctx.span_id:016x}", 16)
            finally:
                sr._detach_context(token)

            back = otel_trace.get_current_span().get_span_context()
            assert back.trace_id == ctx.trace_id
            assert back.span_id == ctx.span_id


class _RecordingMessageQueue:
    """替代 AgentMessageQueue：记录入队信封，并吞掉完成/失败标记调用。"""

    def __init__(self) -> None:
        self.envelopes = []
        self.completed = []
        self.failed = []

    async def put(self, envelope) -> None:
        self.envelopes.append(envelope)

    async def mark_message_completed(self, message_id) -> None:
        self.completed.append(message_id)

    async def mark_message_failed(self, message_id, reason) -> None:
        self.failed.append((message_id, reason))


class _FakeMember:
    """最小成员替身：只产出 on_messages_stream 结果。"""

    async def on_messages_stream(self, messages, context):
        yield {"answer": "ok", "echo": messages}


class _FakeMemberInstanceManager:
    async def get_member_instance(self, recipient):
        return _FakeMember()


class TestResponseEnvelopeTraceMetadata:
    """生产路径：_process_send_message 构造的 ResponseMessageEnvelope 也带 traceparent。"""

    @pytest.mark.asyncio
    async def test_response_envelope_reuses_active_span_traceparent(self, tracer):
        """成员处理期间有活动 span：回程信封 metadata.extra['traceparent'] 即该 span。"""
        runner = StandaloneRunner()
        queue = _RecordingMessageQueue()
        runner._message_queue = queue
        runner._member_instance_manager = _FakeMemberInstanceManager()
        envelope = _send_envelope(None)

        with tracer.start_as_current_span("controller.invoke") as span:
            ctx = span.get_span_context()
            expected = (
                f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-"
                f"{int(ctx.trace_flags):02x}"
            )
            results = await runner._process_send_message(envelope)

        assert results == [{"answer": "ok", "echo": ["payload"]}]
        assert len(queue.envelopes) == 1
        response = queue.envelopes[0]
        assert isinstance(response, ResponseMessageEnvelope)
        assert response.sender == "agent-b"
        assert response.recipient == "agent-a"
        assert response.original_message_id == envelope.message_id
        assert response.metadata is not None
        assert response.metadata.extra == {"traceparent": expected}
        assert queue.completed == [envelope.message_id]

    @pytest.mark.asyncio
    async def test_response_envelope_without_span_has_no_metadata(self):
        """无活动 span：回程信封 metadata 为 None（不写空 traceparent）。"""
        runner = StandaloneRunner()
        queue = _RecordingMessageQueue()
        runner._message_queue = queue
        runner._member_instance_manager = _FakeMemberInstanceManager()

        await runner._process_send_message(_send_envelope(None))

        response = queue.envelopes[0]
        assert isinstance(response, ResponseMessageEnvelope)
        assert response.metadata is None
