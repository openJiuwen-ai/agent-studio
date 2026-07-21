"""Tests for the agent_builder FastAPI shell — route surface only.

Uses TestClient WITHOUT entering lifespan (no `with`), so startup hooks
(ContextManager set_store / Redis ping) do not run and no infra is required.
"""
from fastapi.testclient import TestClient

from agent_builder.serve.server_fastapi import app


def _client():
    # No `with` → lifespan does not run → no Redis/DB needed.
    return TestClient(app, raise_server_exceptions=False)


def _all_paths(routes):
    """Collect all route paths, recursing into FastAPI's _IncludedRouter
    wrappers. FastAPI 0.139+ wraps included routers (whose routes only appear
    under ``original_router``); older versions flatten them into ``app.routes``.
    Duck-typed via ``original_router`` so no private-class import is needed.
    """
    paths = set()
    stack = list(routes)
    while stack:
        r = stack.pop()
        p = getattr(r, "path", None)
        if p is not None:
            paths.add(p)
        orig = getattr(r, "original_router", None)
        if orig is not None:
            stack.extend(getattr(orig, "routes", []))
    return paths


def test_health_returns_200_without_lifespan():
    r = _client().get("/v1/health")
    assert r.status_code == 200
    assert r.text == "the health is good"


def test_n2l_route_is_registered():
    routes = _all_paths(app.routes)
    assert "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat" in routes


def test_flask_app_mounted_at_root():
    # The Flask app is mounted at "/" via WSGIMiddleware → a Flask route
    # (e.g. /flask/...) should be reachable through the FastAPI app.
    # We only assert the mount exists (Flask catch-all), not a specific payload.
    # Starlette 1.x normalizes mount path "/" to "" — accept both.
    mounts = [r for r in app.routes if getattr(r, "path", None) in ("/", "")]
    assert len(mounts) >= 1, "Flask app should be mounted at '/'"


def test_flask_path_normalization_middleware_present():
    # normalize_flask_path rewrites /v1/prompt/... -> /flask/v1/prompt/...
    # Assert it does not crash on a /v1/prompt/ request (Flask returns 404
    # for unknown sub-paths, but must not 500).
    r = _client().get("/v1/prompt/__nonexistent__")
    assert r.status_code != 500
