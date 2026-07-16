#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import asyncio

from agent_builder.common.logging.base import logger

WAIT_FOR_USER_INPUT_TIMEOUT = 600
WAIT_FOR_USER_INPUT_TIMEOUT_ERROR_MESSAGE = (
    "等待输入时长达 {} 秒，对话关闭。请重新开始对话".format(WAIT_FOR_USER_INPUT_TIMEOUT)
)


async def wait_until_timeout(task, timeout: int, default_result=None):
    """
    异步任务超时自动取消
    参数：
        task：为异步任务
        timeout：超时时间
        default_result：超时默认返回信息
    """
    try:
        return await asyncio.wait_for(task, timeout)
    except asyncio.TimeoutError:
        logger.error("挂起任务时长达到 {} 秒，任务自动取消".format(timeout))
        return default_result
