#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Provide API interface logging collection related functions."""

import itertools
import json
import time
from functools import wraps
from typing import Iterable

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import prompt_builder_interface_logger
from agent_builder.common.utils.utils import sanitize_input
from flask import Response


def get_status_code(res):
    """get prompt builder status code"""
    flag = "T"
    if res == ({}, StatusCode.INTERNAL_ERROR.code):
        return StatusCode.INTERNAL_ERROR.code, "F"
    if len(res.data) > 500:
        status_code = StatusCode.SUCCESS.code
    else:
        try:
            code = json.loads(res.data).get("code")
            if code == 0:
                status_code = StatusCode.SUCCESS.code
            else:
                status_code = StatusCode.INTERNAL_ERROR.code
                flag = "F"
        except Exception as _:
            status_code = StatusCode.SUCCESS.code
    return status_code, flag


def log_request_prompt_builder_stats(res):
    """This is a decorator function that records statistical information about a request, including the request URL,
    processing time, client IP, and response code. If an exception occurs during the request processing,
    it will catch the exception and logging it, while returning a standard error response.

      Args:
         func: The function that needs to be decorated

      Returns:
         Returns the decorated function
    """

    def decortor(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            A decorator for measuring the execution time of a function.
            Args:
                *args: Arguments passed to the original function.
                **kwargs: Keyword arguments passed to the original function.

            Returns:
                The return value of the original function.
            """
            start_time = time.perf_counter()
            exception = None
            try:
                result = func(*args, **kwargs)  # 执行原始函数
            except Exception as e:
                result = {}, StatusCode.INTERNAL_ERROR.code
                exception = e
            end_time = time.perf_counter()
            processing_time_ms = round((end_time - start_time) * 1000)
            if (
                isinstance(result, Response)
                and hasattr(result, "response")
                and isinstance(result.response, Iterable)
            ):
                # 流式数据获取status
                def check_iter():
                    flag = "T"
                    status_code = StatusCode.SUCCESS.code
                    item = ""
                    try:
                        # 获取第一个元素判断是否exception
                        for chunk in result.response:
                            item = chunk
                            break
                        result.response = itertools.chain([item], result.response)
                    except Exception as iter_except:
                        status_code = StatusCode.INTERNAL_ERROR.code
                        flag = "F"
                        raise iter_except
                    finally:
                        prompt_builder_interface_logger.info(
                            f"host_info|PromptBuilderServer||V1.0|resp|{func.__name__}|"
                            f"{processing_time_ms}|{sanitize_input(flag)}{sanitize_input(status_code)}"
                        )

                check_iter()
                return result.response
            # 确保能获取标准响应代码
            status_code, flag = get_status_code(result)
            # 日志打印请求URL、处理时间、客户端IP和响应码
            prompt_builder_interface_logger.info(
                f"host_info|PromptBuilderServer||V1.0|resp|{func.__name__}|ip_address|"
                f"|{processing_time_ms}|{sanitize_input(flag)}|{sanitize_input(status_code)}|session_id"
            )
            # 异常场景则直接抛出，外层exception_handle.py处理逻辑会处理此异常
            if exception is not None:
                raise exception
            return result

        return wrapper

    return decortor
