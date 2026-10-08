# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""WorkflowRunner 记忆检索单元测试。

覆盖 _retrieve_memory（BUILTIN）与 _retrieve_memory_external（EXTERNAL）：
- 两次检索（user_mem / history_summary）并行执行，不再串行等待
- 结果拼接格式（<mem> / <history_summary>）保持不变
- 任一检索失败时整体降级返回 None（与原串行实现行为一致）
- EXTERNAL 分支调度正确性
"""

# pylint: disable=no-self-use

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agent_runtime.runner.workflow_runner import WorkflowRunner


LTM_PATCH = "agent_runtime.memory.adapter.ltm_manager.get_ltm"
EXTERNAL_CLIENT_PATCH = (
    "agent_runtime.memory.backend.external_memory_client.get_external_client"
)


def _mem(content: str):
    """SDK MemResult 风格的记忆条目（mem_info.content）。"""
    return SimpleNamespace(mem_info=SimpleNamespace(content=content))


class _SchedulingLtm:
    """记录两次检索调度顺序的 LTM 替身。

    search_user_mem 与 search_user_history_summary 各自先登记 start、
    await 让出事件循环、再登记 end。串行实现的顺序为
    [mem_start, mem_end, summary_start, summary_end]；并行实现中
    两个 start 都先于任一 end 出现。
    """

    def __init__(self, mem_result=None, summary_result=None):
        self.order = []
        self._mem_result = mem_result if mem_result is not None else []
        self._summary_result = summary_result if summary_result is not None else []

    async def search_user_mem(self, **kwargs):
        self.order.append("mem_start")
        await __import__("asyncio").sleep(0)
        self.order.append("mem_end")
        return self._mem_result

    async def search_user_history_summary(self, **kwargs):
        self.order.append("summary_start")
        await __import__("asyncio").sleep(0)
        self.order.append("summary_end")
        return self._summary_result


class _SchedulingExternalClient:
    """记录两次 HTTP 检索调度顺序的 ExternalMemoryClient 替身。"""

    def __init__(self, mem_result=None, summary_result=None):
        self.order = []
        self._mem_result = mem_result if mem_result is not None else []
        self._summary_result = summary_result if summary_result is not None else []

    async def search_memory(self, **kwargs):
        self.order.append("mem_start")
        await __import__("asyncio").sleep(0)
        self.order.append("mem_end")
        return self._mem_result

    async def search_user_history_summary(self, **kwargs):
        self.order.append("summary_start")
        await __import__("asyncio").sleep(0)
        self.order.append("summary_end")
        return self._summary_result


class TestBuiltinRetrieveMemory:
    """BUILTIN 分支：get_ltm() 路径。"""

    @pytest.mark.asyncio
    async def test_two_searches_run_concurrently(self):
        runner = WorkflowRunner(api_key="test-key")
        ltm = _SchedulingLtm(
            mem_result=[_mem("用户偏好咖啡")],
            summary_result=[_mem("用户曾去过深圳")],
        )

        with patch(LTM_PATCH, return_value=ltm):
            msg = await runner._retrieve_memory(  # pylint: disable=protected-access
                "User-1", "repo-1", "用户喜欢什么",
                memory_config={"memory_backend_type": "BUILTIN"},
            )

        # 并行证据：两个 start 都先于任一 end
        assert ltm.order[:2] == ["mem_start", "summary_start"], ltm.order
        assert set(ltm.order[2:]) == {"mem_end", "summary_end"}

        # 结果拼接格式不变
        assert msg is not None
        assert "<mem>用户偏好咖啡</mem>" in msg.content
        assert "<history_summary>用户曾去过深圳</history_summary>" in msg.content

    @pytest.mark.asyncio
    async def test_both_searches_receive_same_arguments(self):
        runner = WorkflowRunner(api_key="test-key")
        ltm = _SchedulingLtm(mem_result=[_mem("m")], summary_result=[_mem("s")])
        calls = {}

        async def mem_spy(**kwargs):
            calls["mem"] = kwargs
            return await ltm.search_user_mem(**kwargs)

        async def summary_spy(**kwargs):
            calls["summary"] = kwargs
            return await ltm.search_user_history_summary(**kwargs)

        stub = SimpleNamespace(
            search_user_mem=mem_spy,
            search_user_history_summary=summary_spy,
        )

        with patch(LTM_PATCH, return_value=stub):
            await runner._retrieve_memory(  # pylint: disable=protected-access
                "User-1", "repo-1", "q",
                memory_config={"memory_backend_type": "BUILTIN"},
            )

        assert calls["mem"] == {
            "query": "q", "num": 20, "user_id": "user-1", "scope_id": "repo-1",
        }
        assert calls["summary"] == {
            "query": "q", "num": 5, "user_id": "user-1", "scope_id": "repo-1",
        }

    @pytest.mark.asyncio
    async def test_summary_failure_degrades_to_none(self):
        """任一检索失败 → 整体返回 None（与原串行行为一致）。"""
        runner = WorkflowRunner(api_key="test-key")

        async def failing_summary(**kwargs):
            raise RuntimeError("summary backend down")

        stub = SimpleNamespace(
            search_user_mem=AsyncMock(return_value=[_mem("用户偏好咖啡")]),
            search_user_history_summary=failing_summary,
        )

        with patch(LTM_PATCH, return_value=stub):
            result = await runner._retrieve_memory(  # pylint: disable=protected-access
                "User-1", "repo-1", "q", memory_config=None,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_mem_failure_degrades_to_none(self):
        runner = WorkflowRunner(api_key="test-key")

        async def failing_mem(**kwargs):
            raise RuntimeError("mem backend down")

        stub = SimpleNamespace(
            search_user_mem=failing_mem,
            search_user_history_summary=AsyncMock(return_value=[_mem("s")]),
        )

        with patch(LTM_PATCH, return_value=stub):
            result = await runner._retrieve_memory(  # pylint: disable=protected-access
                "User-1", "repo-1", "q", memory_config=None,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_memory_returns_none(self):
        runner = WorkflowRunner(api_key="test-key")

        with patch(LTM_PATCH, return_value=_SchedulingLtm()):
            result = await runner._retrieve_memory(  # pylint: disable=protected-access
                "User-1", "repo-1", "q", memory_config=None,
            )

        assert result is None


class TestExternalRetrieveMemory:
    """EXTERNAL 分支：ExternalMemoryClient 路径。"""

    @staticmethod
    def _external_config():
        return {
            "memory_backend_type": "EXTERNAL",
            "instance_id": "inst-1",
            "instance_base_url": "http://memory.example.com",
        }

    @pytest.mark.asyncio
    async def test_two_searches_run_concurrently(self):
        runner = WorkflowRunner(api_key="test-key")
        client = _SchedulingExternalClient(
            mem_result=[{"content": "用户偏好咖啡"}],
            summary_result=[{"content": "用户曾去过深圳"}],
        )

        with patch(EXTERNAL_CLIENT_PATCH, new=AsyncMock(return_value=client)):
            msg = await runner._retrieve_memory_external(  # pylint: disable=protected-access
                "User-1", "repo-1", "用户喜欢什么", self._external_config(),
            )

        # 并行证据：两个 start 都先于任一 end
        assert client.order[:2] == ["mem_start", "summary_start"], client.order
        assert set(client.order[2:]) == {"mem_end", "summary_end"}

        assert msg is not None
        assert "<mem>用户偏好咖啡</mem>" in msg.content
        assert "<history_summary>用户曾去过深圳</history_summary>" in msg.content

    @pytest.mark.asyncio
    async def test_one_failure_degrades_to_none(self):
        runner = WorkflowRunner(api_key="test-key")

        async def failing_summary(**kwargs):
            raise RuntimeError("summary http error")

        client = SimpleNamespace(
            search_memory=AsyncMock(return_value=[{"content": "m"}]),
            search_user_history_summary=failing_summary,
        )

        with patch(EXTERNAL_CLIENT_PATCH, new=AsyncMock(return_value=client)):
            result = await runner._retrieve_memory_external(  # pylint: disable=protected-access
                "User-1", "repo-1", "q", self._external_config(),
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_retrieve_memory_dispatches_to_external(self):
        """backend_type=EXTERNAL 时 _retrieve_memory 走 EXTERNAL 分支。"""
        runner = WorkflowRunner(api_key="test-key")
        client = _SchedulingExternalClient(
            mem_result=[{"content": "m"}], summary_result=[{"content": "s"}],
        )
        builtin_ltm = _SchedulingLtm(
            mem_result=[_mem("builtin-mem")], summary_result=[_mem("builtin-summary")],
        )

        with patch(LTM_PATCH, return_value=builtin_ltm), patch(
            EXTERNAL_CLIENT_PATCH, new=AsyncMock(return_value=client)
        ):
            msg = await runner._retrieve_memory(  # pylint: disable=protected-access
                "User-1", "repo-1", "q", memory_config=self._external_config(),
            )

        # EXTERNAL 被调用，BUILTIN 未被调用
        assert builtin_ltm.order == []
        assert client.order[:2] == ["mem_start", "summary_start"]
        assert "<mem>m</mem>" in msg.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
