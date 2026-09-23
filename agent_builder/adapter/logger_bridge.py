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
try:
    from openjiuwen.core.common.logging import reset_session_id
except ImportError:
    # 兼容 agent-core 未合入 DEF-03：reset_session_id 不存在
    # set_session_id 旧版不返回 token → trace_token=None → reset 跳过
    def reset_session_id(_token):
        pass

# 显式 re-export 清单（避免 ruff F401 误报 unused；COM-05 DEF-05 对齐旧分支）
common = logger  # DEF-05 §5.4 alias

__all__ = [
    "logger",
    "common",
    "interface_logger",
    "prompt_builder_interface_logger",
    "set_session_id",
    "reset_session_id",
    "get_session_id",
    "set_thread_session",
    "get_thread_session",
]


def set_thread_session(trace_id: str = ""):
    """Set the trace/session ID for the current context.

    Bridges the old jiuwen set_thread_session() to agent-core's set_session_id().
    Legacy compat alias — **discards the returned Token**. New request-lifecycle
    code must use ``set_session_id() -> Token`` + ``reset_session_id(token)``
    (COM-05); this alias is kept only for存量 callers.
    """
    set_session_id(trace_id or "")


def get_thread_session() -> str:
    """Get the trace/session ID for the current context.

    Bridges the old jiuwen get_thread_session() to agent-core's get_session_id().
    """
    return get_session_id() or ""
