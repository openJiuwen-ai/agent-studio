# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""uvicorn launcher for the agent_builder service (mirrors EIStart_base)."""

import os

import uvicorn

from agent_builder.adapter.config_bridge import settings


def _get_workers() -> int:
    """计算 uvicorn worker 数量。优先 GUNICORN_WORK_NUM；未设置回退 CPU+1；
    nginx 负载均衡时强制 1。"""
    if getattr(settings.server, "nginx_load_balancing", False):
        return 1
    configured = getattr(settings.server, "workers", None)
    if configured is not None:
        return configured
    return (os.cpu_count() or 1) + 1


def get_ssl_cert_config() -> dict:
    """读取 HTTPS 配置（参考 agent_runtime EIStart_base）。"""
    if not getattr(settings.server, "https", False):
        return {}
    password = (
        settings.server.tls_key_password.encode("utf-8")
        if getattr(settings.server, "tls_key_password", "")
        else None
    )
    return {
        "ssl_certfile": getattr(settings.server, "tls_cert_path", None),
        "ssl_keyfile": getattr(settings.server, "tls_key_path", None),
        "ssl_keyfile_password": password,
        "ssl_ciphers": getattr(settings.server, "tls_ciphers", None),
    }


def main():
    host = settings.server.host
    port = settings.server.port
    log_level = getattr(settings.server, "log_level", "info").lower()

    app_path = "agent_builder.serve.server_fastapi:app"
    ssl_config = get_ssl_cert_config()

    uvicorn.run(
        app_path,
        host=host,
        port=port,
        log_level=log_level,
        workers=_get_workers(),
        **ssl_config,
    )


if __name__ == "__main__":
    main()
