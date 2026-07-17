#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""model_service.policy.invoke_with_strategy 单元测试。

对应 Java RuntimeModelServiceManager.chatCompletions 循环：MODEL 单次 / ROUTER 顺序 failover
+ 每模型 retry + 总 strategy_timeout + available/free gating。纯测，invoke_one 用 AsyncMock。
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from model_service.policy import invoke_with_strategy
from model_service.resolver import (
    InterfaceProtocol, ModelServiceBase, ModelServiceDetail, ModelServiceError,
    ModelStrategy, ProviderAuth, StrategyType,
)


def _detail(mid="m1", available=True):
    m = ModelServiceBase(
        id=mid, model_name="mm", api_url="u", provider_id="p",
        interface_protocol=InterfaceProtocol.OPENAI, project_id="0",
        workspace_id="w", auth_id="a",
    )
    a = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k"})
    return ModelServiceDetail(model=m, auth=a, available=available, is_free_model=False)


def _run(coro):
    return asyncio.run(coro)


def test_model_single_call():
    d = _detail()
    strat = ModelStrategy(type=StrategyType.MODEL, name="n", models=[d])
    invoke_one = AsyncMock(return_value="RESULT")
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert r == "RESULT"
    invoke_one.assert_called_once_with(d, False)


def test_router_first_success():
    d1 = _detail("m1")
    d2 = _detail("m2")
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1, d2], retry_count=0)
    invoke_one = AsyncMock(return_value="R1")
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert r == "R1"
    invoke_one.assert_called_once_with(d1, False)   # 第一个成功即停，不试 d2


def test_router_failover_to_second():
    d1 = _detail("m1")
    d2 = _detail("m2")
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1, d2], retry_count=0)
    invoke_one = AsyncMock(side_effect=[Exception("boom"), "R2"])
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert r == "R2"
    assert invoke_one.call_count == 2   # d1 失败 → d2 成功


def test_router_unavailable_skipped():
    d1 = _detail("m1", available=False)   # 跳过
    d2 = _detail("m2", available=True)
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1, d2], retry_count=0)
    invoke_one = AsyncMock(return_value="R2")
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert r == "R2"
    invoke_one.assert_called_once_with(d2, False)   # d1 跳过


def test_router_retry_within_model():
    d1 = _detail("m1")
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1], retry_count=2)
    invoke_one = AsyncMock(side_effect=[Exception("e1"), Exception("e2"), "R"])
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert r == "R"
    assert invoke_one.call_count == 3   # retry_count + 1


def test_router_all_unavailable_raises():
    d1 = _detail("m1", available=False)
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1])
    invoke_one = AsyncMock(return_value="X")
    with pytest.raises(ModelServiceError) as exc:
        _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert exc.value.code == "MD_MODEL_SERVICE_NOT_AVAILABLE"
    invoke_one.assert_not_called()


def test_router_all_available_but_failed_raises():
    d1 = _detail("m1")
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1], retry_count=0)
    invoke_one = AsyncMock(side_effect=Exception("boom"))
    with pytest.raises(ModelServiceError) as exc:
        _run(invoke_with_strategy(strat, invoke_one, stream=False))
    assert exc.value.code == "MD_STRATEGY_FAILED"


# ── on_attempt 回调（审计归因到实际调用模型）─────────────────────────────

def test_model_single_on_attempt_reports_only_model():
    d = _detail("m1")
    strat = ModelStrategy(type=StrategyType.MODEL, name="n", models=[d])
    invoke_one = AsyncMock(return_value="R")
    attempted = []
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False,
                                  on_attempt=lambda det: attempted.append(det.model.id)))
    assert r == "R"
    assert attempted == ["m1"]


def test_router_failover_on_attempt_reports_winning_detail():
    """m1 失败→m2 成功时，on_attempt 序列为 [m1, m2]（最后指向命中的 m2，非 models[0]=m1）。"""
    d1 = _detail("m1")
    d2 = _detail("m2")
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1, d2], retry_count=0)
    invoke_one = AsyncMock(side_effect=[Exception("boom"), "R2"])
    attempted = []
    r = _run(invoke_with_strategy(strat, invoke_one, stream=False,
                                  on_attempt=lambda det: attempted.append(det.model.id)))
    assert r == "R2"
    assert attempted == ["m1", "m2"]


def test_router_all_unavailable_on_attempt_never_fires():
    d1 = _detail("m1", available=False)
    strat = ModelStrategy(type=StrategyType.ROUTER, name="n", models=[d1])
    invoke_one = AsyncMock(return_value="X")
    attempted = []
    with pytest.raises(ModelServiceError):
        _run(invoke_with_strategy(strat, invoke_one, stream=False,
                                  on_attempt=lambda det: attempted.append(det.model.id)))
    assert attempted == []   # 无可用模型不调 invoke_one，on_attempt 不触发
