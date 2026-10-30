# -*- coding: UTF-8 -*-
"""LLM 请求参数 / 消息数 OTel 扁平键单测（issue #1583 第 4 节）。

覆盖：_build_request_params 的模型对象参数提取（rail 同构：None 不产出、
stop 归一 stop_sequences）、create_trace_manager 的扁平键产出与嵌套
instance_attributes 保持原样、经双写桥转发后 handler 可读的端到端形态。
"""

import pytest

from jiuwen.insight.manager import TraceManager
from jiuwen.planner.common.stream_post_utils import (
    _build_request_params,
    create_trace_manager,
)


class _FakeTracer:
    """记录双写桥转发事件的最小替身。"""

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


class _FakeLLM:
    """按 create_trace_manager 的读取面提供属性（model_name/temperature/top_p…）。"""

    def __init__(self, **attrs):
        self.model_name = attrs.get("model_name", "qwen-max")
        if "temperature" in attrs:
            self.temperature = attrs["temperature"]
        if "top_p" in attrs:
            self.top_p = attrs["top_p"]
        if "max_tokens" in attrs:
            self.max_tokens = attrs["max_tokens"]
        if "stop" in attrs:
            self.stop = attrs["stop"]


class TestBuildRequestParams:
    @staticmethod
    def test_present_attrs_projected():
        llm = _FakeLLM(temperature=0.7, top_p=0.9, max_tokens=2048)
        assert _build_request_params(llm) == {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2048,
        }

    @staticmethod
    def test_none_and_missing_attrs_omitted():
        """未携带 / None 的参数不产出（handler 缺键自动跳过，不落默认值）。"""
        assert _build_request_params(_FakeLLM()) == {}
        assert _build_request_params(_FakeLLM(temperature=None)) == {}

    @staticmethod
    def test_stop_string_normalized_to_sequence():
        result = _build_request_params(_FakeLLM(stop="END"))
        assert result == {"stop_sequences": ["END"]}

    @staticmethod
    def test_stop_list_preserved():
        result = _build_request_params(_FakeLLM(stop=["END", "STOP"]))
        assert result == {"stop_sequences": ["END", "STOP"]}


class TestCreateTraceManagerFlatKeys:
    @staticmethod
    def test_flat_keys_and_nested_attributes():
        manager = create_trace_manager(
            _FakeLLM(temperature=0.7, top_p=0.9),
            ["tool_a"],
            trace_handlers=None,
            messages=[{"role": "user", "content": "hi"}] * 3,
        )
        info = manager.instance_info
        # 扁平键：core handler 的 on_llm_start 读取面
        assert info["request_params"] == {"temperature": 0.7, "top_p": 0.9}
        assert info["message_count"] == 3
        # 嵌套 instance_attributes 保持原样（insights 侧读取面不受影响）
        attrs = info["instance_attributes"]
        assert attrs["model"] == "qwen-max"
        assert attrs["temperature"] == 0.7
        assert attrs["top_p"] == 0.9
        assert attrs["functions"] == ["tool_a"]

    @staticmethod
    def test_messages_none_omits_count():
        manager = create_trace_manager(_FakeLLM(), [], trace_handlers=None)
        assert "message_count" not in manager.instance_info

    @staticmethod
    def test_no_params_omits_request_params_key():
        manager = create_trace_manager(
            _FakeLLM(), [], trace_handlers=None, messages=[{"role": "user", "content": "x"}]
        )
        assert "request_params" not in manager.instance_info
        assert manager.instance_info["message_count"] == 1


class TestEndToEndForwardThroughDualWrite:
    @pytest.mark.asyncio
    async def test_derived_llm_manager_forwards_all_flat_keys(self):
        """端到端：根 manager 携带身份/会话事实，派生 LLM manager 的扁平
        request_params / message_count 与继承键在转发 instance_info 里齐全。
        """
        tracer = _FakeTracer()
        root = TraceManager(
            trace_handlers=[],
            openjiuwen_tracer=tracer,
            agent_identity={"agent_id": "w1", "agent_name": "天气预测"},
            conversation_facts={"conversation_id": "conv-8848", "user_id": "u-42"},
        )

        llm_manager = create_trace_manager(
            _FakeLLM(temperature=0.7, top_p=0.9),
            [],
            trace_handlers=root,
            messages=[{"role": "user", "content": "hi"}],
        )
        await llm_manager.on_llm_start([{"role": "user", "content": "hi"}])

        event_name, kwargs = tracer.events[-1]
        assert event_name == "on_llm_start"
        info = kwargs["instance_info"]
        assert info["request_params"] == {"temperature": 0.7, "top_p": 0.9}
        assert info["message_count"] == 1
        # 继承链：身份与会话事实同时到达 handler 读取面
        assert info["agent_name"] == "天气预测"
        assert info["conversation_id"] == "conv-8848"
        assert info["user_id"] == "u-42"
        assert info["class_name"] == "_FakeLLM"
