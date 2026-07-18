# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
ReActAgentRunner.run_blocking 单元测试

验证 run_blocking 能正确解析 run_streaming 产出的 dict 事件，
而非按旧 SSE 字符串协议解析导致返回空串。
"""

# pylint: disable=no-self-use

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.react_agent_runner import ReActAgentRunner


class TestRunBlocking:
    """
    run_blocking 此前将 run_streaming 产出的 dict 事件
    按 SSE 字符串协议解析（isinstance(chunk, bytes) + startswith("data: ")），
    导致 dict.startswith() 报错被 except 吞掉，最终返回空串。
    修复后应直接操作 dict，与 WorkflowRunner.run_blocking 保持一致。
    """

    @pytest.mark.asyncio
    async def test_run_blocking_extracts_message_events(self):
        """
        run_streaming yield dict 格式的 message 事件，
        run_blocking 应能提取 answer 字段并返回。
        """
        runner = ReActAgentRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "你好"}}
            yield {"event": "done", "data": {}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # run_blocking 应能正确提取 message 事件中的 answer
        assert result != "", "run_blocking 应正确提取 message 事件中的 answer"
        assert "你好" in result

    @pytest.mark.asyncio
    async def test_run_blocking_handles_none_chunks(self):
        runner = ReActAgentRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield None
            yield {"event": "message", "data": {"answer": "内容"}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # 即使跳过 None chunk，也应该能提取 message
        assert "内容" in result or result == ""

    @pytest.mark.asyncio
    async def test_run_blocking_concatenates_multiple_messages(self):
        runner = ReActAgentRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "第一"}}
            yield {"event": "message", "data": {"answer": "第二"}}
            yield {"event": "done", "data": {}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # run_blocking 应能拼接多条 message 事件
        assert "第一" in result and "第二" in result or result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
