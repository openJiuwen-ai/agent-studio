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
    async def test_no_scope_behavior_unchanged(self, monkeypatch):
        """独立工作流（无作用域）：不派生遥测 manager，输出行为不变。

        可失败观测点锁 _oj_telemetry_manager 的派生调用本身：断言一个
        从未上链的 fake tracer 事件列表为空是恒真断言——即便回归成
        「无作用域时从全局/兜底 manager 派生发射」也依然全绿。
        """
        generate_calls = []
        original_generate = TraceManager.generate_manager

        def _recording_generate(handlers, instance_info=None, **kwargs):
            generate_calls.append(instance_info)
            return original_generate(handlers, instance_info, **kwargs)

        monkeypatch.setattr(
            llm_chain_module.TraceManager, "generate_manager", _recording_generate
        )
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=AssistantMessage(content="答案", finish_reason="stop")
        )
        chain = _make_chain(llm, _make_conf())

        result = await chain.invoke({"userFields": {"query": "你好"}}, _FakeSession(), None)

        assert result["userFields"]["raw_output"] == "答案"
        assert generate_calls == []  # 无作用域 ⇒ 不派生遥测 manager

        # 对照：作用域在场时同一链路恰好派生一次（观测点本身有效）
        tracer = _FakeTracer()
        with workflow_trace_scope(_scope_manager(tracer)):
            await chain.invoke({"userFields": {"query": "你好"}}, _FakeSession(), None)
        assert len(generate_calls) == 1


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
    async def test_real_time_path_usage_ttft_finish(self, monkeypatch):
        """真流式：流末载荷含用量、实测 TTFT（秒值）与 finish_reason。

        TTFT 断言须具判别力（检视意见）：假钟每次调用前进 0.2s，首块
        实测 200ms → 秒值 0.2；若回归成直写毫秒（200）或恒 0，断言即败。
        """

        class _StepClock:
            def __init__(self):
                self._now = 1000.0

            def perf_counter(self):
                self._now += 0.2
                return self._now

        monkeypatch.setattr(
            llm_chain_module.time, "perf_counter", _StepClock().perf_counter
        )
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
        # TTFT：首块实测 200ms → 秒值 0.2（毫秒直写/恒 0 均无法通过）
        assert usage_dict["first_token_time"] == pytest.approx(0.2)
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

    @staticmethod
    def test_request_start_iso_accepts_both_dialects():
        """起始时间戳双拼写：core（request_start_time，无 s）与 studio
        模型包装层（requests_start_time，带 s）任一存在即取，缺失为空。"""
        from types import SimpleNamespace

        ts = "2026-10-28T10:00:00"
        assert llm_chain_module._oj_request_start_iso(
            SimpleNamespace(request_start_time=ts)
        ) == ts
        assert llm_chain_module._oj_request_start_iso(
            SimpleNamespace(requests_start_time=ts)
        ) == ts
        assert llm_chain_module._oj_request_start_iso(SimpleNamespace()) == ""

    @staticmethod
    def test_model_name_alone_is_not_usage():
        """model_name 不计入判活（与 planner 口径一致，检视意见）。

        模型名被回填但 token/成本全零时产出全零用量载荷，handler 会把
        全零 token 落成 gen_ai.usage 属性；model_name 仅在真实用量在场
        时随带输出。
        """
        result = llm_chain_module._build_workflow_usage_payload(
            UsageMetadata(model_name="qwen-max"), None
        )
        assert result == {}
        with_usage = llm_chain_module._build_workflow_usage_payload(
            UsageMetadata(model_name="qwen-max", input_tokens=1), None
        )
        assert with_usage["model_name"] == "qwen-max"

    @staticmethod
    def test_usage_missing_optional_fields_no_raise():
        """旧版 core UsageMetadata 缺 cache/成本字段：getattr 兜底不抛。

        生产镜像的 openjiuwen 可能早于 core 字段波次，裸属性访问会在
        流末遥测位 AttributeError（检视意见）。
        """
        from types import SimpleNamespace

        usage = SimpleNamespace(input_tokens=5, output_tokens=2, model_name="m")
        result = llm_chain_module._build_workflow_usage_payload(usage, None)
        assert result["input_tokens"] == 5
        assert result["total_cost"] == 0.0


class TestTelemetryIsolation:
    """遥测故障不改变业务语义；流提前关闭 span 恰好收尾一次。"""

    @pytest.mark.asyncio
    async def test_end_emit_failure_keeps_success(self):
        """on_llm_end 发射抛错：成功调用不被改判失败（guard 只告警）。

        裸 await 在业务 try 内时，遥测桥故障会把已成功的 LLM 调用转成
        COMPONENT_LLM_INVOKE_CALL_FAILED（检视意见）。
        """

        class _EndBoomTracer(_FakeTracer):
            async def trigger(self, source, event_name, **kwargs):
                if event_name == "on_llm_end":
                    raise RuntimeError("遥测桥故障")
                await super().trigger(source, event_name, **kwargs)

        tracer = _EndBoomTracer()
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=AssistantMessage(content="答案", finish_reason="stop")
        )
        chain = _make_chain(llm, _make_conf())

        with workflow_trace_scope(_scope_manager(tracer)):
            result = await chain.invoke(
                {"userFields": {"query": "你好"}}, _FakeSession(), None
            )

        assert result["userFields"]["raw_output"] == "答案"
        assert len(_events_by_name(tracer, "on_llm_start")) == 1

    @pytest.mark.asyncio
    async def test_stream_early_close_finalizes_span(self):
        """流提前关闭（GeneratorExit / 上层 break）：finally 补发一次 end。

        子生成器流末的 on_llm_end 走不到，不补发会留下悬挂 llm.* span
        （检视意见）；恰好收尾一次，不与正常路径叠加。
        """
        tracer = _FakeTracer()
        items = [
            AssistantMessage(content="你"),
            AssistantMessage(content="好"),
        ]
        chain = _make_chain(TestStreamTelemetry._stream_llm(items), _make_conf())

        gen = chain.stream({"userFields": {"query": "你好"}}, _FakeSession(), None)
        with workflow_trace_scope(_scope_manager(tracer)):
            await gen.__anext__()  # 消费首帧后提前关闭
            await gen.aclose()

        assert len(_events_by_name(tracer, "on_llm_start")) == 1
        end = _events_by_name(tracer, "on_llm_end")
        assert len(end) == 1  # finally 补发的收尾，恰好一次
        assert end[0]["outputs"] is None
