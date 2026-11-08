# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""build_traced_model 身份增补契约：user_id 兜底注入 + 模型显示名覆盖。

- user_id：identity 显式值优先，缺省回落 current_user_id()（runner 建会话
  播种）；即便调用方 identity 为 None，只要用户事实在也单独成身份透传；
- class_name：client_config.model_display_name（OBS provider 从元数据带出）
  覆盖装饰器探针结果——span 名与 gen_ai.request.model 显示真名而非
  modelServiceId（UUID）；缺名不覆盖；
- 全无事实时保持原行为（identity 空 → 两参调用）。
"""

import pytest

import agent_runtime.common.trace_compat as trace_compat
from agent_runtime.common.trace_compat import build_traced_model


class _StubSession:
    """满足 _should_decorate 契约的会话替身。"""

    class _Inner:
        def tracer(self):
            return self

        @staticmethod
        def span():
            return None

        @staticmethod
        def agent_handler_valid():
            return True

    def __init__(self):
        self._inner = self._Inner()


class _Cfg:
    def __init__(self, display=None):
        self.model_display_name = display


class _Model:
    def __init__(self, display=None):
        self.model_client_config = _Cfg(display)


class _WrappedModel:
    """组件 config 包装形态（探针第二跳同构）。"""

    def __init__(self):
        self.config = type("C", (), {"model_client_config": _Cfg("Wrapped-Name")})()
        self.model_client_config = None


@pytest.fixture
def decorate_calls(monkeypatch):
    calls = []

    def _decorate(model, session, identity=None):
        calls.append({"model": model, "session": session, "identity": identity})
        return model

    import openjiuwen.core.session.tracer as core_tracer

    monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate)
    monkeypatch.setattr(trace_compat, "callable_accepts_kwarg", lambda f, n: True)
    return calls


def test_user_id_injected_from_contextvar(decorate_calls, monkeypatch):
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: "u-42")

    build_traced_model(_Model("M-1"), session=_StubSession(), identity={"workflow_id": "w1"})

    assert decorate_calls[-1]["identity"]["user_id"] == "u-42"
    assert decorate_calls[-1]["identity"]["workflow_id"] == "w1"


def test_explicit_user_id_wins(decorate_calls, monkeypatch):
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: "u-ctx")

    build_traced_model(
        _Model(), session=_StubSession(), identity={"user_id": "u-explicit"}
    )

    assert decorate_calls[-1]["identity"]["user_id"] == "u-explicit"


def test_user_id_alone_forms_identity(decorate_calls, monkeypatch):
    """调用方 identity 为 None，用户事实在——仍以身份透传（不丢 user.id）。"""
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: "u-7")

    build_traced_model(_Model(), session=_StubSession())

    assert decorate_calls[-1]["identity"] == {"user_id": "u-7"}


def test_display_name_overrides_class_name(decorate_calls, monkeypatch):
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: None)

    build_traced_model(_Model("Qwen-Max"), session=_StubSession(), identity={"workflow_id": "w1"})

    assert decorate_calls[-1]["identity"]["class_name"] == "Qwen-Max"


def test_display_name_from_wrapped_config(decorate_calls, monkeypatch):
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: None)

    build_traced_model(_WrappedModel(), session=_StubSession(), identity={"workflow_id": "w1"})

    assert decorate_calls[-1]["identity"]["class_name"] == "Wrapped-Name"


def test_no_facts_keeps_two_arg_behavior(decorate_calls, monkeypatch):
    """无用户、无显示名且调用方无身份——identity 保持空，两参调用。"""
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: None)

    build_traced_model(_Model(), session=_StubSession())

    assert decorate_calls[-1]["identity"] is None


def test_explicit_identity_not_mutated(decorate_calls, monkeypatch):
    """增补在拷贝上进行，调用方传入的 identity 字典不被改写。"""
    monkeypatch.setattr(trace_compat, "current_user_id", lambda: "u-42")
    original = {"workflow_id": "w1"}

    build_traced_model(_Model("M"), session=_StubSession(), identity=original)

    assert original == {"workflow_id": "w1"}
    assert decorate_calls[-1]["identity"]["user_id"] == "u-42"
