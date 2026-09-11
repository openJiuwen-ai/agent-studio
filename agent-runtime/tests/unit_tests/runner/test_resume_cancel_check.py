# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""恢复路径取消标记检测单元测试（REQ-2026-002 VR-7）。

WorkflowRunner 直读 Redis cancel:{conv} 标记（不 import serve 层）：
中断节点挂起期间被取消 → 检测命中 → 清标记 → 不恢复中断态，从入口重新执行。
恢复分支整体行为由多实例集成测试覆盖（tests/integration_tests）。
"""

# pylint: disable=no-self-use

from unittest.mock import AsyncMock, patch

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
