# tests/unit_tests/extension/workflow_node/test_llm_chain_telemetry.py
# pylint: disable=protected-access  # 单测需直接设置内部状态 _llm/_initialized 等
"""LLMChain 工作流 LLM 节点 OTel 遥测插桩单测（issue #1583 第 7 节）。

覆盖：作用域派生 manager 的扁平键（request_params / message_count /
class_name=模型名）与继承键（agent 身份/会话事实）、invoke 与两条流式
路径（real_time / thinking_enabled）的 on_llm_start/end/error 发射、
usage 载荷按 handler 约定键名过滤（junk 键绝不入载荷）、JSON 模式经
invoke 单次插桩不重复、无作用域（独立工作流）行为不变。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from jiuwen.extension.workflow_node import llm_chain as llm_chain_module
from jiuwen.extension.workflow_node.llm_chain import LLMChain
from jiuwen.insight.manager import TraceManager
from jiuwen.insight.workflow_trace_scope import workflow_trace_scope
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.foundation.llm.schema.message import (
    AssistantMessage,
    UsageMetadata,
)

MESSAGES = [{"role": "user", "content": "你好"}]


class _FakeTracer:
    """记录双写桥转发事件的最小替身（与 insight 侧单测同构）。"""

    def __init__(self):
        self.events = []

        class _SpanManager:
            last_span = None

            @staticmethod
            def create_agent_span(parent):
                return type("Span", (), {"invoke_id": "i", "child_invokes_id": []})()

            @staticmethod
            def update_span(span, data):
                pass

        self.tracer_agent_span_manager = _SpanManager()

    async def trigger(self, source, event_name, **kwargs):
        self.events.append((event_name, kwargs))


class _FakeSession:
    """stream() 读取面的最小会话替身。"""

    def get_component_id(self):
        return "llm_node_1"

    async def write_custom_stream(self, schema):
        pass

    async def trace(self, data=None, **kwargs):
        pass


def _make_conf(thinking_type=None, response_type="text"):
    hyper = {}
    if thinking_type:
        hyper["thinking"] = {"type": thinking_type}
    return {
        "name": "总结节点",
        "model": {
            "modelName": "qwen-max",
            "modelType": "LLM",
            "hyperParameters": {
                **hyper,
                "temperature": 0.7,
                "top_p": 0.9,
            },
        },
        "deployMode": "workflow",
        "templateContent": [{"content": "{{query}}", "role": "user"}],
        "responseFormat": {"type": response_type},
        "userFields": {
            "inputs": [
                {"sourceType": "ref", "id": "query", "type": "string", "required": True}
            ],
            "outputs": [
                {"sourceType": "input", "id": "raw_output", "type": "string"}
            ],
        },
        "stream": True,
        "enableHistory": False,
        "memory": {"enable": False},
    }


def _make_chain(llm, conf):
    chain = LLMChain(conf=conf)
    chain._llm = llm
    chain._initialized = True

    async def _noop_inject(messages, inputs):
        pass

    chain._inject_retrieved_memory = _noop_inject
    return chain


def _scope_manager(tracer):
    """controller 链 child TraceManager 替身：携带身份/会话事实与 oj tracer。"""
    return TraceManager(
        trace_handlers=[],
        openjiuwen_tracer=tracer,
        agent_identity={"agent_id": "w1", "agent_name": "天气预测"},
        conversation_facts={"conversation_id": "c-1", "user_id": "u-1"},
    )


def _events_by_name(tracer, name):
    return [kwargs for event_name, kwargs in tracer.events if event_name == name]


class TestInvokeTelemetry:
    @pytest.mark.asyncio
    async def test_start_flat_keys_and_end_payload(self):
        """invoke：start 携带扁平键+继承键，end 载荷只含 handler 约定键。"""
        tracer = _FakeTracer()
        usage = UsageMetadata(
            input_tokens=10,
            output_tokens=6,
            model_name="qwen-max",
            total_cost=0.02,
            first_token_time="2026-10-28T10:00:02",
            request_start_time="2026-10-28T10:00:00",
        )
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=AssistantMessage(
                content="答案", usage_metadata=usage, finish_reason="stop"
            )
        )
        chain = _make_chain(llm, _make_conf())

        with workflow_trace_scope(_scope_manager(tracer)):
            result = await chain.invoke({"userFields": {"query": "你好"}}, _FakeSession(), None)

        # 行为不变：输出照常返回
        assert result["userFields"]["raw_output"] == "答案"

        start = _events_by_name(tracer, "on_llm_start")
        assert len(start) == 1
        info = start[0]["instance_info"]
        assert info["request_params"] == {"temperature": 0.7, "top_p": 0.9}
        assert info["message_count"] == len(MESSAGES)
        # class_name 口径 = 模型名（gen_ai.request.model / span 名）
        assert info["class_name"] == "qwen-max"
        # 继承链：身份与会话事实到达 handler 读取面
        assert info["agent_name"] == "天气预测"
        assert info["conversation_id"] == "c-1"
        assert info["user_id"] == "u-1"

        end = _events_by_name(tracer, "on_llm_end")
        assert len(end) == 1
        outputs = end[0]["outputs"]
        usage_dict = outputs["usage_metadata"]
        assert usage_dict["input_tokens"] == 10
        assert usage_dict["output_tokens"] == 6
        assert usage_dict["model_name"] == "qwen-max"
        assert usage_dict["total_cost"] == 0.02
        # TTFT：ISO 双时间戳差 2s → 秒值 float
        assert usage_dict["first_token_time"] == 2.0
        assert outputs["finish_reason"] == "stop"
        # junk 键绝不入载荷（prompt 为提示词全文，会被序列化进 completion）
        for junk in ("prompt", "code", "err_msg", "task_id", "total_latency"):
            assert junk not in usage_dict
            assert junk not in outputs

    @pytest.mark.asyncio
    async def test_error_emits_on_llm_error(self, monkeypatch):
        """invoke 失败：on_llm_error 发射且异常继续向上传播。

        _format_llm_error_detail 依赖 model_service（studio 侧包，单测环境
        缺失），与遥测无关，替换为直返文案。
        """
        monkeypatch.setattr(
            llm_chain_module, "_format_llm_error_detail", lambda exc: str(exc)
        )
        tracer = _FakeTracer()
        boom = RuntimeError("模型接入URL无效")
        llm = MagicMock()
        llm.invoke = AsyncMock(side_effect=boom)
        chain = _make_chain(llm, _make_conf())

        with workflow_trace_scope(_scope_manager(tracer)):
            with pytest.raises(BaseError):
                await chain.invoke({"userFields": {"query": "你好"}}, _FakeSession(), None)

        errors = _events_by_name(tracer, "on_llm_error")
        assert len(errors) == 1
        assert errors[0]["error"] is boom

    @pytest.mark.asyncio
    async def test_no_scope_behavior_unchanged(self):
        """独立工作流（无作用域）：不派生遥测，输出行为不变。"""
        tracer = _FakeTracer()  # 不绑定作用域
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=AssistantMessage(content="答案", finish_reason="stop")
        )
        chain = _make_chain(llm, _make_conf())

        result = await chain.invoke({"userFields": {"query": "你好"}}, _FakeSession(), None)

        assert result["userFields"]["raw_output"] == "答案"
        assert tracer.events == []


class TestStreamTelemetry:
    @staticmethod
    def _stream_llm(items):
        llm = MagicMock()

        async def _gen(**kwargs):
            for item in items:
                yield item

        llm.stream = MagicMock(return_value=_gen())
        return llm

    @pytest.mark.asyncio
    async def test_real_time_path_usage_ttft_finish(self):
        """真流式：流末载荷含用量、实测 TTFT（秒值）与 finish_reason。"""
        tracer = _FakeTracer()
        items = [
            AssistantMessage(content="你"),
            AssistantMessage(
                content="好",
                usage_metadata=UsageMetadata(
                    input_tokens=8, output_tokens=4, model_name="qwen-max"
                ),
                finish_reason="stop",
            ),
        ]
        chain = _make_chain(self._stream_llm(items), _make_conf())

        frames = []
        with workflow_trace_scope(_scope_manager(tracer)):
            async for frame in chain.stream(
                {"userFields": {"query": "你好"}}, _FakeSession(), None
            ):
                frames.append(frame)

        # 行为不变：内容帧 + 最终帧都在
        assert any("userFields" in f for f in frames)

        assert len(_events_by_name(tracer, "on_llm_start")) == 1
        end = _events_by_name(tracer, "on_llm_end")
        assert len(end) == 1
        outputs = end[0]["outputs"]
        usage_dict = outputs["usage_metadata"]
        assert usage_dict["input_tokens"] == 8
        assert usage_dict["output_tokens"] == 4
        # TTFT：first_token_ms 实测毫秒 → 秒值 float（替身流瞬时到达，
        # 0.0 是合法实测值，键在即证明换算链路接通）
        assert usage_dict["first_token_time"] >= 0
        assert outputs["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_thinking_enabled_path_emits_end(self):
        """思考流式（预消费）路径同样在流末发射用量/finish_reason。"""
        tracer = _FakeTracer()
        items = [
            AssistantMessage(reasoning_content="想一想"),
            AssistantMessage(
                content="结论",
                usage_metadata=UsageMetadata(
                    input_tokens=3, output_tokens=2, model_name="qwen-max"
                ),
                finish_reason="stop",
            ),
        ]
        chain = _make_chain(self._stream_llm(items), _make_conf(thinking_type="enabled"))

        with workflow_trace_scope(_scope_manager(tracer)):
            async for _ in chain.stream(
                {"userFields": {"query": "你好"}}, _FakeSession(), None
            ):
                pass

        assert len(_events_by_name(tracer, "on_llm_start")) == 1
        end = _events_by_name(tracer, "on_llm_end")
        assert len(end) == 1
        outputs = end[0]["outputs"]
        assert outputs["usage_metadata"]["input_tokens"] == 3
        assert outputs["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_json_mode_single_instrumentation(self):
        """JSON 模式经 invoke 委托：仅一次 on_llm_start，不重复插桩。"""
        tracer = _FakeTracer()
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=AssistantMessage(content='{"k": "v"}', finish_reason="stop")
        )
        chain = _make_chain(llm, _make_conf(response_type="json"))

        with workflow_trace_scope(_scope_manager(tracer)):
            async for _ in chain.stream(
                {"userFields": {"query": "你好"}}, _FakeSession(), None
            ):
                pass

        assert len(_events_by_name(tracer, "on_llm_start")) == 1
        assert len(_events_by_name(tracer, "on_llm_end")) == 1

    @pytest.mark.asyncio
    async def test_empty_usage_still_closes_span(self):
        """全空 usage 且无时延信号：载荷为空，on_llm_end(None) 仍收尾 span。"""
        tracer = _FakeTracer()
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=AssistantMessage(content="答案")
        )
        chain = _make_chain(llm, _make_conf())

        with workflow_trace_scope(_scope_manager(tracer)):
            await chain.invoke({"userFields": {"query": "你好"}}, _FakeSession(), None)

        end = _events_by_name(tracer, "on_llm_end")
        assert len(end) == 1
        # 缺数据路径：outputs 为 None（handler 跳过属性设置但收尾 span）
        assert end[0]["outputs"] is None


class TestUsagePayloadSemantics:
    """_build_workflow_usage_payload：与 planner 侧 build_usage_metadata 语义对齐。"""

    @staticmethod
    def test_none_usage_ttft_only():
        result = llm_chain_module._build_workflow_usage_payload(None, 1500.0)
        assert result == {"first_token_time": 1.5}

    @staticmethod
    def test_all_zero_usage_no_latency_yields_empty():
        result = llm_chain_module._build_workflow_usage_payload(UsageMetadata(), None)
        assert result == {}

    @staticmethod
    def test_usage_with_cache_and_reasoning_tokens():
        usage = UsageMetadata(
            input_tokens=10,
            output_tokens=5,
            model_name="m",
            cache_tokens=3,
            reasoning_tokens=2,
        )
        result = llm_chain_module._build_workflow_usage_payload(usage, None)
        assert result["cache_tokens"] == 3
        assert result["reasoning_tokens"] == 2

    @staticmethod
    def test_iso_delta_ms_guards():
        assert llm_chain_module._oj_iso_delta_ms("", "x") is None
        assert llm_chain_module._oj_iso_delta_ms("bad", "also-bad") is None
        delta = llm_chain_module._oj_iso_delta_ms(
            "2026-10-28T10:00:02", "2026-10-28T10:00:00"
        )
        assert delta == 2000.0
