import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import openjiuwen_studio.routers.deepsearch as deepsearch_router
from openjiuwen_studio.routers.deepsearch import validate_search_run_tool_credentials
from openjiuwen_studio.schemas.deepsearch import DeepSearchSearchRunRequest


def _run_payload(**overrides):
    payload = {
        "space_id": "space-1",
        "query": "What changed in Python 3.13?",
        "llm": {
            "model_name": "gpt-4o-mini",
            "model_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "llm-key",
        },
        "tool_map": "search_fetch",
    }
    payload.update(overrides)
    return payload


def _new_search_config():
    return {
        "search_engine_name": "tavily",
        "search_api_key": "search-key",
        "search_url": "https://api.tavily.com/search",
        "max_web_search_results": 3,
        "extension": {"include_domains": ["python.org"]},
    }


def _new_fetch_config():
    return {
        "provider_name": "jina",
        "api_key": "fetch-key",
        "base_url": "https://r.jina.ai",
        "extension": {"timeout": 15},
    }


def test_search_fetch_accepts_and_forwards_complete_new_config_pair():
    request = DeepSearchSearchRunRequest(
        **_run_payload(
            web_search_engine_config=_new_search_config(),
            web_fetch_provider_config=_new_fetch_config(),
        )
    )

    validate_search_run_tool_credentials(request)

    payload = request.model_dump(exclude={"space_id"}, exclude_none=True)
    assert payload["web_search_engine_config"] == _new_search_config()
    assert payload["web_fetch_provider_config"] == _new_fetch_config()


@pytest.mark.asyncio
async def test_create_search_run_forwards_generic_credential_shape_unchanged(monkeypatch):
    class Client:
        payload = None

        async def create_deepsearch_run(self, payload):
            self.payload = payload
            return {"run_id": "run-1", "status": "created"}

    monkeypatch.setattr(deepsearch_router, "check_user_space", lambda *_: None)
    client = Client()
    credentials = {
        "web_search_engine_config": _new_search_config(),
        "web_fetch_provider_config": _new_fetch_config(),
    }
    request = DeepSearchSearchRunRequest(**_run_payload(**credentials))

    await deepsearch_router.create_search_run(request, client=client, current_user={})

    for field_name in ("web_search_engine_config", "web_fetch_provider_config"):
        assert client.payload[field_name] == credentials[field_name]
    assert "space_id" not in client.payload


def test_search_fetch_rejects_new_search_config_without_fetch_config():
    request = DeepSearchSearchRunRequest(
        **_run_payload(web_search_engine_config=_new_search_config())
    )

    with pytest.raises(HTTPException, match="web_fetch_provider_config"):
        validate_search_run_tool_credentials(request)


def test_search_fetch_rejects_fetch_config_without_explicit_provider_name():
    fetch_config = _new_fetch_config()
    fetch_config.pop("provider_name")

    with pytest.raises(ValidationError, match="provider_name"):
        DeepSearchSearchRunRequest(
            **_run_payload(
                web_search_engine_config=_new_search_config(),
                web_fetch_provider_config=fetch_config,
            )
        )


def test_retrieve_validation_remains_unchanged():
    request = DeepSearchSearchRunRequest(
        **_run_payload(
            tool_map="retrieve",
            milvus={
                "embedder_api_key": "embedding-key",
                "embedder_base_url": "https://embedding.example.com/v1",
            },
        )
    )

    validate_search_run_tool_credentials(request)
