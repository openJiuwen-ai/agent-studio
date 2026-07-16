#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""
exception handler
"""

import re
from functools import wraps, partial
from typing import Type

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.common.utils.utils import sanitize_input
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from pydantic import ValidationError

CODE = "code"
MESSAGE = "message"


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
                err: ValidationError
                err_msg = []
                data = err.errors()
                for i in data:
                    loc = "".join(
                        ("." + seg) if isinstance(seg, str) else f"[{seg}]"
                        for seg in i["loc"]
                    ).lstrip(".")
                    err_msg.append(loc + ": " + i["msg"])
                return {
                    CODE: StatusCode.PARAM_CHECK_FAILED_ERROR.code,
                    MESSAGE: StatusCode.PARAM_CHECK_FAILED_ERROR.errmsg
                    + ". Fields: "
                    + "; ".join(err_msg),
                }, 400
            except JiuWenBaseException as e:
                return {CODE: e.error_code, MESSAGE: e.message}, 500
            except Exception as e:
                msg = _hide_security(e)
                logger.debug(f"msg to client: {sanitize_input(msg)}", exc_info=True)
                return {CODE: StatusCode.ERROR.code, MESSAGE: msg}, 500

        return wrapper


def _hide_security(e: Exception) -> str:
    msg: str = str(e)
    # Hide all address info
    msg = re.sub(r"<([a-zA-Z0-9_.]+) object at 0x([0-9a-fA-F]+)>", r"<one \1>", msg)
    return msg
