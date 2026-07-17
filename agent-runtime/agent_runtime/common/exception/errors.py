# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from openjiuwen.core.common.exception import errors as _base_errors
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import ExecutionError


class AgentBuilderError(ExecutionError):
    """AgentBuilder-engine-open 专用错误类型，可重试"""

    pass


_EXTENSION_STATUS_CODES = {}


class ExtensionStatusCode:
    """扩展错误码，兼容 StatusCode 接口"""

    def __init__(self, code: int, errmsg: str, name: str = None):
        self.code = code
        self.errmsg = errmsg
        self.name = name or f"CUSTOM_{code}"
        _EXTENSION_STATUS_CODES[code] = self

    def __repr__(self):
        return f"ExtensionStatusCode.{self.name}"


# 预定义扩展错误码
ExtensionStatusCode.AgentBuilder_ENGINE_ERROR = ExtensionStatusCode(
    188901, "AgentBuilder engine error, reason: {reason}", "AgentBuilder_ENGINE_ERROR"
)

ExtensionStatusCode.STORAGE_CONFIG_ERROR = ExtensionStatusCode(
    188910, "storage config error, reason: {reason}", "STORAGE_CONFIG_ERROR"
)

ExtensionStatusCode.STORAGE_READ_ERROR = ExtensionStatusCode(
    188911, "storage read error, reason: {reason}", "STORAGE_READ_ERROR"
)

ExtensionStatusCode.STORAGE_WRITE_ERROR = ExtensionStatusCode(
    188912, "storage write error, reason: {reason}", "STORAGE_WRITE_ERROR"
)

ExtensionStatusCode.IR_BUILD_ERROR = ExtensionStatusCode(
    188920, "IR build error, reason: {reason}", "IR_BUILD_ERROR"
)


def init_exception_registry():
    """初始化扩展异常注册表"""
    from openjiuwen.core.common.exception import status_mapping as sm

    registry = sm._get_exception_class_registry()
    registry["AgentBuilderError"] = AgentBuilderError

    sm.RANGE_RULES.append(((200000, 209999), "AgentBuilderError"))


def _resolve_exception_class(status):
    """为扩展错误码解析异常类型"""
    from openjiuwen.core.common.exception import status_mapping as sm

    exc_name = sm._match_keyword(status.name)
    if exc_name:
        registry = sm._get_exception_class_registry()
        return registry[exc_name]

    exc_name = sm._match_range(status.code)
    if exc_name:
        registry = sm._get_exception_class_registry()
        return registry[exc_name]

    return _base_errors.STATUS_TO_EXCEPTION.get(StatusCode.ERROR, ExecutionError)


def build_error(status, *, msg=None, details=None, cause=None, **kwargs):
    """构建异常实例，支持 StatusCode 和 ExtensionStatusCode"""
    if isinstance(status, ExtensionStatusCode):
        exc_cls = _resolve_exception_class(status)
        return exc_cls(status=status, msg=msg, details=details, cause=cause, **kwargs)
    return _base_errors.build_error(
        status, msg=msg, details=details, cause=cause, **kwargs
    )


def raise_error(status, *, msg=None, details=None, cause=None, **kwargs):
    """统一异常抛出入口"""
    raise build_error(status, msg=msg, details=details, cause=cause, **kwargs)
