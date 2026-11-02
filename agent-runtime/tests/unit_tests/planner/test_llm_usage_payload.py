# -*- coding: UTF-8 -*-
"""LLM 用量/成本/时延 OTel 载荷单测（issue #1583 第 2、3 节）。

覆盖：usage_metadata 构造 helper 各分支、_format_yield_result 的
inter-token 掐表与 usage 暂存、stream_function_call 发射点载荷。
"""

import asyncio

import pytest

from jiuwen.common.llm_service.messages import AIMessage, UsageMetadata
from jiuwen.planner.common import stream_post_utils as spu
from jiuwen.planner.common.stream_post_utils import (
    FINISH_REASON,
    LATENCY,
    MODEL_USAGE,
    USAGE_METADATA,
    _format_yield_result,
    build_finish_reason,
    build_llm_end_payload,
    build_usage_metadata,
    _iso_delta_ms,
)


def _usage(**overrides):
    """构造带完整字段的 UsageMetadata，按需覆盖。"""
    base = dict(
        model_name="qwen-max",
        finish_reason="stop",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        first_token_time="2026-10-23T10:00:00.200+08:00",
        requests_start_time="2026-10-23T10:00:00+08:00",
        cache_tokens=5,
        reasoning_tokens=7,
        input_cost=0.01,
        output_cost=0.02,
        total_cost=0.03,
    )
    base.update(overrides)
    return UsageMetadata(**base)


class TestIsoDeltaMs:
    @staticmethod
    def test_valid_pair():
        """合法 ISO 对 → 毫秒差。"""
        assert (
            _iso_delta_ms(
                "2026-10-23T10:00:00.250+08:00", "2026-10-23T10:00:00+08:00"
            )
            == 250.0
        )

    @staticmethod
    def test_missing_value_returns_none():
        """任一侧缺失 → None（不抛错）。"""
        assert _iso_delta_ms("", "2026-10-23T10:00:00+08:00") is None
        assert _iso_delta_ms("2026-10-23T10:00:00+08:00", "") is None

    @staticmethod
    def test_bad_format_returns_none():
        """非法格式 → None。"""
        assert _iso_delta_ms("not-a-time", "2026-10-23T10:00:00+08:00") is None


class TestBuildUsageMetadata:
    @staticmethod
    def test_none_returns_empty():
        """无 usage → 空载荷（发射点据此跳过注入）。"""
        assert build_usage_metadata(None) == {}

    @staticmethod
    def test_all_default_usage_returns_empty():
        """全默认 UsageMetadata（模型错误/未上报用量）→ 空载荷，不注入全零键。"""
        assert build_usage_metadata(UsageMetadata()) == {}
        assert build_usage_metadata(UsageMetadata(input_tokens=0)) == {}

    @staticmethod
    def test_model_name_alone_is_not_usage():
        """仅 model_name 不构成真实用量，不得注入全零 token/成本键。

        qwen._chat/_stream 成功路径总会回填 model_name：若把 model_name
        计入判活，上游缺 usage 字段（token 全 0）时仍会产出全零用量载荷，
        违背「缺数据路径不注入键」契约；model_name 仅在有真实用量时随带输出。
        """
        assert build_usage_metadata(UsageMetadata(model_name="qwen-max")) == {}
        # 真实用量在场时 model_name 随带输出不受影响
        result = build_usage_metadata(
            UsageMetadata(model_name="qwen-max", input_tokens=1)
        )
        assert result["model_name"] == "qwen-max"

    @staticmethod
    def test_total_tokens_only_counts_as_usage():
        """仅 total_tokens 有值也构成真实用量，且随载荷输出。

        判活口径须与 build_llm_end_payload 的 has_tokens（含 total_tokens）
        一致：只上报 total_tokens 的实现下，若 usage_metadata 判活漏掉
        total_tokens 而跳过，同一 span 会 model_usage 有数、usage_metadata
        缺席，两载荷口径不一致；载荷内也不得丢 total_tokens（用量桥按
        input+output 推 total 会得全零）。
        """
        result = build_usage_metadata(UsageMetadata(total_tokens=30))
        assert result != {}
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["total_tokens"] == 30

    @staticmethod
    def test_latency_only_usage_still_emits():
        """token 未上报但时间戳在（model_wrapper 无条件打点）→ 仅时延键。

        全零守卫不得误伤可算时延：TTFT 换算秒值、TPOT 透传，且不虚构
        token/成本键（handler 对缺键有 or 0 兜底，无需我方补零）。
        """
        usage = _usage(
            model_name="",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cache_tokens=0,
            reasoning_tokens=0,
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
        )
        result = build_usage_metadata(usage, tpot_ms=12.5)
        assert result["first_token_time"] == pytest.approx(0.2)
        assert result["inter_token_latency_ms"] == 12.5
        assert "input_tokens" not in result
        assert "model_name" not in result
        assert "total_cost" not in result

    @staticmethod
    def test_tpot_only_emits_without_timestamps():
        """无用量也无模型层时间戳，但掐表可算 → 仅 TPOT 键。"""
        result = build_usage_metadata(UsageMetadata(), tpot_ms=5.0)
        assert result == {"inter_token_latency_ms": 5.0}

    @staticmethod
    def test_malformed_usage_degrades_not_raises():
        """usage_metadata 类型异常（如 dict）→ 告警降级空载荷，不抛错。

        构造器承诺不抛：求值点常在业务 try 内（emit_trace_event 实参位），
        抛错会把遥测构造失败灌进业务分支（plan 重抛 / 理解兜底 / 步骤
        误标 error），违背「遥测失败只告警、不改变业务语义」。
        """
        result = build_usage_metadata({"input_tokens": 1})  # type: ignore[arg-type]
        assert result == {}

    @staticmethod
    def test_none_usage_with_tpot_still_emits():
        """无 finish 块（如 finish_reason=length 截断）时不丢 TPOT。

        usage 为 None 但掐表仍在，TPOT 不得被 usage is None 分支静默丢弃。
        """
        assert build_usage_metadata(None, tpot_ms=12.5) == {
            "inter_token_latency_ms": 12.5
        }
        assert build_usage_metadata(None, tpot_ms=None) == {}

    @staticmethod
    def test_full_usage_keys():
        """完整字段 → core handler 约定键名齐全，TTFT 换算为毫秒数值串。"""
        result = build_usage_metadata(_usage(), tpot_ms=12.5)
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 20
        assert result["model_name"] == "qwen-max"
        assert result["total_cost"] == 0.03
        assert result["input_cost"] == 0.01
        assert result["output_cost"] == 0.02
        assert result["cache_tokens"] == 5
        assert result["reasoning_tokens"] == 7
        # 秒值契约：gen_ai.response.time_to_first_chunk 按秒（200ms → 0.2），
        # 直接给 float（semconv double；handler str()→float() 均可解析）
        assert result["first_token_time"] == pytest.approx(0.2)
        assert result["inter_token_latency_ms"] == 12.5

    @staticmethod
    def test_zero_optional_fields_omitted():
        """零值可选字段（缓存/思考量/TPOT）不产出，避免 handler 落 0 值属性。"""
        result = build_usage_metadata(
            _usage(cache_tokens=0, reasoning_tokens=0), tpot_ms=None
        )
        assert "cache_tokens" not in result
        assert "reasoning_tokens" not in result
        assert "inter_token_latency_ms" not in result

    @staticmethod
    def test_negative_ttft_omitted():
        """TTFT 为负（时钟回拨等异常）不产出。"""
        result = build_usage_metadata(
            _usage(first_token_time="2026-10-23T09:59:59+08:00")
        )
        assert "first_token_time" not in result


class TestBuildFinishReason:
    @staticmethod
    def test_normal_reason():
        """正常值透传。"""
        assert build_finish_reason(_usage(finish_reason="function_call")) == (
            "function_call"
        )

    @staticmethod
    def test_placeholder_and_empty():
        """占位值 null / 空值 / 无 usage → 空串（发射点跳过注入）。"""
        assert build_finish_reason(_usage(finish_reason="null")) == ""
        assert build_finish_reason(_usage(finish_reason="")) == ""
        assert build_finish_reason(None) == ""


class TestFormatYieldResult:
    @staticmethod
    def _consume(items, finish_usage):
        """同步驱动 _format_yield_result，返回 (产出列表, finish_usage)。"""
        llm_output, time_dict, model_stat, model_usage = dict(), dict(), dict(), dict()

        async def run():
            collected = []
            async for out in _format_yield_result(
                items,
                llm_output,
                time_dict,
                model_stat,
                model_usage,
                finish_usage=finish_usage,
            ):
                collected.append(out)
            return collected

        return asyncio.run(run()), finish_usage

    @staticmethod
    def _stream(*items):
        async def gen():
            for item in items:
                yield item

        return gen()

    def test_multi_chunk_records_usage_and_tpot(self):
        """多内容块 → finish_usage 暂存 usage 且产出 TPOT。"""
        items = self._stream(
            AIMessage(content="he", usage_metadata=UsageMetadata()),
            AIMessage(content="ll", usage_metadata=UsageMetadata()),
            AIMessage(content="o", usage_metadata=UsageMetadata()),
            AIMessage(content="done", usage_metadata=_usage()),
        )
        _, finish_usage = self._consume(items, dict())
        assert finish_usage.get("usage") is not None
        assert finish_usage["usage"].total_cost == 0.03
        assert "tpot_ms" in finish_usage
        assert finish_usage["tpot_ms"] >= 0

    def test_single_chunk_no_tpot(self):
        """单内容块 → 无 TPOT（均值无意义）。"""
        items = self._stream(
            AIMessage(content="only", usage_metadata=UsageMetadata()),
            AIMessage(content="done", usage_metadata=_usage()),
        )
        _, finish_usage = self._consume(items, dict())
        assert "tpot_ms" not in finish_usage

    def test_chunk_without_usage_metadata_is_content_not_crash(self):
        """中间块 usage_metadata=None → 按内容块处理，不得解引用崩溃。

        AIMessage.usage_metadata 声明 Optional；非逐块挂 usage 的模型
        实现会出现 None 块，原先判 finish 时直接 .finish_reason 解引用
        会 AttributeError 中断整个流处理。
        """
        items = self._stream(
            AIMessage(content="a", usage_metadata=None),
            AIMessage(content="b", usage_metadata=None),
            AIMessage(content="done", usage_metadata=_usage()),
        )
        outputs, finish_usage = self._consume(items, dict())
        assert finish_usage.get("usage") is not None
        assert "tpot_ms" in finish_usage
        assert any(out.get("content") == "a" for out in outputs)

    def test_tpot_unit_is_milliseconds(self, monkeypatch):
        """tpot_ms 单位锁定：time.time() 秒差须 ×1000 入毫秒键。

        假钟每调用前进 0.1s：两内容块间隔 0.2s → TPOT 应为 200ms
        （若漏乘 1000 会得到 0.2）。
        """

        class _StepClock:
            def __init__(self):
                self._now = 1000.0

            def time(self):
                self._now += 0.1
                return self._now

        monkeypatch.setattr(spu.time, "time", _StepClock().time)
        items = self._stream(
            AIMessage(content="a", usage_metadata=UsageMetadata()),
            AIMessage(content="b", usage_metadata=UsageMetadata()),
            AIMessage(content="done", usage_metadata=_usage()),
        )
        _, finish_usage = self._consume(items, dict())
        assert finish_usage["tpot_ms"] == pytest.approx(200.0)

    def test_default_finish_usage_none_keeps_behavior(self):
        """不传 finish_usage（ask_user_module 裸调用场景）行为不变。"""
        llm_output, time_dict, model_stat, model_usage = dict(), dict(), dict(), dict()

        async def run():
            collected = []
            async for out in _format_yield_result(
                self._stream(
                    AIMessage(content="x", usage_metadata=UsageMetadata()),
                    AIMessage(content="done", usage_metadata=_usage()),
                ),
                llm_output,
                time_dict,
                model_stat,
                model_usage,
            ):
                collected.append(out)
            return collected

        collected = asyncio.run(run())
        assert llm_output["content"] == "done"
        assert time_dict.get("total_latency") is not None
        assert collected  # 流式产出不因缺参中断


class TestStreamFunctionCallEmit:
    @staticmethod
    def test_payload_carries_usage_and_finish_reason(monkeypatch):
        """发射点载荷带约定键名的 usage_metadata 与顶层 finish_reason。"""

        class StubManager:
            def __init__(self):
                self.events = []

            async def on_llm_start(self, messages):
                self.events.append(("start", messages))

            async def on_llm_end(self, payload):
                self.events.append(("end", payload))

            async def on_llm_error(self, error):
                self.events.append(("error", error))

        stub_manager = StubManager()
        monkeypatch.setattr(
            spu, "create_trace_manager", lambda *args, **kwargs: stub_manager
        )

        class StubLLM:
            # 生产链路 llm.astream 是被 await 的协程，返回异步生成器
            @staticmethod
            async def astream(inputs, **kwargs):
                async def gen():
                    yield AIMessage(content="he", usage_metadata=UsageMetadata())
                    yield AIMessage(content="llo", usage_metadata=UsageMetadata())
                    yield AIMessage(content="done", usage_metadata=_usage())

                return gen()

        async def run():
            outs = []
            async for out in spu.stream_function_call(
                [{"role": "user", "content": "hi"}], None, StubLLM()
            ):
                outs.append(out)
            return outs

        asyncio.run(run())
        end_payload = stub_manager.events[-1][1]
        assert USAGE_METADATA in end_payload
        usage_dict = end_payload[USAGE_METADATA]
        assert usage_dict["total_cost"] == 0.03
        assert usage_dict["input_tokens"] == 10
        assert usage_dict["first_token_time"] == pytest.approx(0.2)
        assert end_payload[FINISH_REASON] == "stop"
        # insights 原有键保持原样
        assert "model_stat" in end_payload
        assert "model_usage" in end_payload
        assert end_payload["model_usage"]["total_tokens"] == 30

    @staticmethod
    def test_payload_without_usage_data_skips_injection(monkeypatch):
        """finish 块无 usage 数据 → 不注入空 usage_metadata（行为与改前一致）。"""

        class StubManager:
            def __init__(self):
                self.payloads = []

            @staticmethod
            async def on_llm_start(messages):
                pass

            async def on_llm_end(self, payload):
                self.payloads.append(payload)

        stub_manager = StubManager()
        monkeypatch.setattr(
            spu, "create_trace_manager", lambda *args, **kwargs: stub_manager
        )

        class StubLLM:
            @staticmethod
            async def astream(inputs, **kwargs):
                async def gen():
                    yield AIMessage(content="partial", usage_metadata=UsageMetadata())

                return gen()

        async def run():
            outs = []
            async for out in spu.stream_function_call(
                [{"role": "user", "content": "hi"}], None, StubLLM()
            ):
                outs.append(out)
            return outs

        asyncio.run(run())
        assert stub_manager.payloads  # on_llm_end 仍发出
        assert USAGE_METADATA not in stub_manager.payloads[0]
        assert FINISH_REASON not in stub_manager.payloads[0]


class TestBuildLlmEndPayload:
    """无既有时延/用量链路发射点共用的载荷构造器。

    覆盖 task_plan / task_understanding / PlanExecute StepExecute。
    """

    @staticmethod
    def test_full_usage_payload_shape():
        """完整 usage → content/latency/model_usage/usage_metadata/finish_reason 齐全。"""
        payload = build_llm_end_payload("done", _usage(), 1.25)
        assert payload["role"] == "assistant"
        assert payload["content"] == "done"
        assert payload[LATENCY] == {"total_latency": 1.25}
        assert payload[MODEL_USAGE] == {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }
        usage_dict = payload[USAGE_METADATA]
        assert usage_dict["input_tokens"] == 10
        assert usage_dict["first_token_time"] == pytest.approx(0.2)
        assert payload[FINISH_REASON] == "stop"

    @staticmethod
    def test_none_usage_keeps_latency_only():
        """usage 为 None → 保留 content/latency，缺数据键不注入。"""
        payload = build_llm_end_payload(None, None, 0.5)
        assert payload["content"] == ""
        assert payload[LATENCY] == {"total_latency": 0.5}
        assert MODEL_USAGE not in payload
        assert USAGE_METADATA not in payload
        assert FINISH_REASON not in payload

    @staticmethod
    def test_all_default_usage_skips_injection():
        """全默认 usage（模型错误/未上报）→ 不注入全零键，与既有契约一致。"""
        payload = build_llm_end_payload("x", UsageMetadata(), 0.5)
        assert MODEL_USAGE not in payload
        assert USAGE_METADATA not in payload
        # finish_reason 默认值 None → 不注入
        assert FINISH_REASON not in payload

    @staticmethod
    def test_null_placeholder_finish_reason_skipped():
        """finish_reason 为 "null" 占位 → 不注入（沿用 build_finish_reason 语义）。"""
        payload = build_llm_end_payload("x", _usage(finish_reason="null"), 0.5)
        assert FINISH_REASON not in payload

    @staticmethod
    def test_tpot_passthrough():
        """tpot_ms 可算时随 usage_metadata 透传（批式调用点不传，流式可补）。"""
        payload = build_llm_end_payload("x", _usage(), 0.5, tpot_ms=15.0)
        assert payload[USAGE_METADATA]["inter_token_latency_ms"] == 15.0

    @staticmethod
    def test_list_content_normalized_to_empty():
        """content 为 list（AIMessage 契约允许）→ 载荷按空串兜底。

        `content or ""` 只兜空值，非空 list 会原样进载荷造成 OTel 载荷
        畸形；所有调用点（含 task_plan 直传 result.content）统一在此兜底。
        """
        payload = build_llm_end_payload(["非字符串内容"], _usage(), 0.5)
        assert payload["content"] == ""
        assert payload[USAGE_METADATA]["input_tokens"] == 10

    @staticmethod
    def test_malformed_usage_degrades_to_base_payload():
        """usage_metadata 类型异常 → 降级为基础载荷（content/latency），不抛。"""
        payload = build_llm_end_payload("x", {"input_tokens": 1}, 0.5)  # type: ignore[arg-type]
        assert payload["role"] == "assistant"
        assert payload["content"] == "x"
        assert payload[LATENCY] == {"total_latency": 0.5}
        assert USAGE_METADATA not in payload
        assert MODEL_USAGE not in payload
