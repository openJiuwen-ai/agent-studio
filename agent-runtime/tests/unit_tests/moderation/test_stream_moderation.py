# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for stream moderation generator wrappers."""

import pytest

from agent_runtime.moderation.engine import ModerationEngineDynamicAC
from agent_runtime.moderation.stream_moderation import (
    apply_stream_moderation,
    block_event_generator,
    init_moderation_from_ir,
)


def _make_engine(keywords, action_type="filter", content="", channel="output"):
    """Helper: build engine with rules."""
    action_cfg = {"enable": True, "type": action_type, "content": content}
    config = {
        "enabled": True,
        "rules": [{"keywords": keywords, "actions": {channel: action_cfg}}],
    }
    return ModerationEngineDynamicAC(config)


async def _collect(gen):
    """Collect all items from an async generator."""
    result = []
    async for item in gen:
        result.append(item)
    return result


class TestApplyStreamModeration:

    @pytest.mark.asyncio
    async def test_no_engine_passes_through(self):

        async def raw_gen():
            yield {"event": "message", "data": {"answer": "hello"}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), None))
        assert len(result) == 2
        assert result[0]["data"]["answer"] == "hello"

    @pytest.mark.asyncio
    async def test_safe_content_passes_through(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield {"event": "message", "data": {"answer": "hello", "think": ""}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"] == "hello"

    @pytest.mark.asyncio
    async def test_filter_removes_keyword_in_answer(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield {"event": "message", "data": {"answer": "hello badword world", "think": ""}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert "badword" not in result[0]["data"]["answer"]

    @pytest.mark.asyncio
    async def test_filter_removes_keyword_in_think(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield {"event": "message", "data": {"answer": "", "think": "thinking badword here"}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert "badword" not in result[0]["data"]["think"]

    @pytest.mark.asyncio
    async def test_reply_blocks_and_emits_sensitive(self):
        engine = _make_engine(["badword"], "reply", "不允许")

        async def raw_gen():
            yield {"event": "message", "data": {"answer": "badword", "think": ""}}
            yield {"event": "message", "data": {"answer": "should not reach", "think": ""}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"
        assert result[0]["data"]["text"] == "不允许"

    @pytest.mark.asyncio
    async def test_non_message_events_pass_through(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield {"event": "workflow_start", "data": {}}
            yield {"event": "message", "data": {"answer": "safe", "think": ""}}
            yield {"event": "workflow_end", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 3
        assert result[0]["event"] == "workflow_start"
        assert result[2]["event"] == "workflow_end"

    @pytest.mark.asyncio
    async def test_message_end_event_is_moderated(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield {"event": "message_end", "data": {"answer": "badword", "think": ""}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert "badword" not in result[0]["data"]["answer"]

    @pytest.mark.asyncio
    async def test_message_end_origin_answer_is_moderated(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {"event": "message_end", "data": {"answer": "badword", "think": "", "origin_answer": "badword here"}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"] == "***"
        assert result[0]["data"]["origin_answer"] == "*** here"

    @pytest.mark.asyncio
    async def test_none_chunk_passes_through(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield None
            yield {"event": "message", "data": {"answer": "safe", "think": ""}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 2
        assert result[0] is None

    @pytest.mark.asyncio
    async def test_bytes_chunk_passes_through(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield b"raw bytes"
            yield {"event": "message", "data": {"answer": "safe", "think": ""}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 2
        assert result[0] == b"raw bytes"

    @pytest.mark.asyncio
    async def test_summary_response_is_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {"event": "summary_response", "data": {"answer": {"role": "assistant", "content": "badword here"}}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"]["content"] == "*** here"

    @pytest.mark.asyncio
    async def test_workflow_end_answer_is_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {
                "event": "workflow_end",
                "data": {"answer": "hello badword world", "origin_answer": "hello badword world"},
            }

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"] == "hello *** world"
        assert result[0]["data"]["origin_answer"] == "hello *** world"

    @pytest.mark.asyncio
    async def test_workflow_end_reply_blocks(self):
        engine = _make_engine(["badword"], "reply", "不允许")

        async def raw_gen():
            yield {"event": "workflow_end", "data": {"answer": "badword"}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"
        assert result[0]["data"]["text"] == "不允许"

    @pytest.mark.asyncio
    async def test_workflow_end_safe_passes_through(self):
        engine = _make_engine(["badword"], "filter")

        async def raw_gen():
            yield {"event": "workflow_end", "data": {"answer": "safe content"}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"] == "safe content"

    # ── agent_node_message tests ──

    @pytest.mark.asyncio
    async def test_agent_node_message_outputs_dict_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {
                "event": "agent_node_message",
                "data": {
                    "outputs": {
                        "role": "assistant",
                        "content": "hello badword world",
                        "reasoning_content": "",
                    },
                },
            }

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["outputs"]["content"] == "hello *** world"

    @pytest.mark.asyncio
    async def test_agent_node_message_outputs_reasoning_cleaned(self):
        engine = _make_engine(["badword"], "replace", "###")

        async def raw_gen():
            yield {
                "event": "agent_node_message",
                "data": {
                    "outputs": {
                        "role": "assistant",
                        "content": "safe",
                        "reasoning_content": "think badword more",
                    },
                },
            }

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["outputs"]["reasoning_content"] == "think ### more"

    @pytest.mark.asyncio
    async def test_agent_node_message_outputs_str_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {"event": "agent_node_message", "data": {"outputs": "badword here"}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["outputs"] == "*** here"

    @pytest.mark.asyncio
    async def test_agent_node_message_inputs_not_moderated(self):
        """inputs 是用户输入回显，不应在输出审核中处理（输入审核阶段已拦截）"""
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {
                "event": "agent_node_message",
                "data": {
                    "inputs": [
                        {"role": "user", "content": "badword query"},
                    ],
                    "outputs": {"content": "safe"},
                },
            }

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        # inputs 保持原样
        assert result[0]["data"]["inputs"][0]["content"] == "badword query"

    @pytest.mark.asyncio
    async def test_agent_node_message_reply_blocks(self):
        engine = _make_engine(["badword"], "reply", "blocked")

        async def raw_gen():
            yield {
                "event": "agent_node_message",
                "data": {"outputs": {"content": "badword"}},
            }
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"
        assert result[0]["data"]["text"] == "blocked"

    # ── intermediate_message tests ──

    @pytest.mark.asyncio
    async def test_intermediate_message_list_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {
                "event": "intermediate_message",
                "data": {
                    "answer": [
                        {"role": "assistant", "content": "badword output"},
                        {"role": "tool", "content": "safe result"},
                    ],
                },
            }

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"][0]["content"] == "*** output"
        assert result[0]["data"]["answer"][1]["content"] == "safe result"

    @pytest.mark.asyncio
    async def test_intermediate_message_str_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {"event": "intermediate_message", "data": {"answer": "badword here"}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["answer"] == "*** here"

    # ── REPLY action coverage tests ──

    @pytest.mark.asyncio
    async def test_message_end_origin_answer_reply_blocks(self):
        """origin_answer 命中 REPLY 也应阻断流（Finding 1.3 修复验证）"""
        engine = _make_engine(["badword"], "reply", "blocked")

        async def raw_gen():
            yield {"event": "message_end", "data": {"answer": "safe", "think": "", "origin_answer": "badword here"}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"
        assert result[0]["data"]["text"] == "blocked"

    @pytest.mark.asyncio
    async def test_intermediate_message_list_reply_blocks(self):
        """intermediate_message 列表项命中 REPLY 也应阻断流（Finding 1.4 修复验证）"""
        engine = _make_engine(["badword"], "reply", "blocked")

        async def raw_gen():
            yield {
                "event": "intermediate_message",
                "data": {"answer": [{"role": "assistant", "content": "badword output"}]},
            }
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"

    @pytest.mark.asyncio
    async def test_intermediate_message_str_reply_blocks(self):
        engine = _make_engine(["badword"], "reply", "blocked")

        async def raw_gen():
            yield {"event": "intermediate_message", "data": {"answer": "badword here"}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"

    @pytest.mark.asyncio
    async def test_summary_response_reply_blocks(self):
        """summary_response 命中 REPLY 也应阻断流（Finding 1.5 修复验证）"""
        engine = _make_engine(["badword"], "reply", "blocked")

        async def raw_gen():
            yield {"event": "summary_response", "data": {"answer": {"role": "assistant", "content": "badword here"}}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"

    # ── workflow_node_message tests ──

    @pytest.mark.asyncio
    async def test_workflow_node_message_str_outputs_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {"event": "workflow_node_message", "data": {"outputs": "badword here"}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["outputs"] == "*** here"

    @pytest.mark.asyncio
    async def test_workflow_node_message_dict_outputs_cleaned(self):
        engine = _make_engine(["badword"], "replace", "***")

        async def raw_gen():
            yield {"event": "workflow_node_message", "data": {"outputs": {"text": "badword here"}}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert result[0]["data"]["outputs"]["text"] == "*** here"

    @pytest.mark.asyncio
    async def test_workflow_node_message_reply_blocks(self):
        engine = _make_engine(["badword"], "reply", "blocked")

        async def raw_gen():
            yield {"event": "workflow_node_message", "data": {"outputs": "badword"}}
            yield {"event": "done", "data": {}}

        result = await _collect(apply_stream_moderation(raw_gen(), engine))
        assert len(result) == 1
        assert result[0]["event"] == "sensitive"


class TestBlockEventGenerator:

    @pytest.mark.asyncio
    async def test_workflow_mode_generates_correct_sequence(self):
        result = await _collect(block_event_generator("blocked msg", "workflow", "exec-1"))
        events = [r for r in result if isinstance(r, dict)]
        event_names = [e["event"] for e in events]
        assert "message" in event_names
        assert "workflow_end" in event_names
        assert "done" in event_names

    @pytest.mark.asyncio
    async def test_react_mode_generates_message_and_done(self):
        result = await _collect(block_event_generator("blocked msg", "ReAct", "exec-1"))
        events = [r for r in result if isinstance(r, dict)]
        event_names = [e["event"] for e in events]
        assert "message" in event_names
        assert "done" in event_names
        assert "workflow_end" not in event_names

    @pytest.mark.asyncio
    async def test_default_mode_generates_message_and_done(self):
        result = await _collect(block_event_generator("blocked msg", "Controller", "exec-1"))
        events = [r for r in result if isinstance(r, dict)]
        event_names = [e["event"] for e in events]
        assert "message" in event_names
        assert "done" in event_names


class TestInitModerationFromIr:

    @staticmethod
    def test_disabled_returns_none():
        result = init_moderation_from_ir({"configs": {"content_review": {"enabled": False}}})
        assert result is None

    @staticmethod
    def test_no_config_returns_none():
        result = init_moderation_from_ir({"configs": {}})
        assert result is None

    @staticmethod
    def test_no_configs_key_returns_none():
        result = init_moderation_from_ir({})
        assert result is None

    @staticmethod
    def test_enabled_returns_engine():
        ir_json = {
            "configs": {
                "content_review": {
                    "enabled": True,
                    "rules": [{
                        "keywords": ["badword"],
                        "actions": {"output": {"enable": True, "type": "filter", "content": ""}},
                    }],
                },
            },
        }
        engine = init_moderation_from_ir(ir_json)
        assert engine is not None
        assert engine.enabled is True
