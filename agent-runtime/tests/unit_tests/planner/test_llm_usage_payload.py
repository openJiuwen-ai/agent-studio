# -*- coding: UTF-8 -*-
"""LLM 用量/成本/时延 OTel 载荷单测（issue #1583 第 2、3 节）。

覆盖：usage_metadata 构造 helper 各分支、_format_yield_result 的
inter-token 掐表与 usage 暂存、stream_function_call 发射点载荷。
"""

import asyncio

from jiuwen.common.llm_service.messages import AIMessage, UsageMetadata
from jiuwen.planner.common import stream_post_utils as spu
from jiuwen.planner.common.stream_post_utils import (
    FINISH_REASON,
    USAGE_METADATA,
    _format_yield_result,
    build_finish_reason,
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
        # 秒值契约：gen_ai.response.time_to_first_chunk 按秒（200ms → 0.2）
        assert result["first_token_time"] == "0.2"
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
            async def astream(self, inputs, **kwargs):
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
        assert usage_dict["first_token_time"] == "0.2"
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

            async def on_llm_start(self, messages):
                pass

            async def on_llm_end(self, payload):
                self.payloads.append(payload)

        stub_manager = StubManager()
        monkeypatch.setattr(
            spu, "create_trace_manager", lambda *args, **kwargs: stub_manager
        )

        class StubLLM:
            async def astream(self, inputs, **kwargs):
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
