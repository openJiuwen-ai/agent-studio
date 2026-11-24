# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import json
import os
from typing import Optional

from jiuwen.common.configs.env_constants import (
    DATASOURCE_REDIS_TTL_KEY,
    EXECUTION_STATE_STORAGE_MEDIUM_KEY,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.store.async_redis import get_async_redis_instance
from jiuwen.common.store.redis import get_redis_instance, DEFAULT_REDIS_TTL
from jiuwen.common.utils.singleton import Singleton
from jiuwen.common.utils.utils import safe_json_loads
from jiuwen.serve.common.logger.request_logger import log_function_timing
from jiuwen.serve.controllers.async_execution.aps_server.constants import (
    ACTIVE_WORKERS_KEY,
    JobStatus,
    job_metadata_key,
    worker_running_jobs_key,
    worker_queued_jobs_key,
)
from jiuwen.serve.controllers.execution.constants import DEFAULT_TTL
from jiuwen.serve.controllers.execution.enum import AsyncExecutionStatus
from jiuwen.serve.controllers.execution.state_storage import (
    RedisStateStorage,
    MemoryStateStorage,
    AsyncRedisStateStorage,
    AsyncMemoryStateStorage,
)
from jiuwen.serve.controllers.execution.types import (
    StreamingChatResponse,
    AsyncExecutionState,
)

_UTF8 = "UTF-8"


class StateManager(metaclass=Singleton):
    """Agent状态管理器"""

    _initialized = False
    _storage_medium = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    @log_function_timing
    def save_state(self, key, value):
        """根据配置项进行数据库/内存操作：增"""
        self._storage_medium.set_state(k=key, v=value)

    @log_function_timing
    def delete_state(self, key):
        """根据配置项进行数据库/内存操作：删"""
        self._storage_medium.delete_state(k=key)

    @log_function_timing
    def get_state(self, key):
        """根据配置项进行数据库/内存操作：查"""
        state = self._storage_medium.get_state(k=key)
        return state

    def _init_storage(self):
        state_storage_medium = os.getenv(
            EXECUTION_STATE_STORAGE_MEDIUM_KEY, "memory"
        ).lower()
        if state_storage_medium == "redis":
            self._storage_medium = RedisStateStorage()
            logger.info("Initialized state storage medium: Redis")
        elif state_storage_medium == "memory":
            self._storage_medium = MemoryStateStorage()
            logger.info("Initialized state storage medium: Memory")
        else:
            raise JiuWenBaseException(
                error_code=StatusCode.INVALID_STATE_STORAGE_MEDIUM_ERROR.code,
                message=StatusCode.INVALID_STATE_STORAGE_MEDIUM_ERROR.errmsg,
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


class AsyncExecStateManager(metaclass=Singleton):
    """异步执行状态管理器"""

    _initialized = False
    _storage = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    @staticmethod
    def get_state_key(conv_id: str):
        """生成conversation_id的状态的key"""
        return f"{conv_id}_status"

    def get_state(self, conv_id):
        """进行数据库操作：查"""
        key = self.get_state_key(conv_id)
        return self._storage.get(key)

    def get_state_parsed(self, conv_id) -> Optional[AsyncExecutionState]:
        """进行数据库操作：查，并解析成数据结构"""
        key = self.get_state_key(conv_id)
        state_dict = self._storage.hash_getall(key)
        if not state_dict:
            return None
        conv_state_dict = {
            k.decode("utf-8"): v.decode("utf-8") for k, v in state_dict.items()
        }
        conv_state = AsyncExecutionState.model_validate(conv_state_dict)
        return conv_state

    def set_state_status(self, conv_id: str, status: AsyncExecutionStatus):
        """进行数据库操作：改，修改执行状态，输入为AsyncExecutionStatus枚举值"""
        self._storage.hash_set(
            name=self.get_state_key(conv_id), key="status", value=status.value
        )

    def set_state(self, conv_id, value=""):
        """进行数据库操作：改"""
        key = self.get_state_key(conv_id)
        self._storage.set(key, value)

    def set_state_structure(self, conv_id, value: AsyncExecutionState):
        """进行数据库操作：改，输入为AsyncExecutionState数据结构"""
        key = self.get_state_key(conv_id)
        self._storage.hash_set(
            name=key, mapping={"status": value.status.value, "exec_id": value.exec_id}
        )

    def delete_state(self, conv_id):
        """进行数据库操作：删"""
        key = self.get_state_key(conv_id)
        self._storage.delete(key)

    def _init_storage(self):
        self._storage = get_redis_instance()


class AsyncExecAsyncStateManager(metaclass=Singleton):
    """异步执行状态管理器"""

    _initialized = False
    _storage = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    @staticmethod
    def get_state_key(conv_id: str):
        """生成conversation_id的状态的key"""
        return f"{conv_id}_status"

    async def get_state(self, conv_id):
        """进行数据库操作：查"""
        key = self.get_state_key(conv_id)
        return await self._storage.get(key)

    async def init(self):
        """init"""
        await self._storage.init()

    async def get_state_parsed(self, conv_id) -> Optional[AsyncExecutionState]:
        """进行数据库操作：查，并解析成数据结构"""
        key = self.get_state_key(conv_id)
        state_dict = await self._storage.hash_getall(key)
        if not state_dict:
            return None
        conv_state_dict = {
            k.decode("utf-8"): v.decode("utf-8") for k, v in state_dict.items()
        }
        conv_state = AsyncExecutionState.model_validate(conv_state_dict)
        return conv_state

    async def set_state_status(self, conv_id: str, status: AsyncExecutionStatus):
        """进行数据库操作：改，修改执行状态，输入为AsyncExecutionStatus枚举值"""
        await self._storage.hash_set(
            name=self.get_state_key(conv_id), key="status", value=status.value
        )

    async def set_state(self, conv_id, value=""):
        """进行数据库操作：改"""
        key = self.get_state_key(conv_id)
        await self._storage.set(key, value)

    async def set_state_structure(self, conv_id, value: AsyncExecutionState):
        """进行数据库操作：改，输入为AsyncExecutionState数据结构"""
        key = self.get_state_key(conv_id)
        await self._storage.hash_set(
            name=key, mapping={"status": value.status.value, "exec_id": value.exec_id}
        )

    async def delete_state(self, conv_id):
        """进行数据库操作：删"""
        key = self.get_state_key(conv_id)
        await self._storage.delete(key)

    def _init_storage(self):
        self._storage = get_async_redis_instance()


class ExecutionResultManager(metaclass=Singleton):
    """工作流执行结果管理器"""

    _initialized = False
    _storage = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    def append_message(self, key, value: StreamingChatResponse):
        """进行数据库操作：在某个key对应的消息列表的末尾加上一条消息"""
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_TTL))
        message_str = value.model_dump_json(by_alias=True, exclude_none=True)
        self._storage.list_append(key, message_str, ttl=ttl)

    def get_messages(self, key):
        """进行数据库操作：根据对应的key取消息列表"""
        messages = self._storage.list_get(key)
        messages_parsed = []
        for msg in messages:
            msg_dict = safe_json_loads(msg.decode(_UTF8))
            msg_parsed = StreamingChatResponse.model_validate(msg_dict)
            messages_parsed.append(msg_parsed)
        return messages_parsed

    def delete_result(self, key):
        """进行数据库操作：删"""
        self._storage.delete(key)

    def _init_storage(self):
        self._storage = get_redis_instance()


class AsyncExecutionResultManager(metaclass=Singleton):
    """工作流执行结果管理器"""

    _initialized = False
    _storage = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    async def init(self):
        """init"""
        await self._storage.init()

    async def append_message(self, key, value: StreamingChatResponse):
        """进行数据库操作：在某个key对应的消息列表的末尾加上一条消息"""
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_TTL))
        message_str = value.model_dump_json(by_alias=True, exclude_none=True)
        await self._storage.list_append(key, message_str, ttl=ttl)

    async def get_messages(self, key):
        """进行数据库操作：根据对应的key取消息列表"""
        messages = await self._storage.list_get(key)
        messages_parsed = []
        for msg in messages:
            msg_dict = safe_json_loads(msg.decode(_UTF8))
            msg_parsed = StreamingChatResponse.model_validate(msg_dict)
            messages_parsed.append(msg_parsed)
        return messages_parsed

    async def delete_result(self, key):
        """进行数据库操作：删"""
        await self._storage.delete(key)

    def _init_storage(self):
        self._storage = get_async_redis_instance()


class ApsRedisManager(metaclass=Singleton):
    """
    作流执行结果管理器
    """

    _initialized = False
    _storage = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    def get_active_workers(self):
        """
        从Redis获取活跃Worker列表
        """
        return self._storage.get_redis_client().smembers(ACTIVE_WORKERS_KEY)

    def set_job_metadata(
        self,
        exec_id,
        job_status: JobStatus = None,
        worker_id: str = None,
        conv_id: str = None,
    ):
        """
        设置任务元数据
        """
        mapping = {}
        if job_status:
            mapping.update({"status": job_status})
        if worker_id:
            mapping.update({"worker_id": worker_id})
        if conv_id:
            mapping.update({"conversation_id": conv_id})
        if mapping:
            self._storage.hash_set(name=job_metadata_key(exec_id), mapping=mapping)

    def get_job_metadata(self, job_id: str):
        """
        获取任务元数据
        """
        res = self._storage.get_redis_client().hgetall(name=job_metadata_key(job_id))
        return {k.decode("utf-8"): v.decode("utf-8") for k, v in res.items()}

    def add_job_to_queued_jobs(self, worker_id, task_data: dict):
        """
        将任务添加到某个worker上待处理任务队列
        """
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL))
        self._storage.list_append(
            worker_queued_jobs_key(worker_id), json.dumps(task_data), ttl=ttl
        )

    def add_job_to_running_jobs(self, worker_id: str, job_id: str):
        """
        将任务添加到某个worker上正在运行的任务列表
        """
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL))
        self._storage.list_append(worker_running_jobs_key(worker_id), job_id, ttl=ttl)

    def remove_job_from_running_jobs(self, worker_id: str, job_id: str):
        """
        从某个worker上正在运行的任务列表中移除任务
        """
        self._storage.list_remove(worker_running_jobs_key(worker_id), 1, job_id)

    def get_length_of_running_jobs(self, worker_id):
        """
        获取某个worker上正在运行的任务列表的长度
        """
        return self._storage.list_length(worker_running_jobs_key(worker_id))

    def _init_storage(self):
        self._storage = get_redis_instance()


class AsyncApsRedisManager(metaclass=Singleton):
    """
    作流执行结果管理器
    """

    _initialized = False
    _storage = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    async def init(self):
        """init"""
        await self._storage.init()

    async def get_active_workers(self):
        """
        从Redis获取活跃Worker列表
        """
        return await self._storage.get_redis_client().smembers(ACTIVE_WORKERS_KEY)

    async def set_job_metadata(
        self,
        exec_id,
        job_status: JobStatus = None,
        worker_id: str = None,
        conv_id: str = None,
    ):
        """
        设置任务元数据
        """
        mapping = {}
        if job_status:
            mapping.update({"status": job_status})
        if worker_id:
            mapping.update({"worker_id": worker_id})
        if conv_id:
            mapping.update({"conversation_id": conv_id})
        if mapping:
            await self._storage.hash_set(
                name=job_metadata_key(exec_id), mapping=mapping
            )

    async def get_job_metadata(self, job_id: str):
        """
        获取任务元数据
        """
        res = await self._storage.get_redis_client().hgetall(
            name=job_metadata_key(job_id)
        )
        return {k.decode("utf-8"): v.decode("utf-8") for k, v in res.items()}

    async def add_job_to_queued_jobs(self, worker_id, task_data: dict):
        """
        将任务添加到某个worker上待处理任务队列
        """
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL))
        await self._storage.list_append(
            worker_queued_jobs_key(worker_id), json.dumps(task_data), ttl=ttl
        )

    async def add_job_to_running_jobs(self, worker_id: str, job_id: str):
        """
        将任务添加到某个worker上正在运行的任务列表
        """
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL))
        await self._storage.list_append(
            worker_running_jobs_key(worker_id), job_id, ttl=ttl
        )

    async def remove_job_from_running_jobs(self, worker_id: str, job_id: str):
        """
        从某个worker上正在运行的任务列表中移除任务
        """
        await self._storage.list_remove(worker_running_jobs_key(worker_id), 1, job_id)

    async def get_length_of_running_jobs(self, worker_id):
        """
        获取某个worker上正在运行的任务列表的长度
        """
        return await self._storage.list_length(worker_running_jobs_key(worker_id))

    def _init_storage(self):
        self._storage = get_async_redis_instance()
