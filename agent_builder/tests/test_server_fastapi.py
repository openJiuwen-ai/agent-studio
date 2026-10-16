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


def test_health_returns_custom_rsp_when_configured(monkeypatch):
    from agent_builder.adapter.config_bridge import settings

    monkeypatch.setattr(settings.health_check, "custom_rsp", "custom-healthy")
    r = _client().get("/v1/health")
    assert r.status_code == 200
    assert r.text == "custom-healthy"


def test_n2l_route_is_registered():
    routes = _all_paths(app.routes)
    assert "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat" in routes


def test_root_mount_removed_and_dispatcher_present():
    # SUT-01 CD-018 (B2): 根路径 WSGI catch-all 已移除；Flask app 由
    # FlaskRouteDispatchMiddleware 持有，不再 mount("/")。
    mounts = [r for r in app.routes if getattr(r, "path", None) in ("/", "")]
    assert mounts == [], f"root catch-all mount should be removed, got {mounts}"
    names = [
        (m.cls.__name__ if hasattr(m, "cls") else type(m).__name__)
        for m in app.user_middleware
    ]
    assert "FlaskRouteDispatchMiddleware" in names, (
        f"FlaskRouteDispatchMiddleware should be registered, got {names}")


def test_middleware_order_context_outer_dispatcher_inner():
    # §6.4: establish_inbound_context（@app.middleware→BaseHTTPMiddleware）必须在
    # FlaskRouteDispatchMiddleware 外层（先建立 ID 再分派）。LIFO：后注册者外层。
    names = [
        (m.cls.__name__ if hasattr(m, "cls") else type(m).__name__)
        for m in app.user_middleware
    ]
    try:
        ctx_idx = names.index("BaseHTTPMiddleware")
    except ValueError:
        ctx_idx = -1
    disp_idx = names.index("FlaskRouteDispatchMiddleware")
    assert ctx_idx >= 0 and ctx_idx < disp_idx, (
        f"context(establish) must be OUTER than dispatcher; got {names}")


def test_fastapi_path_wrong_method_returns_405_with_allow():
    # CD-018: DELETE /v1/health 原被 root mount 抢占为 Flask 404，现 FastAPI 拥有
    # method ownership → canonical 405 + Allow（13100003）。
    r = _client().delete("/v1/health", headers={"X-Request-Id": "rid-del-health"})
    assert r.status_code == 405
    assert r.headers.get("Allow") is not None
    assert r.json()["error_code"] == "openjiuwen.13100003"
    assert r.json()["request_id"] == "rid-del-health"
    assert r.headers.get("X-Request-Id") == "rid-del-health"


def test_fastapi_path_options_returns_405_with_allow():
    # §6.2/§8.3 连带：FastAPI 已登记路径 OPTIONS 由 FastAPI 返回 405+Allow
    # （恢复 method ownership 的同源变化，不通过 dispatcher 特判回退）。
    r = _client().options("/v1/health", headers={"X-Request-Id": "rid-opt-health"})
    assert r.status_code == 405
    assert r.headers.get("Allow") is not None
    assert r.json()["error_code"] == "openjiuwen.13100003"


def test_flask_path_options_keeps_method_limit_404():
    # §6.9: Flask 路径 OPTIONS 经 dispatcher 进入 Flask，保持 method_limit() 空 body + 404。
    r = _client().options("/v1/prompt/build", headers={"X-Request-Id": "rid-opt-prompt"})
    assert r.status_code == 404


def test_fastapi_unknown_path_returns_canonical_404():
    r = _client().get("/v1/__no_such_fastapi_route__", headers={"X-Request-Id": "rid-404"})
    assert r.status_code == 404
    assert r.json()["error_code"] == "openjiuwen.13100002"


def _assert_flask_canonical_400_13100001(r, rid):
    """正向断言：经 dispatcher 命中 Flask 的 @catch_exception Werkzeug 分支
    （CD-015）→ 400 + 13100001 + 五字段 + body/header ID 同值。证明：
    (1) dispatcher 把 /v1/prompt|MMprompt 路由到 Flask（非 FastAPI 404）；
    (2) B1 Werkzeug 分支在 Flask 侧生效。"""
    assert r.status_code == 400, f"expected Flask 400, got {r.status_code}: {r.text[:160]}"
    body = r.json()
    assert body["error_code"] == "openjiuwen.13100001", body
    for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[f], f"{f} non-empty"
    assert body["request_id"] == rid
    assert r.headers.get("X-Request-Id") == rid


def test_prompt_route_reaches_flask_canonical_400():
    # P1-3: /v1/prompt/build 空 body（application/json）经 dispatcher→Flask，
    # request.json 触发 Werkzeug BadRequest → @catch_exception → 400+13100001。
    r = _client().post("/v1/prompt/build", content=b"",
                       headers={"Content-Type": "application/json", "X-Request-Id": "rid-prompt"})
    _assert_flask_canonical_400_13100001(r, "rid-prompt")


def test_mmapo_route_reaches_flask_canonical_400():
    # P1-3: /v1/MMprompt/... 同理命中 Flask mmapo blueprint
    r = _client().post("/v1/MMprompt/templates_optimization/jobs", content=b"",
                       headers={"Content-Type": "application/json", "X-Request-Id": "rid-mmapo"})
    _assert_flask_canonical_400_13100001(r, "rid-mmapo")


def test_explicit_flask_prefix_compat_path_reaches_flask():
    # P2-3: 显式 /flask/v1/prompt/... 兼容路径经 dispatcher rule 3 原样交 WSGI
    r = _client().post("/flask/v1/prompt/build", content=b"",
                       headers={"Content-Type": "application/json", "X-Request-Id": "rid-flask-explicit"})
    _assert_flask_canonical_400_13100001(r, "rid-flask-explicit")


def test_dynamic_context_established_before_dispatch_on_flask_path():
    # P2-3 动态探针：Flask 路径响应带外层 establish 写入的 X-Request-Id（单值），
    # 证明 establish_inbound_context 在 dispatcher 外层先建立 ID、再分派到 Flask，
    # 且 write_x_request_id 在响应回写。结构顺序（test_middleware_order_...）+ 此动态证据。
    r = _client().post("/v1/prompt/build", content=b"",
                       headers={"Content-Type": "application/json", "X-Request-Id": "rid-dynamic"})
    assert r.headers.get_list("X-Request-Id") == ["rid-dynamic"]
    assert r.json()["request_id"] == "rid-dynamic"


def test_url_encoded_path_dispatches_correctly():
    # P2-3: URL 编码路径经 dispatcher 一次解码正确分派，不双重解码/误路由。
    # /v1/prompt/build（含编码的 %62 = 'b'）应与 /v1/prompt/build 等价命中 Flask。
    r = _client().post("/v1/prompt/%62uild", content=b"",
                       headers={"Content-Type": "application/json", "X-Request-Id": "rid-enc"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "openjiuwen.13100001"


def test_allow_whitelist_only_copies_allow_not_arbitrary_headers():
    # P2-1 反证：构造带 Allow + 伪造 X-Evil + 伪造 X-Request-Id 的 StarletteHTTPException(405)，
    # 直接单测 _apply_allow_header_if_405——只补 Allow，不注入 X-Evil，不覆盖外层 X-Request-Id。
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.responses import JSONResponse
    from agent_builder.serve.server_fastapi import _apply_allow_header_if_405

    forged = StarletteHTTPException(
        status_code=405,
        headers={"Allow": "GET, HEAD", "X-Evil": "inject-me", "X-Request-Id": "forged-rid"},
    )
    # 外层已建立的响应（X-Request-Id 由 establish 写入）
    resp = JSONResponse(content={"error_code": "openjiuwen.13100003"}, headers={"X-Request-Id": "real-rid"})
    _apply_allow_header_if_405(resp, forged)

    lower = {k.lower(): v for k, v in resp.headers.items()}
    assert lower.get("allow") == "GET, HEAD"          # Allow 透传
    assert "x-evil" not in lower, "forged X-Evil must NOT be copied"  # 白名单挡住
    assert lower.get("x-request-id") == "real-rid", "forged X-Request-Id must NOT overwrite outer"  # 关联 ID 不被覆盖


def test_allow_whitelist_not_applied_on_non_405():
    # P2-1: 非 405（如 404）即使 exc.headers 含 Allow 也不补
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.responses import JSONResponse
    from agent_builder.serve.server_fastapi import _apply_allow_header_if_405

    exc404 = StarletteHTTPException(status_code=404, headers={"Allow": "GET"})
    resp = JSONResponse(content={})
    _apply_allow_header_if_405(resp, exc404)
    assert "allow" not in {k.lower() for k in resp.headers}


def test_correlation_header_single_value_on_fastapi_path():
    r = _client().get("/v1/health", headers={"X-Request-Id": "rid-single"})
    assert r.headers.get_list("X-Request-Id") == ["rid-single"]


def test_query_string_preserved_on_fastapi_path():
    # P2-2: FastAPI 路径 query 基线（/v1/health 直交 FastAPI router）
    r = _client().get("/v1/health?foo=bar&baz=qux", headers={"X-Request-Id": "rid-q-fastapi"})
    assert r.status_code == 200


def test_query_string_preserved_on_flask_path():
    # P2-2: Flask 路径 query 经 dispatcher→Flask，query_string 在 child scope 保留
    r = _client().post("/v1/prompt/build?foo=bar", content=b"",
                       headers={"Content-Type": "application/json", "X-Request-Id": "rid-q-flask"})
    _assert_flask_canonical_400_13100001(r, "rid-q-flask")


def test_direct_flask_blueprint_unchanged():
    # P2-3: B2 只改 server_fastapi（mounted 模式），未碰 server.py direct / agent_builder.app。
    # 结构证明：direct Flask app 仍持有 prompt/mmapo blueprint @ /flask 前缀（未丢路由）。
    # 注：direct Flask 的 test_client 运行时会触发 server.py:192 的 ContextVar 双重 reset
    # （既有问题，非 B2 引入——B2 未碰 server.py），故用 url_map 结构证明而非 runtime 请求。
    from agent_builder.app import app as direct_flask_app
    rules = {r.rule for r in direct_flask_app.url_map.iter_rules()}
    assert any(r.startswith("/flask/v1/prompt/") for r in rules), \
        "direct Flask prompt blueprint @ /flask missing"
    assert any(r.startswith("/flask/v1/MMprompt/") for r in rules), \
        "direct Flask mmapo blueprint @ /flask missing"
