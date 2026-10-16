# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.policy (audit / alarm / invoke_with_strategy)."""

import asyncio

import pytest

from model_service.policy import AuditLog, alarm, invoke_with_strategy, record_audit
from model_service.resolver import (
    ModelServiceDetail,
    ModelServiceError,
    ModelServiceBase,
    ModelStrategy,
    ProviderAuth,
    StrategyType,
    InterfaceProtocol,
)


def _detail(model_id="m1", available=True, is_free=False):
    model = ModelServiceBase(
        id=model_id,
        model_name=f"model-{model_id}",
        api_url="http://x/v1",
        provider_id="prov",
        interface_protocol=InterfaceProtocol.OPENAI,
        project_id="p",
        workspace_id="w",
        auth_id="a",
    )
    auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k"})
    return ModelServiceDetail(model=model, auth=auth, available=available, is_free_model=is_free)


class TestAuditLog:
    @staticmethod
    def test_dataclass_fields():
        log = AuditLog(model_id="m", model_name="n", api_url="u", stream=False,
                       status="success", duration_ms=1, project_id="p",
                       workspace_id="w", auth_id="a", provider_id="prov")
        assert log.model_id == "m"
        assert log.prompt_tokens is None

    @staticmethod
    def test_record_audit_does_not_raise():
        log = AuditLog(model_id="m", model_name="n", api_url="u", stream=False,
                       status="success", duration_ms=1, project_id="p",
                       workspace_id="w", auth_id="a", provider_id="prov")
        record_audit(log)

    @staticmethod
    def test_alarm_does_not_raise():
        alarm("LLM", "res", "cause")


class TestInvokeModelStrategy:
    @staticmethod
    def test_model_strategy_single_invoke():
        async def invoke_one(detail, stream):
            return f"result-{detail.model.id}"

        strategy = ModelStrategy(type=StrategyType.MODEL, name="m", models=[_detail()])

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        assert asyncio.run(_run()) == "result-m1"

    @staticmethod
    def test_model_strategy_passes_stream():
        captured = {}

        async def invoke_one(detail, stream):
            captured["stream"] = stream
            return "ok"

        strategy = ModelStrategy(type=StrategyType.MODEL, name="m", models=[_detail()])

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=True)

        assert asyncio.run(_run()) == "ok"
        assert captured["stream"] is True

    @staticmethod
    def test_model_strategy_on_attempt_called():
        attempts = []

        def on_attempt(detail):
            attempts.append(detail.model.id)

        async def invoke_one(detail, stream):
            return "ok"

        strategy = ModelStrategy(type=StrategyType.MODEL, name="m", models=[_detail()])

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False, on_attempt=on_attempt)

        asyncio.run(_run())
        assert attempts == ["m1"]


class TestRouterStrategy:
    @staticmethod
    def test_router_first_model_success():
        order = []

        async def invoke_one(detail, stream):
            order.append(detail.model.id)
            return "ok"

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1"), _detail("m2")],
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        assert asyncio.run(_run()) == "ok"
        assert order == ["m1"]

    @staticmethod
    def test_router_failover_to_second():
        order = []

        async def invoke_one(detail, stream):
            order.append(detail.model.id)
            if detail.model.id == "m1":
                raise RuntimeError("fail m1")
            return "ok-m2"

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1"), _detail("m2")],
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        assert asyncio.run(_run()) == "ok-m2"
        assert order == ["m1", "m2"]

    @staticmethod
    def test_router_retry_count():
        order = []

        async def invoke_one(detail, stream):
            order.append(detail.model.id)
            raise RuntimeError("always fail")

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1")], retry_count=2,
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_STRATEGY_FAILED"
        # retry_count=2 → 3 次尝试。
        assert order == ["m1", "m1", "m1"]

    @staticmethod
    def test_router_skips_unavailable_nonfree():
        order = []

        async def invoke_one(detail, stream):
            order.append(detail.model.id)
            return "ok"

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1", available=False), _detail("m2", available=True)],
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        assert asyncio.run(_run()) == "ok"
        assert order == ["m2"]

    @staticmethod
    def test_router_free_model_always_tried():
        order = []

        async def invoke_one(detail, stream):
            order.append(detail.model.id)
            return "ok"

        # free model 即使 available=False 也尝试。
        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1", available=False, is_free=True)],
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        assert asyncio.run(_run()) == "ok"
        assert order == ["m1"]

    @staticmethod
    def test_router_no_available_model():
        async def invoke_one(detail, stream):
            return "ok"

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1", available=False)],
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_MODEL_SERVICE_NOT_AVAILABLE"

    @staticmethod
    def test_router_timeout(monkeypatch):
        import model_service.policy as policy_mod

        async def invoke_one(detail, stream):
            raise RuntimeError("slow")

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1")], strategy_timeout_ms=600_000,
        )

        # 每次调用 monotonic 递增 1000 秒，使 begin 之后的第一次超时检查即触发。
        counter = {"v": 0.0}

        def _monotonic():
            counter["v"] += 1000.0
            return counter["v"]

        monkeypatch.setattr(policy_mod.time, "monotonic", _monotonic)

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_STRATEGY_TIMEOUT"

    @staticmethod
    def test_router_on_attempt_tracks_actual_detail():
        attempts = []

        def on_attempt(detail):
            attempts.append(detail.model.id)

        async def invoke_one(detail, stream):
            if detail.model.id == "m1":
                raise RuntimeError("fail")
            return "ok"

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1"), _detail("m2")],
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False, on_attempt=on_attempt)

        asyncio.run(_run())
        assert attempts == ["m1", "m2"]

    @staticmethod
    def test_negative_retry_count_treated_as_zero():
        order = []

        async def invoke_one(detail, stream):
            order.append(detail.model.id)
            raise RuntimeError("fail")

        strategy = ModelStrategy(
            type=StrategyType.ROUTER, name="r",
            models=[_detail("m1")], retry_count=-5,
        )

        async def _run():
            return await invoke_with_strategy(strategy, invoke_one, stream=False)

        with pytest.raises(ModelServiceError):
            asyncio.run(_run())
        # retry_count 钳制为 0 → 仅 1 次尝试。
        assert order == ["m1"]
