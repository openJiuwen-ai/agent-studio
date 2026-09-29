# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for Qwen._chat() tool_calls 非流式解析防御。

Bug 背景：_chat() 原来硬编码字典形态链式 .get：
    res_json.get("choices")[0].get("message").get("tool_calls").get("function").get("name")
当模型服务返回标准 OpenAI list 形态 tool_calls（最常见格式）时，
'list' object has no attribute 'get' 直接 AttributeError；
当 finish_reason == "tool_calls" 但 message 缺失 tool_calls 时，
'NoneType' object has no attribute 'get' 崩溃；
当 arguments 为 None 时，ModelUtil.check_and_trans2json 内
json.loads(None) 抛 TypeError，不被 except json.JSONDecodeError 捕获；
当工具调用消息 content 为 null（标准协议）时，AIMessage.content
校验不接受 None，pydantic ValidationError。
修复后与 _stream()（af58a024）的 list/dict 双形态兼容逻辑对齐。
review（chenfeng）补充修复：
- 并行调用不再只取首个，收集全部有效 function 返回 List[ToolCall]；
- 兜底分支仅 function_info 非空时覆盖 content，避免原始文本丢失；
- arguments else 改为 isinstance(arguments, dict)，list/int 等走兜底。
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


def _no_valid_toolcall(value) -> bool:
    """判断 tool_calls 是否无有效调用。

    AIMessage.tool_calls 类型为 Union[ToolCall, List[ToolCall]]，
    传入 {} 会被 pydantic 强制转换为 ToolCall(name="", args={}, id="")，
    因此"无有效调用"必须按 name 是否为空判断。
    """
    return (not isinstance(value, ToolCall)) or value.name == ""


def _make_chat_response(message: dict, finish_reason: str = "tool_calls") -> MagicMock:
    """构造 mock requests.post 的非流式响应。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "chatcmpl-1",
        "model": "qwen-test",
        "choices": [{"message": message, "finish_reason": finish_reason}],
    }
    return mock_resp


class TestQwenChatToolCalls:
    """Qwen._chat() — 非流式 tool_calls 解析（list/dict 双形态 + 畸形防御）。"""

    @staticmethod
    def _make_qwen():
        """通过正常构造器创建 Qwen 实例。"""
        from jiuwen.common.llm_service.language_model.qwen import Qwen
        return Qwen(api_key="test-key", api_base="http://localhost:9999/v1/chat",
                    model="qwen-test", temperature=0.5, top_p=0.5, stream=False)

    def _run_chat(self, message: dict, finish_reason: str = "tool_calls"):
        """统一执行 _chat 并返回 AIMessage。"""
        qwen = self._make_qwen()
        with patch(
            "jiuwen.common.llm_service.language_model.qwen.requests.post",
            return_value=_make_chat_response(message, finish_reason),
        ), patch(
            "jiuwen.common.llm_service.language_model.qwen.TemplateManager"
        ) as tm, patch(
            "jiuwen.common.llm_service.language_model.qwen.ModelUtil.truncate_params",
            side_effect=lambda p: (p.get("top_p", 0.5), p.get("temperature", 0.5)),
        ):
            tm.return_value.get.return_value = MagicMock(content=[])
            return qwen._chat([])

    def test_tool_calls_list_format(self):
        """标准 OpenAI list 形态 tool_calls → 正确解析出 ToolCall（原代码 AttributeError）。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": '{"title": "周会"}',
                    },
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert isinstance(result, ToolCall)
        assert result.name == "create_meeting"
        assert result.args == {"title": "周会"}

    def test_tool_calls_dict_format(self):
        """dict 形态 tool_calls（原代码唯一支持的形态）→ 行为保持不变。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": {
                "function": {
                    "name": "query_meetings",
                    "arguments": '{"date": "2026-09-28"}',
                }
            },
        }
        result = self._run_chat(message).tool_calls
        assert isinstance(result, ToolCall)
        assert result.name == "query_meetings"
        assert result.args == {"date": "2026-09-28"}

    def test_tool_calls_missing_preserves_content(self):
        """finish_reason=tool_calls 但 message 缺失 tool_calls → 不崩溃，保留原始 content。

        review（chenfeng）L203/L219：兜底分支不应覆盖原始 assistant 文本。
        修复后兜底直接保留 res_content，不再 json.dumps 覆盖。
        """
        message = {
            "role": "assistant",
            "content": "未完成工具调用的兜底回复",
        }
        aim = self._run_chat(message)
        assert _no_valid_toolcall(aim.tool_calls)
        assert aim.content == "未完成工具调用的兜底回复"

    def test_tool_calls_arguments_none(self):
        """function.arguments 为 None → 不再触发 TypeError（json.loads(None)），走兜底。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_002",
                    "type": "function",
                    "function": {"name": "create_meeting", "arguments": None},
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert _no_valid_toolcall(result)

    def test_tool_calls_arguments_already_dict(self):
        """arguments 已是 dict（部分模型服务直接返回解析结果）→ 直接使用。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_003",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": {"title": "周会"},
                    },
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert isinstance(result, ToolCall)
        assert result.name == "create_meeting"
        assert result.args == {"title": "周会"}

    def test_tool_calls_arguments_list_type(self):
        """arguments 为 list（畸形值）→ 走兜底，不触发 pydantic ValidationError。

        review（chenfeng）L196：原 else 未校验类型，list 传入 ToolCall.args 会
        pydantic ValidationError。修复后 else 改为 isinstance(arguments, dict)。
        """
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_007",
                    "type": "function",
                    "function": {"name": "create_meeting", "arguments": [1, 2]},
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert _no_valid_toolcall(result)

    def test_tool_calls_arguments_int_type(self):
        """arguments 为 int（畸形值）→ 走兜底，不崩溃。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_008",
                    "type": "function",
                    "function": {"name": "create_meeting", "arguments": 42},
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert _no_valid_toolcall(result)

    def test_tool_calls_arguments_invalid_json(self):
        """arguments 为非法 JSON 字符串 → 走兜底，保留原始 content。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_004",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": "not-a-json",
                    },
                }
            ],
        }
        aim = self._run_chat(message)
        assert _no_valid_toolcall(aim.tool_calls)
        assert aim.content == ""

    def test_no_tool_calls_normal_reply(self):
        """finish_reason=stop 普通文本回复 → 无有效 ToolCall。"""
        message = {"role": "assistant", "content": "你好，请问有什么可以帮您？"}
        result = self._run_chat(message, finish_reason="stop").tool_calls
        assert _no_valid_toolcall(result)

    def test_tool_calls_list_item_missing_function_key(self):
        """list 中某项缺 function 键 → 跳过该项取下一个，不崩溃。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_005", "type": "function"},
                {
                    "id": "call_006",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": '{"title": "周会"}',
                    },
                },
            ],
        }
        result = self._run_chat(message).tool_calls
        assert isinstance(result, ToolCall)
        assert result.name == "create_meeting"

    def test_parallel_tool_calls(self):
        """并行调用：多个有效 tool_calls → 返回 List[ToolCall]，id 各自正确。

        review（chenfeng）L187/L205：原代码 break 只取首个；
        第二次 review L205：双循环残留 tool_call 变量导致 id 错配。
        修复后合并为单循环，id 在当前迭代中正确绑定。
        """
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": '{"title": "周会"}',
                    },
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {
                        "name": "query_meetings",
                        "arguments": '{"date": "2026-09-28"}',
                    },
                },
            ],
        }
        result = self._run_chat(message).tool_calls
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].name == "create_meeting"
        assert result[0].args == {"title": "周会"}
        assert result[0].id == "call_a"
        assert result[1].name == "query_meetings"
        assert result[1].args == {"date": "2026-09-28"}
        assert result[1].id == "call_b"

    def test_tool_calls_message_content_none_fallback(self):
        """工具调用消息 content=None（标准协议）→ 兜底为空串，不再 pydantic ValidationError。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": {
                "function": {
                    "name": "create_meeting",
                    "arguments": '{"title": "周会"}',
                }
            },
        }
        aim = self._run_chat(message)
        assert aim.content == ""
        assert isinstance(aim.tool_calls, ToolCall)

    def test_message_null(self):
        """message 为 null → 不崩溃，content 兜底空串。

        review（chenfeng）L165：原链式 .get("message").get("content") 在 message=null
        时 AttributeError，先于后续 or {} 兜底。
        """
        message = None
        aim = self._run_chat(message)
        assert aim.content == ""
        assert _no_valid_toolcall(aim.tool_calls)

    def test_tool_calls_scalar_value(self):
        """tool_calls 为标量（true/数字）→ 兜底空列表，不抛 TypeError。

        review（chenfeng）L183：标量不可迭代，for 循环直接 TypeError。
        """
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": True,
        }
        aim = self._run_chat(message)
        assert _no_valid_toolcall(aim.tool_calls)

    def test_tool_calls_arguments_json_non_dict(self):
        """arguments 为合法 JSON 但非 dict（如 "null"/"[]"）→ 走兜底，不 pydantic 崩溃。

        review（chenfeng）L202：check_and_trans2json 返回 (True, None/列表)，
        ToolCall(args=非 dict) 触发 pydantic ValidationError。
        """
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_009",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": "null",
                    },
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert _no_valid_toolcall(result)

    def test_tool_calls_arguments_json_array(self):
        """arguments 为合法 JSON 数组 → 走兜底，不 pydantic 崩溃。"""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_010",
                    "type": "function",
                    "function": {
                        "name": "create_meeting",
                        "arguments": "[1, 2]",
                    },
                }
            ],
        }
        result = self._run_chat(message).tool_calls
        assert _no_valid_toolcall(result)
