# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""CLI entry point for the agent_builder service."""

import argparse

from agent_builder.EIBuilder_base import main as start_server


def main():
    parser = argparse.ArgumentParser(
        description="agent_builder microservice (prompt/mmapo/n2l)"
    )
    parser.add_argument("--host", default=None, help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Bind port")
    parser.add_argument("--log-level", default=None, help="Log level")

    args = parser.parse_args()

    from agent_builder.adapter.config_bridge import settings

    if args.host is not None:
        settings.server.host = args.host
    if args.port is not None:
        settings.server.port = args.port
    if args.log_level is not None:
        # ServerSettings may not have log_level; set via env-style attr if present.
        if hasattr(settings.server, "log_level"):
            settings.server.log_level = args.log_level

    start_server()


if __name__ == "__main__":
    main()
