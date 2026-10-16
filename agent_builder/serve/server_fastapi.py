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
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from flask import Flask
from starlette.middleware.wsgi import WSGIMiddleware

from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.serve.common.flask_route_dispatch import FlaskRouteDispatchMiddleware

# Single Flask app (already has prompt.manager + mmapo.manager blueprints
# registered via ServerApp in agent_builder/serve/server.py).
from agent_builder.app import app as prompt_manage_app
from agent_builder.serve.apis.model_service_api import model_service_router
from agent_builder.serve.apis.n2l_api import builder_router

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
    from agent_builder.adapter.request_context_bridge import (
        get_env_variables,
        get_request_customer_headers,
        get_request_headers,
    )

    ports.set_storage_provider(storage.get_storage_provider)
    ports.set_llm_settings(lambda: settings.llm)
    ports.set_request_headers(get_request_headers)
    ports.set_env_variables(get_env_variables)
    # 注册独立 customer Header provider（强类型，不退化为无 provenance 的 dict）
    ports.set_request_customer_headers(get_request_customer_headers)
    ports.set_cache_queues(None, None)
    logger.info(
        "model_service ports registered (storage/llm/request-headers/customer-headers/env-variables; cache disabled)"
    )


def _load_customer_header_profile() -> None:
    """从环境变量加载客户 Header 配置"""
    from common_utils.customer_header import load_from_env, set_config
    cfg = load_from_env()
    set_config(cfg)
    logger.info(f"[customer-header] Config loaded from env, enabled={cfg.enabled}, mappings={list(cfg.mappings)}")


def _capture_customer_headers(request: Request) -> dict:
    """按配置白名单捕获客户 header（cust-*，不含 x-auth-token）。

    Profile 未启用时返回空 dict。
    """
    try:
        from common_utils.customer_header import get_capture_keys, get_config
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[customer-header] customer_header package unavailable, skip capture: {e}")
        return {}

    cfg = get_config()
    if not cfg.enabled:
        return {}
    capture_keys = get_capture_keys()

    result: dict = {}
    for name in capture_keys:
        value = request.headers.get(name) or request.headers.get(name.lower())
        if value:
            result[name] = value
    if result:
        logger.info(
            f"[customer-header] Inbound customer header capture: "
            f"captured_keys={list(result.keys())}"
        )
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: redefined-outer-name
    # 注入主 FastAPI event loop，供 Flask 同步路由的 _run_async 桥接（run_coroutine_threadsafe）
    # 调度协程到主 loop，避免新建 loop 与主 loop 上的 async 单例（S3StorageProvider 等）跨 loop。
    from agent_builder.adapter.llm_bridge import set_main_loop
    set_main_loop(asyncio.get_running_loop())

    await _init_prompt_store()
    await _ping_redis()
    await _init_s3_storage()
    _load_customer_header_profile()
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


def _apply_allow_header_if_405(response, exc):
    """SUT-01 CD-018 (B2) §6.5：405 时按白名单补回 exc.headers 中的 Allow。

    build_json_response 只产出 X-Request-Id，不保留 exc.headers 的 Allow；405 必须带
    Allow（RFC 9110 + §3.2）。本 helper 仅在 status==405、仅 Allow、替换语义补回，
    不无条件复制其他异常 Header（如伪造 X-Evil / X-Request-Id），不覆盖已写的
    X-Request-Id / Content-Type 等响应元数据。抽为模块级以便白名单反证单测。
    """
    if getattr(exc, "status_code", None) == 405 and getattr(exc, "headers", None):
        for k, v in exc.headers.items():
            if k.lower() == "allow":
                response.headers["Allow"] = v
                break
    return response


def instance_app() -> FastAPI:
    """Build the agent_builder FastAPI server."""
    app = FastAPI(
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )

    # SUT-01 CD-018 (B2): 先注册 dispatcher（内层用户 middleware），后注册
    # establish_inbound_context（外层）。Starlette LIFO：后注册者在外层包装，
    # 故 establish 在 dispatcher 外层，先建立 ID 再分派；dispatcher 不读/不生成 ID。
    # 禁止在保留 establish 为 @app.middleware 后再 add_middleware(dispatcher)——
    # 那样 dispatcher 会跑到 establish 外层，与目标序相反（§6.4 第 4 点）。
    app.add_middleware(FlaskRouteDispatchMiddleware, flask_app=prompt_manage_app)

    @app.middleware("http")
    async def establish_inbound_context(request: Request, call_next):
        from common_utils import load_environment_variables

        from agent_builder.adapter.logger_bridge import reset_session_id, set_session_id
        from agent_builder.adapter.request_context_bridge import (
            ContextSource,
            RequestContext,
            _request_ctx,
        )
        from agent_builder.serve.common.error_response import (
            build_inbound_error_response,
        )
        from agent_builder.serve.common.inbound_context import (
            apply_platform_headers,
            select_ids,
            write_x_request_id,
        )

        # 1. 纯读取选值（无日志、无外部依赖）；Builder 不收 X-Execution-Id
        request_id, trace_id, illegal_req, illegal_trace = select_ids(request.headers)
        # 2. 最小 RequestContext + 同步写 request.state（异常 handler 可在 reset 后读）
        ctx = RequestContext(request_id=request_id, source=ContextSource.FASTAPI_MOUNT)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        # 3. 原子建立两个 token；第二个失败立即恢复第一个
        request_token = _request_ctx.set(ctx)
        try:
            trace_token = set_session_id(trace_id)
        except Exception:
            _request_ctx.reset(request_token)
            raise
        try:
            if illegal_req:
                logger.warning(
                    f"header X-Request-Id is illegal; "
                    f"regenerated request_id={request_id}"
                )
            if illegal_trace:
                logger.warning(
                    f"header TraceID is illegal; fell back to trace_id={trace_id}"
                )
            # token 有效期内补充分仓（平台 header + 客户 header + env_variables）
            apply_platform_headers(ctx, request.headers)
            ctx.customer_headers = _capture_customer_headers(request)
            # sync_01 独有：按 X-Environment-Id 加载环境变量

            def _h(name: str) -> str:
                return request.headers.get(name) or request.headers.get(name.lower(), "")
            environment_id = _h("X-Environment-Id")
            workspace_id = _h("X-Workspace-Id") or request.query_params.get("workspace_id", "")
            # sync_01 兼容（审视 04c1c58d §2.2）：Header 缺失时 query 参数回退写回
            # ctx.headers——model_service 经 get_request_headers 读 X-Workspace-Id
            # 作 workspace_id（原 populate_request_context 最终值语义，Header 优先）
            if workspace_id and not ctx.headers.get("X-Workspace-Id"):
                ctx.headers["X-Workspace-Id"] = workspace_id
            ctx.env_variables = await load_environment_variables(environment_id, workspace_id)

            response = await call_next(request)
            write_x_request_id(response, request_id)
            return response
        except Exception as exc:  # 请求级异常边界，token 有效期内按类型分派收口
            err_response = build_inbound_error_response(request, exc)
            write_x_request_id(err_response, request_id)
            return err_response
        finally:
            # LIFO 逆序 reset，嵌套 try/finally 保证两个 reset 均被尝试
            try:
                reset_session_id(trace_token)
            finally:
                _request_ctx.reset(request_token)

    # SUT-01 CD-018 (B2): 独立 normalize_flask_path 已并入 FlaskRouteDispatchMiddleware
    # （normalize_registered_flask_path 覆盖 /v1/prompt + /v1/MMprompt），删除避免
    # 两处分别改 path。根路径 app.mount("/", WSGIMiddleware(flask)) catch-all 已移除
    # ——Flask app 由 dispatcher 持有并按前缀分派，不再 catch-all 抢占 FastAPI method
    # 不匹配分派（DELETE /v1/health 404→405、FastAPI OPTIONS 404→405）。
    for i in apps_map:
        if isinstance(i, Flask):
            continue  # Flask app 由 FlaskRouteDispatchMiddleware 持有，不再 mount("/")
        app.include_router(i)

    from agent_builder.common.error_contract import factory as error_factory

    @app.exception_handler(JiuWenBaseException)
    async def builder_exception_handler(request: Request, exc: JiuWenBaseException):
        """框架业务异常 → COM-03 canonical8 五字段（error_code/error_msg/
        error_reason/error_suggestion/request_id + X-Request-Id Header）。

        SYNC-01 P5-R3b（2026-09-22）：旧分支 COM-03 此 handler 已改五字段 +
        factory 分类。sync_01 原裸 3-field（``str(exc)`` 外露 + 裸 error_code）
        升级为 from_builder_exception 分类 + build_json_response；error_code
        透传语义保（经 factory 分类映射）。
        COM-08 §4.6：日志不写 str(exc)（防哨兵泄漏），固定基础事件 + exc_info。
        """
        trace_id = getattr(request.state, "trace_id", "")
        request_id = getattr(request.state, "request_id", "")
        logger.error(
            f"JiuWenBaseException: [{getattr(exc, 'error_code', -1)}], "
            f"trace_id={trace_id}, request_id={request_id}",
            exc_info=True,
        )
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        descriptor = error_factory.from_builder_exception(exc, request_id or None)
        return error_factory.build_json_response(descriptor, language)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """COM-03 §7.2：参数校验失败 → canonical8 五字段（400）。"""
        trace_id = getattr(request.state, "trace_id", "")
        request_id = getattr(request.state, "request_id", "")
        logger.warning(
            f"ValidationError: trace_id={trace_id}, request_id={request_id}",
        )
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        descriptor = error_factory.from_validation(exc, request_id or None)
        return error_factory.build_json_response(descriptor, language)

    # 注册到 starlette 父类：路由级 404/405 抛 starlette.HTTPException（父类），
    # fastapi.HTTPException（子类）实例同样命中本 handler（Runtime 同款教训）。
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """COM-03 §7.2 第 1 点：HTTPException 统一 adapter（404/405/4xx/5xx）。"""
        trace_id = getattr(request.state, "trace_id", "")
        request_id = getattr(request.state, "request_id", "")
        logger.warning(
            f"HTTPException {exc.status_code}: trace_id={trace_id}, "
            f"request_id={request_id}",
        )
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        descriptor = error_factory.from_http_exception(exc, request_id or None)
        response = error_factory.build_json_response(descriptor, language)
        # SUT-01 CD-018 (B2) §6.5：405 补 Allow（白名单，见 _apply_allow_header_if_405）
        return _apply_allow_header_if_405(response, exc)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        """COM-03 §7.2：未处理异常 → INTERNAL_ERROR（openjiuwen.13100004）五字段。

        sync_01 原裸 internal_error 3-field 升级为 from_internal canonical8。
        COM-08 §4.6：日志不写 str(exc)/类型名正文，固定基础事件 + exc_info。
        """
        trace_id = getattr(request.state, "trace_id", "")
        request_id = getattr(request.state, "request_id", "")
        logger.error(
            f"Unhandled exception: trace_id={trace_id}, request_id={request_id}",
            exc_info=True,
        )
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        descriptor = error_factory.from_internal(exc, request_id or None)
        return error_factory.build_json_response(descriptor, language)

    return app


# Create the app instance at module level
app = instance_app()
