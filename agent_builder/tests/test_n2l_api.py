"""Tests for the builder FastAPI router (route registration only)."""
from agent_builder.serve.apis.n2l_api import builder_router


def _paths(router):
    return {getattr(r, "path", None) for r in router.routes}


def test_builder_router_has_health():
    assert "/v1/health" in _paths(builder_router)


def test_builder_router_has_n2l_chat():
    n2l = "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"
    assert n2l in _paths(builder_router)


def test_n2l_chat_methods_include_post():
    n2l = "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"
    methods = set()
    for r in builder_router.routes:
        if getattr(r, "path", None) == n2l:
            methods.update(r.methods or [])
    assert "POST" in methods


def test_n2l_chat_handler_delegates_to_chat(monkeypatch):
    """n2l POST handler plumbs the payload through _n2l_json_wapper to _chat.

    Monkeypatches _chat so no infra (Redis/LLM/DB) is needed. The body must
    include ``model.modelName`` because _n2l_json_wapper accesses it eagerly.
    """
    import agent_builder.serve.apis.n2l_api as n2l_api
    from fastapi.responses import StreamingResponse
    from fastapi.testclient import TestClient
    from agent_builder.serve.server_fastapi import app

    captured = {}

    async def fake_chat(payload):
        captured["payload"] = payload

        async def gen():
            yield b'data: {"event":"done"}\n\n'

        return StreamingResponse(gen(), media_type="text/event-stream")

    monkeypatch.setattr(n2l_api, "_chat", fake_chat)
    client = TestClient(app, raise_server_exceptions=False)
    r = client.post(
        "/v1/proj1/ReAct/generator/conversations/c1/chat",
        json={"query": "hi", "model": {"modelName": "test-model"}},
    )
    assert r.status_code == 200
    assert captured["payload"] is not None
    assert captured["payload"]["query"] == "hi"
    assert captured["payload"]["conversationId"] == "c1"
