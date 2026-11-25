# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""恢复路径取消标记检测单元测试（REQ-2026-002 VR-7）。

WorkflowRunner 直读 Redis cancel:{conv} 标记（不 import serve 层）：
中断节点挂起期间被取消 → 检测命中 → 清标记 → 不恢复中断态，从入口重新执行。
恢复分支整体行为由多实例集成测试覆盖（tests/integration_tests）。
"""

# pylint: disable=no-self-use

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.workflow_runner import WorkflowRunner


def _runner() -> WorkflowRunner:
    """绕过 __init__（被测辅助方法不依赖实例状态）。"""
    return WorkflowRunner.__new__(WorkflowRunner)


def _patch_redis(get=None, delete=None):
    """workflow_runner 模块顶层 import 的 get_redis_client —— patch 模块命名空间。"""
    client = AsyncMock()
    client.get = get or AsyncMock(return_value=None)
    client.delete = delete or AsyncMock()
    return patch("agent_runtime.runner.workflow_runner.get_redis_client", return_value=client)


class TestIsSessionCancelled:
    @pytest.mark.asyncio
    async def test_true_flag_detected(self):
        runner = _runner()
        with _patch_redis(get=AsyncMock(return_value=b"true")):
            assert await runner._is_session_cancelled("conv-1") is True

    @pytest.mark.asyncio
    async def test_false_flag_not_detected(self):
        runner = _runner()
        with _patch_redis(get=AsyncMock(return_value=b"false")):
            assert await runner._is_session_cancelled("conv-1") is False

    @pytest.mark.asyncio
    async def test_missing_flag_not_detected(self):
        runner = _runner()
        with _patch_redis(get=AsyncMock(return_value=None)):
            assert await runner._is_session_cancelled("conv-none") is False

    @pytest.mark.asyncio
    async def test_str_client_compatibility(self):
        """非 bytes 客户端（decode_responses=True）兼容。"""
        runner = _runner()
        with _patch_redis(get=AsyncMock(return_value="true")):
            assert await runner._is_session_cancelled("conv-1") is True


class TestClearSessionCancelled:
    @pytest.mark.asyncio
    async def test_deletes_cancel_key(self):
        runner = _runner()
        delete = AsyncMock()
        with _patch_redis(delete=delete):
            await runner._clear_session_cancelled("conv-1")

        delete.assert_awaited_once_with("cancel:conv-1")


class _StopAfterCheckpoint(Exception):
    """在取消清理分支之后的 session 创建点抛出，截断 run_streaming 后续流程。

    清理分支位于 session 创建之前（US3 顺序约定），outer try/finally 不吞
    该异常，测试借此只驱动到被测分支即止。
    """


class TestCancelRestartFromEntry:
    """run_streaming 取消清理分支（挂起期间被取消 → 清 checkpoint → 入口重跑）。

    回归锁（0996eb84 merge 后 session 创建点后移到清理分支之后）：清理调用
    不得引用尚未创建的 session 局部变量——UnboundLocalError 会被 except 吞成
    warning，checkpoint 清理静默失败，同会话重发撞 111121
    （CHECKPOINTER_PRE_WORKFLOW_EXECUTION_ERROR）。
    """

    IR_JSON = {"workflowId": "wf-1"}

    @staticmethod
    def _make_req():
        """最小 ExecutionRequest 替身（属性 duck-typing，走到清理分支即止）。"""
        params = SimpleNamespace(
            conversation_history=[],
            is_debug=False,
            enable_memory_extract=False,
            model_dump=lambda: {},
        )
        return SimpleNamespace(
            conversation_id="conv-c",
            ir_path="ir/path.json",
            query="你好",
            user_id="u1",
            resume_input=None,
            params=params,
        )

    @staticmethod
    def _make_runner():
        runner = _runner()
        runner._ir_converter = MagicMock(
            async_ir_to_workflow=AsyncMock(return_value=MagicMock())
        )
        runner._is_session_interrupted = AsyncMock(return_value=True)
        runner._is_session_cancelled = AsyncMock(return_value=True)
        runner._clear_session_cancelled = AsyncMock()
        return runner

    def _enter_patches(self, stack: ExitStack, fake_checkpointer) -> None:
        """patch run_streaming 入口到清理分支的全部模块级依赖。

        session 创建点（清理分支之后）以 _StopAfterCheckpoint 截断，后续
        inputs 构建 / 事件 yield / workflow.stream 均不进入。
        """
        factory = MagicMock()
        factory.get_checkpointer = MagicMock(return_value=fake_checkpointer)
        conv_cls = MagicMock()
        conv_cls.extract_node_defs = AsyncMock(return_value={})
        stack.enter_context(
            patch(
                "agent_runtime.runner.workflow_runner.async_ir_load",
                AsyncMock(return_value=self.IR_JSON),
            )
        )
        stack.enter_context(
            patch("agent_runtime.runner.workflow_runner.IRConverter", conv_cls)
        )
        stack.enter_context(
            patch(
                "agent_runtime.runner.workflow_runner.create_conversation_context",
                MagicMock(return_value=MagicMock()),
            )
        )
        stack.enter_context(
            patch("agent_runtime.context.request_context._request_ctx", MagicMock())
        )
        stack.enter_context(
            patch("agent_runtime.runner.workflow_runner.CheckpointerFactory", factory)
        )
        stack.enter_context(
            patch(
                "agent_runtime.runner.workflow_runner.create_workflow_session_with_trace",
                MagicMock(side_effect=_StopAfterCheckpoint()),
            )
        )

    @pytest.mark.asyncio
    async def test_clear_called_with_none_session_before_session_created(self):
        """清理在 session 创建前发生：第三参必须为 None，不得引用未创建变量。

        FastRedisCheckpointer 精确删除主路径（ns 索引 SMEMBERS + batch_delete
        + SREM）不依赖 session，None 同 release_workflow 先例；清理成功后取消
        标记被消费。
        """
        runner = self._make_runner()
        clear = AsyncMock()
        fake_checkpointer = MagicMock()
        fake_checkpointer._clear_checkpoint_and_sentinel = clear

        with ExitStack() as stack:
            self._enter_patches(stack, fake_checkpointer)
            with pytest.raises(_StopAfterCheckpoint):
                async for _ in runner.run_streaming(self._make_req()):
                    pass

        clear.assert_awaited_once_with("conv-c", "wf-1", None)
        runner._clear_session_cancelled.assert_awaited_once_with("conv-c")

    @pytest.mark.asyncio
    async def test_clear_failure_keeps_cancel_flag(self):
        """清理失败（如 Redis 异常）：异常被吞、保留取消标记供下次重发重走入口。"""
        runner = self._make_runner()
        fake_checkpointer = MagicMock()
        fake_checkpointer._clear_checkpoint_and_sentinel = AsyncMock(
            side_effect=RuntimeError("redis down")
        )

        with ExitStack() as stack:
            self._enter_patches(stack, fake_checkpointer)
            with pytest.raises(_StopAfterCheckpoint):
                async for _ in runner.run_streaming(self._make_req()):
                    pass

        fake_checkpointer._clear_checkpoint_and_sentinel.assert_awaited_once()
        runner._clear_session_cancelled.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_fast_checkpointer_keeps_cancel_flag(self):
        """checkpointer 无 _clear_checkpoint_and_sentinel（非 FastRedisCheckpointer）：
        走显式 warning 分支、不抛异常，标记保留。
        """
        runner = self._make_runner()
        # spec=[] 使任意属性访问抛 AttributeError → getattr(..., None) 回退 None
        fake_checkpointer = MagicMock(spec=[])

        with ExitStack() as stack:
            self._enter_patches(stack, fake_checkpointer)
            with pytest.raises(_StopAfterCheckpoint):
                async for _ in runner.run_streaming(self._make_req()):
                    pass

        runner._clear_session_cancelled.assert_not_awaited()
