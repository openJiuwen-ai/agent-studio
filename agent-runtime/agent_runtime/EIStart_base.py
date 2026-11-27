# pylint: disable=huawei-invalid-name
# Keep this legacy module name compatible with the EIStart.py bootstrap entrypoint.
import asyncio
import logging

import uvicorn

from agent_runtime.common import settings
from agent_runtime.common.uvicron_log_cfg import UvicornLogConfig

_logger = logging.getLogger(__name__)


def _get_workers() -> int:
    """返回 uvicorn worker 数量；nginx 负载均衡时强制单 worker。"""
    if settings.server.nginx_load_balancing:
        return 1
    return settings.server.workers


def get_ssl_cert_config() -> dict:
    """读取 HTTPS 相关配置（参考旧版 agentBuilder-engine）"""
    if not settings.server.https:
        return {}

    password = (
        settings.server.tls_key_password.encode("utf-8")
        if settings.server.tls_key_password
        else None
    )

    return {
        "ssl_certfile": settings.server.tls_cert_path,
        "ssl_keyfile": settings.server.tls_key_path,
        "ssl_keyfile_password": password,
        "ssl_ciphers": settings.server.tls_ciphers,
    }


def main(with_adapter: bool = False, adapter_port: int = 31016):
    host = settings.server.host
    port = settings.server.port
    log_level = settings.server.log_level.lower()

    app_path = "agent_runtime.serve.server:app"

    log_config_instance = UvicornLogConfig(log_level=log_level)

    # 获取 SSL 配置
    ssl_config = get_ssl_cert_config()

    if with_adapter:
        _run_with_adapter(host, port, adapter_port, app_path, log_level,
                          log_config_instance, ssl_config)
    else:
        uvicorn.run(
            app_path,
            host=host,
            port=port,
            log_level=log_level,
            log_config=log_config_instance.to_dict(),
            workers=_get_workers(),
            **ssl_config,
        )


def _run_with_adapter(host, port, adapter_port, app_path, log_level,
                      log_config_instance, ssl_config):
    """启动 uvicorn + TCP 适配层。

    uvicorn 监听 port（原始端口，不变），adapter 监听 adapter_port。
    RDC 注册地址应指向 adapter_port。

    adapter↔uvicorn 为明文 TCP，因此 adapter 模式下强制不启用 TLS。
    h2c 问题仅存在于明文 HTTP 场景；若启用 HTTPS，gateway 走 h2（over TLS），
    不存在 h2c 升级问题，无需 adapter。
    """
    from agent_runtime.serve.a2a_adapter import start_adapter

    if ssl_config:
        _logger.warning(
            "HTTPS enabled but --with-adapter also set; adapter speaks plain TCP "
            "to uvicorn, forcing TLS off for uvicorn. If HTTPS is required, "
            "do not use --with-adapter (h2c issue does not apply under TLS)."
        )

    config = uvicorn.Config(
        app_path,
        host=host,
        port=port,
        log_level=log_level,
        log_config=log_config_instance.to_dict(),
        workers=1,  # adapter 模式强制单 worker
    )
    server = uvicorn.Server(config)

    async def _run_both():
        # 并行启动 uvicorn 和 adapter
        await asyncio.gather(
            server.serve(),
            start_adapter(host, adapter_port, host, port),
        )

    _logger.info("Starting uvicorn on %s:%s + adapter on %s:%s",
                 host, port, host, adapter_port)
    asyncio.run(_run_both())


if __name__ == "__main__":
    main()
