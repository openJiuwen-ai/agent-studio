"""CLI entry point for OLE server."""

import argparse

# 在 openjiuwen 导入之前应用 patch
from agent_runtime.patch import apply_patches
apply_patches()

from EIStart_base import main as start_server


def main():
    parser = argparse.ArgumentParser(description="Open AgentBuilder Engine (OLE) MVP")
    parser.add_argument("--host", default=None, help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Bind port")
    parser.add_argument("--log-level", default=None, help="Log level")
    parser.add_argument("--with-adapter", action="store_true",
                        help="Start HTTP/2 adapter in front of uvicorn (FEAT-131)")
    parser.add_argument("--adapter-port", type=int, default=31016,
                        help="Adapter listen port (default 31016, used with --with-adapter)")

    args = parser.parse_args()

    from agent_runtime.common import settings

    if args.host is not None:
        settings.server.host = args.host
    if args.port is not None:
        settings.server.port = args.port
    if args.log_level is not None:
        settings.server.log_level = args.log_level

    start_server(
        with_adapter=args.with_adapter,
        adapter_port=args.adapter_port,
    )


if __name__ == "__main__":
    main()
