# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Prometheus /metrics endpoint helpers (#1659 / #1727, 3-8-1)."""

from __future__ import annotations

from fastapi import APIRouter, Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
except ImportError:  # pragma: no cover — optional until dependency installed
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    Counter = None  # type: ignore[misc, assignment]
    generate_latest = None  # type: ignore[misc, assignment]

metrics_router = APIRouter(tags=["metrics"])

_HTTP_REQUESTS = (
    Counter(
        "studio_http_requests_total",
        "HTTP requests handled by this service",
        ["service", "method", "status"],
    )
    if Counter is not None
    else None
)


def record_http_request(service: str, method: str, status: int) -> None:
    if _HTTP_REQUESTS is None:
        return
    _HTTP_REQUESTS.labels(service=service, method=method, status=str(status)).inc()


@metrics_router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Expose Prometheus text exposition format."""
    if generate_latest is None:
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain; charset=utf-8",
            status_code=503,
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
