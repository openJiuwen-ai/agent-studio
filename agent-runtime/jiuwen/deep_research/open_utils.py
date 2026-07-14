# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""This module contains open utilities for DeepResearch."""

import base64
import os

import aiohttp
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.net import Connector
from agent_runtime.storage.object_storage import get_storage_provider
from jiuwen.deep_research.env_constants import (
    MAX_TEMPLATE_CACHE_NUM_KEY,
    TEMPLATE_CACHE_ENABLE_KEY,
)
from jiuwen.serve.common.logger.request_logger import log_function_timing
from jiuwen.serve.controllers.execution.open_utils import ConcurrentLimitedQueue

MAX_TEMPLATE_CACHE_NUM = int(os.getenv(MAX_TEMPLATE_CACHE_NUM_KEY, str(100)))
HTTP_STATUS_CODE = 300
cache_template_queue = ConcurrentLimitedQueue(
    capacity=MAX_TEMPLATE_CACHE_NUM, cache_name="template"
)


@log_function_timing
async def async_template_load(path: str, is_external_path: bool) -> str:
    """
    异步加载DeepResearch template内容
    """

    logger.info("Async Loading template content from %s", path)

    cache_template_queue.update_capacity()
    template_value = await cache_template_queue.aget(path)
    if template_value:
        logger.info(
            "Cache HIT! Process %d async got pickled data: %s", os.getpid(), path
        )
        return template_value

    if is_external_path:
        connector = Connector().get_tcp_connector()
        async with aiohttp.ClientSession(
            connector=connector, connector_owner=connector is None
        ) as session:
            async with session.get(url=path) as res:
                if res.status < HTTP_STATUS_CODE:
                    template_bytes = await res.content.read()
                else:
                    content = await res.content.read()
                    logger.error(f"Fail read template. url {path} content: {content}")
                    raise JiuWenBaseException(
                        error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
                        message="Failed to get template file.",
                    )
    else:
        logger.info(
            "Cache MISS! Process %d async loading from OBS: %s", os.getpid(), path
        )
        template_bytes = await get_storage_provider().get_object_bytes(object_key=path)
    template_file_stream = base64.b64encode(template_bytes).decode("utf-8")

    if str(os.environ.get(TEMPLATE_CACHE_ENABLE_KEY, "false")).lower() == "true":
        await cache_template_queue.aput(path, template_file_stream)
        logger.info("Process %d async pickled and cached data: %s", os.getpid(), path)

    return template_file_stream
