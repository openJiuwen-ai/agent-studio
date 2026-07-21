#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.

"""
general server for agent_builder services

Initialization uses local adapter layer instead of jiuwen.
"""

import os
import secrets
from datetime import timedelta

from agent_builder.adapter.exception_bridge import JiuWenException
from agent_builder.adapter.init_server import load_yaml_config, env_to_config
from agent_builder.adapter.redis_bridge import RedisClientManager
from agent_builder.common.logging.base import set_thread_session, logger
from agent_builder.common.security.sts_service import sts_init
from agent_builder.serve.apis.mmapo import mmapo_app
from agent_builder.serve.apis.prompt import prompt_manage_app
from agent_builder.serve.common.ssl_ctx import create_context
from agent_builder.serve.config import load_config
from flask import Flask, request

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

    app.before_request(_set_trace_id_from_request)
    return app


def _set_trace_id_from_request():
    """Get TraceID from header and set it to thread-local for every request."""
    trace_id = request.headers.get("TraceID", "")
    set_thread_session(trace_id)


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
