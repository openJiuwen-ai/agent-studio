#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Provide API interface log collection related functions."""

import asyncio
import hashlib
import json
import logging
import secrets
import time
from functools import wraps

from jiuwen.common.log.base import (
    interface_logger,
    logger,
    prompt_builder_interface_logger,
)
from jiuwen.serve.common.context import request, request_json, is_json


def get_client_ip():
    """
    Obtain the IP address of the client.

    Returns:
        ip (str): IP address of the client
    """
    req = request.get()
    if req.headers.get("X-Forwarded-For"):
        ip = req.headers["X-Forwarded-For"].split(",")[0]
    else:
        ip = req.client.host
    return ip


def log_request_stats(func):
    """This is a decorator function that records statistical information about a request, including the request URL,
    processing time, client IP, and response code. If an exception occurs during the request processing,
    it will catch the exception and log it, while returning a standard error response.

      Args:
         func: The function that needs to be decorated

      Returns:
         Returns the decorated function
    """

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
        flag = "T"  # 假设请求处理成功
        status_code = 200  # 默认成功
        exception = None
        try:
            result = func(*args, **kwargs)  # 执行原始函数
        except Exception as e:
            result = {}, 500
            exception = e
        end_time = time.perf_counter()
        processing_time_ms = round((end_time - start_time) * 1000)
        ip_address = get_client_ip()

        # 确保能获取标准响应代码
        if result is not None and isinstance(result, tuple):
            _, status_code = result if len(result) == 2 else (result[0], status_code)
        if status_code < 200 or status_code > 299:
            flag = "F"

        # 日志打印请求URL、处理时间、客户端IP和响应码
        host_infos = request.get().client.host.split(":") or ["unknown"]
        if is_json(request.get()) and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s JiuWenRequestRecorder request.json = %s",
                func.__name__,
                json.dumps(request_json.get(), ensure_ascii=False),
                simple_log=f"{func.__name__} JiuWenRequestRecorder request.json.",
            )

        interface_logger.info(
            f"{host_infos[0]}|JiuWenServer||V1.0|resp|{func.__name__}|{ip_address}|"
            f"|{processing_time_ms}|{flag}|{status_code}"
        )
        # 异常场景则直接抛出，外层exception_handle.py处理逻辑会处理此异常
        if exception is not None:
            raise exception
        return result

    return wrapper


def get_status_code(res):
    """get prompt builder status code"""
    flag = "T"
    if res == ({}, 500):
        return 500, "F"
    if len(res.data) > 500:
        status_code = 200
    else:
        try:
            code = json.loads(res.data).get("code")
            if code == 0:
                status_code = 200
            else:
                status_code = 500
                flag = "F"
        except Exception as _:
            status_code = 200
    return status_code, flag


def log_function_timing(func):
    """log function timing"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed_time = (time.perf_counter() - start_time) * 1000
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s completed in %.2f ms", func.__name__, elapsed_time)
            return result
        except Exception as e:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"{func.__name__} failed after {elapsed_time:.2f} ms", exc_info=True)
            raise

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            elapsed_time = (time.perf_counter() - start_time) * 1000
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("async %s completed in %.2f ms", func.__name__, elapsed_time)
            return result
        except Exception as e:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"async {func.__name__} failed after {elapsed_time:.2f} ms", exc_info=True)
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


def log_request_prompt_builder_stats(res):
    """This is a decorator function that records statistical information about a request, including the request URL,
    processing time, client IP, and response code. If an exception occurs during the request processing,
    it will catch the exception and log it, while returning a standard error response.

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
            flag = "T"  # 假设请求处理成功
            status_code = 200  # 默认成功
            try:
                result = func(*args, **kwargs)  # 执行原始函数
            except Exception as e:
                result = {}, 500
                exception = e
            try:
                session_id = res.get().get("modelInfo").get("headers").get("session_id")
            except Exception as _:
                session_id = hashlib.sha256(secrets.token_bytes(16)).hexdigest()
            end_time = time.perf_counter()
            processing_time_ms = round((end_time - start_time) * 1000)
            ip_address = get_client_ip()

            # 确保能获取标准响应代码
            if result is not None and isinstance(result, tuple):
                _, status_code = (
                    result if len(result) == 2 else (result[0], status_code)
                )
            if status_code < 200 or status_code > 299:
                flag = "F"

            # 日志打印请求URL、处理时间、客户端IP和响应码
            host_infos = request.get().client.host.split(":") or ["unknown"]
            prompt_builder_interface_logger.info(
                f"{host_infos[0]}|PromptBuilderServer||V1.0|resp|{func.__name__}|{ip_address}|"
                f"|{processing_time_ms}|{flag}|{status_code}|{session_id}",
                simple_log=f"PromptBuilderServer||V1.0|resp|{func.__name__}|"
                f"{processing_time_ms}|{flag}|{status_code}",
            )
            # 异常场景则直接抛出，外层exception_handle.py处理逻辑会处理此异常
            if exception is not None:
                raise exception
            return result

        return wrapper

    return decortor
