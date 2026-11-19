# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""IR 策略模型凭证请求级注入测试（issue #1705 / P0-2）。

背景：组件实例跨执行复用（静态图复用），Model 懒初始化后跨请求共享。
``IRModelConfigProvider`` 若在建 Model 时把首个请求的 ``X-Auth-Token`` 烘焙
进 ``ModelClientConfig.custom_headers``，后续所有请求都会带首个请求的凭证。
本文件钉住：IR provider 只放静态头（X-Auth-Id），token 由请求级代理在每次
invoke/stream 时从 ``_request_ctx`` 取当次值注入。
"""
from types import SimpleNamespace

import pytest

from agent_runtime.context.request_context import RequestContext, _request_ctx


class _RecordingModel:
    """最小 Model 桩：只记录每次调用收到的 kwargs。"""

    def __init__(self):
        self.calls = []

    async def invoke(self, *args, **kwargs):
        self.calls.append(kwargs)
        return "ok"

    async def stream(self, *args, **kwargs):
        self.calls.append(kwargs)
        yield "chunk"


def _set_token(token: str):
    """绑定带指定 token（或空 token）的请求上下文，返回 reset token。"""
    headers = {"X-Auth-Token": token} if token else {}
    return _request_ctx.set(RequestContext(headers=headers))


def _auth_headers(kwargs: dict) -> dict:
    return kwargs.get("custom_headers") or {}


class TestRequestScopedAuthModel:
    @pytest.mark.asyncio
    async def test_each_invoke_uses_current_request_token(self):
        """同一 Model 连续两次调用：各自带当次请求的 X-Auth-Token。"""
        from agent_runtime.common.request_scoped_model import bind_request_scoped_auth

        model = _RecordingModel()
        wrapped = bind_request_scoped_auth(
            model, SimpleNamespace(request_scoped_auth=True)
        )

        token = _set_token("tok-a")
        try:
            await wrapped.invoke(messages=[])
        finally:
            _request_ctx.reset(token)

        token = _set_token("tok-b")
        try:
            await wrapped.invoke(messages=[])
        finally:
            _request_ctx.reset(token)

        assert _auth_headers(model.calls[0]) == {"X-Auth-Token": "tok-a"}
        assert _auth_headers(model.calls[1]) == {"X-Auth-Token": "tok-b"}

    @pytest.mark.asyncio
    async def test_first_request_without_token_then_with_token(self):
        """反向判别：首请求无 token 不注入，次请求有 token 必须注入。"""
        from agent_runtime.common.request_scoped_model import bind_request_scoped_auth

        model = _RecordingModel()
        wrapped = bind_request_scoped_auth(
            model, SimpleNamespace(request_scoped_auth=True)
        )

        token = _set_token("")
        try:
            await wrapped.invoke(messages=[])
        finally:
            _request_ctx.reset(token)

        token = _set_token("tok-second")
        try:
            await wrapped.invoke(messages=[])
        finally:
            _request_ctx.reset(token)

        assert _auth_headers(model.calls[0]) == {}
        assert _auth_headers(model.calls[1]) == {"X-Auth-Token": "tok-second"}

    @pytest.mark.asyncio
    async def test_stream_uses_current_request_token(self):
        """流式调用同样按当次请求注入 token。"""
        from agent_runtime.common.request_scoped_model import bind_request_scoped_auth

        model = _RecordingModel()
        wrapped = bind_request_scoped_auth(
            model, SimpleNamespace(request_scoped_auth=True)
        )

        token = _set_token("tok-stream")
        try:
            chunks = [chunk async for chunk in wrapped.stream(messages=[])]
        finally:
            _request_ctx.reset(token)

        assert chunks == ["chunk"]
        assert _auth_headers(model.calls[0]) == {"X-Auth-Token": "tok-stream"}

    @pytest.mark.asyncio
    async def test_caller_headers_merged_without_mutation(self):
        """调用方传入的静态头保留，请求 token 覆盖同名头，入参 dict 不被改写。"""
        from agent_runtime.common.request_scoped_model import bind_request_scoped_auth

        model = _RecordingModel()
        wrapped = bind_request_scoped_auth(
            model, SimpleNamespace(request_scoped_auth=True)
        )
        caller_headers = {"X-Auth-Id": "auth-1", "X-Auth-Token": "stale"}

        token = _set_token("tok-fresh")
        try:
            await wrapped.invoke(messages=[], custom_headers=caller_headers)
        finally:
            _request_ctx.reset(token)

        assert _auth_headers(model.calls[0]) == {
            "X-Auth-Id": "auth-1",
            "X-Auth-Token": "tok-fresh",
        }
        assert caller_headers == {"X-Auth-Id": "auth-1", "X-Auth-Token": "stale"}

    @staticmethod
    def test_non_request_scoped_config_is_not_wrapped():
        """非 IR 策略（无标记）的模型原样返回，不改变既有行为。"""
        from agent_runtime.common.request_scoped_model import bind_request_scoped_auth

        model = _RecordingModel()
        assert bind_request_scoped_auth(model, SimpleNamespace()) is model


class TestIRModelConfigProviderAuthHeaders:
    @staticmethod
    def _ir_node() -> dict:
        return {
            "configs": {
                "modelConfig": {
                    "modelName": "model-1",
                    "extension": {"authId": "auth-1"},
                }
            }
        }

    @pytest.mark.asyncio
    async def test_provider_does_not_bake_request_token(self):
        """provider 只放静态头；请求 token 不落在共享 Model 配置里。"""
        from unittest.mock import MagicMock, patch

        from agent_runtime.common.model_providers import IRModelConfigProvider

        mock_settings = MagicMock()
        mock_settings.llm.api_key = "sk-placeholder"
        mock_settings.llm.api_base = "https://api.openai.com/v1"
        mock_settings.llm.model_name = "model-1"
        mock_settings.llm.temperature = 0.5
        mock_settings.llm.top_p = 0.5
        mock_settings.llm.timeout = 900.0
        mock_settings.llm.ssl_verify = False

        token = _set_token("tok-request")
        try:
            with patch("agent_runtime.common.model_providers.settings", mock_settings):
                llm_config = await IRModelConfigProvider().get_llm_config(
                    self._ir_node()
                )
        finally:
            _request_ctx.reset(token)

        client_config = llm_config.model_client_config
        headers = client_config.custom_headers or {}
        assert headers.get("X-Auth-Id") == "auth-1"
        assert not any(key.lower() == "x-auth-token" for key in headers)
        assert client_config.request_scoped_auth is True
