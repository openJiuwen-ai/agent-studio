#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""logger for common and interface."""

__all__ = (
    "logger",
    "interface_logger",
    "prompt_builder_interface_logger",
    "set_thread_session",
)


# Use local adapter logger instead of jiuwen's logger
from agent_builder.adapter.logger_bridge import (
    logger,
    interface_logger,
    prompt_builder_interface_logger,
    set_thread_session,
)
