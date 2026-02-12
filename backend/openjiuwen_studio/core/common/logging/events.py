# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from dataclasses import (
    dataclass
)
from enum import Enum
from typing import (
    Dict,
    Optional,
)
from openjiuwen.core.common.logging.events import (
    BaseLogEvent,
    ModuleType,
    register_event_class
)


@dataclass
class InterfaceEvent(BaseLogEvent):
    """Interface related event"""
    interface_name: Optional[str] = None # interface name
    execution_time_ms: Optional[float] = None  # Execution time (milliseconds)

    def __post_init__(self):
        super().__post_init__()
        self.module_type = ModuleType.SYSTEM


class CustomLogEventType(Enum):
    # Interface events
    INTERFACE_CLI = "interface_cli"  # Interface client
    INTERFACE_SRV = "interface_srv"  # Interface service


_CUSTOM_EVENT_CLASS_MAP: Dict[CustomLogEventType, type] = {
    # Interface events
    CustomLogEventType.INTERFACE_CLI: InterfaceEvent,
    CustomLogEventType.INTERFACE_SRV: InterfaceEvent,
}


def regist_log_event():
    # regist custom event class
    for event_type_enum, event_class in _CUSTOM_EVENT_CLASS_MAP.items():
        register_event_class(event_type_enum.value, event_class)


regist_log_event()
