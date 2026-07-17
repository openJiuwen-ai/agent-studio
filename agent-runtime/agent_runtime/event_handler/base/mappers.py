# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Event value mappers — 原始数据→结构化值的映射器."""

from datetime import datetime
from typing import Optional

from agent_runtime.event_handler.base.enums import EventStatus, NodeStatus, OriginStatus
from agent_runtime.event_handler.base.constants import TIME_FORMAT
from agent_runtime.event_handler.base.trace import Latency
from agent_runtime.event_handler.base.language import LanguageManager


class NodeStatusMapper:
    """Node status mapper — 原始状态→(节点状态,事件状态) 枚举映射."""

    @staticmethod
    def resolve_node_status(node_type: str) -> tuple[str, dict]:
        if node_type == OriginStatus.START.value:
            return NodeStatus.STARTED.value, EventStatus.SUCCESS.value
        elif node_type == OriginStatus.ERROR.value:
            return NodeStatus.FINISHED.value, EventStatus.ERROR.value
        elif node_type == OriginStatus.FINISH.value:
            return NodeStatus.FINISHED.value, EventStatus.SUCCESS.value
        elif node_type == OriginStatus.RUNNING.value:
            return NodeStatus.WAITING.value, EventStatus.WAITING.value
        else:
            return NodeStatus.FINISHED.value, EventStatus.ERROR.value


class ErrorContextBuilder:
    """Error context builder."""

    _language_manager = LanguageManager()

    @staticmethod
    def get_language_context(language, key):
        error_code = f"openjiuwen.{key}"
        error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder._language_manager.get_error_context(language, key)
        )
        return error_code, error_msg, error_reason, error_suggestion


class TimeConverter:
    """Time format converter."""

    @staticmethod
    def datetime_to_timestamp_ms(datetime_str: Optional[str]) -> Optional[int]:
        if not datetime_str:
            return None
        try:
            dt = datetime.strptime(datetime_str, TIME_FORMAT)
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            return None


class LatencyMapper:
    """Latency mapper — 从dict提取延迟统计."""

    TIME_CONSUMPTION = "time_consumption"
    MODEL_LATENCY = "model_latency"
    OVERALL_LATENCY = "overall_latency"
    PLUGIN_LATENCY = "plugin_latency"
    ANSWER_KEY = "answer"

    @staticmethod
    def get_statistic_latency(data: dict) -> Latency:
        answer = data.get(LatencyMapper.ANSWER_KEY, {})
        overall = answer.get(LatencyMapper.OVERALL_LATENCY)
        model = answer.get(LatencyMapper.MODEL_LATENCY)
        plugin = answer.get(LatencyMapper.PLUGIN_LATENCY)
        return Latency(model=model, overall=overall, plugin=plugin)

    @staticmethod
    def get_function_call_latency(data: dict) -> Latency:
        consumption = data.get(LatencyMapper.ANSWER_KEY, {}).get(LatencyMapper.TIME_CONSUMPTION, {})
        overall = consumption.get(LatencyMapper.OVERALL_LATENCY)
        model = consumption.get(LatencyMapper.MODEL_LATENCY)
        plugin = consumption.get(LatencyMapper.PLUGIN_LATENCY)
        return Latency(model=model, overall=overall, plugin=plugin)
