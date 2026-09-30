# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Tests for agent_runtime.common.background_task — fire-and-forget 后台任务工具。"""

import asyncio
import time
from unittest.mock import patch

import pytest

from agent_runtime.common import background_task
from agent_runtime.common.background_task import run_in_background, await_pending


class _FakeRedis:
    """内存 Redis：仅实现租约标记原语 hset/hdel/hgetall/expire。"""

    def __init__(self):
        self.store = {}

    async def hset(self, key, field, value):
        self.store.setdefault(key, {})[field] = value
        return 1

    async def hdel(self, key, *fields):
        entry = self.store.get(key)
        if entry is None:
            return 0
        removed = 0
        for field in fields:
            if entry.pop(field, None) is not None:
                removed += 1
        if not entry:
            self.store.pop(key, None)
        return removed

    async def hgetall(self, key):
        return dict(self.store.get(key, {}))

    async def expire(self, key, ttl):
        return True


class TestRunInBackground:
    """run_in_background 行为测试。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_executes_coroutine_and_discards_reference():
        """后台执行协程；完成后从强引用集合移除。"""
        done = asyncio.Event()

        async def work():
            done.set()

        task = run_in_background(work(), name="t-exec")
        assert isinstance(task, asyncio.Task)
        assert task in background_task._BACKGROUND_TASKS

        for _ in range(100):
            if done.is_set():
                break
            await asyncio.sleep(0.01)
        assert done.is_set()

        await task
        # done_callback 经 call_soon 调度，让出一次控制权后引用应被移除
        for _ in range(10):
            if task not in background_task._BACKGROUND_TASKS:
                break
            await asyncio.sleep(0)
        assert task not in background_task._BACKGROUND_TASKS

    @staticmethod
    def test_returns_none_without_running_loop():
        """无运行中事件循环时放弃执行、关闭协程并返回 None。"""

        async def work():
            pass

        coro = work()
        result = run_in_background(coro, name="t-noloop")
        assert result is None
        # 协程已被 close，避免 "coroutine was never awaited" 告警
        assert coro.cr_frame is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_logs_unexpected_exception():
        """协程异常逃逸时兜底记录 error 日志。"""

        async def boom():
            raise RuntimeError("boom")

        task = run_in_background(boom(), name="t-boom")
        with patch.object(background_task.workflow_logger, "error") as mock_error:
            with pytest.raises(RuntimeError):
                await task
            # done_callback 经 call_soon 调度，让出控制权触发
            for _ in range(10):
                if mock_error.called:
                    break
                await asyncio.sleep(0)
        assert mock_error.called

    @staticmethod
    @pytest.mark.asyncio
    async def test_survives_caller_cancellation():
        """后台任务不随调用方协程取消而取消（fire-and-forget 语义）。"""
        finished = asyncio.Event()

        async def work():
            await asyncio.sleep(0.05)
            finished.set()

        async def caller():
            run_in_background(work(), name="t-cancel")
            await asyncio.sleep(3600)

        caller_task = asyncio.create_task(caller())
        await asyncio.sleep(0)  # 让 caller 启动并创建后台任务
        caller_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller_task

        # 调用方已取消，后台任务仍应完成
        for _ in range(200):
            if finished.is_set():
                break
            await asyncio.sleep(0.01)
        assert finished.is_set()


class TestAwaitPending:
    """await_pending 有界 join 行为测试（含 wait_for+gather 陷阱回归防线）。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_join_waits_all_tracked_tasks():
        """join 等待 key 名下全部在飞任务完成后才返回。"""
        finished = []

        async def slow():
            await asyncio.sleep(0.2)
            finished.append("slow")

        async def fast():
            await asyncio.sleep(0.02)
            finished.append("fast")

        run_in_background(slow(), name="t-slow", track_key="conv-join")
        run_in_background(fast(), name="t-fast", track_key="conv-join")
        await await_pending("conv-join")
        assert set(finished) == {"fast", "slow"}

    @staticmethod
    @pytest.mark.asyncio
    async def test_empty_registry_returns_immediately():
        """key 无在飞任务时立即返回，无额外开销。"""
        loop = asyncio.get_running_loop()
        start = loop.time()
        await await_pending("conv-nonexistent")
        assert loop.time() - start < 0.05

    @staticmethod
    @pytest.mark.asyncio
    async def test_timeout_proceeds_and_keeps_tasks_alive():
        """超时后放行并记 error；后台任务必须存活未被取消（wait_for 陷阱防线）。"""

        async def hang():
            await asyncio.sleep(30)

        task = run_in_background(hang(), name="t-hang", track_key="conv-timeout")
        loop = asyncio.get_running_loop()
        start = loop.time()
        with patch.object(background_task.workflow_logger, "error") as mock_error:
            await await_pending("conv-timeout", timeout=0.05)
        assert loop.time() - start < 1.0
        assert mock_error.called
        # 关键断言：超时不得取消后台任务（wait_for+gather 实现会在此失败）
        assert not task.cancelled() and not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @staticmethod
    @pytest.mark.asyncio
    async def test_registry_cleaned_after_completion():
        """任务完成后 done_callback 清理 track_key 注册表项。"""

        async def quick():
            await asyncio.sleep(0.01)

        run_in_background(quick(), name="t-quick", track_key="conv-clean")
        await await_pending("conv-clean")
        for _ in range(20):
            if "conv-clean" not in background_task._TRACKED_TASKS:
                break
            await asyncio.sleep(0)
        assert "conv-clean" not in background_task._TRACKED_TASKS

    @staticmethod
    @pytest.mark.asyncio
    async def test_task_exception_does_not_break_join():
        """单任务异常不从 await_pending 传播（异常已由 done_callback 记录）。"""

        async def boom():
            raise RuntimeError("persist failed")

        async def ok():
            await asyncio.sleep(0.01)

        run_in_background(boom(), name="t-bad", track_key="conv-exc")
        run_in_background(ok(), name="t-good", track_key="conv-exc")
        await await_pending("conv-exc")

    @staticmethod
    @pytest.mark.asyncio
    async def test_caller_cancel_does_not_kill_tracked_tasks():
        """join 调用方被取消不传播取消到后台任务（下一轮断连场景防线）。"""

        async def slow_persist():
            await asyncio.sleep(30)

        task = run_in_background(
            slow_persist(), name="t-persist", track_key="conv-cancel"
        )

        async def next_turn_entry():
            await await_pending("conv-cancel", timeout=10)

        caller = asyncio.create_task(next_turn_entry())
        await asyncio.sleep(0.01)
        caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller
        await asyncio.sleep(0)
        # 关键断言：调用方取消仅中止 join 本身，后台落库任务继续执行
        assert not task.cancelled() and not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestRunInBackgroundTracked:
    """run_in_background_tracked 跨进程在飞租约行为。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_mark_before_schedule_unmark_on_done():
        """HSET 在调度返回前同步完成；任务结束后 HDEL，空 hash 自动删除。"""
        fake = _FakeRedis()
        started = asyncio.Event()
        release = asyncio.Event()

        async def work():
            started.set()
            await release.wait()

        key = f"{background_task.INFLIGHT_KEY_PREFIX}conv-tracked"
        with patch.object(background_task, "_get_redis", return_value=fake):
            task = await background_task.run_in_background_tracked(
                work(), name="t-tracked", track_key="conv-tracked")
            # HSET 严格先于调度返回（保证 finish 事件发出前标记已可见）
            assert len(fake.store[key]) == 1
            await started.wait()
            release.set()
            await task
        assert key not in fake.store

    @staticmethod
    @pytest.mark.asyncio
    async def test_without_track_key_degrades_to_plain():
        """track_key 为空时退化为 run_in_background，不触碰 Redis。"""
        fake = _FakeRedis()
        done = asyncio.Event()

        async def work():
            done.set()

        with patch.object(background_task, "_get_redis", return_value=fake):
            task = await background_task.run_in_background_tracked(
                work(), name="t-nokey")
        assert task is not None
        await task
        assert done.is_set()
        assert fake.store == {}

    @staticmethod
    @pytest.mark.asyncio
    async def test_redis_unavailable_still_schedules():
        """Redis 不可用时退化为仅进程内保护，任务照常执行。"""
        done = asyncio.Event()

        async def work():
            done.set()

        with patch.object(background_task, "_get_redis", return_value=None):
            task = await background_task.run_in_background_tracked(
                work(), name="t-noredis", track_key="conv-noredis")
        assert task is not None
        await task
        assert done.is_set()

    @staticmethod
    @pytest.mark.asyncio
    async def test_exception_in_coro_still_unmarks():
        """任务异常时 finally 仍执行 HDEL，租约不泄漏。"""
        fake = _FakeRedis()

        async def boom():
            raise RuntimeError("persist failed")

        with patch.object(background_task, "_get_redis", return_value=fake):
            task = await background_task.run_in_background_tracked(
                boom(), name="t-boom", track_key="conv-boom")
            with pytest.raises(RuntimeError):
                await task
        assert fake.store == {}


class TestCrossProcessJoin:
    """await_pending 跨进程（Redis 租约标记）轮询行为。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_waits_remote_inflight_lease():
        """他进程在飞标记存在时轮询等待，标记删除后返回。"""
        fake = _FakeRedis()
        key = f"{background_task.INFLIGHT_KEY_PREFIX}conv-remote"
        fake.store[key] = {"remote-task": str(time.time())}

        async def remote_finish():
            await asyncio.sleep(0.15)
            fake.store.pop(key, None)  # 模拟他进程 HDEL（空 hash 即删 key）

        with patch.object(background_task, "_get_redis", return_value=fake):
            remote = asyncio.create_task(remote_finish())
            loop = asyncio.get_running_loop()
            start = loop.time()
            await await_pending("conv-remote")
            elapsed = loop.time() - start
            await remote
        assert elapsed >= 0.1, "应等待远端租约标记清除后才返回"

    @staticmethod
    @pytest.mark.asyncio
    async def test_stale_lease_self_heals():
        """崩溃残留标记（龄期>STALE）被读侧清理并立即放行——活跃会话不再每轮白等 5s（检视意见2回归）。"""
        fake = _FakeRedis()
        key = f"{background_task.INFLIGHT_KEY_PREFIX}conv-stale"
        fake.store[key] = {
            "dead-task": str(
                time.time() - background_task.INFLIGHT_STALE_SECONDS - 5
            ),
        }

        with patch.object(background_task, "_get_redis", return_value=fake):
            loop = asyncio.get_running_loop()
            start = loop.time()
            await await_pending("conv-stale", timeout=5)
            elapsed = loop.time() - start
        assert elapsed < 0.5, "残留标记应按龄期识别并立即放行，不得等满超时"
        assert fake.store == {}, "残留 field 应被 HDEL 自愈"

    @staticmethod
    @pytest.mark.asyncio
    async def test_stale_cleaned_and_live_still_waited():
        """残留与新鲜标记并存：残留被清理，仍等待新鲜标记归零。"""
        fake = _FakeRedis()
        key = f"{background_task.INFLIGHT_KEY_PREFIX}conv-mixed"
        fake.store[key] = {
            "dead-task": str(
                time.time() - background_task.INFLIGHT_STALE_SECONDS - 5
            ),
            "live-task": str(time.time()),
        }

        async def remote_finish():
            await asyncio.sleep(0.1)
            fake.store[key].pop("live-task", None)

        with patch.object(background_task, "_get_redis", return_value=fake):
            remote = asyncio.create_task(remote_finish())
            loop = asyncio.get_running_loop()
            start = loop.time()
            await await_pending("conv-mixed", timeout=5)
            elapsed = loop.time() - start
            await remote
        assert elapsed >= 0.05, "应等待 live 标记清除"
        assert fake.store.get(key, {}) == {}

    @staticmethod
    @pytest.mark.asyncio
    async def test_remote_timeout_proceeds_with_error_log():
        """远端租约未超龄（任务确实仍在执行）时超时放行记 error，且不得误删 live 标记。"""
        fake = _FakeRedis()
        key = f"{background_task.INFLIGHT_KEY_PREFIX}conv-stuck"
        fake.store[key] = {"busy-task": str(time.time())}

        with patch.object(background_task, "_get_redis", return_value=fake):
            with patch.object(
                background_task.workflow_logger, "error"
            ) as mock_error:
                loop = asyncio.get_running_loop()
                start = loop.time()
                await await_pending("conv-stuck", timeout=0.2)
                elapsed = loop.time() - start
        assert 0.15 < elapsed < 1.0
        assert mock_error.called
        assert "busy-task" in fake.store.get(key, {}), "超时不得误删未超龄标记"

    @staticmethod
    @pytest.mark.asyncio
    async def test_redis_get_failure_degrades():
        """HGETALL 失败时降级为仅进程内 join，放行并记 warning。"""

        class _BrokenRedis:
            async def hgetall(self, key):
                raise ConnectionError("redis down")

        with patch.object(
            background_task, "_get_redis", return_value=_BrokenRedis()
        ):
            with patch.object(
                background_task.workflow_logger, "warning"
            ) as mock_warning:
                await await_pending("conv-broken", timeout=0.2)
        assert mock_warning.called

    @staticmethod
    @pytest.mark.asyncio
    async def test_corrupted_field_cleaned_and_proceeds():
        """标记值损坏（非数值）时按残留清理并立即放行，不阻塞。"""
        fake = _FakeRedis()
        key = f"{background_task.INFLIGHT_KEY_PREFIX}conv-bad"
        fake.store[key] = {"bad-task": "garbage"}

        with patch.object(background_task, "_get_redis", return_value=fake):
            loop = asyncio.get_running_loop()
            start = loop.time()
            await await_pending("conv-bad", timeout=5)
            elapsed = loop.time() - start
        assert elapsed < 0.5
        assert fake.store == {}, "损坏 field 应被清理"


class TestBackgroundingEnabled:
    """PERSIST_BACKGROUND_ENABLE 平台级回滚开关解析。"""

    @staticmethod
    def test_default_enabled(monkeypatch):
        """默认开启（未设置环境变量）。"""
        monkeypatch.delenv("PERSIST_BACKGROUND_ENABLE", raising=False)
        assert background_task.backgrounding_enabled() is True

    @staticmethod
    def test_disabled_values(monkeypatch):
        """false/0/no（大小写与空白不敏感）关闭后台化。"""
        for value in ("false", "False", " FALSE ", "0", "no"):
            monkeypatch.setenv("PERSIST_BACKGROUND_ENABLE", value)
            assert background_task.backgrounding_enabled() is False, value

    @staticmethod
    def test_enabled_values(monkeypatch):
        """true/1/yes 及其他非关闭值一律视为开启。"""
        for value in ("true", "1", "yes", "anything"):
            monkeypatch.setenv("PERSIST_BACKGROUND_ENABLE", value)
            assert background_task.backgrounding_enabled() is True, value


class TestInflightPairing:
    """HSET/HDEL 配对（检视意见1：HSET 降级后不得 HDEL 误写 Redis）。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_mark_degraded_skips_unmark():
        """HSET 时 Redis 不可用，任务完成后不得再触碰 Redis 做 HDEL。"""
        fake = _FakeRedis()
        redis_calls = []

        def flaky_redis():
            redis_calls.append(1)
            return None if len(redis_calls) == 1 else fake

        done = asyncio.Event()

        async def work():
            done.set()

        with patch.object(background_task, "_get_redis", side_effect=flaky_redis):
            task = await background_task.run_in_background_tracked(
                work(), name="t-degraded", track_key="conv-degraded")
            assert task is not None
            # await 必须在 patch 内：HDEL 阶段 _get_redis 返回 fake（模拟
            # 「任务执行期间 Redis 恢复」）——若代码回归为无条件 HDEL，
            # redis_calls 会出现第二次调用，断言即失败
            await task
        assert done.is_set()
        assert len(redis_calls) == 1, "HSET 降级后不得再为 HDEL 调用 Redis"
        assert fake.store == {}

    @staticmethod
    @pytest.mark.asyncio
    async def test_expire_failure_after_mark_still_unmarks():
        """HSET 成功但 EXPIRE 失败不得破坏配对：HDEL 照常，租约不泄漏。"""
        fake = _FakeRedis()

        async def broken_expire(key, ttl):
            raise ConnectionError("expire failed")

        fake.expire = broken_expire
        done = asyncio.Event()

        async def work():
            done.set()

        with patch.object(background_task, "_get_redis", return_value=fake):
            task = await background_task.run_in_background_tracked(
                work(), name="t-expire", track_key="conv-expire")
            # await 在 patch 内：finally 的 HDEL 必须能拿到 fake 客户端
            await task
        assert done.is_set()
        assert fake.store == {}, "EXPIRE 失败不得跳过 HDEL（否则租约泄漏）"
