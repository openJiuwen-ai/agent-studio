#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.

"""
general server for agent_builder services

Initialization uses local adapter layer instead of jiuwen.
"""

import os
import secrets
from datetime import timedelta

from common_utils.redis_manager import RedisClientManager
from flask import Flask, request

from agent_builder.adapter.exception_bridge import JiuWenBaseException, JiuWenException
from agent_builder.adapter.init_server import load_yaml_config, env_to_config
from agent_builder.common.logging.base import logger
from agent_builder.common.security.sts_service import sts_init
from agent_builder.serve.apis.mmapo import mmapo_app
from agent_builder.serve.apis.prompt import prompt_manage_app
from agent_builder.serve.common.ssl_ctx import create_context
from agent_builder.serve.config import load_config

apps_map = {
    "prompt.manager": prompt_manage_app,
    "mmapo.manager": mmapo_app,
}


def extract_host_and_port(config):
    """extract host and port"""
    if not config:
        raise JiuWenException("config is required")
    host = config.get("host")
    port = config.get("port")

    if isinstance(port, str) and port.isdigit():
        port = int(port)

    if not isinstance(port, int):
        raise JiuWenException("port should be an integer")

    return host, port


def instance_app(config):
    """instance flask server"""
    manager_key = "manager"
    app = Flask(__name__)
    if not config:
        raise JiuWenException("config is required")
    apps = config.get("apps")
    for k, v in apps.items():
        if v[manager_key] is True or v[manager_key] in ["true", "True"]:
            manager_app = apps_map.get(k + "." + manager_key)
            if manager_app:
                app.register_blueprint(manager_app, url_prefix="/flask")
            else:
                raise ValueError("app not found, please check your setting.yaml")

    app.before_request(_establish_inbound_context)
    app.teardown_request(_teardown_inbound_context)

    # SYNC-01 P5-R3b: COM-03 §7.3 第 4/5 点 — Flask 等价 errorhandler。
    # 404/405 等 HTTPException 不再走 Flask 默认 HTML/描述页，统一映射为
    # 标准五字段（error_code/error_msg/error_reason/error_suggestion/request_id）。
    # 落旧分支 COM-03 机制 + 保 sync_01 Flask app 结构（before/teardown 不变）。
    from werkzeug.exceptions import HTTPException as WerkzeugHTTPException

    @app.errorhandler(WerkzeugHTTPException)
    def _com03_http_error_handler(exc: WerkzeugHTTPException):
        from agent_builder.common.error_contract import factory as error_factory

        if exc.code and exc.code >= 500:
            logger.error(f"Flask HTTPException: code={exc.code}")
        else:
            logger.warning(f"Flask HTTPException: code={exc.code}")
        request_id = None
        try:
            from agent_builder.adapter.request_context_bridge import get_request_id

            request_id = get_request_id() or None
        except Exception:
            request_id = None
        descriptor = error_factory.from_http_status(
            exc.code or 500, request_id, exc)
        language = "zh-cn"
        try:
            language = request.headers.get("x-language", "zh-cn")
        except Exception:
            pass
        return error_factory.build_flask_error(descriptor, language)

    # DEF-06 §6.3：全局 Flask JiuWenBaseException Handler——未使用 @catch_exception
    # 装饰的普通 Flask 路由也遵守同一业务异常分类。
    @app.errorhandler(JiuWenBaseException)
    def _def06_flask_business_handler(exc: JiuWenBaseException):
        from agent_builder.common.error_contract import factory as error_factory

        logger.error(
            f"JiuWenBaseException: error_code={getattr(exc, 'error_code', -1)}",
            exc_info=True,
        )
        request_id = None
        try:
            from agent_builder.adapter.request_context_bridge import get_request_id

            request_id = get_request_id() or None
        except Exception:
            pass
        descriptor = error_factory.from_builder_exception(exc, request_id)
        language = "zh-cn"
        try:
            language = request.headers.get("x-language", "zh-cn")
        except Exception:
            pass
        return error_factory.build_flask_error(descriptor, language)

    # COM-03 §3.6：Flask unknown-exception handler——未被业务装饰器捕获的
    # 未知异常不再输出 Flask 默认 HTML 500，统一映射为标准五字段。
    @app.errorhandler(Exception)
    def _com03_flask_unknown_handler(exc: Exception):
        from agent_builder.common.error_contract import factory as error_factory

        logger.error(
            f"Flask unhandled exception: type={type(exc).__name__}",
            exc_info=True,
        )
        request_id = None
        try:
            from agent_builder.adapter.request_context_bridge import get_request_id

            request_id = get_request_id() or None
        except Exception:
            pass
        descriptor = error_factory.from_internal(exc, request_id)
        language = "zh-cn"
        try:
            language = request.headers.get("x-language", "zh-cn")
        except Exception:
            pass
        return error_factory.build_flask_error(descriptor, language)
    return app


def _establish_inbound_context():
    """COM-05 Flask 入口：mounted 形态桥接外层 FastAPI，direct 形态独立选值+建 token。

    mounted（外层 FastAPI 已建立 source=FASTAPI_MOUNT）：直接 return，上下文与
    trace session 由外层 FastAPI 中间件随 WSGI 线程上下文继承，外层 finally 重置。
    direct（source=NONE，Flask 独立运行）：select_ids 选值 + source=FLASK_DIRECT
    + 原子双 token 存 g（Flask 请求作用域），teardown 逆序恢复。
    """
    from flask import g, request
    from agent_builder.adapter.logger_bridge import set_session_id
    from agent_builder.adapter.request_context_bridge import (
        ContextSource,
        RequestContext,
        _request_ctx,
    )
    from agent_builder.serve.common.inbound_context import (
        apply_platform_headers,
        select_ids,
    )

    current = _request_ctx.get()
    if current.source == ContextSource.FASTAPI_MOUNT:
        # mounted：外层 FastAPI 已建立上下文，桥接不二次建立
        return

    # direct：独立选值 + 建立双 token
    request_id, trace_id, illegal_req, illegal_trace = select_ids(request.headers)
    ctx = RequestContext(request_id=request_id, source=ContextSource.FLASK_DIRECT)
    request_token = _request_ctx.set(ctx)
    try:
        trace_token = set_session_id(trace_id)
    except Exception:
        _request_ctx.reset(request_token)
        raise
    # token 存 g（Flask 请求作用域），teardown 逆序恢复
    g._com05_request_token = request_token
    g._com05_trace_token = trace_token

    if illegal_req:
        logger.warning(f"header X-Request-Id is illegal; regenerated request_id={request_id}")
    if illegal_trace:
        logger.warning(f"header TraceID is illegal; fell back to trace_id={trace_id}")

    # token 有效期内补充分仓（平台 + 客户 header）
    apply_platform_headers(ctx, request.headers)
    ctx.customer_headers = _capture_flask_customer_headers()


def _teardown_inbound_context(exc=None):
    """COM-05 Flask teardown：LIFO 逆序恢复 g 中存的 token（mounted 不存→跳过）。"""
    from flask import g
    from agent_builder.adapter.logger_bridge import reset_session_id
    from agent_builder.adapter.request_context_bridge import _request_ctx

    trace_token = getattr(g, "_com05_trace_token", None)
    request_token = getattr(g, "_com05_request_token", None)
    try:
        if trace_token is not None:
            reset_session_id(trace_token)
    finally:
        if request_token is not None:
            _request_ctx.reset(request_token)


def _capture_flask_customer_headers() -> dict:
    """Flask 侧按白名单捕获客户 header（cust-*，不含 x-auth-token）。"""
    try:
        from common_utils.customer_header import get_capture_keys, get_config
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[customer-header] customer_header package unavailable, skip: {e}")
        return {}
    cfg = get_config()
    if not cfg.enabled:
        return {}
    result: dict = {}
    for name in get_capture_keys():
        value = request.headers.get(name) or request.headers.get(name.lower())
        if value:
            result[name] = value
    return result


class ServerApp:
    """agent_builder server"""

    def __init__(
        self,
        server_config_path=None,
        framework_config_path=None,
        default_server_config="",
        default_framework_config="",
    ):
        # Initialize framework config (replaces JiuWen.init())
        if server_config_path and os.path.isfile(server_config_path):
            self.server_config_path = server_config_path
        else:
            self.server_config_path = default_server_config
        if framework_config_path and os.path.isfile(framework_config_path):
            self.framework_config_path = framework_config_path
        else:
            self.framework_config_path = default_framework_config
        self.init_framework_config()
        self.server_config = self.load_server_config()
        self.host, self.port = extract_host_and_port(config=self.server_config)
        self.tls_config = self.server_config.get("tls")
        self.init_sts_config()
        self.init_redis()
        self.http_ssl_context = (
            create_context(self.tls_config) if self.server_config.get("https") else None
        )
        self.app = self.instance_app()

    @staticmethod
    def init_sts_config():
        """init sts config"""
        try:
            service = os.environ.get("STS_SERVICE")
            micro_service = os.environ.get("STS_MICROSERVICE")
            req_domain_url = os.environ.get("STS_SERVICE_DOMAIN")
            sts_init(
                service=service,
                micro_service=micro_service,
                sts_server_domain=req_domain_url,
            )
        except Exception as e:
            logger.warning(f"sts init failed: {str(e)}")

    @staticmethod
    def init_redis():
        """init redis client"""
        try:
            redis_mgr = RedisClientManager.get_instance()
            redis_mgr.init()
            if not redis_mgr.is_initialized:
                logger.warning(
                    "Redis client not initialized, please check REDIS_* configuration"
                )
            else:
                logger.info("Redis client initialized successfully")
        except Exception as e:
            logger.warning(f"Redis init failed: {str(e)}")

    def init_framework_config(self):
        """init framework config using local adapter"""
        load_yaml_config(cfg_file=self.framework_config_path)

    def load_server_config(self):
        """load server config using local adapter"""
        server_configs = load_config(config=self.server_config_path)
        env_to_config(yaml_cfg=server_configs)
        return server_configs

    def instance_app(self):
        """initial instance app"""
        connection_key = "connection"
        server_config_connection = self.server_config.get(connection_key)
        if (
            isinstance(server_config_connection, dict)
            and "host" not in server_config_connection
        ):
            self.server_config[connection_key]["host"] = self.host
        return instance_app(config=self.server_config)

    def get_app(self):
        """get app instance"""
        self.app.config.from_mapping(
            SECRET_KEY=secrets.token_bytes(64),  # 密钥设置为安全随机数
            MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 请求的消息主体和消息头的大小限制
            PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),  # 会话超时时间
        )
        return self.app

    def get_host_and_port(self):
        """get host and port info"""
        return self.host, self.port

    def __nat_of(self, nat_name: str, real):
        nat = self.server_config.get("nat") or dict()
        return nat.get(nat_name) or real
