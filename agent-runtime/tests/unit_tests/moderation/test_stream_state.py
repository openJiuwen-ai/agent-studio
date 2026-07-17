# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for StreamModeratorState."""

from agent_runtime.moderation.engine import ModerationEngineDynamicAC
from agent_runtime.moderation.stream_state import StreamModeratorState


def _make_engine(keywords, action_type="filter", content=""):
    """Helper: build engine with output rules."""
    config = {
        "enabled": True,
        "rules": [{
            "keywords": keywords,
            "actions": {"output": {"enable": True, "type": action_type, "content": content}},
        }],
    }
    return ModerationEngineDynamicAC(config)


class TestStreamModeratorState:

    @staticmethod
    def test_safe_text_passes_through():
        engine = _make_engine(["badword"], "filter")
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk("hello world")
        assert safe == "hello world"
        assert interrupt == ""

    @staticmethod
    def test_filter_removes_keyword():
        engine = _make_engine(["badword"], "filter")
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk("hello badword world")
        assert "badword" not in safe
        assert interrupt == ""

    @staticmethod
    def test_replace_replaces_keyword():
        engine = _make_engine(["badword"], "replace", "***")
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk("hello badword world")
        assert safe == "hello *** world"
        assert interrupt == ""

    @staticmethod
    def test_reply_blocks_and_returns_fallback():
        engine = _make_engine(["badword"], "reply", "不允许")
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk("hello badword world")
        assert safe == ""
        assert interrupt == "不允许"
        assert state.is_interrupted is True

    @staticmethod
    def test_empty_chunk_passes_through():
        engine = _make_engine(["badword"], "filter")
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk("")
        assert safe == ""
        assert interrupt == ""

    @staticmethod
    def test_none_chunk_passes_through():
        engine = _make_engine(["badword"], "filter")
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk(None)
        assert safe == ""
        assert interrupt == ""

    @staticmethod
    def test_cross_chunk_keyword_detected():
        """Keywords spanning two chunks should be caught."""
        engine = _make_engine(["badword"], "filter")
        state = StreamModeratorState(engine)
        safe1, _ = state.process_chunk("bad")
        safe2, _ = state.process_chunk("word")
        combined = safe1 + safe2
        assert "badword" not in combined

    @staticmethod
    def test_flush_returns_remaining_buffer():
        engine = _make_engine(["badword"], "replace", "***")
        state = StreamModeratorState(engine)
        state.process_chunk("hello ")  # emitted immediately as safe
        state.process_chunk("bad")     # prefix of "badword", held in buffer
        remaining = state.flush()
        assert remaining == "bad"

    @staticmethod
    def test_clean_full_text_replaces():
        engine = _make_engine(["badword"], "replace", "***")
        state = StreamModeratorState(engine)
        result = state.clean_full_text("hello badword world")
        assert result == "hello *** world"

    @staticmethod
    def test_clean_full_text_reply_blocks():
        engine = _make_engine(["badword"], "reply", "blocked")
        state = StreamModeratorState(engine)
        result = state.clean_full_text("hello badword world")
        assert result == "blocked"
        assert state.is_interrupted is True

    @staticmethod
    def test_prefix_suspect_held_in_buffer():
        """A chunk that is a prefix of a keyword should be held, not emitted."""
        engine = _make_engine(["badword"], "filter")
        state = StreamModeratorState(engine)
        safe, _ = state.process_chunk("bad")
        assert safe == ""
        safe2, _ = state.process_chunk(" day")
        assert "bad day" in safe2

    @staticmethod
    def test_disabled_engine_passes_through():
        engine = ModerationEngineDynamicAC({"enabled": False, "rules": []})
        state = StreamModeratorState(engine)
        safe, interrupt = state.process_chunk("anything")
        assert safe == "anything"
        assert interrupt == ""
