# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Utilities for orchestration modules"""

__all__ = ("ExecutorService", "wait_until_timeout")

import asyncio
import threading
from collections.abc import Mapping
from os import environ

from jiuwen.common.config import config
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import safe_json_loads_raise_exception
from jiuwen.executor_sdk.client.executor_client import ExecutorClient


class ExecutorService:
    """
    Class for Executor Service.

    Attributes:
       _EXECUTOR_MGR_CONFIGS (dict): The configurations for the executor manager.
       _EXECUTOR_WORKER_CONFIGS (tuple): The configurations for the executor worker.
       __instance_lock (threading.Lock): The lock for the singleton instance.
       __instance_map (dict[str, ExecutorClient]): The map for the singleton instances.
    """

    _EXECUTOR_MGR_CONFIGS = dict(
        ip_address="EXECUTOR_MANAGER_HOST",
        user_id="EXECUTOR_MANAGER_USER_ID",
        project_id="EXECUTOR_MANAGER_PROJECT_ID",
    )
    _config_executor: dict = config.get("executor", dict()).get("worker")
    # config name | name in environ | post process | default val in config
    _EXECUTOR_WORKER_CONFIGS = (
        ("endpoints", "EXECUTOR_WORKER_ENDPOINTS", lambda x: x, ""),
        ("mq_server_host", "EXECUTOR_MQ_SERVER_HOST", lambda x: x, ""),
        (
            "conn_timeout",
            "EXECUTOR_WORKER_CONN_TIMEOUT",
            safe_json_loads_raise_exception,
            _config_executor.get("conn_timeout"),
        ),
        (
            "read_timeout",
            "EXECUTOR_WORKER_READ_TIMEOUT",
            safe_json_loads_raise_exception,
            _config_executor.get("read_timeout"),
        ),
        (
            "resume_interval",
            "EXECUTOR_WORKER_RESUME_INTERVAL",
            safe_json_loads_raise_exception,
            _config_executor.get("resume_interval"),
        ),
        (
            "max_retry_count",
            "EXECUTOR_WORKER_MAX_RETRY",
            safe_json_loads_raise_exception,
            _config_executor.get("max_retry"),
        ),
        (
            "thread_num",
            "EXECUTOR_WORKER_THREAD_NUM",
            safe_json_loads_raise_exception,
            _config_executor.get("thread_num"),
        ),
        (
            "stream_out_mode",
            "EXECUTOR_WORKER_STREAM_OUT_MODE",
            lambda x: x,
            _config_executor.get("stream_out_mode") or "mq",
        ),
    )
    # Executor client has default value for items in _EXECUTOR_TLS_CONFIGS and _EXECUTOR_TLS_PROPERTIES
    _EXECUTOR_TLS_CONFIGS = (
        ("use_tls", "EXECUTOR_WORKER_TLS_ENABLE", safe_json_loads_raise_exception),
        ("enable_hmac", "EXECUTOR_WORKER_TLS_HMAC", safe_json_loads_raise_exception),
        ("cert_pem", "EXECUTOR_WORKER_TLS_CERT", lambda x: x),
        ("key_pem", "EXECUTOR_WORKER_TLS_KEY", lambda x: x),
        ("cafile", "EXECUTOR_WORKER_TLS_CA", lambda x: x),
    )
    _EXECUTOR_TLS_PROPERTIES = (
        ("hmac_auth_key", "EXECUTOR_WORKER_TLS_HMAC_KEY"),
        ("tls_password", "EXECUTOR_WORKER_TLS_PWD"),
    )

    __instance_lock = threading.Lock()
    __instance_map: "dict[str, ExecutorClient]" = dict()

    @staticmethod
    def __mute_close():
        pass

    @classmethod
    def get(cls, value_from: Mapping[str, str] = None) -> ExecutorClient:
        """Get ExecutorClient instance."""
        pass

    @classmethod
    def worker_timeout(cls) -> int:
        """Get executor worker timeout configuration."""
        if "EXECUTOR_WORKER_TIMEOUT" in environ:
            return safe_json_loads_raise_exception(
                environ.get("EXECUTOR_WORKER_TIMEOUT")
            )
        return cls._config_executor.get("timeout", 200_000)


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
    except JiuWenBaseException as e:
        raise e
    except Exception as e:
        raise JiuWenBaseException(
            message=StatusCode.WORKFLOW_EXECUTE_ERROR.errmsg.format(
                f"found unexpected error from wait_until_timeout: {e}"
            ),
            error_code=StatusCode.WORKFLOW_EXECUTE_ERROR.code,
        ) from e


def del_safely(obj, attr_name: str):
    """避免重复del"""
    if hasattr(obj, attr_name):
        delattr(obj, attr_name)
