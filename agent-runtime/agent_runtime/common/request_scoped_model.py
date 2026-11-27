# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""IR 策略模型的请求级认证头注入代理（issue #1705 / P0-2）。

组件实例与懒初始化的 Model 跨执行复用（静态图复用），``X-Auth-Token`` 属
请求级凭证：建模期读取首个请求的 token 并烘焙进 ``ModelClientConfig`` 后，
后续请求会一直带首个请求的凭证（多用户串用、token 轮换后 401 无法自愈）。
``IRModelConfigProvider`` 只在配置里放静态头并打 ``request_scoped_auth``
标记；本模块的透明代理在每次 invoke/stream 时从请求上下文取当次 token 注入。
"""

import inspect
from typing import Any

from agent_runtime.context.request_context import _request_ctx

REQUEST_SCOPED_AUTH_FIELD = "request_scoped_auth"


def current_request_auth_headers() -> dict:
    """当次请求的认证头（X-Auth-Token）；无请求上下文或无 token 时为空。"""
    ctx = _request_ctx.get()
    headers = getattr(ctx, "headers", None) or {}
    token = headers.get("X-Auth-Token") or headers.get("x-auth-token") or ""
    return {"X-Auth-Token": token} if token else {}


class RequestScopedAuthModel:
    """透明 Model 代理：每次调用把当次请求的认证头并入 ``custom_headers``。

    只覆写 invoke/stream，其余属性经 ``__getattr__`` 原样透传；底层 core
    客户端在每次调用时 ``pop("custom_headers")`` 与配置级 base headers 合并，
    因此请求 token 可覆盖调用方传入的同名头，且不改写调用方的 dict。
    """

    def __init__(self, model: Any):
        self._model = model

    @staticmethod
    def _inject(kwargs: dict) -> None:
        headers = dict(kwargs.get("custom_headers") or {})
        headers.update(current_request_auth_headers())
        if headers:
            kwargs["custom_headers"] = headers

    async def invoke(self, *args, **kwargs):
        self._inject(kwargs)
        result = self._model.invoke(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def stream(self, *args, **kwargs):
        self._inject(kwargs)
        result = self._model.stream(*args, **kwargs)
        # 与 invoke 同一口径：内层可能是普通 async def（返回 async iterator），
        # 此时需先 await，否则落入同步迭代分支抛 TypeError 并泄漏未 await 警告。
        if inspect.isawaitable(result):
            result = await result
        if hasattr(result, "__aiter__"):
            async for chunk in result:
                yield chunk
        else:
            for chunk in result:
                yield chunk

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)


def bind_request_scoped_auth(model: Any, model_client_config: Any) -> Any:
    """按 ``ModelClientConfig`` 的标记决定是否套请求级认证代理。

    非 IR 策略（无标记）原样返回，不改变既有 OBS/env 行为。
    """
    if not getattr(model_client_config, REQUEST_SCOPED_AUTH_FIELD, False):
        return model
    return RequestScopedAuthModel(model)
