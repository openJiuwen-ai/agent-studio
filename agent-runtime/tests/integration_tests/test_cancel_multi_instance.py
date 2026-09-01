# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""执行终止多实例集成测试（REQ-2026-002 VR-9 / US3）。

真实组件协作（ExecutionRegistry + Redis 双层状态 + pub/sub 广播 + cancel 端点 +
WorkflowRunner 恢复检测），Redis 用 fakeredis 替身（decode_responses=False 与生产一致）：
- VR-9 跨实例取消传播：实例 A 持有在飞执行并订阅广播，实例 B 受理 /cancel →
  runtime:cancel 广播 → A 本地 task.cancel 即时终止；
- US3 挂起恢复：挂起期间被取消 → 注册已注销但 cancel 标记留存 → 恢复路径检测命中
  → 清标记 → 从入口重跑（不恢复中断态）；
- 端到端：cancel 端点 → registry 校验/标记/广播 → 订阅回调 → 本地 task 取消全链。
"""

# pylint: disable=no-self-use

import asyncio
import time
from unittest.mock import patch

import fakeredis.aioredis
import pytest

from agent_runtime.runner.workflow_runner import WorkflowRunner
from agent_runtime.serve.apis.orchestration import cancel_execution
from agent_runtime.serve.execution_registry import (
    CANCEL_CHANNEL,
    ExecutionRegistry,
    reset_execution_registry,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_execution_registry()
    yield
    reset_execution_registry()


async def _wait_channel_subscribed(client, timeout: float = 2.0) -> bool:
    """轮询等待 runtime:cancel 频道出现订阅者（pub/sub 就绪判定）。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        channels = await client.pubsub_channels()
        if CANCEL_CHANNEL.encode("utf-8") in channels:
            return True
        await asyncio.sleep(0.02)
    return False


async def _stop_subscriber(sub_task) -> None:
    sub_task.cancel()
    try:
        await sub_task
    except asyncio.CancelledError:
        pass


def _make_request(headers: dict | None = None):
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/proj-1/conversations/conv-it/cancel",
        "headers": [
            (k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in (headers or {}).items()
        ],
        "query_string": b"",
    }
    from fastapi import Request

    return Request(scope)


class TestCrossInstanceCancelBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_cancels_task_on_holding_instance(self):
        """VR-9：执行在实例 A，/cancel 受理在实例 B → 广播 → A 本地 task 被取消。"""
        client = fakeredis.aioredis.FakeRedis(decode_responses=False)
        try:
            with patch("common_utils.redis_manager.get_redis_client", return_value=client):
                # 实例 A：注册在飞执行 + 启动广播订阅（对应 server lifespan 启动的订阅者）
                registry_a = ExecutionRegistry()
                running_task = asyncio.create_task(asyncio.sleep(30))
                await registry_a.register(
                    "conv-it-1", running_task,
                    execution_id="exec-a", project_id="proj-1", agent_id="agent-1", user_id="u-1",
                )
                sub_task = asyncio.create_task(registry_a.subscribe_runtime_cancel())
                assert await _wait_channel_subscribed(client), "pub/sub 订阅未就绪"

                # 实例 B：受理终止请求（不同 registry 实例 = 不同进程语义）
                registry_b = ExecutionRegistry()
                await registry_b.mark_cancelled("conv-it-1")

                # 广播到达实例 A → 本地 task 即时取消
                for _ in range(50):
                    if running_task.done():
                        break
                    await asyncio.sleep(0.02)
                assert running_task.cancelled() or running_task.done()

                # Redis 标记与注册状态对两实例一致可见
                assert await registry_b.is_cancelled("conv-it-1") is True
                assert await registry_b.get_registration("conv-it-1") != {}

                await _stop_subscriber(sub_task)
                running_task.cancel()
                try:
                    await running_task
                except asyncio.CancelledError:
                    pass
        finally:
            await client.flushall()
            await client.aclose()


class TestResumeAfterCancelDuringSuspend:
    @pytest.mark.asyncio
    async def test_suspend_cancel_flag_survives_unregister_and_cleared_on_resume(self):
        """US3：挂起期间被取消 → 注册注销后标记留存 → 恢复检测命中并清标记。"""
        client = fakeredis.aioredis.FakeRedis(decode_responses=False)
        try:
            with patch("common_utils.redis_manager.get_redis_client", return_value=client):
                registry = ExecutionRegistry()
                task = asyncio.create_task(asyncio.sleep(30))
                await registry.register(
                    "conv-it-2", task, execution_id="exec-1", project_id="proj-1"
                )

                # 挂起期间外部终止（流已注销，标记无人删 → 留存至恢复）
                await registry.mark_cancelled("conv-it-2")
                await registry.unregister("conv-it-2", task=task)

                assert await registry.get_registration("conv-it-2") == {}
                assert await registry.is_cancelled("conv-it-2") is True

                # 恢复路径（workflow_runner 直读 Redis，不 import serve 层）
                with patch(
                    "agent_runtime.runner.workflow_runner.get_redis_client",
                    return_value=client,
                ):
                    runner = WorkflowRunner.__new__(WorkflowRunner)
                    assert await runner._is_session_cancelled("conv-it-2") is True
                    await runner._clear_session_cancelled("conv-it-2")
                    assert await runner._is_session_cancelled("conv-it-2") is False
        finally:
            await client.flushall()
            await client.aclose()


class TestCancelEndpointEndToEnd:
    @pytest.mark.asyncio
    async def test_endpoint_to_local_task_cancel_full_chain(self):
        """端到端：端点受理 → 标记 + 广播 → 持有实例订阅回调 → 本地 task 取消。"""
        client = fakeredis.aioredis.FakeRedis(decode_responses=False)
        try:
            with patch("common_utils.redis_manager.get_redis_client", return_value=client):
                registry = ExecutionRegistry()
                running_task = asyncio.create_task(asyncio.sleep(30))
                await registry.register(
                    "conv-it-3", running_task,
                    execution_id="exec-1", project_id="proj-1", agent_id="agent-1", user_id="u-1",
                )
                sub_task = asyncio.create_task(registry.subscribe_runtime_cancel())
                assert await _wait_channel_subscribed(client), "pub/sub 订阅未就绪"

                resp = await cancel_execution(
                    _make_request({"x-language": "zh-cn"}),
                    project_id="proj-1",
                    conversation_id="conv-it-3",
                )

                assert resp.status_code == 200
                body = resp.body.decode("utf-8")
                assert '"cancelled":true' in body.replace(" ", "")
                assert '"running":true' in body.replace(" ", "")

                # 标记置位 + 广播 → 本地 task 取消（同实例协作式终止生效）
                assert await registry.is_cancelled("conv-it-3") is True
                for _ in range(50):
                    if running_task.done():
                        break
                    await asyncio.sleep(0.02)
                assert running_task.cancelled() or running_task.done()

                await _stop_subscriber(sub_task)
        finally:
            await client.flushall()
            await client.aclose()

    @pytest.mark.asyncio
    async def test_endpoint_403_project_mismatch_real_errorrsp(self):
        """端到端 403：project 不匹配 → 真实 _build_error_response（ErrorRsp i18n），标记不置位。"""
        client = fakeredis.aioredis.FakeRedis(decode_responses=False)
        try:
            with patch("common_utils.redis_manager.get_redis_client", return_value=client):
                registry = ExecutionRegistry()
                task = asyncio.create_task(asyncio.sleep(30))
                await registry.register(
                    "conv-it-4", task,
                    execution_id="exec-1", project_id="proj-other", agent_id="wf-1", user_id="u-1",
                )

                resp = await cancel_execution(
                    _make_request({"x-language": "zh-cn"}),
                    project_id="proj-1",
                    conversation_id="conv-it-4",
                )

                assert resp.status_code == 403
                assert await registry.is_cancelled("conv-it-4") is False  # 403 不置标记
                assert not task.done()  # 未被取消

                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        finally:
            await client.flushall()
            await client.aclose()
