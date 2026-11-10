# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""RestfulApiToolNew.ainvoke 的 trace 错误形态契约测试。

HTTP 插件包装器的 on_plugin_start/on_plugin_error 发射机制为基线已有
（成功态 on_plugin_end 在 _async_send_request 内部发射）。本测试钉住
错误路径可见性——参数构造/校验失败必须发 on_plugin_error 而非静默，
多智能体调单智能体实测的"工具连续失败 21 次全程无 tool span"场景，
错误 span 正依赖这一路。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from jiuwen.extension.wrapper.restful_api_new import RestfulApiToolNew


def _make_recording_handler():
    """构造记录 on_plugin_* 事件的 trace handler 替身。"""
    handler = MagicMock()
    handler.on_plugin_start = AsyncMock()
    handler.on_plugin_end = AsyncMock()
    handler.on_plugin_error = AsyncMock()
    return handler


def _make_wrapper(monkeypatch, create_side_effect):
    """绕过构造器依赖（IR/卡片链），仅装配 ainvoke 触碰的成员。

    参数构造失败走 except → on_plugin_error + 错误响应包装，
    不触达真实 HTTP 发送路径。
    """
    wrapper = RestfulApiToolNew.__new__(RestfulApiToolNew)
    monkeypatch.setattr(wrapper, "_merge_input_parameters", lambda inputs: inputs)
    # _request_params_creator 仅 __init__ 装配，__new__ 实例上直接注入
    wrapper._request_params_creator = SimpleNamespace(
        create=MagicMock(side_effect=create_side_effect)
    )
    monkeypatch.setattr(
        wrapper,
        "_create_error_invoke_response",
        lambda error: {"errCode": -1, "errMessage": str(error)},
    )
    return wrapper


def test_ainvoke_param_failure_emits_error_event(monkeypatch):
    """参数构造失败：on_plugin_start/on_plugin_error 成对，错误响应包装。"""
    handler = _make_recording_handler()
    wrapper = _make_wrapper(monkeypatch, ValueError("bad params"))

    import asyncio

    result = asyncio.run(wrapper.ainvoke({"q": 1}, trace_handlers=[handler]))

    assert result["errCode"] == -1
    handler.on_plugin_start.assert_awaited_once()
    handler.on_plugin_error.assert_awaited_once()
    assert isinstance(handler.on_plugin_error.await_args.args[0], ValueError)
    handler.on_plugin_end.assert_not_awaited()


def test_ainvoke_param_failure_without_handlers_wraps_silently(monkeypatch):
    """不传 trace_handlers：事件空转，错误响应包装行为不变。"""
    wrapper = _make_wrapper(monkeypatch, ValueError("bad params"))

    import asyncio

    result = asyncio.run(wrapper.ainvoke({"q": 1}))

    assert result["errCode"] == -1
