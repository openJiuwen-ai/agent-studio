import os

import uvicorn

from agent_runtime.common import settings
from agent_runtime.common.uvicron_log_cfg import UvicornLogConfig


def _cgroup_cpu_count() -> int:
    """返回容器可见的 CPU 核数（cgroup 感知）。

    K8s 的 cpu request/limit 只设 CFS quota，并不改变 sched_getaffinity /
    os.cpu_count()，后两者在 64 核节点上的 4 核 Pod 里仍会返回 64，导致 uvicorn
    worker 超配、小内存容器 OOM。因此优先解析 cgroup v2/v1 的 CFS quota 换算核数，
    读不到再退回 affinity（≈ nproc）/ cpu_count。逻辑与 start_nginx_lb.sh 的
    _cpu_count 保持一致。
    """
    def _ceil_div(q: int, p: int) -> int:
        return (q + p - 1) // p

    # cgroup v2: /sys/fs/cgroup/cpu.max 形如 "quota period"，quota 为 "max" 表示无限制。
    try:
        with open("/sys/fs/cgroup/cpu.max", "r") as f:
            parts = f.read().split()
            if len(parts) == 2 and parts[0] != "max":
                quota, period = int(parts[0]), int(parts[1])
                if quota > 0 and period > 0:
                    return _ceil_div(quota, period)
    # OSError 已覆盖 FileNotFoundError；ValueError 处理内容非整数的解析失败。
    except (ValueError, OSError):
        pass

    # cgroup v1: cpu.cfs_quota_us / cpu.cfs_period_us，quota 为 -1 表示无限制。
    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", "r") as fq, \
             open("/sys/fs/cgroup/cpu/cpu.cfs_period_us", "r") as fp:
            quota, period = int(fq.read().strip()), int(fp.read().strip())
            if quota > 0 and period > 0:
                return _ceil_div(quota, period)
    except (ValueError, OSError):
        pass

    # 退回 affinity（≈ nproc），再退回 cpu_count。
    try:
        aff = len(os.sched_getaffinity(0))
        if aff > 0:
            return aff
    except (AttributeError, OSError):
        pass
    return os.cpu_count() or 1


def _get_workers() -> int:
    """计算 uvicorn worker 数量。

    优先使用环境变量 GUNICORN_WORK_NUM；未设置时回退到 cgroup 感知的容器 CPU 核数 + 1
    （非 LB 模式下不再用 os.cpu_count()，避免读到宿主机核数导致超配）。
    当 NGINX_LOAD_BALANCING=true 时强制返回 1，由 Nginx 管理多实例。
    """
    if settings.server.nginx_load_balancing:
        return 1
    configured = settings.server.workers
    if configured is not None:
        return configured
    return (_cgroup_cpu_count() or 1) + 1


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


def main():
    host = settings.server.host
    port = settings.server.port
    log_level = settings.server.log_level.lower()

    app_path = "agent_runtime.serve.server:app"

    log_config_instance = UvicornLogConfig(log_level=log_level)

    # 获取 SSL 配置
    ssl_config = get_ssl_cert_config()

    uvicorn.run(
        app_path,
        host=host,
        port=port,
        log_level=log_level,
        log_config=log_config_instance.to_dict(),
        workers=_get_workers(),
        **ssl_config,
    )


if __name__ == "__main__":
    main()
