import httpx
import pytest
from fastapi import HTTPException

import openjiuwen_studio.routers.deepsearch as deepsearch_router
from openjiuwen_studio.schemas.deepsearch import (
    TaskSpaceWebFetchProviderAccessRequestDTO,
    TaskSpaceWebSearchProviderAccessRequestDTO,
)


@pytest.fixture(autouse=True)
def allow_provider_urls(monkeypatch):
    monkeypatch.setattr(deepsearch_router, "validate_plugin_url", lambda url: url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "response_payload", "expected_header", "expected_body_key"),
    [
        ("xunfei", {"data": [{"title": "result"}]}, ("Authorization", "Bearer search-key"), "q"),
        ("petal", {"results": [{"title": "result"}]}, ("Authorization", "Bearer search-key"), "q"),
        ("tavily", {"results": [{"title": "result"}]}, None, "query"),
        ("google", {"organic": [{"title": "result"}]}, ("X-API-KEY", "search-key"), "q"),
        ("jina", {"data": [{"title": "result"}]}, ("Authorization", "Bearer search-key"), "q"),
        ("serper", {"organic": [{"title": "result"}]}, ("X-API-KEY", "search-key"), "q"),
        ("bocha", {"data": [{"title": "result"}]}, ("Authorization", "Bearer search-key"), "query"),
        ("perplexity", {"choices": [{"message": {"content": "result"}}]}, ("Authorization", "Bearer search-key"), "messages"),
        ("custom", {"items": [{"title": "result"}]}, ("Authorization", "Bearer search-key"), "q"),
    ],
)
async def test_search_adapters_translate_and_normalize_each_supported_provider(
    monkeypatch,
    provider,
    response_payload,
    expected_header,
    expected_body_key,
):
    captured = {}

    async def fake_post(endpoint, headers, request_body):
        captured.update(endpoint=endpoint, headers=headers, body=request_body)
        return httpx.Response(200, json=response_payload)

    monkeypatch.setattr(deepsearch_router, "_post_generic_provider_test", fake_post)

    results = await deepsearch_router.perform_web_search_provider_test(
        provider_name=provider,
        api_key="search-key",
        search_url="https://custom.example.test/search" if provider == "custom" else None,
        extension={"max_results": 3, "api_key": "must-not-forward", "headers": {"x": "unsafe"}},
        query="latest AI",
    )

    assert captured["body"][expected_body_key]
    assert "api_key" not in captured["body"] or provider == "tavily"
    assert "headers" not in captured["body"]
    if provider == "tavily":
        assert captured["body"]["api_key"] == "search-key"
    elif expected_header:
        assert captured["headers"][expected_header[0]] == expected_header[1]
    assert results


@pytest.mark.asyncio
async def test_custom_search_forwards_submitted_endpoint_and_safe_extension(monkeypatch):
    captured = {}

    async def fake_post(endpoint, headers, request_body):
        captured.update(endpoint=endpoint, headers=headers, body=request_body)
        return httpx.Response(200, json={"results": []})

    monkeypatch.setattr(deepsearch_router, "_post_generic_provider_test", fake_post)

    await deepsearch_router.perform_web_search_provider_test(
        provider_name="custom",
        api_key="search-key",
        search_url="https://search.example.test/custom",
        extension={"language": "en", "query": "cannot override", "endpoint": "cannot override"},
        query="actual query",
    )

    assert captured["endpoint"] == "https://search.example.test/custom"
    assert captured["body"] == {"q": "actual query", "language": "en"}


@pytest.mark.asyncio
async def test_tavily_search_uses_the_search_path_for_a_runtime_base_url(monkeypatch):
    captured = {}

    async def fake_post(endpoint, headers, request_body):
        captured.update(endpoint=endpoint, headers=headers, body=request_body)
        return httpx.Response(200, json={"results": []})

    monkeypatch.setattr(deepsearch_router, "_post_generic_provider_test", fake_post)

    await deepsearch_router.perform_web_search_provider_test(
        provider_name="tavily",
        api_key="search-key",
        search_url="https://api.tavily.com",
        extension={},
        query="actual query",
    )

    assert captured["endpoint"] == "https://api.tavily.com/search"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "extension", "expected_endpoint"),
    [
        ("serper", {}, "https://google.serper.dev/search"),
        ("serper", {"type": "news"}, "https://google.serper.dev/news"),
        ("google", {}, "https://google.serper.dev/search"),
    ],
)
async def test_serper_backed_search_uses_the_same_url_path_as_deep_research(
    monkeypatch,
    provider,
    extension,
    expected_endpoint,
):
    captured = {}

    async def fake_post(endpoint, headers, request_body):
        captured.update(endpoint=endpoint, headers=headers, body=request_body)
        return httpx.Response(200, json={"organic": []})

    monkeypatch.setattr(deepsearch_router, "_post_generic_provider_test", fake_post)

    await deepsearch_router.perform_web_search_provider_test(
        provider_name=provider,
        api_key="search-key",
        search_url="https://google.serper.dev",
        extension=extension,
        query="actual query",
    )

    assert captured["endpoint"] == expected_endpoint
    assert captured["body"]["gl"] == "us"
    assert captured["body"]["hl"] == "en"
    assert "type" not in captured["body"]


@pytest.mark.asyncio
async def test_jina_fetch_adapter_forwards_base_url_and_safe_extension(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, endpoint, headers, params):
            captured.update(endpoint=endpoint, headers=headers, params=params)
            return httpx.Response(200, text="fetched page")

    monkeypatch.setattr(deepsearch_router.httpx, "AsyncClient", FakeClient)

    results = await deepsearch_router.perform_web_fetch_provider_test(
        provider_name="jina",
        api_key="fetch-key",
        base_url="https://reader.example.test",
        extension={"timeout": 10, "authorization": "must-not-forward"},
        test_url="https://example.com/article",
    )

    assert captured["endpoint"] == "https://reader.example.test/https://example.com/article"
    assert captured["headers"]["Authorization"] == "Bearer fetch-key"
    assert captured["params"] == {"timeout": 10}
    assert results == [{"url": "https://example.com/article", "content": "fetched page"}]


@pytest.mark.asyncio
async def test_unsupported_provider_is_rejected_without_a_network_call():
    with pytest.raises(HTTPException, match="Unsupported search provider") as exc_info:
        await deepsearch_router.perform_web_search_provider_test(
            provider_name="unsupported",
            api_key="key",
            search_url=None,
            extension={},
            query="query",
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_provider_timeout_is_normalized_and_does_not_expose_credential(monkeypatch):
    class TimeoutClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(deepsearch_router.httpx, "AsyncClient", TimeoutClient)

    with pytest.raises(HTTPException) as exc_info:
        await deepsearch_router.perform_web_search_provider_test(
            provider_name="serper",
            api_key="secret-search-key",
            search_url=None,
            extension={},
            query="query",
        )

    assert exc_info.value.status_code == 502
    assert "secret-search-key" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_provider_results_redact_credentials_before_returning_to_browser(monkeypatch):
    async def fake_post(_endpoint, _headers, _request_body):
        return httpx.Response(
            200,
            json={"results": [{"api_key": "search-secret", "excerpt": "key=search-secret"}]},
        )

    monkeypatch.setattr(deepsearch_router, "_post_generic_provider_test", fake_post)

    results = await deepsearch_router.perform_web_search_provider_test(
        provider_name="tavily",
        api_key="search-secret",
        search_url=None,
        extension={},
        query="query",
    )

    assert results == [{"api_key": "[REDACTED]", "excerpt": "key=[REDACTED]"}]


@pytest.mark.asyncio
async def test_search_route_authorizes_space_and_uses_request_only_adapter(monkeypatch):
    authorized_spaces = []
    provider_calls = []

    monkeypatch.setattr(
        deepsearch_router,
        "check_user_space",
        lambda space_id, _user: authorized_spaces.append(space_id),
    )

    async def fake_test(**kwargs):
        provider_calls.append(kwargs)
        return [{"title": "result"}]

    monkeypatch.setattr(deepsearch_router, "perform_web_search_provider_test", fake_test)
    request = TaskSpaceWebSearchProviderAccessRequestDTO(
        space_id="space-1",
        search_engine_name="tavily",
        search_api_key="search-key",
        search_url="https://api.tavily.com/search",
        extension={"max_results": 1},
        query="test query",
    )

    result = await deepsearch_router.access_task_space_web_search_provider(request, current_user={})

    assert authorized_spaces == ["space-1"]
    assert provider_calls == [{
        "provider_name": "tavily",
        "api_key": "search-key",
        "search_url": "https://api.tavily.com/search",
        "extension": {"max_results": 1},
        "query": "test query",
    }]
    assert result["provider_name"] == "tavily"


@pytest.mark.asyncio
async def test_fetch_route_authorizes_space_and_uses_request_only_adapter(monkeypatch):
    authorized_spaces = []
    provider_calls = []

    monkeypatch.setattr(
        deepsearch_router,
        "check_user_space",
        lambda space_id, _user: authorized_spaces.append(space_id),
    )

    async def fake_test(**kwargs):
        provider_calls.append(kwargs)
        return [{"url": "https://example.com", "content": "result"}]

    monkeypatch.setattr(deepsearch_router, "perform_web_fetch_provider_test", fake_test)
    request = TaskSpaceWebFetchProviderAccessRequestDTO(
        space_id="space-1",
        provider_name="jina",
        api_key="fetch-key",
        base_url="https://r.jina.ai",
        extension={"timeout": 10},
        test_url="https://example.com",
    )

    result = await deepsearch_router.access_task_space_web_fetch_provider(request, current_user={})

    assert authorized_spaces == ["space-1"]
    assert provider_calls == [{
        "provider_name": "jina",
        "api_key": "fetch-key",
        "base_url": "https://r.jina.ai",
        "extension": {"timeout": 10},
        "test_url": "https://example.com",
    }]
    assert result["provider_name"] == "jina"


@pytest.mark.asyncio
async def test_provider_test_routes_propagate_space_authorization_failures(monkeypatch):
    def reject_space(*_args):
        raise HTTPException(status_code=403, detail="Forbidden")

    monkeypatch.setattr(deepsearch_router, "check_user_space", reject_space)
    request = TaskSpaceWebSearchProviderAccessRequestDTO(
        space_id="space-1",
        search_engine_name="tavily",
        search_api_key="search-key",
    )

    with pytest.raises(HTTPException) as exc_info:
        await deepsearch_router.access_task_space_web_search_provider(request, current_user={})

    assert exc_info.value.status_code == 403


def test_provider_test_routes_do_not_call_engine_crud_or_database_clients():
    source = (deepsearch_router.__file__ and open(deepsearch_router.__file__, encoding="utf-8").read())
    start = source.index("async def access_task_space_web_search_provider(")
    end = source.index('@deepsearch_router.post("/reports/convert"')
    route_source = source[start:end]
    for forbidden_call in (
        "create_web_searchs",
        "update_web_search_engines",
        "delete_web_search_engines",
        "access_web_search_engines",
        "get_db",
    ):
        assert forbidden_call not in route_source
