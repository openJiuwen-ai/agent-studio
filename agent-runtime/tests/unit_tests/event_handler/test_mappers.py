# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for mappers.py — NodeStatusMapper, TimeConverter, LatencyMapper."""

from agent_runtime.event_handler.base.mappers import (
    NodeStatusMapper,
    TimeConverter,
    LatencyMapper,
)
from agent_runtime.event_handler.base.enums import NodeStatus, EventStatus


class TestNodeStatusMapper:
    """Node status mapping tests."""

    @staticmethod
    def test_start_status():
        node_status, event_status = NodeStatusMapper.resolve_node_status("start")
        assert node_status == NodeStatus.STARTED.value
        assert event_status == EventStatus.SUCCESS.value

    @staticmethod
    def test_error_status():
        node_status, event_status = NodeStatusMapper.resolve_node_status("error")
        assert node_status == NodeStatus.FINISHED.value
        assert event_status == EventStatus.ERROR.value

    @staticmethod
    def test_finish_status():
        node_status, event_status = NodeStatusMapper.resolve_node_status("finish")
        assert node_status == NodeStatus.FINISHED.value
        assert event_status == EventStatus.SUCCESS.value

    @staticmethod
    def test_running_status():
        node_status, event_status = NodeStatusMapper.resolve_node_status("running")
        assert node_status == NodeStatus.WAITING.value
        assert event_status == EventStatus.WAITING.value

    @staticmethod
    def test_unknown_status_fallback():
        node_status, event_status = NodeStatusMapper.resolve_node_status("unknown")
        assert node_status == NodeStatus.FINISHED.value
        assert event_status == EventStatus.ERROR.value


class TestTimeConverter:
    """Time conversion tests."""

    @staticmethod
    def test_valid_datetime():
        ts = TimeConverter.datetime_to_timestamp_ms("2026-01-01T00:00:00.000000+0000")
        assert ts is not None
        assert isinstance(ts, int)

    @staticmethod
    def test_none_input():
        assert TimeConverter.datetime_to_timestamp_ms(None) is None

    @staticmethod
    def test_empty_string():
        assert TimeConverter.datetime_to_timestamp_ms("") is None

    @staticmethod
    def test_invalid_format():
        assert TimeConverter.datetime_to_timestamp_ms("not-a-date") is None


class TestLatencyMapper:
    """Latency extraction tests."""

    @staticmethod
    def test_get_statistic_latency():
        data = {"answer": {"overall_latency": 1.5, "model_latency": 1.2, "plugin_latency": 0.3}}
        latency = LatencyMapper.get_statistic_latency(data)
        assert latency.overall == 1.5
        assert latency.model == 1.2
        assert latency.plugin == 0.3

    @staticmethod
    def test_get_statistic_latency_empty():
        latency = LatencyMapper.get_statistic_latency({"answer": {}})
        assert latency.to_dict() == {}

    @staticmethod
    def test_get_statistic_latency_no_answer():
        latency = LatencyMapper.get_statistic_latency({})
        assert latency.to_dict() == {}

    @staticmethod
    def test_get_function_call_latency():
        data = {
            "answer": {
                "time_consumption": {
                    "overall_latency": 2.0,
                    "model_latency": 1.5,
                    "plugin_latency": 0.5,
                }
            }
        }
        latency = LatencyMapper.get_function_call_latency(data)
        assert latency.overall == 2.0
        assert latency.model == 1.5
        assert latency.plugin == 0.5

    @staticmethod
    def test_get_function_call_latency_empty():
        latency = LatencyMapper.get_function_call_latency({})
        assert latency.to_dict() == {}

    @staticmethod
    def test_to_dict_skips_none():
        latency = LatencyMapper.get_statistic_latency({"answer": {"overall_latency": 1.0}})
        result = latency.to_dict()
        assert result == {"overall": 1.0}
        assert "model" not in result
        assert "plugin" not in result
