# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
agent_builder FastAPI server — mirrors agent_runtime/serve/server.py structure.

FastAPI shell that mounts the existing single Flask `agent_builder.app` via
WSGIMiddleware and includes the builder_router (n2l + health) BEFORE the
Flask mount (Flask catches all routes).
"""

import asyncio
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
from agent_builder.serve.apis.model_service_api import model_service_router

logger = logging.getLogger("agent_builder.server_fastapi")

# FastAPI routers must be included BEFORE Flask app mount (Flask catches all routes)
apps_map = [builder_router, model_service_router, prompt_manage_app]


async def _ping_redis() -> None:
    """Best-effort Redis ping at startup (fail-fast on misconfig).

    n2l history.py creates its client lazily from the same config_bridge
    settings; this only validates config at boot. Warn-and-continue on failure.
    """
    try:
        from common_utils.redis_manager import RedisClientManager

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
    """Initialize prompt-optimization DB store."""
    try:
        from agent_builder.prompt.tune.base.context_manager import ContextManager

        ContextManager().set_store()
        logger.info("Prompt optimization store initialized")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Prompt optimization store init failed (non-critical): {e}")


async def _init_s3_storage() -> None:
    """Initialize the OBS/S3 storage client via the shared `storage` package.

    Required when MODEL_ROUTER_API is unconfigured so that the model_service
    resolver can read model-service metadata + auth from OBS. Non-critical:
    on misconfig the resolver falls back to LocalStorageProvider, so startup
    still succeeds.
    """
    try:
        import storage
        from agent_builder.adapter.config_bridge import settings

        storage.set_settings(lambda: settings.object_storage)
        await storage.S3StorageProvider.instance().initialize()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"S3 async storage client initialization failed (non-critical): {e}")


def _register_model_service_ports() -> None:
    """注入 model_service 所需的 storage / llm settings / request-headers，使其
    不依赖 agent_runtime（agent_builder 用自有 bridge + 共享 storage 包）。cache 不注入
    （跳过 L2，resolver 每次直读 OBS；如需缓存可后续接 common_utils.redis_manager 实现的 CacheQueue）。"""
    import storage
    from model_service import ports
    from agent_builder.adapter.config_bridge import settings
    from agent_builder.adapter.request_context_bridge import get_request_headers

    ports.set_storage_provider(storage.get_storage_provider)
    ports.set_llm_settings(lambda: settings.llm)
    ports.set_request_headers(get_request_headers)
    ports.set_cache_queues(None, None)
    logger.info("model_service ports registered (storage/llm/request-headers; cache disabled)")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: redefined-outer-name
    # 注入主 FastAPI event loop，供 Flask 同步路由的 _run_async 桥接（run_coroutine_threadsafe）
    # 调度协程到主 loop，避免新建 loop 与主 loop 上的 async 单例（S3StorageProvider 等）跨 loop。
    from agent_builder.adapter.llm_bridge import set_main_loop
    set_main_loop(asyncio.get_running_loop())

    await _init_prompt_store()
    await _ping_redis()
    await _init_s3_storage()
    _register_model_service_ports()
    try:
        yield
    finally:
        try:
            import storage

            await storage.S3StorageProvider.instance().close()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"S3 storage client close failed (non-critical): {e}")
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

    # 请求上下文中间件：把九问平台认证/工作空间头透传到 agent_builder 自有的 _request_ctx，
    # 供未配置 MODEL_ROUTER_API 时 StudioModelClient._resolve_inputs 取 projectId/workspace_id
    # （经 model_service.ports.set_request_headers 注入 getter，不依赖 agent_runtime）。
    @app.middleware("http")
    async def populate_request_context(request: Request, call_next):
        from agent_builder.adapter.request_context_bridge import (
            RequestContext, _request_ctx,
        )

        def _h(name: str) -> str:
            return request.headers.get(name) or request.headers.get(name.lower(), "")

        ctx = RequestContext(
            headers={
                "X-Owner-Project-Id": _h("X-Owner-Project-Id"),
                "X-Workspace-Id": _h("X-Workspace-Id"),
                "X-Auth-Id": _h("X-Auth-Id"),
                "X-Auth-Token": _h("X-Auth-Token"),
                "X-Deployment-Id": _h("X-Deployment-Id"),
            }
        )
        token = _request_ctx.set(ctx)
        try:
            return await call_next(request)
        finally:
            _request_ctx.reset(token)

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
