# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SUT-01 CD-018 (B2): FlaskRouteDispatchMiddleware 纯分派单元测试。

覆盖 §6.3 分派规则、§6.4 scope 复制（不修改原 scope）、路径规范化函数。
不依赖真实 Flask/WSGI 运行——以记录型 ASGI callable 替换 dispatcher 的 flask_app
与内层 app，验证分派决策与 child_scope 字段。
"""
import pytest

from agent_builder.serve.common.flask_route_dispatch import (
    FlaskRouteDispatchMiddleware,
    normalize_registered_flask_path,
)


# ------------------- normalize_registered_flask_path -------------------


@pytest.mark.parametrize("path,expected", [
    # 规则 1: /v1/prompt → /flask/v1/prompt
    ("/v1/prompt", "/flask/v1/prompt"),
    ("/v1/prompt/build", "/flask/v1/prompt/build"),
    ("/v1/prompt/templates_optimization/jobs", "/flask/v1/prompt/templates_optimization/jobs"),
    # 规则 2: /v1/MMprompt → /flask/v1/MMprompt
    ("/v1/MMprompt", "/flask/v1/MMprompt"),
    ("/v1/MMprompt/templates_optimization/jobs", "/flask/v1/MMprompt/templates_optimization/jobs"),
    # 规则 3: 已带 /flask 前缀 → 原样
    ("/flask/v1/prompt/build", "/flask/v1/prompt/build"),
    ("/flask/v1/MMprompt/x", "/flask/v1/MMprompt/x"),
    # 规则 4: 其他 → None（FastAPI 拥有）
    ("/v1/health", None),
    ("/v1/unknown", None),
    ("/flask/other", None),  # 非 prompt/MMprompt 的 /flask 子路径不属本 dispatcher
    ("/", None),
    ("", None),
])
def test_normalize_registered_flask_path(path, expected):
    assert normalize_registered_flask_path(path) == expected


# ------------------- 分派决策 + scope 复制 -------------------


def _make_dispatcher():
    """构造 dispatcher，内层 app 与 flask_app 均替换为记录型 ASGI callable。"""
    seen = {"inner": None, "flask": None}

    async def fake_inner(scope, receive, send):
        seen["inner"] = dict(scope)

    async def fake_flask(scope, receive, send):
        seen["flask"] = dict(scope)

    m = FlaskRouteDispatchMiddleware(app=fake_inner, flask_app=object())
    # 替换 WSGIMiddleware 包装为记录型，避免依赖真实 Flask
    m.flask_app = fake_flask
    return m, seen


def _http_scope(path, method="GET", query=b"k=v"):
    return {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query,
        "headers": [],
        "root_path": "",
    }


async def _noop_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


async def _noop_send(msg):
    pass


@pytest.mark.asyncio
async def test_flask_path_dispatches_to_flask_with_prefixed_scope():
    m, seen = _make_dispatcher()
    scope = _http_scope("/v1/prompt/build", method="POST")
    await m(scope, _noop_receive, _noop_send)
    assert seen["flask"] is not None
    assert seen["inner"] is None
    # child_scope 路径已规范化为 /flask 前缀
    assert seen["flask"]["path"] == "/flask/v1/prompt/build"
    assert seen["flask"]["raw_path"] == b"/flask/v1/prompt/build"


@pytest.mark.asyncio
async def test_mmapo_path_dispatches_to_flask():
    m, seen = _make_dispatcher()
    await m(_http_scope("/v1/MMprompt/templates_optimization/jobs", method="POST"),
            _noop_receive, _noop_send)
    assert seen["flask"] is not None
    assert seen["inner"] is None
    assert seen["flask"]["path"] == "/flask/v1/MMprompt/templates_optimization/jobs"


@pytest.mark.asyncio
async def test_fastapi_path_dispatches_to_inner_unchanged():
    m, seen = _make_dispatcher()
    scope = _http_scope("/v1/health", method="DELETE")
    await m(scope, _noop_receive, _noop_send)
    assert seen["inner"] is not None
    assert seen["flask"] is None
    # FastAPI 路径 scope 原样（不补 /flask）
    assert seen["inner"]["path"] == "/v1/health"


@pytest.mark.asyncio
async def test_original_scope_not_mutated():
    # §6.3 规则 5: 不修改原 request scope 对象
    m, _ = _make_dispatcher()
    scope = _http_scope("/v1/prompt/build", method="POST")
    original_path = scope["path"]
    original_raw = scope["raw_path"]
    await m(scope, _noop_receive, _noop_send)
    assert scope["path"] == original_path  # 原对象未被改
    assert scope["raw_path"] == original_raw


@pytest.mark.asyncio
async def test_query_string_preserved_in_child_scope():
    m, seen = _make_dispatcher()
    scope = _http_scope("/v1/prompt/build", query=b"a=1&b=2")
    await m(scope, _noop_receive, _noop_send)
    assert seen["flask"]["query_string"] == b"a=1&b=2"


@pytest.mark.asyncio
async def test_non_http_scope_dispatches_to_inner():
    m, seen = _make_dispatcher()
    await m({"type": "websocket", "path": "/v1/prompt/build"}, _noop_receive, _noop_send)
    assert seen["inner"] is not None
    assert seen["flask"] is None


@pytest.mark.asyncio
async def test_method_does_not_affect_dispatch():
    # §6.3 规则 8: 分派仅依据路径，不依据 method；同一路径 GET/DELETE/OPTIONS 进同一框架
    for method in ("GET", "DELETE", "OPTIONS", "POST"):
        m, seen = _make_dispatcher()
        await m(_http_scope("/v1/prompt/build", method=method), _noop_receive, _noop_send)
        assert seen["flask"] is not None, f"method {method} should still dispatch to Flask"
