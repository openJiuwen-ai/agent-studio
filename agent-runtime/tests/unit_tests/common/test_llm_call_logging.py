# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for agent_runtime.common.llm_call_logging — LLM 请求/响应日志（callback framework 版）"""

import json
import logging
import pytest

from openjiuwen.core.runner.callback.events import LLMCallEvents
from openjiuwen.core.runner.callback.utils import get_callback_framework


@pytest.fixture(autouse=True)
def _reset_registration(monkeypatch):
    """每个测试前重置注册状态，开启开关并设 DEBUG 级别，并清理已注册的回调"""
    from agent_runtime.common.llm_call_logging import reset_registration_state
    reset_registration_state()
    # 默认开启 model-call 日志开关并设 DEBUG 级别，让详情注册生效
    monkeypatch.setenv("MODEL_CALL_LOGGING_ENABLED", "true")
    monkeypatch.setenv("WORKFLOW_LOG_LEVEL", "DEBUG")
    yield
    # 清理：移除测试中注册的回调
    fw = get_callback_framework()
    for event in (LLMCallEvents.LLM_INPUT, LLMCallEvents.LLM_OUTPUT, LLMCallEvents.LLM_CALL_ERROR):
        fw.callbacks.pop(event, None)
    reset_registration_state()


def test_register_adds_callbacks():
    """验证注册后 callback framework 中包含对应事件的回调"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    assert LLMCallEvents.LLM_INPUT in fw.callbacks
    assert len(fw.callbacks[LLMCallEvents.LLM_INPUT]) >= 1

    assert LLMCallEvents.LLM_OUTPUT in fw.callbacks
    assert len(fw.callbacks[LLMCallEvents.LLM_OUTPUT]) >= 1

    assert LLMCallEvents.LLM_CALL_ERROR in fw.callbacks
    assert len(fw.callbacks[LLMCallEvents.LLM_CALL_ERROR]) >= 1


def test_register_at_info_level(monkeypatch):
    """验证开关开启 + WORKFLOW_LOG_LEVEL=INFO 时注册详情回调"""
    from agent_runtime.common.llm_call_logging import (
        register_llm_call_logging_callbacks, reset_registration_state,
    )

    monkeypatch.setenv("MODEL_CALL_LOGGING_ENABLED", "true")
    monkeypatch.setenv("WORKFLOW_LOG_LEVEL", "INFO")
    reset_registration_state()

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()
    assert LLMCallEvents.LLM_INPUT in fw.callbacks
    assert LLMCallEvents.LLM_OUTPUT in fw.callbacks
    assert LLMCallEvents.LLM_CALL_ERROR in fw.callbacks


def test_register_skipped_when_warning_level(monkeypatch):
    """验证开关开启 + WARNING 时：input/output 不注册（零开销），error 仍注册"""
    from agent_runtime.common.llm_call_logging import (
        register_llm_call_logging_callbacks, reset_registration_state,
    )

    monkeypatch.setenv("MODEL_CALL_LOGGING_ENABLED", "true")
    monkeypatch.setenv("WORKFLOW_LOG_LEVEL", "WARNING")
    reset_registration_state()

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()
    # input/output 受门控，WARNING 下不注册
    assert LLMCallEvents.LLM_INPUT not in fw.callbacks
    assert LLMCallEvents.LLM_OUTPUT not in fw.callbacks
    # error 无条件注册，错误始终可见
    assert LLMCallEvents.LLM_CALL_ERROR in fw.callbacks
    # 幂等：再次调用不应重复注册（注册标志已置位，跳过后续检查）
    error_count = len(fw.callbacks[LLMCallEvents.LLM_CALL_ERROR])
    register_llm_call_logging_callbacks()
    assert len(fw.callbacks[LLMCallEvents.LLM_CALL_ERROR]) == error_count


def test_register_skipped_when_disabled(monkeypatch):
    """验证开关默认关闭（MODEL_CALL_LOGGING_ENABLED 未设）时：详情不注册，error 仍注册"""
    from agent_runtime.common.llm_call_logging import (
        register_llm_call_logging_callbacks, reset_registration_state,
    )

    # 不设 MODEL_CALL_LOGGING_ENABLED，取默认 false；级别设 DEBUG 也无济于事
    monkeypatch.delenv("MODEL_CALL_LOGGING_ENABLED", raising=False)
    monkeypatch.setenv("WORKFLOW_LOG_LEVEL", "DEBUG")
    reset_registration_state()

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()
    # 开关关闭，详情回调不注册（与级别无关）
    assert LLMCallEvents.LLM_INPUT not in fw.callbacks
    assert LLMCallEvents.LLM_OUTPUT not in fw.callbacks
    # error 无条件注册，不受开关影响
    assert LLMCallEvents.LLM_CALL_ERROR in fw.callbacks


def test_register_idempotent():
    """验证重复调用不会重复注册回调"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()
    input_count = len(get_callback_framework().callbacks.get(LLMCallEvents.LLM_INPUT, []))

    register_llm_call_logging_callbacks()
    input_count_after = len(get_callback_framework().callbacks.get(LLMCallEvents.LLM_INPUT, []))

    assert input_count == input_count_after


@pytest.mark.asyncio
async def test_input_callback_logs_request(caplog):
    """验证 LLM_INPUT 回调正确打印请求体"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_INPUT,
            model_name="test-model",
            model_provider="openai",
            messages=[{"role": "user", "content": "你好"}],
            tools=None,
            temperature=0.7,
            top_p=0.9,
            max_tokens=4096,
            is_stream=False,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    request_logs = [r for r in info_records if "model call request data" in r.message]
    assert len(request_logs) >= 1

    log_msg = request_logs[0].message
    assert "test-model" in log_msg
    assert "openai" in log_msg
    assert '"stream": false' in log_msg
    assert '"temperature": 0.7' in log_msg
    assert "你好" in log_msg


@pytest.mark.asyncio
async def test_input_callback_stream_flag(caplog):
    """验证 LLM_INPUT 回调正确标记 is_stream=True"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_INPUT,
            model_name="stream-model",
            model_provider="siliconflow",
            messages=[{"role": "user", "content": "test"}],
            is_stream=True,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    request_logs = [r for r in info_records if "model call request data" in r.message]
    assert len(request_logs) >= 1
    assert '"stream": true' in request_logs[0].message
    assert "siliconflow" in request_logs[0].message


@pytest.mark.asyncio
async def test_output_callback_logs_response(caplog):
    """验证 LLM_OUTPUT 回调正确打印响应内容"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="test-model",
            model_provider="openai",
            response="好的，已收到您的指令。",
            usage=None,
            tool_calls=None,
            is_stream=False,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    response_logs = [r for r in info_records if "model call response data" in r.message]
    assert len(response_logs) >= 1
    assert "好的，已收到您的指令。" in response_logs[0].message


@pytest.mark.asyncio
async def test_output_callback_logs_usage_and_cost(caplog):
    """验证 LLM_OUTPUT 回调正确打印 token 用量和费用"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks
    from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    usage = UsageMetadata(
        model_name="test-model",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cache_tokens=30,
        input_cost=0.001,
        output_cost=0.002,
        total_cost=0.003,
    )

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="test-model",
            response="test",
            usage=usage,
            tool_calls=None,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    usage_logs = [r for r in info_records if "model call token usage" in r.message]
    latency_logs = [r for r in info_records if "model call latency" in r.message]

    # token usage + cost
    assert len(usage_logs) >= 1
    usage_msg = usage_logs[0].message
    assert "input_tokens" in usage_msg
    assert "output_tokens" in usage_msg
    assert "total_tokens" in usage_msg
    assert "cache_tokens" in usage_msg
    assert "input_cost" in usage_msg
    assert "output_cost" in usage_msg
    assert "total_cost" in usage_msg

    # latency dict 中包含 model_name
    assert len(latency_logs) >= 1
    latency_msg = latency_logs[0].message
    assert "model_name" in latency_msg


@pytest.mark.asyncio
async def test_output_callback_logs_latency(caplog):
    """验证 LLM_OUTPUT 回调正确打印延迟信息"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks
    from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    usage = UsageMetadata(
        model_name="gpt-4o",
        task_id="req-abc123",
        first_token_time="0.15s",
        total_latency=1.23,
        request_start_time="2026-06-30T12:00:00",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="gpt-4o",
            model_provider="openai",
            response="test",
            usage=usage,
            tool_calls=None,
            is_stream=True,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    latency_logs = [r for r in info_records if "model call latency" in r.message]
    assert len(latency_logs) >= 1
    latency_msg = latency_logs[0].message
    assert "first_token_time" in latency_msg
    assert "total_latency" in latency_msg
    assert "request_start_time" in latency_msg
    assert "model_name" in latency_msg
    assert "gpt-4o" in latency_msg
    assert "model_provider" in latency_msg
    assert "openai" in latency_msg
    assert "task_id" in latency_msg
    assert "req-abc123" in latency_msg
    assert "is_stream" in latency_msg


@pytest.mark.asyncio
async def test_output_callback_logs_tool_calls(caplog):
    """验证 LLM_OUTPUT 回调正确打印 tool_calls"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks
    from openjiuwen.core.foundation.llm.schema.message import ToolCall

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    tool_calls = [
        ToolCall(id="call_1", type="function", name="get_weather", arguments='{"city": "北京"}'),
    ]

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="test-model",
            response=None,
            usage=None,
            tool_calls=tool_calls,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    tc_logs = [r for r in info_records if "model call tool_calls" in r.message]
    assert len(tc_logs) >= 1
    tc_msg = tc_logs[0].message
    assert "get_weather" in tc_msg
    assert "北京" in tc_msg


@pytest.mark.asyncio
async def test_output_callback_logs_streaming_result(caplog):
    """验证 LLM_OUTPUT 回调正确处理流式调用的 result 参数（SiliconFlow/InferenceAffinity）"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="siliconflow-model",
            model_provider="siliconflow",
            result="流式响应内容",
            is_stream=True,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    response_logs = [r for r in info_records if "model call response data" in r.message]
    assert len(response_logs) >= 1
    assert "流式响应内容" in response_logs[0].message


@pytest.mark.asyncio
async def test_output_callback_prefers_response_over_result(caplog):
    """验证同时传入 response 和 result 时，优先使用 response（非流式语义）"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="test-model",
            response="非流式响应",
            result="流式响应",
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    response_logs = [r for r in info_records if "model call response data" in r.message]
    assert len(response_logs) >= 1
    # response 优先
    assert "非流式响应" in response_logs[0].message


@pytest.mark.asyncio
async def test_error_callback_logs_error(caplog):
    """验证 LLM_CALL_ERROR 回调正确打印错误"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    test_error = RuntimeError("connection timeout")

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_CALL_ERROR,
            model_name="test-model",
            model_provider="openai",
            error=test_error,
            is_stream=True,
        )

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    error_logs = [r for r in error_records if "model call error" in r.message]
    assert len(error_logs) >= 1
    error_msg = error_logs[0].message
    assert "test-model" in error_msg
    assert "openai" in error_msg
    assert "connection timeout" in error_msg


@pytest.mark.asyncio
async def test_output_callback_empty_response(caplog):
    """验证空响应时仍打印空行"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="test-model",
            response=None,
            usage=None,
            tool_calls=None,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    response_logs = [r for r in info_records if "model call response data" in r.message]
    assert len(response_logs) >= 1
    # 空响应打印 "model call response data: "
    assert response_logs[0].message.endswith("model call response data: ")


@pytest.mark.asyncio
async def test_usage_zero_cost_not_logged(caplog):
    """验证费用为 0 时不打印 cost 字段（避免无意义的 0 值）"""
    from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks
    from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

    register_llm_call_logging_callbacks()

    fw = get_callback_framework()

    usage = UsageMetadata(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        # input_cost/output_cost/total_cost 默认为 0.0，不应出现在日志中
    )

    with caplog.at_level(logging.DEBUG, logger="workflow"):
        await fw.trigger(
            LLMCallEvents.LLM_OUTPUT,
            model_name="test-model",
            response="test",
            usage=usage,
            tool_calls=None,
        )

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    usage_logs = [r for r in info_records if "model call token usage" in r.message]
    assert len(usage_logs) >= 1
    usage_msg = usage_logs[0].message
    # 零值费用不应出现
    assert "input_cost" not in usage_msg
    assert "output_cost" not in usage_msg
    assert "total_cost" not in usage_msg
    # token 计数应出现
    assert "input_tokens" in usage_msg


def test_extract_usage_dict_extracts_all_nonzero_fields():
    """验证 _extract_usage_dict 提取所有非零 token + 费用字段"""
    from agent_runtime.common.llm_call_logging import _extract_usage_dict
    from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

    usage = UsageMetadata(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cache_tokens=30,
        input_cost=0.001,
        output_cost=0.002,
        total_cost=0.003,
    )

    result = _extract_usage_dict(usage)
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50
    assert result["total_tokens"] == 150
    assert result["cache_tokens"] == 30
    assert result["input_cost"] == 0.001
    assert result["output_cost"] == 0.002
    assert result["total_cost"] == 0.003


def test_extract_latency_dict_extracts_all_nonzero_fields():
    """验证 _extract_latency_dict 提取所有非零延迟 + 元信息字段"""
    from agent_runtime.common.llm_call_logging import _extract_latency_dict
    from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

    usage = UsageMetadata(
        model_name="gpt-4o",
        task_id="req-123",
        first_token_time="0.15s",
        total_latency=1.23,
        request_start_time="2026-06-30T12:00:00",
    )

    result = _extract_latency_dict(usage, model_name="gpt-4o",
                                   model_provider="openai", is_stream=True)
    assert result["first_token_time"] == "0.15s"
    assert result["total_latency"] == 1.23
    assert result["request_start_time"] == "2026-06-30T12:00:00"
    assert result["model_name"] == "gpt-4o"
    assert result["task_id"] == "req-123"
    assert result["model_provider"] == "openai"
    assert result["is_stream"] is True


def test_extract_latency_dict_skips_empty_fields():
    """验证 _extract_latency_dict 跳过空字符串和零值"""
    from agent_runtime.common.llm_call_logging import _extract_latency_dict
    from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

    usage = UsageMetadata(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        # model_name, task_id, first_token_time 等为默认空值/零值
    )

    result = _extract_latency_dict(usage)
    # 空值字段不应出现
    assert "first_token_time" not in result
    assert "total_latency" not in result
    assert "request_start_time" not in result
    assert "model_name" not in result
    assert "task_id" not in result
    # 未传 model_provider / is_stream 也不应出现
    assert "model_provider" not in result
    assert "is_stream" not in result
