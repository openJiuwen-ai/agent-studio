from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
THIRDPARTY_CLIENT = REPO_ROOT / "backend/openjiuwen_studio/core/thirdparty_client.py"


def _lazy_deepsearch_client_source() -> str:
    source = THIRDPARTY_CLIENT.read_text(encoding="utf-8")
    start = source.index("class LazyDeepSearchHttpClient:")
    end = source.index("class DeepSearchAgentClient:")
    return source[start:end]


def test_deepsearch_http_client_does_not_follow_redirects():
    source = _lazy_deepsearch_client_source()

    assert "follow_redirects=False" in source
    assert "follow_redirects=True" not in source


def test_deepsearch_run_path_matches_trailing_slash_route():
    source = THIRDPARTY_CLIENT.read_text(encoding="utf-8")

    assert 'self._http.stream("POST", "/api/v1/agent/deepsearch/run/"' in source
    assert 'self._http.stream("POST", "/api/v1/agent/deepsearch/run"' not in source


def test_lazy_deepsearch_client_serializes_init_and_safe_invalidate():
    source = _lazy_deepsearch_client_source()

    assert "_mode_locks" in source
    assert "async def _ensure_client" in source
    assert "async def _invalidate_client" in source
    assert "self._clients.get(mode) is not client" in source


def test_deepsearch_call_error_includes_exception_type_when_message_empty():
    from openjiuwen_studio.core.thirdparty_client import _format_deepsearch_call_error
    import httpx

    assert _format_deepsearch_call_error(httpx.ReadError("")) == "ReadError"
    assert _format_deepsearch_call_error(ValueError("bad host")) == "bad host"
