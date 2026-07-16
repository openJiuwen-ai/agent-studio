# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for field_processor.py — FieldDataProcessor."""

import json

from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.event_handler.base.trace import Trace


class TestProcessFieldData:
    """process_field_data — dict field expansion."""

    @staticmethod
    def test_expand_field_keys():
        data = {"userFields": {"q": "hello"}, "systemFields": {"x": 1}, "otherKey": "val"}
        result = FieldDataProcessor.process_field_data(data, ["userFields", "systemFields"])
        assert result["q"] == "hello"
        assert result["x"] == 1
        assert result["otherKey"] == "val"

    @staticmethod
    def test_invalid_data_dict():
        assert FieldDataProcessor.process_field_data(None, ["key"]) == {}
        assert FieldDataProcessor.process_field_data("string", ["key"]) == {}

    @staticmethod
    def test_invalid_field_keys():
        assert FieldDataProcessor.process_field_data({"a": 1}, "not-list") == {}

    @staticmethod
    def test_none_values_filtered():
        data = {"key": None, "key2": "val"}
        result = FieldDataProcessor.process_field_data(data, ["key2"])
        assert result == {"key2": "val"}
        assert "key" not in result

    @staticmethod
    def test_field_key_with_non_dict_value():
        data = {"userFields": "not-a-dict"}
        result = FieldDataProcessor.process_field_data(data, ["userFields"])
        assert result["userFields"] == "not-a-dict"


class TestProcessNodeMessage:
    """process_node_message — appends to trace.messages."""

    @staticmethod
    def test_appends_node_message():
        trace = Trace()
        full_data = {
            "data": {
                "node_id": "n1",
                "node_name": "LLM Node",
                "answer": "hello",
                "origin_answer": "raw",
            }
        }
        FieldDataProcessor.process_node_message("LLM", full_data, trace)
        assert trace.messages is not None
        assert len(trace.messages) == 1
        assert trace.messages[0]["role"] == "assistant"
        assert trace.messages[0]["content"] == "hello"
        assert trace.messages[0]["origin"] == "raw"

    @staticmethod
    def test_initializes_messages_when_none():
        trace = Trace()
        assert trace.messages is None
        FieldDataProcessor.process_node_message("LLM", {"data": {}}, trace)
        assert trace.messages is not None
        assert len(trace.messages) == 1


class TestHandleOtherMessage:
    """handle_other_message — intermediate message processing."""

    @staticmethod
    def test_empty_answer():
        trace = Trace()
        FieldDataProcessor.handle_other_message({"answer": []}, [], trace)
        assert trace.conversation_info["messages"] == []

    @staticmethod
    def test_json_string_answer():
        trace = Trace()
        answer_json = json.dumps([{"role": "user", "content": "hi"}])
        FieldDataProcessor.handle_other_message({"answer": answer_json}, [], trace)
        msgs = trace.conversation_info["messages"]
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    @staticmethod
    def test_invalid_json_string():
        trace = Trace()
        FieldDataProcessor.handle_other_message({"answer": "not-valid-json"}, [], trace)
        assert trace.conversation_info["messages"] == []

    @staticmethod
    def test_list_filters_none_values():
        trace = Trace()
        data = {"answer": [{"role": "user", "content": None}, {"role": "assistant", "content": "hi"}]}
        FieldDataProcessor.handle_other_message(data, [], trace)
        msgs = trace.conversation_info["messages"]
        assert len(msgs) == 2
        assert "content" not in msgs[0]
        assert msgs[1]["content"] == "hi"

    @staticmethod
    def test_dict_answer_calls_summary_response():
        trace = Trace()
        data = {"answer": {"role": "assistant", "content": "final"}}
        FieldDataProcessor.handle_other_message(data, [], trace)
        msgs = trace.conversation_info["messages"]
        assert len(msgs) == 1
        assert msgs[0]["role"] == "assistant"


class TestHandleSummaryResponse:
    """handle_summary_response — dedup and append."""

    @staticmethod
    def test_append_when_empty():
        trace = Trace()
        messages = []
        FieldDataProcessor.handle_summary_response(
            {"role": "user", "content": "hi"}, messages, trace
        )
        assert len(messages) == 1

    @staticmethod
    def test_skip_duplicate():
        trace = Trace()
        messages = [{"role": "user", "content": "hi"}]
        FieldDataProcessor.handle_summary_response(
            {"role": "user", "content": "hi"}, messages, trace
        )
        assert len(messages) == 1

    @staticmethod
    def test_append_different_role():
        trace = Trace()
        messages = [{"role": "user", "content": "hi"}]
        FieldDataProcessor.handle_summary_response(
            {"role": "assistant", "content": "hello"}, messages, trace
        )
        assert len(messages) == 2


class TestGenerateErrorEventField:
    """generate_error_event_field — fallback error event."""

    @staticmethod
    def test_with_end_time():
        trace = Trace(
            handler_type="Workflow",
            error_code=103104,
            error_message="fail",
            end_time=5000,
            language="en-us",
        )
        result = FieldDataProcessor.generate_error_event_field(trace)
        assert result.event == "error"
        assert result.created_time == 5000
        assert result.data["code"] == 103104
        assert result.data["error_code"] == "openjiuwen.103104"

    @staticmethod
    def test_without_end_time_uses_current_time():
        trace = Trace(
            handler_type="Workflow",
            error_code=999999,
            error_message="internal",
            end_time=None,
            language="en-us",
        )
        result = FieldDataProcessor.generate_error_event_field(trace)
        assert result.created_time > 0


class TestGenerateMemoryHistoryMessages:
    """generate_memory_history_messages — conversation persistence."""

    @staticmethod
    def test_converts_messages():
        trace = Trace()
        trace.conversation_info["messages"] = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = FieldDataProcessor.generate_memory_history_messages(trace)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert json.loads(result[0]["content"])["content"] == "hi"

    @staticmethod
    def test_empty_messages():
        trace = Trace()
        result = FieldDataProcessor.generate_memory_history_messages(trace)
        assert result == []

    @staticmethod
    def test_non_user_role_becomes_assistant():
        trace = Trace()
        trace.conversation_info["messages"] = [{"role": "tool", "content": "x"}]
        result = FieldDataProcessor.generate_memory_history_messages(trace)
        assert result[0]["role"] == "assistant"
