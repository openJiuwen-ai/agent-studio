# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.dispatch.rerank response post-processing.

rerank 的响应后处理逻辑（results 排序、top_n 截断）与上游 HTTP 调用解耦测试，
通过 monkeypatch build_httpx_client 与 get_chat_connection 隔离网络。
"""

import asyncio

import pytest

from model_service.dispatch import rerank


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp
        self.posted = None

    async def post(self, url, json=None, headers=None, timeout=None):
        self.posted = (url, json, headers, timeout)
        return self._resp

    async def aclose(self):
        return None


class _FakeRequest:
    def __init__(self, query="q", docs=None, top_n=None):
        self.query = query
        self.docs = docs or []
        self.top_n = top_n


class _FakeModel:
    id = "m1"
    model_name = "model"
    api_url = "http://x/rerank"
    interface_protocol = "openai"
    api_url_env_placeholders = None


class _FakeAuth:
    auth_type = "API_KEY"
    auth_info = {"api_key": "sk-1"}


def _mk_conn():
    from model_service.dispatch import ResolvedConnection
    from model_service.resolver import InterfaceProtocol
    return ResolvedConnection(
        api_base="http://x/rerank", api_key="sk-1", custom_headers=None,
        model_name="model", interface_protocol=InterfaceProtocol.OPENAI,
        timeout=30.0, verify_ssl=False,
    )


class TestRerank:
    def test_sorts_results_by_index(self, monkeypatch):
        import model_service.dispatch as dispatch

        fake_client = _FakeClient(_FakeResponse(json_data={
            "results": [
                {"index": 2, "doc": "c"},
                {"index": 0, "doc": "a"},
                {"index": 1, "doc": "b"},
            ],
        }))
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: fake_client)

        async def _run():
            return await rerank(_FakeModel(), _FakeAuth(), _FakeRequest(docs=["d1", "d2"]))

        data = asyncio.run(_run())
        assert [r["index"] for r in data["results"]] == [0, 1, 2]

    def test_none_index_sorted_last(self, monkeypatch):
        import model_service.dispatch as dispatch

        fake_client = _FakeClient(_FakeResponse(json_data={
            "results": [
                {"index": None, "doc": "x"},
                {"index": 1, "doc": "y"},
            ],
        }))
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: fake_client)

        async def _run():
            return await rerank(_FakeModel(), _FakeAuth(), _FakeRequest())

        data = asyncio.run(_run())
        assert data["results"][-1]["index"] is None

    def test_top_n_truncates(self, monkeypatch):
        import model_service.dispatch as dispatch

        fake_client = _FakeClient(_FakeResponse(json_data={
            "results": [
                {"index": 0}, {"index": 1}, {"index": 2}, {"index": 3},
            ],
        }))
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: fake_client)

        async def _run():
            return await rerank(_FakeModel(), _FakeAuth(), _FakeRequest(top_n=2))

        data = asyncio.run(_run())
        assert len(data["results"]) == 2

    def test_upstream_error_raises(self, monkeypatch):
        import model_service.dispatch as dispatch
        from model_service.resolver import ModelServiceError

        fake_client = _FakeClient(_FakeResponse(status_code=500, text="boom"))
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: fake_client)

        async def _run():
            return await rerank(_FakeModel(), _FakeAuth(), _FakeRequest())

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_INVOKE_MODEL_SERVICE_FAIL"
        assert exc_info.value.upstream_status == 500

    def test_request_body_built(self, monkeypatch):
        import model_service.dispatch as dispatch

        fake_client = _FakeClient(_FakeResponse(json_data={"results": []}))
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: fake_client)

        async def _run():
            return await rerank(_FakeModel(), _FakeAuth(), _FakeRequest(query="q", docs=["a", "b"]))

        asyncio.run(_run())
        body = fake_client.posted[1]
        assert body["model"] == "model"
        assert body["query"] == "q"
        assert body["documents"] == ["a", "b"]
        assert body["return_documents"] is True

    def test_empty_results_ok(self, monkeypatch):
        import model_service.dispatch as dispatch

        fake_client = _FakeClient(_FakeResponse(json_data={"results": []}))
        monkeypatch.setattr(dispatch, "get_chat_connection", lambda m, a: _mk_conn())
        monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **k: fake_client)

        async def _run():
            return await rerank(_FakeModel(), _FakeAuth(), _FakeRequest())

        data = asyncio.run(_run())
        assert data["results"] == []
