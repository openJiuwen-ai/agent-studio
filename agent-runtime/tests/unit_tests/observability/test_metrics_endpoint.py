# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_runtime.observability.metrics import metrics_router, record_http_request


def test_metrics_endpoint_returns_prometheus_text():
    app = FastAPI()
    app.include_router(metrics_router)
    client = TestClient(app)
    record_http_request("runtime", "GET", 200)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "studio_http_requests_total" in body
    assert "# HELP" in body or "TYPE" in body
