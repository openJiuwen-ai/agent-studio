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
    RegistrationInfo,
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
                info=RegistrationInfo(
                    project_id="proj-1", agent_id="agent-1", user_id="user-1"
                ),
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
        # nx=True：仅当标记不存在时初始化 false，保留挂起期间 cancel 置位的 true（US3 恢复检测依赖）
        client.set.assert_awaited_once_with(
            "cancel:conv-1", "false", ex=EXEC_TTL_SECONDS, nx=True
        )

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
        """旧流 finally 晚到时不得误删新执行的本地注册（同会话二次执行竞态保护）。"""
        client = _make_redis()
        registry = ExecutionRegistry()
        old_task = asyncio.create_task(asyncio.sleep(0))
        new_task = asyncio.create_task(asyncio.sleep(0))

        with _patch_redis(client):
            await registry.register("conv-1", old_task)
            await registry.register("conv-1", new_task)
            await registry.unregister("conv-1", task=old_task)

        assert registry._records["conv-1"].task is new_task  # noqa: SLF001
        # stale task 在本地所有权校验即被拦截（早于 Redis 侧），delete 不应被调
        client.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unregister_keeps_redis_key_owned_by_other_instance(self):
        """跨实例晚删保护（检视④）：注册键已归其他实例时，本实例晚到的 finally
        不得删除它——否则新实例刚写入的注册（归属校验/取消数据源）被误删。
        """
        client = _make_redis()
        client.hgetall = AsyncMock(return_value={b"instance_id": b"i-other", b"project_id": b"p"})
        registry = ExecutionRegistry()

        with _patch_redis(client):
            await registry.unregister("conv-1")

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
        """pubsub mock：首轮 listen 吐出 messages；流断开后的重连轮抛 CancelledError
        （模拟 shutdown task.cancel），使订阅协程以取消语义退出、单测可 await 到返回。"""
        pubsub = MagicMock()
        pubsub.subscribe = AsyncMock()
        pubsub.unsubscribe = AsyncMock()
        pubsub.aclose = AsyncMock()

        async def _listen():
            for message in messages:
                yield message

        state = {"first": True}

        def _listen_call():
            if not state["first"]:

                async def _shutdown():
                    raise asyncio.CancelledError
                    yield  # pragma: no cover 使其成为 async generator

                return _shutdown()
            state["first"] = False
            return _listen()

        pubsub.listen = _listen_call
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

        with _patch_redis(client), \
             patch("agent_runtime.serve.execution_registry.SUBSCRIBER_RETRY_SECONDS", 0):
            await registry.register("conv-1", task)
            with pytest.raises(asyncio.CancelledError):
                await registry.subscribe_runtime_cancel()

        assert task.cancelled() or task.done()
        # 重连语义下每轮 finally 均清理连接，断言至少清理一次而非恰好一次
        assert pubsub.unsubscribe.await_count >= 1
        assert pubsub.aclose.await_count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_ignores_unknown_conversation(self):
        client = _make_redis()
        pubsub = self._make_pubsub(
            [{"type": "message", "channel": CANCEL_CHANNEL.encode(), "data": b"conv-none"}]
        )
        client.pubsub = MagicMock(return_value=pubsub)
        registry = ExecutionRegistry()

        with _patch_redis(client), \
             patch("agent_runtime.serve.execution_registry.SUBSCRIBER_RETRY_SECONDS", 0):
            with pytest.raises(asyncio.CancelledError):
                await registry.subscribe_runtime_cancel()

        assert pubsub.unsubscribe.await_count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_does_not_cancel_other_conversation(self):
        """路由隔离：广播仅命中目标会话，注册中的其他会话 task 不得被误取消。"""
        client = _make_redis()
        pubsub = self._make_pubsub(
            [{"type": "message", "channel": CANCEL_CHANNEL.encode(), "data": b"conv-2"}]
        )
        client.pubsub = MagicMock(return_value=pubsub)
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(10))

        with _patch_redis(client), \
             patch("agent_runtime.serve.execution_registry.SUBSCRIBER_RETRY_SECONDS", 0):
            await registry.register("conv-1", task)  # 广播目标是 conv-2
            with pytest.raises(asyncio.CancelledError):
                await registry.subscribe_runtime_cancel()

        assert not task.cancelled()  # conv-1 的在飞 task 不受 conv-2 广播影响
        task.cancel()  # 清理

    @pytest.mark.asyncio
    async def test_subscriber_resubscribes_after_connection_error(self):
        """断线自愈：listen 抛连接异常不终止订阅，退避后重连并处理后续广播。"""
        client = _make_redis()
        pubsub = MagicMock()
        pubsub.subscribe = AsyncMock()
        pubsub.unsubscribe = AsyncMock()
        pubsub.aclose = AsyncMock()

        async def _broken():
            raise ConnectionError("redis gone")
            yield  # pragma: no cover 使其成为 async generator

        async def _ok():
            yield {"type": "message", "channel": CANCEL_CHANNEL.encode(), "data": b"conv-1"}
            raise asyncio.CancelledError  # 处理完目标消息后模拟 shutdown

        calls = {"n": 0}

        def _listen_call():
            calls["n"] += 1
            return _broken() if calls["n"] == 1 else _ok()

        pubsub.listen = _listen_call
        client.pubsub = MagicMock(return_value=pubsub)
        registry = ExecutionRegistry()
        task = asyncio.create_task(asyncio.sleep(10))

        with _patch_redis(client), \
             patch("agent_runtime.serve.execution_registry.SUBSCRIBER_RETRY_SECONDS", 0):
            await registry.register("conv-1", task)
            with pytest.raises(asyncio.CancelledError):
                await registry.subscribe_runtime_cancel()

        assert calls["n"] == 2  # 第一轮断线，第二轮重连成功
        await asyncio.sleep(0)  # 让 task.cancel() 信号得到调度
        assert task.cancelled() or task.done()  # 重连后的广播仍完成了本地取消


class TestSingleton:
    def test_get_execution_registry_returns_same_instance(self):
        assert get_execution_registry() is get_execution_registry()
