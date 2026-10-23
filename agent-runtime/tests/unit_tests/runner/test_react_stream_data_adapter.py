# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ReactStreamDataAdapter interaction interrupt regression tests."""

from types import SimpleNamespace

from agent_runtime.runner.react_stream_data_adapter import ReactStreamDataAdapter


def test_interaction_is_exposed_as_interrupting_message_events():
    adapter = ReactStreamDataAdapter(execution_id="exec-r01")
    chunk = SimpleNamespace(
        type="__interaction__",
        payload=SimpleNamespace(id="questioner-r01", value="请确认是否继续？"),
    )

    events = adapter.adapt(chunk)

    assert [event["event"] for event in events] == [
        "message",
        "message_end",
        "agent_interrupted",
    ]
    assert events[0]["data"] == {
        "answer": "请确认是否继续？",
        "node_id": "questioner-r01",
        "interaction_id": "questioner-r01",
        "should_interrupt": True,
    }
    assert events[1]["data"] == {
        **events[0]["data"],
        "enable_history": True,
    }
    assert all(event["executionId"] == "exec-r01" for event in events)
    assert events[2]["data"] == {
        "reason": "waiting_user_input",
        "state": "interrupted",
        "task_id": "exec-r01",
        "interaction_id": "questioner-r01",
        "node_id": "questioner-r01",
    }
    assert adapter.final_output == "请确认是否继续？"


def test_interaction_accepts_dict_payload_and_structured_question():
    adapter = ReactStreamDataAdapter(execution_id="exec-r01-dict")
    chunk = SimpleNamespace(
        type="__interaction__",
        payload={
            "id": "approval-r01",
            "value": {"question": "是否批准？", "options": ["是", "否"]},
        },
    )

    events = adapter.adapt(chunk)

    assert events[0]["data"]["answer"] == "是否批准？"
    assert events[0]["data"]["interaction_id"] == "approval-r01"
    assert events[0]["data"]["should_interrupt"] is True
