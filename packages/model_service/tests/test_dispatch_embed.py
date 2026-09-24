# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.dispatch.embed (mocked AsyncOpenAI)."""

import asyncio

import pytest

from model_service.dispatch import embed


class _FakeEmbeddings:
    def __init__(self, model, input_):
        self.model = model
        self.input = input_

    async def create(self, model, input):  # pylint: disable=redefined-builtin  # OpenAI SDK 关键字参数名
        self.model = model
        self.input = input
        return {"data": "fake-embeddings"}


class _FakeAsyncOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.embeddings = _FakeEmbeddings(None, None)
        self.closed = False

    async def close(self):
        self.closed = True


class _FakeRequest:
    def __init__(self, input_):
        self.input = input_


class _FakeModel:
    id = "m1"
    model_name = "embed-model"
    api_url = "http://x/v1"
    interface_protocol = "openai"
    api_url_env_placeholders = None


class _FakeAuth:
    auth_type = "API_KEY"
    auth_info = {"api_key": "sk-1"}


def _mk_conn():
    from model_service.dispatch import ResolvedConnection
    from model_service.resolver import InterfaceProtocol
    return ResolvedConnection(
        api_base="http://x/v1", api_key="sk-1", custom_headers=None,
        model_name="embed-model", interface_protocol=InterfaceProtocol.OPENAI,
        timeout=30.0, verify_ssl=False,
    )


class _FakeHttpxClient:
    @staticmethod
    async def aclose():
        return None


class TestEmbed:
    @staticmethod
    def test_embed_calls_create(monkeypatch):
        import model_service.dispatch as dispatch
        from openai import AsyncOpenAI

        fake = _FakeAsyncOpenAI()
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: _FakeHttpxClient())
        monkeypatch.setattr(AsyncOpenAI, "__new__", lambda cls, *a, **k: fake)

        async def _run():
            return await embed(_FakeModel(), _FakeAuth(), _FakeRequest(["a", "b"]))

        resp = asyncio.run(_run())
        assert resp == {"data": "fake-embeddings"}
        assert fake.embeddings.model == "embed-model"
        assert fake.embeddings.input == ["a", "b"]
        assert fake.closed is True
