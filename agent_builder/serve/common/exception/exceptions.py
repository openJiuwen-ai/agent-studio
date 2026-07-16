#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""
exceptions
"""

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class BaseJiuwenServerException(JiuWenBaseException):
    """Base server exception class for JiuWen"""

    def __init__(self, err_code: StatusCode, message: str = None):
        super().__init__(
            error_code=err_code.value[0],
            message=(
                f"Server {err_code.value[1]}, root cause={message}"
                if message
                else f"{err_code.value[1]}"
            ),
        )


class ResourceNotFoundException(BaseJiuwenServerException):
    """Exception class for resource is not found"""

    def __init__(self, message: str = None):
        super().__init__(err_code=StatusCode.RESOURCE_NOT_FOUND_ERROR, message=message)


class ParamCheckFailedException(BaseJiuwenServerException):
    """Exception class for parameters checking is failed"""

    def __init__(self, message: str = None):
        super().__init__(err_code=StatusCode.PARAM_CHECK_FAILED_ERROR, message=message)
