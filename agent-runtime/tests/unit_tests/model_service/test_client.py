#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""StudioModelClient._invoke_one_model 的 CALL 级事件契约测试。

``_invoke_one_model`` 不委托 ``super().invoke()``（其方法体内的 LLM_INPUT / LLM_OUTPUT /
LLM_CALL_ERROR trigger 不会自动触发），故手动补回三个事件。本测试锁定：

- 非流成功：LLM_INPUT（含 frequency_penalty 等超参，#1198）→ LLM_OUTPUT，无 LLM_CALL_ERROR。
- 非流失败：LLM_INPUT → LLM_CALL_ERROR，无 LLM_OUTPUT。

流式路径需构造 chunk 形状 mock，留作集成验证；此处覆盖非流契约。
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openjiuwen.core.foundation.llm import ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner.callback.events import LLMCallEvents

from model_service.client import StudioModelClient, _is_verbatim_endpoint
from model_service.resolver import (
    InterfaceProtocol, ModelServiceBase, ModelServiceDetail, ProviderAuth,
)


def _detail():
    m = ModelServiceBase(
        id="m1", model_name="mm", api_url="http://x/v1/chat/completions",
        provider_id="p", interface_protocol=InterfaceProtocol.OPENAI,
        project_id="0", workspace_id="w", auth_id="a",
    )
    a = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k1"})
    return ModelServiceDetail(model=m, auth=a, available=True, is_free_model=False)


def _verbatim_detail():
    """非 OpenAI 非常规路径端点（mock）：api_url 不以 /chat/completions 结尾、非 /vN base。"""
    m = ModelServiceBase(
        id="m2", model_name="mock", api_url="http://mock/xxx/yyy",
        provider_id="p", interface_protocol=InterfaceProtocol.OPENAI,
        project_id="0", workspace_id="w", auth_id="a",
    )
    a = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k1"})
    return ModelServiceDetail(model=m, auth=a, available=True, is_free_model=False)


def _studio_client():
    mcc = ModelClientConfig(client_provider="studio", api_key="k", api_base="b",
                             verify_ssl=False, timeout=10, max_retries=0)
    mrc = ModelRequestConfig(model="mm", temperature=0.5, frequency_penalty=0.3)
    return StudioModelClient(model_config=mrc, model_client_config=mcc)


def _fake_response():
    """构造 _parse_response 能消费的 OpenAI 形状响应（SimpleNamespace）。"""
    return SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content="hi", tool_calls=None, reasoning_content=None),
            token_ids=None, logprobs=None,
        )],
        usage=None, prompt_token_ids=None,
    )


def _fake_openai(return_value=None, side_effect=None):
    fake = MagicMock()
    fake.chat.completions.create = AsyncMock(
        return_value=return_value, side_effect=side_effect)
    fake.close = AsyncMock()
    return fake


def _run(coro):
    return asyncio.run(coro)


@patch("model_service.client.trigger")
@patch("model_service.dispatch._settings_llm")
@patch("model_service.client.AsyncOpenAI")
def test_non_stream_success_emits_input_then_output_with_frequency_penalty(
        mock_async_openai, mock_settings_llm, mock_trigger):
    mock_settings_llm.return_value = SimpleNamespace(timeout=10, ssl_verify=False)
    mock_async_openai.return_value = _fake_openai(return_value=_fake_response())

    sc = _studio_client()
    msg = _run(sc._invoke_one_model(_detail(), stream=False, messages="hi", temperature=0.5))  # pylint: disable=protected-access

    assert msg.content == "hi"
    calls = mock_trigger.call_args_list
    events = [c.args[0] for c in calls]

    assert events[0] == LLMCallEvents.LLM_INPUT
    # #1198：frequency_penalty 等 extra 超参随 LLM_INPUT 传递
    assert calls[0].kwargs.get("frequency_penalty") == 0.3
    assert calls[0].kwargs.get("model_name") == "mm"
    assert calls[0].kwargs.get("is_stream") is False
    # LLM_INPUT 同时携带完整 pre-send params（供 wire-body 审计）
    params = calls[0].kwargs.get("params")
    assert params is not None
    assert params.get("frequency_penalty") == 0.3
    assert params.get("model") == "mm"

    assert events[1] == LLMCallEvents.LLM_OUTPUT
    assert calls[1].kwargs.get("response") == "hi"

    assert LLMCallEvents.LLM_CALL_ERROR not in events   # 成功路径不应有


@patch("model_service.client.trigger")
@patch("model_service.dispatch._settings_llm")
@patch("model_service.client.AsyncOpenAI")
def test_non_stream_failure_emits_call_error_not_output(
        mock_async_openai, mock_settings_llm, mock_trigger):
    mock_settings_llm.return_value = SimpleNamespace(timeout=10, ssl_verify=False)
    mock_async_openai.return_value = _fake_openai(side_effect=RuntimeError("boom"))

    sc = _studio_client()
    with pytest.raises(RuntimeError):
        _run(sc._invoke_one_model(_detail(), stream=False, messages="hi", temperature=0.5))  # pylint: disable=protected-access

    calls = mock_trigger.call_args_list
    events = [c.args[0] for c in calls]

    assert events[0] == LLMCallEvents.LLM_INPUT
    assert LLMCallEvents.LLM_CALL_ERROR in events
    assert LLMCallEvents.LLM_OUTPUT not in events   # 失败路径不应有 LLM_OUTPUT


# ----------------------------- verbatim 分支 -----------------------------


class _FakeResp:
    """最小 httpx.Response 形状，覆盖 verbatim 分支用到的字段。"""

    def __init__(self, status, payload=None, text=None):
        self.status_code = status
        self._payload = payload
        self.text = (text if text is not None
                     else (json.dumps(payload) if payload is not None else ""))
        self._lines = ()

    def json(self):
        return self._payload

    async def aread(self):
        return self.text.encode("utf-8")

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    def set_lines(self, lines):
        self._lines = lines


class _FakeHttpx:
    """最小 httpx.AsyncClient 形状（post / build_request / send / aclose）。"""

    def __init__(self, resp):
        self._resp = resp
        self.post = AsyncMock(return_value=resp)
        self.build_request = MagicMock(return_value=MagicMock())
        self.send = AsyncMock(return_value=resp)

    async def aclose(self):
        return None


def _openai_chat_payload(content="hi", usage=None):
    return {
        "choices": [{
            "message": {"content": content, "tool_calls": None,
                        "reasoning_content": None},
            "token_ids": None, "logprobs": None,
        }],
        "usage": usage,
        "prompt_token_ids": None,
    }


@pytest.mark.parametrize("url, expected", [
    ("http://x/v1/chat/completions", False),   # 完整 OpenAI 端点 → SDK
    ("http://x/v1/chat/completions/", False),
    ("http://x/v1", False),                     # 版本 base → SDK
    ("http://x", False),                        # 裸 host → SDK
    ("http://x/", False),
    ("http://mock/xxx/yyy", True),               # mock 非常规路径 → verbatim
    ("https://h/compatible-mode/v1/ask", True), # 非 /chat/completions 非常规路径
    ("", False),
])
def test_is_verbatim_endpoint(url, expected):
    assert _is_verbatim_endpoint(url) is expected


@patch("model_service.client.trigger")
@patch("model_service.dispatch._settings_llm")
@patch("model_service.dispatch.build_httpx_client")
def test_verbatim_non_stream_success_uses_httpx_post_to_raw_url(
        mock_build_httpx, mock_settings_llm, mock_trigger):
    """verbatim 端点：httpx.post 打到原样 api_url（不拼 /chat/completions），复用 _parse_response。"""
    mock_settings_llm.return_value = SimpleNamespace(timeout=10, ssl_verify=False)
    fake_resp = _FakeResp(200, payload=_openai_chat_payload("hi"))
    mock_build_httpx.return_value = _FakeHttpx(fake_resp)

    sc = _studio_client()
    msg = _run(sc._invoke_one_model(  # pylint: disable=protected-access
        _verbatim_detail(), stream=False, messages="hi", temperature=0.5))

    assert msg.content == "hi"
    fake = mock_build_httpx.return_value
    fake.post.assert_awaited_once()
    args, _ = fake.post.call_args
    posted_url = args[0]
    assert posted_url == "http://mock/xxx/yyy"          # verbatim，无 /chat/completions
    assert "/chat/completions" not in posted_url

    calls = mock_trigger.call_args_list
    events = [c.args[0] for c in calls]
    assert events[0] == LLMCallEvents.LLM_INPUT
    assert events[1] == LLMCallEvents.LLM_OUTPUT
    assert calls[1].kwargs.get("response") == "hi"
    assert LLMCallEvents.LLM_CALL_ERROR not in events


@patch("model_service.client.trigger")
@patch("model_service.dispatch._settings_llm")
@patch("model_service.dispatch.build_httpx_client")
def test_verbatim_non_stream_non2xx_raises_model_service_error(
        mock_build_httpx, mock_settings_llm, mock_trigger):
    """verbatim 端点上游非 2xx → MD_INVOKE_MODEL_SERVICE_FAIL（而非 NotFoundError）。"""
    mock_settings_llm.return_value = SimpleNamespace(timeout=10, ssl_verify=False)
    fake_resp = _FakeResp(404, text="not found")
    mock_build_httpx.return_value = _FakeHttpx(fake_resp)

    sc = _studio_client()
    from model_service import resolver
    with pytest.raises(resolver.ModelServiceError) as exc:
        _run(sc._invoke_one_model(  # pylint: disable=protected-access
            _verbatim_detail(), stream=False, messages="hi"))
    assert exc.value.code == "MD_INVOKE_MODEL_SERVICE_FAIL"

    calls = mock_trigger.call_args_list
    events = [c.args[0] for c in calls]
    assert events[0] == LLMCallEvents.LLM_INPUT
    assert LLMCallEvents.LLM_CALL_ERROR in events
    assert LLMCallEvents.LLM_OUTPUT not in events
