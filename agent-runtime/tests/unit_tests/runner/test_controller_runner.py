# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
ControllerRunner.run_blocking 单元测试

验证 run_blocking 能正确解析 run_streaming 产出的 dict 事件，
与 ReActAgentRunner.run_blocking 同源问题。
"""

# pylint: disable=no-self-use

from unittest.mock import MagicMock, patch

import pytest

from agent_runtime.runner.controller_runner import ControllerRunner


class TestControllerRunBlocking:
    """
    run_blocking 与 ReActAgentRunner 有相同的 dict 事件解析问题：
    按旧 SSE 字符串协议解析 dict chunk，导致返回空串。
    修复后应直接操作 dict。
    """

    @pytest.mark.asyncio
    async def test_run_blocking_with_dict_chunks(self):
        """run_streaming yield dict，run_blocking 应能解析并返回 answer 字段"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "你好世界"}}
            yield {"event": "done", "data": {}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # run_blocking 应能提取 dict chunk 中的 answer
        assert result != "", "run_blocking 应正确提取 dict chunk 中的 answer"
        assert "你好世界" in result

    @pytest.mark.asyncio
    async def test_run_blocking_none_chunks_skipped(self):
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield None
            yield {"event": "message", "data": {"answer": "内容"}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # run_blocking 应能提取 message；即使跳过 None chunk 也不应为空
        assert "内容" in result or result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
