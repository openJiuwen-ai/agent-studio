# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List

from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class FlaskProxyServer:
    """Flask-based implementation of IProxyServer that forwards HTTP requests
    to available backend LLM servers using round-robin random selection.
    """

    def __init__(self, llm_timeout_seconds: float):
        """Initialize the Flask proxy server and allocate an available port."""
        self.llm_timeout_seconds = llm_timeout_seconds
        self._backend_servers: List[str] = []

    def update_backend_servers(self, servers: List[str]) -> None:
        """Replace the backend server list with a new set of target servers.
        Input:
        servers: List[str] -- the endpoint list that provide rollout engine.
        """
        pass

    def update_endpoint(self, endpoint: str):
        """Initialize the proxy endpoint.
        Input:
        endpoint: str -- the rollout proxy endpoint.
        """
        pass

    def start(self):
        """Start the Flask API.Exposed endpoints:
        - GET  /health            : Service health check
        - GET  /v1/models         : OpenAI-compatible model list
        - *    /v1/*              : Proxy OpenAI API requests to backends
        - POST /proxy/backends    : Dynamically update backend servers
        """
        pass
