# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
ControllerRunner.run_blocking 单元测试

Controller 正常流产出 SSE bytes("data: {...}\\n\\n"),错误流(adapt_error)产出 dict;
run_blocking 必须同时支持两类输入,并按"完整终态优先、delta 兜底"裁决,
保证答案恰好一份(不重复 ×4、不空 ×0)。
"""

# pylint: disable=no-self-use

import json
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime.runner.controller_runner import ControllerRunner


def _sse(event: str, data: dict | None = None) -> bytes:
    """构造 Controller run_streaming 正常流产出的 SSE bytes帧。"""
    payload = {"event": event, "data": data or {}}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


class TestControllerRunBlocking:
    """以真实 SSE bytes 为主输入,精确断言,不允许空结果蒙混通过。"""

    @pytest.mark.asyncio
    async def test_real_reproduction_sequence_exactly_one_copy(self):
        """真实复现序列:message delta×2 + message_end + workflow_end + done → 恰好一份。"""
        answer = "🔧【技术·child-B】已接单: 我需要技术支持"
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message", {"answer": "🔧【技术·child-B】已接单: "})
            yield _sse("message", {"answer": "我需要技术支持"})
            yield _sse("message_end", {"answer": answer})     # 完整快照
            yield _sse("workflow_end", {"answer": answer})    # 完整快照(权威源)
            yield _sse("done", {"answer": answer})            # done#1 带 answer,应忽略

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == answer  # 精确一份,不是 answer×2 或 answer×4

    @pytest.mark.asyncio
    async def test_workflow_end_only(self):
        """终态唯一:只有 workflow_end → 返回 workflow_end 答案。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("start", {})
            yield _sse("workflow_end", {"answer": "完整答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "完整答案"

    @pytest.mark.asyncio
    async def test_message_end_only(self):
        """message_end 唯一:返回 message_end 答案。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message_end", {"answer": "终态答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "终态答案"

    @pytest.mark.asyncio
    async def test_delta_only_no_terminal(self):
        """仅 delta:message×N 无终态 → 正确拼接 delta。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message", {"answer": "foo"})
            yield _sse("message", {"answer": "bar"})
            yield _sse("done", {})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "foobar"

    @pytest.mark.asyncio
    async def test_cumulative_message_with_terminal_no_duplication(self):
        """累计 message:A、AB + 终态 AB → 返回 AB,不能 AAB。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("message", {"answer": "A"})
            yield _sse("message", {"answer": "AB"})
            yield _sse("message_end", {"answer": "AB"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "AB"  # 终态优先,不受累积 message 影响

    @pytest.mark.asyncio
    async def test_dict_chunks_compatible_with_bytes(self):
        """dict 兼容(错误路径 adapt_error 产 dict):与 bytes 结果一致。"""
        answer = "dict 路径答案"
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "dict "}}
            yield {"event": "message", "data": {"answer": "路径答案"}}
            yield {"event": "workflow_end", "data": {"answer": answer}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == answer

    @pytest.mark.asyncio
    async def test_output_fallback(self):
        """data.output 非空(无 answer)→ 正确返回 output。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield _sse("workflow_end", {"output": "output 答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "output 答案"

    @pytest.mark.asyncio
    async def test_empty_and_non_data_frames_skipped(self):
        """空帧:None、空 answer、非 data: 帧 → 跳过且不影响有效结果。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield None
            yield _sse("message", {"answer": ""})   # 空 answer,跳过
            yield b"keep-alive\n\n"                 # 非 data: 帧,跳过
            yield _sse("workflow_end", {"answer": "有效答案"})

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        assert result == "有效答案"

    @pytest.mark.asyncio
    async def test_invalid_input_does_not_crash(self):
        """非法输入:非法 UTF-8/JSON/不支持类型 → 有日志、不崩溃、返回空。"""
        runner = ControllerRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield b"\xff\xfe not utf-8"            # 非法 UTF-8 → 逐帧吞
            yield _sse("message", {"answer": "x"})  # 有效帧
            yield "data: {not json}\n\n".encode("utf-8")  # JSONDecodeError → 跳过
            yield 12345                                # 不支持类型 → 跳过

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            result = await runner.run_blocking(MagicMock())

        # 不崩溃;唯一有效帧是 message "x",无终态 → delta 兜底
        assert result == "x"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
