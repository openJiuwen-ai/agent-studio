# coding=utf-8
"""
Logger bridge: delegates to agent-core (openjiuwen) logging system.

Re-exports agent-core's named loggers and session ID management,
providing the same interface used by 34+ consumer files.

agent-core capabilities used:
  - openjiuwen.core.common.logging.logger (LazyLogger, "common")
  - openjiuwen.core.common.logging.interface_logger (LazyLogger, "interface")
  - openjiuwen.core.common.logging.prompt_builder_logger (LazyLogger, "prompt_builder")
  - openjiuwen.core.common.logging.set_session_id / get_session_id
"""

from openjiuwen.core.common.logging import (
    logger,
    interface_logger,
    prompt_builder_logger as prompt_builder_interface_logger,
    set_session_id,
    get_session_id,
)


def set_thread_session(trace_id: str = ""):
    """Set the trace/session ID for the current context.

    Bridges the old jiuwen set_thread_session() to agent-core's set_session_id().
    """
    set_session_id(trace_id or "")


def get_thread_session() -> str:
    """Get the trace/session ID for the current context.

    Bridges the old jiuwen get_thread_session() to agent-core's get_session_id().
    """
    return get_session_id() or ""
