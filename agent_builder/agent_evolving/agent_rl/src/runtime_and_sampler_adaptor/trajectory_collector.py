# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
import json
from functools import wraps

from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


def async_retry_on_exception(max_retries_attr):
    """
    Retry an async instance method on exception with exponential backoff.
    Max retries are read from a self attribute.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            max_retries = getattr(self, max_retries_attr)
            for retry_count in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    logger.info(f"Attempt {retry_count + 1} failed: {e}")
                    if retry_count < max_retries - 1:
                        wait_time = 2 ** (retry_count + 1)
                        logger.info(f"Waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning("Max retries reached")
            return []

        return wrapper

    return decorator


class SpanBuilder:
    def __init__(self):
        self.max_retry = 3

    @staticmethod
    def span_filter(text):
        """Extract valid LLM spans from streamed JSON response text."""
        text = text.replace("None", "null")
        text_list = text.strip().split("\n\n")
        response_list = []
        for line in text_list:
            if line.startswith("data: "):
                json_str = line[len("data: ") :]
                try:
                    data = json.loads(json_str)
                    if (
                        "data" in data
                        and data["data"]["invokeType"] == "llm"
                        and data["data"]["outputs"]
                    ):
                        response_list.append(data)
                except Exception as e:
                    logger.error(f"Error occurred when filtering span:{e}")
        return response_list

    @async_retry_on_exception(max_retries_attr="max_retry")
    async def processing_ir(self, task_sample):
        """
        Send an async POST request with updated query, then parse and filter response spans
        Input : task_sample (dict) – data sample
        Output: valid_span_list (List[Any]) – filtered spans parsed from the response
        """
        pass
