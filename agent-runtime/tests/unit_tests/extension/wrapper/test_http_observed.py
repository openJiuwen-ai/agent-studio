# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""HttpObservedComponent / HttpObservedExecutable 单测。

核心不变量：业务失败（ok=false）只上报标记，结果与流程不受影响；
业务成功（ok=true）不产生额外上报；观测失败不得阻断业务返回。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjiuwen.core.workflow.components.tool.http import (
    HttpComponentConfig,
    HttpRequestParamConfig,
)
from openjiuwen.core.workflow.components.tool.http.http_request_component import (
    HTTPRequestExecutable,
)

from jiuwen.extension.workflow_node.http_observed import (
    HttpObservedComponent,
    HttpObservedExecutable,
)


def _make_executable() -> HttpObservedExecutable:
    config = HttpComponentConfig(
        request_params=HttpRequestParamConfig(url="http://example.com/api", method="GET")
    )
    return HttpObservedExecutable(config)


def _make_session() -> MagicMock:
    session = MagicMock()
    session.trace = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_failure_result_reports_business_error_and_keeps_result():
    """ok=false：上报 business_error 标记，且结果原样透传（不影响业务）。"""
    failure_result = {
        "statusCode": 500,
        "headers": {},
        "body": {"error": "server internal error"},
        "url": "http://example.com/api",
        "ok": False,
    }
    exe = _make_executable()
    session = _make_session()
    with patch.object(HTTPRequestExecutable, "invoke", new=AsyncMock(return_value=failure_result)):
        result = await exe.invoke({"query": "x"}, session, None)

    assert result == failure_result
    session.trace.assert_awaited_once()
    data = session.trace.await_args.args[0]
    biz = data["business_error"]
    assert biz["status_code"] == 500
    assert "server internal error" in biz["body"]


@pytest.mark.asyncio
async def test_success_result_does_not_report():
    """ok=true：正常业务结果不产生任何上报标记。"""
    success_result = {
        "statusCode": 200,
        "headers": {},
        "body": {"result": "ok"},
        "url": "http://example.com/api",
        "ok": True,
    }
    exe = _make_executable()
    session = _make_session()
    with patch.object(HTTPRequestExecutable, "invoke", new=AsyncMock(return_value=success_result)):
        result = await exe.invoke({"query": "x"}, session, None)

    assert result == success_result
    session.trace.assert_not_called()


@pytest.mark.asyncio
async def test_trace_failure_does_not_block_business():
    """观测上报失败（trace 抛异常）时，业务结果仍正常返回。"""
    failure_result = {"ok": False, "statusCode": 502, "headers": {}, "body": "bad gateway", "url": "u"}
    exe = _make_executable()
    session = MagicMock()
    session.trace = AsyncMock(side_effect=RuntimeError("report failed"))
    with patch.object(HTTPRequestExecutable, "invoke", new=AsyncMock(return_value=failure_result)):
        result = await exe.invoke({"query": "x"}, session, None)

    assert result == failure_result


def test_component_to_executable_returns_observed():
    """HttpObservedComponent 产出可观测执行体（类型正确）。"""
    comp = HttpObservedComponent(
        HttpComponentConfig(request_params=HttpRequestParamConfig(url="http://e.com", method="GET"))
    )
    assert isinstance(comp.to_executable(), HttpObservedExecutable)