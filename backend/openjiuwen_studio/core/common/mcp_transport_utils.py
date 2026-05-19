# -*- coding: UTF-8 -*-
"""Helpers for MCP HTTP/SSE transports."""

from __future__ import annotations

import urllib.parse
from typing import Dict, Optional, Tuple


def merge_mcp_server_url_query_params(
    url: str,
    auth_query: Optional[Dict[str, str]] = None,
) -> Tuple[str, Dict[str, str]]:
    """
    Split an MCP server URL into a query-free base URL and merged query parameters.

    For SSE, the MCP SDK POSTs JSON-RPC to an endpoint URL advertised in the SSE stream
    (often ``/messages/?session_id=...``). That URL does not inherit the query string from
    the original ``/sse?...`` URL, so credentials must be supplied via
    ``McpServerConfig.auth_query_params`` (merged onto every httpx request by
    ``AuthHeaderAndQueryProvider``).

    Keys in ``auth_query`` override same-named keys parsed from ``url``'s query string.
    """
    if not isinstance(url, str):
        return "", dict(auth_query or {})
    trimmed = url.strip()
    if not trimmed:
        return "", dict(auth_query or {})

    parsed = urllib.parse.urlparse(trimmed)
    from_url = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    merged: Dict[str, str] = {**from_url, **(auth_query or {})}
    clean = urllib.parse.urlunparse(parsed._replace(query=""))
    return clean, merged
