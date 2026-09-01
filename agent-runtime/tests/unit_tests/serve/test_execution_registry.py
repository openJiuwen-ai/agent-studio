# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ExecutionRegistry 单元测试：进程内 task 映射 + Redis 双层行为（REQ-2026-002 终止接口）。"""

# pylint: disable=no-self-use

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.serve.execution_registry import (
    CANCEL_CHANNEL,
    EXEC_TTL_SECONDS,
    ExecutionRegistry,
    get_execution_registry,
    reset_execution_registry,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """每个用例前后重置进程内单例，避免跨用例串状态。"""
    reset_execution_registry()
    yield
    reset_execution_registry()


def _make_redis() -> MagicMock:
    """构造全 AsyncMock 的异步 Redis 客户端（decode_responses=False 语义：返回 bytes）。"""
    client = MagicMock()
    client.hset = AsyncMock()
    client.expire = AsyncMock()
    client.set = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.delete = AsyncMock()
    client.publish = AsyncMock()
    client.exists = AsyncMock(return_value=0)
    client.hgetall = AsyncMock(return_value={})
    return client


def _patch_redis(client):
    """registry._redis() 为函数内 lazy import，必须 patch common_utils 模块命名空间。"""
    return patch("common_utils.redis_manager.get_redis_client", return_value=client)


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_writes_local_and_redis(self):
        client = _make_redis()
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(0))

        with _patch_redis(client):
            await registry.register(
                "conv-1", task, execution_id="exec-1",
                project_id="proj-1", agent_id="agent-1", user_id="user-1",
            )

        assert registry._records["conv-1"].task is task  # noqa: SLF001 进程内映射写入
        client.hset.assert_awaited_once_with(
            "exec:conv-1",
            mapping={
                "instance_id": "single",
                "project_id": "proj-1",
                "agent_id": "agent-1",
                "user_id": "user-1",
            },
        )
        client.expire.assert_awaited_once_with("exec:conv-1", EXEC_TTL_SECONDS)
        client.set.assert_awaited_once_with("cancel:conv-1", "false", ex=EXEC_TTL_SECONDS)

    @pytest.mark.asyncio
    async def test_register_empty_conversation_skipped(self):
        client = _make_redis()
        registry = ExecutionRegistry()

        with _patch_redis(client):
            await registry.register("", asyncio.create_task(asyncio.sleep(0)))

        client.hset.assert_not_awaited()


class TestRegistrationQuery:
    @pytest.mark.asyncio
    async def test_get_registration_decodes_bytes(self):
        client = _make_redis()
        client.hgetall = AsyncMock(
            return_value={
                b"instance_id": b"i-1",
                b"project_id": b"proj-1",
                b"agent_id": b"agent-1",
                b"user_id": b"user-1",
            }
        )
        registry = ExecutionRegistry()

        with _patch_redis(client):
            reg = await registry.get_registration("conv-1")

        assert reg == {
            "instance_id": "i-1",
            "project_id": "proj-1",
            "agent_id": "agent-1",
            "user_id": "user-1",
        }

    @pytest.mark.asyncio
    async def test_get_registration_empty_when_absent(self):
        registry = ExecutionRegistry()
        with _patch_redis(_make_redis()):
            assert await registry.get_registration("conv-x") == {}


class TestCancelMark:
    @pytest.mark.asyncio
    async def test_mark_cancelled_sets_flag_and_publishes(self):
        client = _make_redis()
        registry = ExecutionRegistry()

        with _patch_redis(client):
            await registry.mark_cancelled("conv-1")

        client.set.assert_awaited_once_with("cancel:conv-1", "true", ex=EXEC_TTL_SECONDS)
        client.publish.assert_awaited_once_with(CANCEL_CHANNEL, "conv-1")

    @pytest.mark.asyncio
    async def test_is_cancelled_bytes_semantics(self):
        registry = ExecutionRegistry()
        client = _make_redis()

        for raw, expected in [(b"true", True), (b"false", False), (None, False)]:
            client.get = AsyncMock(return_value=raw)
            with _patch_redis(client):
                assert await registry.is_cancelled("conv-1") is expected

        # 非 bytes 客户端（decode_responses=True 场景）兼容
        client.get = AsyncMock(return_value="true")
        with _patch_redis(client):
            assert await registry.is_cancelled("conv-1") is True

    @pytest.mark.asyncio
    async def test_clear_cancelled_deletes_flag(self):
        client = _make_redis()
        registry = ExecutionRegistry()

        with _patch_redis(client):
            await registry.clear_cancelled("conv-1")

        client.delete.assert_awaited_once_with("cancel:conv-1")


class TestUnregister:
    @pytest.mark.asyncio
    async def test_unregister_removes_local_and_redis(self):
        client = _make_redis()
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(0))

        with _patch_redis(client):
            await registry.register("conv-1", task)
            await registry.unregister("conv-1", task=task)

        assert "conv-1" not in registry._records  # noqa: SLF001
        client.delete.assert_awaited_once_with("exec:conv-1")  # cancel 标记不随注销删除

    @pytest.mark.asyncio
    async def test_unregister_keeps_cancel_flag_for_resume(self):
        """挂起场景：先置标记后注销 → 标记留存至恢复路径消费（US3）。"""
        client = _make_redis()
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(0))

        with _patch_redis(client):
            await registry.register("conv-1", task)
            await registry.mark_cancelled("conv-1")
            await registry.unregister("conv-1", task=task)

        # 注销只删注册键（标记留存语义由 fakeredis 集成测试验证，AsyncMock 无状态）
        client.delete.assert_awaited_once_with("exec:conv-1")

    @pytest.mark.asyncio
    async def test_unregister_keeps_new_execution_for_stale_task(self):
        """旧流 finally 晚到时不得误删新执行的注册（同会话二次执行竞态保护）。"""
        client = _make_redis()
        registry = ExecutionRegistry()
        old_task = asyncio.create_task(asyncio.sleep(0))
        new_task = asyncio.create_task(asyncio.sleep(0))

        with _patch_redis(client):
            await registry.register("conv-1", old_task)
            await registry.register("conv-1", new_task)
            await registry.unregister("conv-1", task=old_task)

        assert registry._records["conv-1"].task is new_task  # noqa: SLF001
        client.delete.assert_not_awaited()


class TestLocalCancel:
    @pytest.mark.asyncio
    async def test_cancel_local_cancels_running_task_once(self):
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(10))

        with _patch_redis(_make_redis()):
            await registry.register("conv-1", task)
            first = await registry.cancel_local("conv-1")

        assert first is True
        await asyncio.sleep(0)  # 让 cancel 生效
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_cancel_local_ignores_finished_task(self):
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(0))
        await asyncio.sleep(0.01)  # 等 task 完成

        with _patch_redis(_make_redis()):
            await registry.register("conv-1", task)
            result = await registry.cancel_local("conv-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_local_unknown_conversation(self):
        registry = ExecutionRegistry()
        with _patch_redis(_make_redis()):
            assert await registry.cancel_local("conv-none") is False


class TestSubscriber:
    @staticmethod
    def _make_pubsub(messages):
        pubsub = MagicMock()
        pubsub.subscribe = AsyncMock()
        pubsub.unsubscribe = AsyncMock()
        pubsub.aclose = AsyncMock()

        async def _listen():
            for message in messages:
                yield message

        pubsub.listen = lambda: _listen()
        return pubsub

    @pytest.mark.asyncio
    async def test_subscriber_cancels_local_on_broadcast(self):
        client = _make_redis()
        pubsub = self._make_pubsub(
            [
                {"type": "subscribe", "channel": CANCEL_CHANNEL.encode()},
                {"type": "message", "channel": CANCEL_CHANNEL.encode(), "data": b"conv-1"},
            ]
        )
        client.pubsub = MagicMock(return_value=pubsub)
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(10))

        with _patch_redis(client):
            await registry.register("conv-1", task)
            await registry.subscribe_runtime_cancel()

        await asyncio.sleep(0)
        assert task.canceling if hasattr(task, "canceling") else True
        assert task.cancelled() or task.done()
        pubsub.unsubscribe.assert_awaited_once_with(CANCEL_CHANNEL)
        pubsub.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_subscriber_ignores_unknown_conversation(self):
        client = _make_redis()
        pubsub = self._make_pubsub(
            [{"type": "message", "channel": CANCEL_CHANNEL.encode(), "data": b"conv-none"}]
        )
        client.pubsub = MagicMock(return_value=pubsub)
        registry = ExecutionRegistry()

        with _patch_redis(client):
            await registry.subscribe_runtime_cancel()  # 不抛错即通过

        pubsub.unsubscribe.assert_awaited_once_with(CANCEL_CHANNEL)


class TestSingleton:
    def test_get_execution_registry_returns_same_instance(self):
        assert get_execution_registry() is get_execution_registry()
