# coding=utf-8
"""
Exception bridge: delegates to agent-core (openjiuwen) ExecutionError.

JiuWenBaseException now inherits from agent-core's ExecutionError,
integrating into the unified exception hierarchy while preserving
the legacy (error_code, message) interface used by 33+ consumer files.

agent-core capability used:
  - openjiuwen.core.common.exception.errors.ExecutionError
"""

from openjiuwen.core.common.exception.errors import ExecutionError


class _CompatStatus:
    """Wraps an integer error code as a StatusCode-compatible object.

    agent-core's BaseError.__init__ accesses status.code and status.errmsg.
    This shim provides both from a plain int, bridging the old interface.
    """

    def __init__(self, code: int, errmsg: str = ""):
        self.code = code
        self.errmsg = errmsg or f"error code {code}"


class JiuWenBaseException(ExecutionError):
    """
    Unified exception class that inherits from agent-core's ExecutionError.

    Preserves the legacy interface:
    - error_code (int): numeric status code
    - message (str): human-readable error description
    - **kwargs: stored as attributes for backward compat

    Usage:
        raise JiuWenBaseException(error_code=102001, message="LLM call failed")
    """

    def __init__(self, error_code: int, message: str, **kwargs):
        super().__init__(
            status=_CompatStatus(error_code, message),
            msg=message,
        )
        self.error_code = error_code
        # Store any extra context (node_id, node_name, etc.) for compatibility
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f"[{self.error_code}]{self.message}\t"

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(error_code={self.error_code}, message={self.message!r})"
        )


class JiuWenException(JiuWenBaseException):
    """
    General-purpose exception compatible with the original jiuwen JiuWenException.

    Usage:
        raise JiuWenException("config is required")
    """

    def __init__(self, message: str):
        super().__init__(error_code=-1, message=message)


class FileNotFoundException(JiuWenBaseException):
    """Exception raised when a required file is not found."""

    def __init__(self, message: str):
        super().__init__(error_code=-1, message=message)
