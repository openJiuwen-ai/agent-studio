# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""执行状态管理器。

Phase 4 第五批清理（设计文档 §六）：老 jiuwen 分布式 worker 拓扑
（celery/aps worker + add_job 投递链 + 其 Web 侧配套状态/结果管理器）在新架构
中无分发入口——`EXECUTION_ASYNC_WORKER` 开关未随新 orchestration 移植，分发
函数零生产调用方，worker 即使启动也无任务来源（引用封闭性已逐一核实）。
本次随 worker 文件一并删除，本模块仅保留活路径使用的 ``AsyncStateManager``
（存储介质二选一：redis_spi accessor 装配的 AsyncRedisStateStorage / 进程内
AsyncMemoryStateStorage）。

已删除的死簇类（对齐 lumina 旧树的引用不在此列，那是独立代码拷贝）：
StateManager / AsyncExecStateManager / AsyncExecAsyncStateManager /
ExecutionResultManager / AsyncExecutionResultManager / ApsRedisManager /
AsyncApsRedisManager。
"""

import os

from jiuwen.common.configs.env_constants import EXECUTION_STATE_STORAGE_MEDIUM_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.singleton import Singleton
from jiuwen.serve.common.logger.request_logger import log_function_timing
from jiuwen.serve.controllers.execution.state_storage import (
    AsyncMemoryStateStorage,
    AsyncRedisStateStorage,
)


class AsyncStateManager(metaclass=Singleton):
    """Agent状态管理器"""

    _initialized = False
    _storage_medium = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    async def init(self):
        """init"""
        await self._storage_medium.init()

    @log_function_timing
    async def save_state(self, key, value):
        """根据配置项进行数据库/内存操作：增"""
        await self._storage_medium.set_state(k=key, v=value)

    @log_function_timing
    async def delete_state(self, key):
        """根据配置项进行数据库/内存操作：删"""
        await self._storage_medium.delete_state(k=key)

    @log_function_timing
    async def get_state(self, key):
        """根据配置项进行数据库/内存操作：查"""
        state = await self._storage_medium.get_state(k=key)
        return state

    def _init_storage(self):
        state_storage_medium = os.getenv(
            EXECUTION_STATE_STORAGE_MEDIUM_KEY, "memory"
        ).lower()
        if state_storage_medium == "redis":
            self._storage_medium = AsyncRedisStateStorage()
            logger.info("Initialized async state storage medium: Redis")
        elif state_storage_medium == "memory":
            self._storage_medium = AsyncMemoryStateStorage()
            logger.info("Initialized async state storage medium: Memory")
        else:
            raise JiuWenBaseException(
                error_code=StatusCode.INVALID_STATE_STORAGE_MEDIUM_ERROR.code,
                message=StatusCode.INVALID_STATE_STORAGE_MEDIUM_ERROR.errmsg,
            )
