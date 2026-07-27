# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""运行时轨迹 — 纯内部状态，不需要校验."""

import time
from dataclasses import dataclass, field
from typing import Optional, Any

from agent_runtime.event_handler.base.enums import EventStatus


@dataclass
class Latency:
    """Runtime latency stats — 内部数据搬运."""
    overall: Optional[float] = None
    model: Optional[float] = None
    plugin: Optional[float] = None

    def to_dict(self) -> dict:
        data = {"overall": self.overall, "model": self.model, "plugin": self.plugin}
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class HistoryMessage:
    """History message for session persistence — 内部数据."""
    role: Optional[str] = None
    content: Optional[str] = None
    create_time: Optional[int] = None
    name: Optional[Any] = None
    function_call: Optional[Any] = None
    tool_calls: Optional[Any] = None
    tool_call_id: Optional[Any] = None
    enable_history: Optional[bool] = None
    intent: Optional[list] = None
    execution_id: Optional[str] = None
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    agent_id: Optional[str] = None
    rating: Optional[int] = None
    files: Optional[list] = None
    reason: Optional[dict] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class NodeMessage:
    """Node message for result recording — 内部数据."""
    role: Optional[str] = None
    content: Optional[str] = None
    origin: Optional[str] = None
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    node_name: Optional[str] = None

    # 对齐旧 Java NodeMessage 的 @JsonProperty 序列化键名（camelCase），
    # 使非流式响应 messages 字段与旧 studio-service 输出一致。
    _CAMEL_KEYS = {"node_id": "nodeId", "node_type": "nodeType", "node_name": "nodeName"}

    def to_dict(self) -> dict:
        return {
            self._CAMEL_KEYS.get(k, k): v
            for k, v in self.__dict__.items()
            if v is not None
        }


@dataclass
class Trace:
    """Runtime data trajectory manager."""
    conversation_id: str = ""
    handler_type: str = "agent"
    instance_id: str = ""
    user_id: str = ""
    version_id: str = ""
    is_debug: bool = False
    language: str = "en-us"
    # 本轮用户输入，用于落库时把 user 一轮写入会话历史（对齐旧 Java 路径的 seed 行为）
    query: str = ""

    # 运行时状态
    start_time: int = field(default_factory=lambda: int(time.time() * 1000))
    end_time: Optional[int] = None
    status: Any = field(default_factory=lambda: EventStatus.SUCCESS.value)
    task_end: bool = False
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    messages: Optional[list] = None
    outputs: Optional[dict] = None
    metadata: Optional[dict] = None
    events: Optional[list] = None
    knowledge_base_files_info: list = field(default_factory=list)
    node_info: Optional[list] = None
    conversation_info: dict = field(default_factory=lambda: {"messages": []})
    dialogue_end: bool = False
    block: bool = False
    execution_id: Optional[str] = None
    pre_event: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None

    def overall_time(self) -> float:
        if self.end_time is None:
            return 0
        return float(self.end_time - self.start_time) / 1000
