#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""
exception handler

COM-03 §7.3 第 5 点：``@catch_exception`` 装饰器只抛/映射 descriptor——
异常经 ``agent_builder.common.error_contract`` factory 分类后由 HTTP
builder 输出标准五字段（``error_code/error_msg/error_reason/
error_suggestion/request_id`` + X-Request-Id Header），不再返回含异常
字符串的 ``{code,message}``。legacy 业务码与异常文本只进日志。

wire 变化（基线 #130-132：``{code,message}`` + str(e) → 标准五字段）
已记入出口清单；Flask 业务路由错误码修复归 COM-06。

SYNC-01 P5-R3b（2026-09-22）：旧分支 COM-03 此装饰器已改五字段 + factory
分类。sync_01 独有业务语义保留：ValidationError 字段列表经
``from_pydantic_validation`` 的 allowlist ``safe_details``；JiuWenBaseException
``error_code`` 经 ``from_builder_exception`` 分类透传；Exception 分支原
``_hide_security`` 脱敏由 COM-03 fail-closed（不外露 ``str(e)``）自动满足，
不再单独脱敏。
"""

from functools import wraps, partial
from typing import Type

from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.request_context_bridge import get_request_id
from agent_builder.common.error_contract import factory as error_factory
from agent_builder.common.logging.base import logger
from pydantic import ValidationError


def _current_language() -> str:
    """Flask 请求上下文内读取 x-language（无请求上下文时用默认）。"""
    try:
        from flask import request

        return request.headers.get("x-language", "zh-cn")
    except Exception:
        return "zh-cn"


class ExceptionHandler:
    """server exception handler class"""

    @staticmethod
    def catch_exception(func=None, *, pass_message: "tuple[Type[Exception]]" = None):
        """when catch exception"""
        if func is None:
            return partial(ExceptionHandler.catch_exception, pass_message=pass_message)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValidationError as err:
                descriptor = error_factory.from_pydantic_validation(
                    err, get_request_id() or None)
                logger.warning(f"ValidationError: {descriptor.safe_details}")
                return error_factory.build_flask_error(descriptor, _current_language())
            except JiuWenBaseException as e:
                logger.error(
                    f"JiuWenBaseException: error_code={getattr(e, 'error_code', -1)}",
                    exc_info=True,
                )
                descriptor = error_factory.from_builder_exception(e, get_request_id() or None)
                return error_factory.build_flask_error(descriptor, _current_language())
            except Exception as e:
                logger.error("Unhandled Flask exception", exc_info=True)
                descriptor = error_factory.from_internal(e, get_request_id() or None)
                return error_factory.build_flask_error(descriptor, _current_language())

        return wrapper
