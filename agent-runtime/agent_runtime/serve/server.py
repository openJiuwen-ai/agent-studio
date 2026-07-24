# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
OLE FastAPI server — lightweight version of jiwen-server/serve/server.py
"""

import os
from contextlib import asynccontextmanager

import opentelemetry.context as _otel_context
_otel_runtime_ctx = getattr(_otel_context, '_RUNTIME_CONTEXT')


def _silent_detach(token):
    try:
        _otel_runtime_ctx.detach(token)
    except ValueError:
        pass


_otel_context.detach = _silent_detach

# 在所有 jiuwen import 之前，先接管日志配置
# 这样 jiuwen SingletonLogger 检测到标志后不再添加自己的 handler，避免重复日志
from agent_runtime.common.logging_context import (
    install_log_formatter_patch,
    install_request_id_log_record_factory,
)
install_request_id_log_record_factory()
install_log_formatter_patch()

# 在任何 jiuwen OBS 操作之前，补丁 Crypt 类使用明文解密
# agent_runtime 本地调试环境 SK 为明文存储，而 jiuwen Crypt 默认实现抛异常
from jiuwen.common.security.cryptor import Crypt as JiuWenCrypt


def _plain_encrypt(origin: str):
    """明文加密 — 直接返回原始字符串（agent_runtime 本地环境不加密）"""
    return origin


def _plain_decrypt(encrypt_str: str):
    """明文解密 — 直接返回原始字符串（agent_runtime 本地环境 SK 为明文存储）"""
    return encrypt_str


JiuWenCrypt.encrypt = staticmethod(_plain_encrypt)
JiuWenCrypt.decrypt = staticmethod(_plain_decrypt)

from storage import S3StorageProvider

from agent_runtime.common import settings
from agent_runtime.common.checkpointer_config import build_redis_checkpointer_config
from agent_runtime.common.exception.errors import AgentBuilderError
from agent_runtime.event_handler.base.mappers import ErrorContextBuilder
from agent_runtime.common.llm_call_logging import register_llm_call_logging_callbacks
from agent_runtime.common.logging_context import COMMON_LOG_FORMAT
from common_utils.redis_manager import RedisClientManager
from agent_runtime.context.middleware import RequestContextMiddleware
from agent_runtime.observability import setup_otel_tracer
from agent_runtime.memory.adapter.ltm_manager import init_ltm
from agent_runtime.memory.internal_routes import memory_internal_router
from agent_runtime.serve.apis.orchestration import execution_app
from agent_runtime.serve.apis.app_run import app_run_app
from agent_runtime.serve.apis.web_run import web_run_app
from agent_runtime.serve.apis.user_variable_api import user_variable_router
from agent_runtime.serve.apis.conversation_variable_api import conversation_variable_router
from agent_runtime.serve.apis.inner_tools import inner_tools_router
from agent_runtime.serve.apis.release_api import release_api_router
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# 初始化 prompt 模板
from jiuwen.common.init import init_prompt
from openjiuwen.core.common.logging import workflow_logger as logger
from openjiuwen.core.common.logging.log_config import configure_log_config
from openjiuwen.core.runner import Runner
from openjiuwen.core.session.checkpointer.checkpointer import CheckpointerFactory
from openjiuwen.core.sys_operation import SysOperationCard, OperationMode
from openjiuwen.core.sys_operation.config import (
    SandboxGatewayConfig,
    SandboxIsolationConfig,
    ContainerScope,
    PreDeployLauncherConfig,
)

from openjiuwen.extensions.sys_operation.sandbox import providers as _  # noqa: F401

# 导入 redis checkpointer 模块以触发 @CheckpointerFactory.register("redis") 装饰器
from openjiuwen.extensions.checkpointer.redis import checkpointer as _  # noqa: F401
from agent_runtime.runner.fast_redis_checkpointer import FastRedisCheckpointer

prompt_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "jiuwen", "prompt", "template", "default"
)
if os.path.exists(prompt_dir):
    init_prompt(prompt_dir=prompt_dir)
    logger.info(f"Initialized prompt templates from {prompt_dir}")
else:
    logger.warning(f"Prompt template directory not found: {prompt_dir}")

# 注册工作流组件到组件池
from jiuwen.orchestration.flow.component_class_pool import component_class_pool
from agent_runtime.extension.workflow_node.flow_code import FlowCode, JIUWEN_CODE_TYPE

component_class_pool.register_component_class(JIUWEN_CODE_TYPE, FlowCode)
logger.info("Registered workflow component: jiuwen.code")

# FastAPI routers must be included BEFORE Flask app mount (Flask catches all routes)
# 注：prompt_manage_app（agent_builder.app）已随 agent_builder 抽离到 studio-builder 镜像，runtime 不含。
apps_map = [
    execution_app, app_run_app, web_run_app, user_variable_router,
    conversation_variable_router, memory_internal_router, inner_tools_router,
    release_api_router,
]


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: redefined-outer-name
    """define startup and shutdown logic here"""
    # 初始化 workflow_logger 日志级别（从环境变量 WORKFLOW_LOG_LEVEL 读取）
    workflow_log_level = settings.workflow_log.level.upper()
    graph_log_level = settings.workflow_log.graph_level.upper()
    llm_log_level = settings.workflow_log.llm_level.upper()
    
    configure_log_config(
        {
            "backend": "default",
            "level": "INFO",  # 全局默认级别保持 INFO
            "format": COMMON_LOG_FORMAT,
            "loggers": {
                "workflow": {"level": workflow_log_level},
                "graph": {"level": graph_log_level},
                "llm": {"level": llm_log_level},
                "performance": {"level": "INFO"},
                "sys_operation": {
                    "level": "WARNING"
                },  # 关闭 sys_operation 的 INFO 日志
            },
        }
    )
    logger.info(f"Logger level set - workflow: {workflow_log_level}, graph: {graph_log_level}, llm: {llm_log_level}")

    # 初始化 OpenTelemetry tracer（当 OTEL_ENABLED=true 时生效）
    setup_otel_tracer()

    # 注册 LLM 调用日志回调 — 打印模型请求体和响应内容
    register_llm_call_logging_callbacks()

    # 初始化 Redis 客户端
    redis_mgr = RedisClientManager.get_instance()
    redis_mgr.init()

    # 检查 Redis 连接是否正常
    if not redis_mgr.is_initialized:
        raise RuntimeError(
            "Redis client initialization failed, please check REDIS_* configuration"
        )

    redis_client = redis_mgr.get_client()
    try:
        await redis_client.ping()
        logger.info("Redis connection check passed")
    except Exception as e:
        raise RuntimeError(f"Redis connection check failed: {e}") from e

    # Initialize memory library (LTM) — non-critical, degrades gracefully
    memory_ok = await init_ltm(redis_client)
    if memory_ok:
        logger.info("Memory library enabled")
    else:
        logger.info("Memory library not available (non-critical)")

    # 创建并设置 Redis Checkpointer 为默认
    checkpointer_config = build_redis_checkpointer_config()
    redis_checkpointer = await CheckpointerFactory.create(checkpointer_config)

    if settings.checkpointer.fast_checkpointer_enabled:
        fast_checkpointer = FastRedisCheckpointer(
            delegate=redis_checkpointer,
            redis_client=redis_client,
            ttl_seconds=settings.checkpointer.sentinel_ttl_seconds,
        )
        CheckpointerFactory.set_default_checkpointer(fast_checkpointer)
        logger.info("FastRedisCheckpointer initialized and set as default (scan_iter bypass enabled)")
    else:
        CheckpointerFactory.set_default_checkpointer(redis_checkpointer)
        logger.info("Redis checkpointer initialized and set as default (fast checkpointer disabled)")

    # 初始化异步 S3 存储客户端（实现位于共享包 storage；先注入 OBS 配置再 initialize）
    try:
        import storage as _storage
        _storage.set_settings(lambda: settings.object_storage)
        s3_provider = S3StorageProvider.instance()
        await s3_provider.initialize()
        logger.info("S3 async storage client initialized")
    except Exception as e:
        logger.warning(f"S3 async storage client initialization failed (non-critical): {e}")

    # 注册 flow_code 专用的 SysOperation（local mode）
    # 注意：当 LOCAL_CODE_EXEC_MODE=inprocess（默认）时，代码节点使用进程内 exec() 执行，
    # 不依赖此 sys_operation。仅 LOCAL_CODE_EXEC_MODE=subprocess 时才会使用。
    sys_op_id = "flow_code_sys_op"
    if Runner.resource_mgr.get_sys_operation(sys_op_id) is None:
        card = SysOperationCard(id=sys_op_id, mode=OperationMode.LOCAL)
        add_res = Runner.resource_mgr.add_sys_operation(card)
        if add_res.is_ok():
            logger.info(
                f"Registered SysOperation: {sys_op_id} (mode={OperationMode.LOCAL})"
            )
        else:
            logger.error(f"Failed to register flow_code_sys_op: {add_res}")

    # 注册 SANDBOX SysOperation（根据 SECURITY_SANDBOX_SERVER 配置）
    sandbox_server = settings.security_sandbox.server
    if sandbox_server:
        sandbox_sys_op_id = "flow_code_sandbox_sys_op"
        if Runner.resource_mgr.get_sys_operation(sandbox_sys_op_id) is None:
            scope = ContainerScope.SYSTEM
            if settings.security_sandbox.scope == "session":
                scope = ContainerScope.SESSION
            sandbox_card = SysOperationCard(
                id=sandbox_sys_op_id,
                mode=OperationMode.SANDBOX,
                gateway_config=SandboxGatewayConfig(
                    isolation=SandboxIsolationConfig(container_scope=scope),
                    launcher_config=PreDeployLauncherConfig(
                        base_url=sandbox_server,
                        sandbox_type=settings.security_sandbox.sandbox_type,
                        idle_ttl_seconds=settings.security_sandbox.idle_ttl_seconds,
                    ),
                    timeout_seconds=settings.security_sandbox.timeout_seconds,
                ),
            )
            sandbox_res = Runner.resource_mgr.add_sys_operation(sandbox_card)
            if sandbox_res.is_ok():
                sb = settings.security_sandbox
                logger.info(
                    f"Registered SysOperation: {sandbox_sys_op_id} (mode={OperationMode.SANDBOX}) | "
                    f"server={sb.server} type={sb.sandbox_type} scope={sb.scope} "
                    f"ssl_verify={sb.ssl_verify} idle_ttl={sb.idle_ttl_seconds}s "
                    f"timeout={sb.timeout_seconds}s"
                )
            else:
                logger.error(f"Failed to register sandbox SysOperation: {sandbox_res}")

    try:
        yield
    finally:
        # 关闭异步 S3 存储客户端
        try:
            s3_provider = S3StorageProvider.instance()
            await s3_provider.close()
        except Exception as e:
            logger.warning(f"S3 storage client close failed (non-critical): {e}")

        # 关闭 Redis 客户端
        await redis_mgr.close()
        logger.info("Redis client closed")
        logger.info("OLE shutdown")


def instance_app(config: dict | None = None):
    """instance FastAPI server"""
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)  # noqa: redefined-outer-name
    app.add_middleware(RequestContextMiddleware)

    for i in apps_map:
        app.include_router(i)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """请求参数校验失败时返回统一格式的错误响应，而非FastAPI默认的detail格式."""
        errors = exc.errors()
        detail_parts = []
        for err in errors:
            loc = ".".join(str(part) for part in err.get("loc", []))
            msg = err.get("msg", "")
            detail_parts.append(f"{loc}: {msg}" if loc else msg)
        detail_str = "; ".join(detail_parts)
        logger.warning(f"Request validation error: {detail_str}")
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context(language, "02001003")
        )
        return JSONResponse(
            status_code=400,
            content={
                "error_code": error_code,
                "error_msg": error_msg,
                "error_reason": detail_str,
                "error_suggestion": error_suggestion,
            },
        )

    @app.exception_handler(AgentBuilderError)
    async def agent_builder_error_handler(request: Request, exc: AgentBuilderError):
        exec_id = getattr(request.state, "execution_id", "unknown")
        req_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            f"AgentBuilderError: {exc}, execution_id={exec_id}, request_id={req_id}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": getattr(exc, "code", "AgentBuilder_ERROR"),
                    "message": str(exc),
                }
            },
        )

    # Storage 异常已迁移至共享包 storage（不再是 AgentBuilderError 子类），
    # 这里单独兜底，保持未捕获 storage 错误的结构化 500 响应不变（code 取 exc.code）。
    from storage.exceptions import StorageConfigError, StorageReadError

    @app.exception_handler(StorageReadError)
    async def storage_read_error_handler(request: Request, exc: StorageReadError):
        logger.error(f"StorageReadError: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": getattr(exc, "code", 188911), "message": str(exc)}},
        )

    @app.exception_handler(StorageConfigError)
    async def storage_config_error_handler(request: Request, exc: StorageConfigError):
        logger.error(f"StorageConfigError: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": getattr(exc, "code", 188910), "message": str(exc)}},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        exec_id = getattr(request.state, "execution_id", "unknown")
        req_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc}, execution_id={exec_id}, request_id={req_id}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {"code": "internal_error", "message": "Internal server error"}
            },
        )

    return app


# Create the app instance at module level
app = instance_app()
