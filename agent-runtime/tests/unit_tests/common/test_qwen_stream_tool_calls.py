# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for Qwen._stream() tool_calls 流式累积。

Bug 背景：_stream() 原来每个 chunk 硬编码 tool_calls={}，
流式 delta 中的 tool_calls 被丢弃，单智能体工具调用永远失败。
修复后在流式循环中累积 name/arguments/id，流结束后构造 ToolCall 对象。
"""
# pylint: disable=protected-access
import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
for _pkg in ("common_utils", "storage", "model_service"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.insert(0, _pkg_path)  # pylint: disable=no-use-sys-path-insert

from jiuwen.common.llm_service.messages import ToolCall


def _make_sse_lines(chunks: list[dict]) -> list[bytes]:
    """将 chunk dict 列表转成 SSE 格式的 bytes 行。"""
    lines = []
    for chunk in chunks:
        data = json.dumps(chunk, ensure_ascii=False)
        lines.append(f"data: {data}".encode("utf-8"))
    lines.append(b"data: [DONE]")
    return lines


class TestQwenStreamToolCalls:
    """Qwen._stream() — 流式 tool_calls 累积与构造。"""

    @staticmethod
    def _make_qwen():
        """通过正常构造器创建 Qwen 实例。"""
        from jiuwen.common.llm_service.language_model.qwen import Qwen
        return Qwen(api_key="test-key", api_base="http://localhost:9999/v1/chat",
                    model="qwen-test", temperature=0.5, top_p=0.5, stream=True)

    @staticmethod
    def _mock_response(lines: list[bytes]):
        """构造 mock requests.post 的流式响应。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(lines)
        return mock_resp

    def test_tool_calls_accumulated_from_stream(self):
        """流式返回 tool_calls → 正确累积出 ToolCall 对象。"""
        chunks = [
            # chunk 1: 文本 + tool_call id 和 name 开头
            {"id": "1", "choices": [{"delta": {"content": ""}, "finish_reason": None}]},
            # chunk 2: tool_call name 完整 + arguments 第一部分
            {"id": "1", "choices": [{"delta": {
                "tool_calls": [{"id": "call_001", "function": {
                    "name": "zhinenghuiyizhushoucreate_meeting",
                    "arguments": "{\"title\": "
                }}]
            }, "finish_reason": None}]},
            # chunk 3: arguments 第二部分
            {"id": "1", "choices": [{"delta": {
                "tool_calls": [{"function": {
                    "name": "",
                    "arguments": "\"需求评审会\"}"
                }}]
            }, "finish_reason": None}]},
            # chunk 4: finish_reason = tool_calls
            {"id": "1", "choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
            # chunk 5: usage
            {"id": "1", "choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}},
        ]
        lines = _make_sse_lines(chunks)
        qwen = self._make_qwen()

        with patch("jiuwen.common.llm_service.language_model.qwen.requests.post",
                    return_value=self._mock_response(lines)), \
             patch("jiuwen.common.llm_service.language_model.qwen.TemplateManager") as tm, \
             patch("jiuwen.common.llm_service.language_model.qwen.ModelUtil.truncate_params",
                    side_effect=lambda p: (p.get("top_p", 0.5), p.get("temperature", 0.5))):
            tm.return_value.get.return_value = MagicMock(content=[])
            messages = list(qwen._stream([]))

        # 最后一条消息应包含正确累积的 tool_calls
        last = messages[-1]
        assert isinstance(last.tool_calls, ToolCall)
        assert last.tool_calls.name == "zhinenghuiyizhushoucreate_meeting"
        assert "需求评审会" in str(last.tool_calls.args)
        assert last.tool_calls.id == "call_001"

    def test_no_tool_calls_text_response(self):
        """普通文本回复（无 tool_calls）→ 最终消息无有效 ToolCall。"""
        chunks = [
            {"id": "1", "choices": [{"delta": {"content": "你好"}, "finish_reason": None}]},
            {"id": "1", "choices": [{"delta": {"content": "世界"}, "finish_reason": None}]},
            {"id": "1", "choices": [{"delta": {}, "finish_reason": "stop"}]},
            {"id": "1", "choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}},
        ]
        lines = _make_sse_lines(chunks)
        qwen = self._make_qwen()

        with patch("jiuwen.common.llm_service.language_model.qwen.requests.post",
                    return_value=self._mock_response(lines)), \
             patch("jiuwen.common.llm_service.language_model.qwen.TemplateManager") as tm, \
             patch("jiuwen.common.llm_service.language_model.qwen.ModelUtil.truncate_params",
                    side_effect=lambda p: (p.get("top_p", 0.5), p.get("temperature", 0.5))):
            tm.return_value.get.return_value = MagicMock(content=[])
            messages = list(qwen._stream([]))

        # 最后一条消息不应有有效 ToolCall（name 为空或 tool_calls 为空 dict）
        last = messages[-1]
        if isinstance(last.tool_calls, ToolCall):
            assert last.tool_calls.name == ""
        # 文本内容应被拼接
        all_content = "".join(m.content or "" for m in messages)
        assert "你好" in all_content

    def test_tool_calls_dict_format(self):
        """tool_calls 以 dict 格式返回（非 list）→ 也能正确累积。"""
        chunks = [
            {"id": "1", "choices": [{"delta": {
                "tool_calls": {"id": "call_002", "function": {
                    "name": "query_meetings",
                    "arguments": "{\"date\": \"2026-09-08\"}"
                }}
            }, "finish_reason": None}]},
            {"id": "1", "choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
            {"id": "1", "choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}},
        ]
        lines = _make_sse_lines(chunks)
        qwen = self._make_qwen()

        with patch("jiuwen.common.llm_service.language_model.qwen.requests.post",
                    return_value=self._mock_response(lines)), \
             patch("jiuwen.common.llm_service.language_model.qwen.TemplateManager") as tm, \
             patch("jiuwen.common.llm_service.language_model.qwen.ModelUtil.truncate_params",
                    side_effect=lambda p: (p.get("top_p", 0.5), p.get("temperature", 0.5))):
            tm.return_value.get.return_value = MagicMock(content=[])
            messages = list(qwen._stream([]))

        last = messages[-1]
        assert isinstance(last.tool_calls, ToolCall)
        assert last.tool_calls.name == "query_meetings"

    def test_parallel_tool_calls_multiple_indices(self):
        """并行 function calling：多个 index 的 tool_calls → 生成 List[ToolCall]。"""
        chunks = [
            # chunk 1: index 0 的 tool_call 开始
            {"id": "1", "choices": [{"delta": {
                "tool_calls": [{"index": 0, "id": "call_a", "function": {
                    "name": "create_meeting",
                    "arguments": "{\"title\": \"周会\"}"
                }}]
            }, "finish_reason": None}]},
            # chunk 2: index 1 的 tool_call 开始
            {"id": "1", "choices": [{"delta": {
                "tool_calls": [{"index": 1, "id": "call_b", "function": {
                    "name": "query_meetings",
                    "arguments": "{\"date\": \"2026-09-08\"}"
                }}]
            }, "finish_reason": None}]},
            # chunk 3: finish_reason
            {"id": "1", "choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
            {"id": "1", "choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}},
        ]
        lines = _make_sse_lines(chunks)
        qwen = self._make_qwen()

        with patch("jiuwen.common.llm_service.language_model.qwen.requests.post",
                    return_value=self._mock_response(lines)), \
             patch("jiuwen.common.llm_service.language_model.qwen.TemplateManager") as tm, \
             patch("jiuwen.common.llm_service.language_model.qwen.ModelUtil.truncate_params",
                    side_effect=lambda p: (p.get("top_p", 0.5), p.get("temperature", 0.5))):
            tm.return_value.get.return_value = MagicMock(content=[])
            messages = list(qwen._stream([]))

        last = messages[-1]
        # 多个 tool_calls 应返回列表
        assert isinstance(last.tool_calls, list)
        assert len(last.tool_calls) == 2
        assert last.tool_calls[0].name == "create_meeting"
        assert last.tool_calls[0].id == "call_a"
        assert last.tool_calls[1].name == "query_meetings"
        assert last.tool_calls[1].id == "call_b"
