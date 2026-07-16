# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
agent_builder FastAPI server — mirrors agent_runtime/serve/server.py structure.

FastAPI shell that mounts the existing single Flask `agent_builder.app` via
WSGIMiddleware and includes the builder_router (n2l + health) BEFORE the
Flask mount (Flask catches all routes).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from flask import Flask
from starlette.middleware.wsgi import WSGIMiddleware

from agent_builder.adapter.exception_bridge import JiuWenException
from agent_builder.adapter.logger_bridge import get_thread_session, set_thread_session

# Single Flask app (already has prompt.manager + mmapo.manager blueprints
# registered via ServerApp in agent_builder/serve/server.py).
from agent_builder.app import app as prompt_manage_app
from agent_builder.serve.apis.n2l_api import builder_router

logger = logging.getLogger("agent_builder.server_fastapi")

# FastAPI routers must be included BEFORE Flask app mount (Flask catches all routes)
apps_map = [builder_router, prompt_manage_app]


async def _ping_redis() -> None:
    """Best-effort Redis ping at startup (fail-fast on misconfig).

    n2l history.py creates its client lazily from the same config_bridge
    settings; this only validates config at boot. Warn-and-continue on failure.
    """
    try:
        from agent_builder.adapter.redis_bridge import RedisClientManager

        mgr = RedisClientManager.get_instance()
        mgr.init()
        if not mgr.is_initialized:
            logger.warning("Redis client not initialized (non-critical)")
            return
        client = mgr.get_client()
        await client.ping()
        logger.info("Redis connection check passed")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Redis connection check failed (non-critical): {e}")


async def _init_prompt_store() -> None:
    """Initialize prompt-optimization DB store (moved from agent_runtime lifespan)."""
    try:
        from agent_builder.prompt.tune.base.context_manager import ContextManager

        ContextManager().set_store()
        logger.info("Prompt optimization store initialized")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Prompt optimization store init failed (non-critical): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: redefined-outer-name
    await _init_prompt_store()
    await _ping_redis()
    try:
        yield
    finally:
        logger.info("agent_builder shutdown")


def instance_app() -> FastAPI:
    """Build the agent_builder FastAPI server."""
    app = FastAPI(
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )

    @app.middleware("http")
    async def set_trace_id(request: Request, call_next):
        trace_id = request.headers.get("TraceID", "")
        set_thread_session(trace_id)
        return await call_next(request)

    # Flask 路径规范化中间件：OptimizationTemplateService 调用 /v1/prompt/...
    # 而 Flask blueprint 注册了 url_prefix="/flask"，需要统一补上前缀
    @app.middleware("http")
    async def normalize_flask_path(request: Request, call_next):
        path = request.url.path
        if path.startswith("/v1/prompt/") and not path.startswith("/flask"):
            prefixed = f"/flask{path}"
            request = Request(request.scope, request.receive)
            request.scope["path"] = prefixed
        return await call_next(request)

    for i in apps_map:
        if isinstance(i, Flask):
            app.mount("/", WSGIMiddleware(i))
        else:
            app.include_router(i)

    @app.exception_handler(JiuWenException)
    async def builder_exception_handler(request: Request, exc: JiuWenException):
        trace_id = get_thread_session()
        logger.error(
            f"JiuWenException: {exc}, trace_id={trace_id}", exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": getattr(exc, "error_code", -1),
                    "message": str(exc),
                    "trace_id": trace_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        trace_id = get_thread_session()
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc}, trace_id={trace_id}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "trace_id": trace_id,
                }
            },
        )

    return app


# Create the app instance at module level
app = instance_app()
