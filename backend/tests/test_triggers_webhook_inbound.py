#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Webhook inbound 接口必须同时接受 GET 与 POST。

外部系统（GitHub、CI 等）投递 webhook 走 POST；GET 保留给手工/浏览器触发。
未知名 token 仍返回 200，避免 token 枚举。
"""

from __future__ import annotations

import os
from pathlib import Path

# 先于 openjiuwen_studio 导入设置 Settings 必需环境变量（与 test_vlm_model_config.py 一致）
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("SQLITE_DB_PATH", str(Path(__file__).resolve().parent / ".tmp-db"))
os.environ.setdefault("OPS_SQLITE_DB", "ops-test.db")
os.environ.setdefault("AGENT_SQLITE_DB", "agent-test.db")

from fastapi import FastAPI
from fastapi.testclient import TestClient

import openjiuwen_studio.routers.triggers as triggers_router_module
from openjiuwen_studio.routers.triggers import triggers_inbound_router


class _FakeTrigger:
    trigger_id = "trg-1"
    is_active = True
    config = {}  # 无 webhook_secret → 跳过签名校验


class _FakeQuery:
    def __init__(self, trigger):
        self._trigger = trigger

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._trigger


class _FakeDB:
    def __init__(self, trigger):
        self._trigger = trigger

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._trigger)

    def close(self):
        pass


def _make_client(monkeypatch, trigger) -> TestClient:
    monkeypatch.setattr(triggers_router_module, "SessionLocal", lambda: _FakeDB(trigger))
    # handler 内部延迟 import；打桩避免真实执行触发任务
    monkeypatch.setattr(
        "openjiuwen_studio.core.scheduler.runner.execute_trigger_job",
        lambda *args, **kwargs: None,
    )
    app = FastAPI()
    app.include_router(triggers_inbound_router)
    return TestClient(app)


def test_webhook_inbound_accepts_get(monkeypatch):
    client = _make_client(monkeypatch, _FakeTrigger())
    resp = client.get("/inbound/token-1")
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}


def test_webhook_inbound_accepts_post(monkeypatch):
    client = _make_client(monkeypatch, _FakeTrigger())
    resp = client.post("/inbound/token-1", json={"action": "opened"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}


def test_webhook_inbound_unknown_token_returns_200(monkeypatch):
    client = _make_client(monkeypatch, None)
    for method in ("get", "post"):
        resp = getattr(client, method)("/inbound/unknown-token")
        assert resp.status_code == 200
        assert resp.json() == {"status": "accepted"}
