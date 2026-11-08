# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SendMessageEnvelope.user_id 携带与回绑契约。

消息经队列与 asyncio.create_task 投递，处理任务继承消费循环上下文（用户
事实为空）——用户 id 由 envelope 携带过界、在处理入口回绑 ContextVar，
下游 current_user_id 读取方（ModelWrapper 兜底 / build_traced_model 注入）
恢复可见。
"""

import contextvars

import pytest

import agent_runtime.common.trace_compat as trace_compat
from agent_runtime.common.trace_compat import bind_current_user_id, current_user_id
from jiuwen.multi_agent.core.common.message_type import SendMessageEnvelope
from jiuwen.multi_agent.core.runner.standalone_runner import (
    _bind_current_user_id,
    _current_user_id_or_none,
)


@pytest.fixture(autouse=True)
def _fresh_user_contextvar(monkeypatch):
    """每例独立 ContextVar，互不串扰且不污染全局。"""
    monkeypatch.setattr(
        trace_compat, "_CURRENT_USER_ID", contextvars.ContextVar("t_user", default=None)
    )
    yield


def _make_envelope(user_id=None):
    return SendMessageEnvelope(
        message={"text": "hi"},
        sender="agent-a",
        recipient="agent-b",
        user_id=user_id,
    )


def test_envelope_serialization_roundtrip():
    envelope = _make_envelope("u-42")

    data = envelope.to_dict()
    assert data["user_id"] == "u-42"

    restored = SendMessageEnvelope.from_dict(data)
    assert restored.user_id == "u-42"


def test_envelope_user_id_defaults_none_and_backfill():
    """未携带（默认 None）不影响序列化；回绑后 ContextVar 可见。"""
    assert current_user_id() is None

    envelope = _make_envelope()
    assert envelope.to_dict()["user_id"] is None

    bind_current_user_id("u-9")
    assert current_user_id() == "u-9"
    # 空值回绑不清除既有值
    bind_current_user_id(None)
    assert current_user_id() == "u-9"


def test_runner_helpers_bridge_the_boundary():
    """runner 侧助手：读取当前用户 / 把 envelope 值回绑任务上下文。"""
    assert _current_user_id_or_none() is None

    _bind_current_user_id("u-bound")
    assert _current_user_id_or_none() == "u-bound"
    assert current_user_id() == "u-bound"
