"""CLI entry point for OLE server."""

import argparse
import os

# 在 openjiuwen 导入之前应用 patch
from agent_runtime.patch import apply_patches
apply_patches()

from EIStart_base import main as start_server


def main():
    parser = argparse.ArgumentParser(description="Open AgentBuilder Engine (OLE) MVP")
    parser.add_argument("--host", default=None, help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Bind port")
    parser.add_argument("--log-level", default=None, help="Log level")

    args = parser.parse_args()

    from agent_runtime.common import settings

    if args.host is not None:
        settings.server.host = args.host
    if args.port is not None:
        settings.server.port = args.port
    if args.log_level is not None:
        settings.server.log_level = args.log_level
        # 同步写回环境变量：legacy jiuwen logger（base.py）直读 os.environ 的
        # LOG_LEVEL，只写 settings 会造成 uvicorn/agent-core 与 legacy 级别分叉
        os.environ["LOG_LEVEL"] = args.log_level

    start_server()


if __name__ == "__main__":
    main()
