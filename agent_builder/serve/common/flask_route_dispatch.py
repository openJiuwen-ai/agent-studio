# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SUT-01 CD-018 (B2): FastAPI/Flask 显式路径分派中间件。

移除根路径 ``app.mount("/", WSGIMiddleware(flask_app))`` catch-all 后，由本
中间件按**路径所有权**（不依据 HTTP method，§6.3 规则 8）把已登记 Flask 前缀
（``/v1/prompt``、``/v1/MMprompt`` 及其 ``/flask`` 别名）复制 scope 并规范化后
交给 WSGIMiddleware(Flask)，其余路径交给内层 FastAPI router。

设计约束（§6.3）：
- 不修改原 request scope 对象（``dict(scope)`` 复制），避免影响日志/异常/后续中间件；
- 只按冻结的完整路径前缀分派，不用包含 ``prompt`` 的宽泛判断；
- 分派层不自行构造 404/405，不选择错误码，不生成关联 ID；
- 同一路径的 GET/DELETE/OPTIONS 必须进入同一框架（§6.3 规则 8），由所属框架
  决定 404/405/``Allow``——这是 ``DELETE /v1/health`` 404→405 与 FastAPI 路径
  OPTIONS 404→405 同源的必要连带变化。
"""

from __future__ import annotations

from starlette.middleware.wsgi import WSGIMiddleware


def normalize_registered_flask_path(path: str) -> str | None:
    """把已登记 Flask 前缀规范化为 Flask app 实际注册的 ``/flask`` 路径。

    返回 None 表示该路径属于 FastAPI（不交 WSGI）。规则（§6.3）：

    1. ``/v1/prompt`` / ``/v1/prompt/...`` → ``/flask/v1/prompt...``
    2. ``/v1/MMprompt`` / ``/v1/MMprompt/...`` → ``/flask/v1/MMprompt...``
    3. ``/flask/v1/prompt...`` / ``/flask/v1/MMprompt...`` 原样（已是别名）
    4. 其他 → None（FastAPI router）
    """
    # 已带 /flask 前缀的已登记 Flask 路径——原样交给 WSGI
    if path == "/flask/v1/prompt" or path.startswith("/flask/v1/prompt/"):
        return path
    if path == "/flask/v1/MMprompt" or path.startswith("/flask/v1/MMprompt/"):
        return path
    # 未带前缀的已登记 Flask 路径——补 /flask 前缀（URL 路由前缀，非文件系统路径）
    if path == "/v1/prompt" or path.startswith("/v1/prompt/"):
        return f"/flask{path}"
    if path == "/v1/MMprompt" or path.startswith("/v1/MMprompt/"):
        return f"/flask{path}"
    return None


class FlaskRouteDispatchMiddleware:
    """纯 ASGI 分派中间件：Flask 前缀 → WSGI，其余 → 内层 FastAPI。"""

    def __init__(self, app, flask_app):
        # app = 内层 ASGI app（FastAPI ExceptionMiddleware/Router）；flask_app = Flask app
        self.fastapi_app = app
        self.flask_app = WSGIMiddleware(flask_app)

    async def __call__(self, scope, receive, send):
        # 非 http scope（如 websocket/lifespan）直接交内层
        if scope.get("type") != "http":
            return await self.fastapi_app(scope, receive, send)
        target_path = normalize_registered_flask_path(scope.get("path", ""))
        if target_path is None:
            # FastAPI 拥有的路径——原样交内层 router（method ownership 归 FastAPI）
            return await self.fastapi_app(scope, receive, send)
        # 复制 scope（不修改原对象），规范化 path/raw_path 后交 WSGI
        child_scope = dict(scope)
        child_scope["path"] = target_path
        child_scope["raw_path"] = target_path.encode("utf-8")
        return await self.flask_app(child_scope, receive, send)
