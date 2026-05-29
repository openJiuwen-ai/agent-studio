from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEEPSEARCH_ROUTER = REPO_ROOT / "backend/openjiuwen_studio/routers/deepsearch.py"


def _deepsearch_source() -> str:
    return DEEPSEARCH_ROUTER.read_text(encoding="utf-8")


def _provider_test_route_source() -> str:
    source = _deepsearch_source()
    start = source.index("async def access_task_space_web_search_provider(")
    end = source.index("@deepsearch_router.post(\"/reports/convert\"")
    return source[start:end]


def test_provider_test_route_uses_direct_http_provider_calls():
    source = _deepsearch_source()

    assert '"jina": {"engine_name": "jina", "endpoint": "https://s.jina.ai/"}' in source
    assert '"serper": {"engine_name": "google", "endpoint": "https://google.serper.dev/search"}' in source
    assert "async def perform_provider_test(provider: str, api_key: str, query: str)" in source
    assert "async with httpx.AsyncClient(" in source


def test_provider_test_route_no_longer_persists_temporary_engines():
    route_source = _provider_test_route_source()

    assert "await perform_provider_test(provider=provider, api_key=api_key, query=query)" in route_source
    assert "create_web_searchs" not in route_source
    assert "update_web_search_engines" not in route_source
    assert "delete_web_search_engines" not in route_source
    assert "access_web_search_engines" not in route_source


def test_provider_test_route_returns_success_payload_without_saved_engine_dependency():
    route_source = _provider_test_route_source()

    assert '"code": status.HTTP_200_OK' in route_source
    assert '"msg": "success"' in route_source
    assert '"search_engine_name": TASK_SPACE_PROVIDER_TEST_PRESETS[provider]["engine_name"]' in route_source
    assert '"datas": datas' in route_source


def test_provider_test_sets_provider_specific_auth_headers():
    source = _deepsearch_source()

    assert 'headers["Authorization"] = f"Bearer {api_key}"' in source
    assert 'headers["X-API-KEY"] = api_key' in source
    assert 'request_body: dict[str, Any] = {"q": query}' in source
