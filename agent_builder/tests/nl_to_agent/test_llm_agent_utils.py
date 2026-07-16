#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""llm_agent.utils 模块单元测试"""

import asyncio
from unittest.mock import MagicMock

import pytest
from agent_builder.nl_to_agent.llm_agent.utils import (
    AGENT_MSG,
    CACHE_TOKEN,
    FINAL_MSG,
    LLM_AGENT_IR,
    call_model,
    call_model_async,
    format_dialogue_history,
)


class TestConstants:

    @staticmethod
    def test_final_msg_value():
        assert FINAL_MSG == "final_msg"

    @staticmethod
    def test_agent_msg_value():
        assert AGENT_MSG == "agent_msg"

    @staticmethod
    def test_cache_token_value():
        assert CACHE_TOKEN == "cache_token"

    @staticmethod
    def test_llm_agent_ir_value():
        assert LLM_AGENT_IR == "llm_agent_ir"


class TestFormatDialogueHistory:

    @staticmethod
    def test_user_role_formatting():
        history = [{"role": "user", "content": "hello"}]
        result = format_dialogue_history(history)
        assert result == ["User: hello"]

    @staticmethod
    def test_assistant_role_formatting():
        history = [{"role": "assistant", "content": "hi"}]
        result = format_dialogue_history(history)
        assert result == ["Assistant: hi"]

    @staticmethod
    def test_ignores_other_roles():
        history = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
        result = format_dialogue_history(history)
        assert result == ["User: hello"]

    @staticmethod
    def test_empty_list_returns_empty():
        result = format_dialogue_history([])
        assert result == []

    @staticmethod
    def test_only_user_messages():
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "user", "content": "msg2"},
        ]
        result = format_dialogue_history(history)
        assert result == ["User: msg1", "User: msg2"]

    @staticmethod
    def test_only_assistant_messages():
        history = [
            {"role": "assistant", "content": "ans1"},
            {"role": "assistant", "content": "ans2"},
        ]
        result = format_dialogue_history(history)
        assert result == ["Assistant: ans1", "Assistant: ans2"]

    @staticmethod
    def test_mixed_content():
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "how are you"},
            {"role": "assistant", "content": "fine"},
        ]
        result = format_dialogue_history(history)
        assert result == [
            "User: hello",
            "Assistant: hi",
            "User: how are you",
            "Assistant: fine",
        ]

    @staticmethod
    def test_entry_without_role_key_ignored():
        history = [{"content": "no role"}]
        result = format_dialogue_history(history)
        assert result == []


class TestCallModel:

    @staticmethod
    def test_yields_raw_content():
        chunk1 = MagicMock()
        chunk1.raw_content = "hello"
        chunk2 = MagicMock()
        chunk2.raw_content = "world"
        mock_model = MagicMock()
        mock_model.chat.return_value = [chunk1, chunk2]
        result = list(call_model(mock_model, [{"role": "user", "content": "hi"}]))
        assert result == ["hello", "world"]

    @staticmethod
    def test_skip_empty_raw_content():
        chunk1 = MagicMock()
        chunk1.raw_content = "hello"
        chunk2 = MagicMock()
        chunk2.raw_content = ""
        mock_model = MagicMock()
        mock_model.chat.return_value = [chunk1, chunk2]
        result = list(call_model(mock_model, [{"role": "user", "content": "hi"}]))
        assert result == ["hello"]

    @staticmethod
    def test_skip_attribute_error():
        chunk1 = MagicMock()
        chunk1.raw_content = "hello"
        chunk2 = MagicMock(spec=[])
        mock_model = MagicMock()
        mock_model.chat.return_value = [chunk1, chunk2]
        result = list(call_model(mock_model, [{"role": "user", "content": "hi"}]))
        assert result == ["hello"]

    @staticmethod
    def test_calls_model_chat_with_correct_args():
        mock_model = MagicMock()
        mock_model.chat.return_value = []
        query_list = [{"role": "user", "content": "hi"}]
        list(call_model(mock_model, query_list))
        actual_args, actual_kwargs = mock_model.chat.call_args
        assert actual_kwargs == {"method": "stream", "add_prefix": False}
        assert len(actual_args[0]) == 1
        msg = actual_args[0][0]
        assert msg.type == "user"
        assert msg.content == "hi"


class TestCallModelAsync:

    @staticmethod
    def test_yields_raw_content():
        async def mock_achat(*args, **kwargs):
            chunk1 = MagicMock()
            chunk1.raw_content = "hello"
            chunk2 = MagicMock()
            chunk2.raw_content = "world"
            for chunk in [chunk1, chunk2]:
                yield chunk

        mock_model = MagicMock()
        mock_model.achat = mock_achat

        async def _run():
            result = []
            async for item in call_model_async(mock_model, [{"role": "user", "content": "hi"}]):
                result.append(item)
            return result

        assert asyncio.run(_run()) == ["hello", "world"]

    @staticmethod
    def test_skip_empty_raw_content():
        async def mock_achat(*args, **kwargs):
            chunk1 = MagicMock()
            chunk1.raw_content = "hello"
            chunk2 = MagicMock()
            chunk2.raw_content = ""
            for chunk in [chunk1, chunk2]:
                yield chunk

        mock_model = MagicMock()
        mock_model.achat = mock_achat

        async def _run():
            result = []
            async for item in call_model_async(mock_model, [{"role": "user", "content": "hi"}]):
                result.append(item)
            return result

        assert asyncio.run(_run()) == ["hello"]

    @staticmethod
    def test_skip_attribute_error():
        async def mock_achat(*args, **kwargs):
            chunk1 = MagicMock()
            chunk1.raw_content = "hello"
            chunk2 = MagicMock(spec=[])
            for chunk in [chunk1, chunk2]:
                yield chunk

        mock_model = MagicMock()
        mock_model.achat = mock_achat

        async def _run():
            result = []
            async for item in call_model_async(mock_model, [{"role": "user", "content": "hi"}]):
                result.append(item)
            return result

        assert asyncio.run(_run()) == ["hello"]

    @staticmethod
    def test_calls_model_achat_with_correct_args():
        async def mock_achat(*args, **kwargs):
            return
            yield

        mock_model = MagicMock()
        mock_model.achat = mock_achat
        query_list = [{"role": "user", "content": "hi"}]

        async def _run():
            async for _ in call_model_async(mock_model, query_list):
                pass

        asyncio.run(_run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])