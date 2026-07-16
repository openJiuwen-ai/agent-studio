#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.

"""base exception for promptengine"""

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class BasePromptException(JiuWenBaseException):
    """
    Base Prompt Exception
    """

    def __init__(self, err_code: StatusCode, message: str = None):
        super().__init__(
            error_code=err_code.value[0],
            message=(
                f"{err_code.value[1]}, root cause={message}"
                if message
                else f"{err_code.value[1]}"
            ),
        )
