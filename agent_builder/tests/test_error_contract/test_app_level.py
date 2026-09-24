"""COM-03 §10.4: Builder app 级 HTTPException 出口测试。

回归防护（Runtime 同款教训）：HTTPException handler 必须注册到
starlette 父类，路由级 404/405 才不会落回 FastAPI 默认 ``{"detail":...}``。
"""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from agent_builder.common.error_contract import factory


def _make_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        descriptor = factory.from_http_exception(
            exc, getattr(request.state, "request_id", None) if request else None)
        return factory.build_json_response(descriptor, "zh-cn")

    @app.get("/exists")
    async def exists():
        return {"ok": True}

    return app


def test_route_404_returns_standard_five_fields():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/no-such-route")
    assert r.status_code == 404
    body = r.json()
    assert body["error_code"] == "openjiuwen.13100002"
    for field in ("error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[field], f"{field} non-empty"


def test_route_405_returns_method_not_allowed():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.delete("/exists")
    assert r.status_code == 405
    assert r.json()["error_code"] == "openjiuwen.13100003"


def test_fastapi_raised_http_exception_caught_by_parent_handler():
    from fastapi import HTTPException

    app = _make_app()

    @app.get("/raise")
    async def raise_http():
        raise HTTPException(status_code=400, detail="bad input")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/raise")
    assert r.status_code == 400
    assert r.json()["error_code"] == "openjiuwen.13100001"
