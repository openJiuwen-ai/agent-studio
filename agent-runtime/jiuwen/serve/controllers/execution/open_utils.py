# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""This module contains open utilities — CacheUtils (LRU + Redis) and IR loading."""

import asyncio
import builtins
import importlib
import io
import json
import logging
import os
import pickle
import time
from typing import Any, Optional

from cachetools import LRUCache
from common_utils.redis_manager import get_redis_client
from redis import RedisError

from storage import get_storage_provider
from agent_runtime.common.config import settings
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import safe_json_loads_raise_exception
from openjiuwen.core.common.logging import workflow_logger

from jiuwen.serve.common.logger.request_logger import log_function_timing


_IR_LOAD_SLOW_CACHE_HIT_MS = 50


class CacheUtils:
    """内存+Redis二级缓存

    注意：读取方法直接返回缓存引用，不拷贝。调用方不可修改返回对象，
    否则会污染缓存；如需修改请用 copy-on-write（浅拷贝顶层 dict）。
    """

    def __init__(
        self,
        capacity: int,
        should_serialize: bool,
        cache_name: str,
        memory_ttl: int = -1,
        redis_ttl: int = -1,
    ):
        self.memory_cache = LRUCache(capacity)
        self._redis_cache = None
        self._async_redis_cache = None
        self.should_serialize = should_serialize
        self.cache_name = cache_name
        self.memory_ttl = memory_ttl
        self.redis_ttl = redis_ttl

    @property
    def redis_cache(self):
        """惰性获取 Redis 客户端"""
        if self._redis_cache is None:
            self._redis_cache = get_redis_client()
        return self._redis_cache

    @property
    def async_redis_cache(self):
        """惰性获取异步 Redis 客户端"""
        if self._async_redis_cache is None:
            self._async_redis_cache = get_redis_client()
        return self._async_redis_cache

    async def aput(self, key: str, value: Any, ttl: Optional[int] = None):
        """异步刷新内存和redis缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: Redis TTL 覆盖值。None 表示使用 self.redis_ttl；
                 正整数表示自定义秒数；-1 表示永不过期(ex=None)。
        """
        try:
            effective_ttl = self.redis_ttl
            if ttl is not None:
                effective_ttl = None if ttl == -1 else ttl
            unique_key = self._generate_unique_key(key)
            self._update_memory_cache(unique_key, value)
            if self.should_serialize:
                await self.async_redis_cache.set(
                    unique_key, serialize_object(value), ex=effective_ttl
                )
            else:
                await self.async_redis_cache.set(
                    unique_key, value, ex=effective_ttl
                )
            logger.info(
                f"put {key} in {self.cache_name} memory and redis, "
                f"memory size {self.memory_cache.currsize}/{self.memory_cache.maxsize}"
            )
        except Exception as e:
            logger.error(f"cache put error, exception {e}", exc_info=True)

    def put(self, key: str, value: Any, ttl: Optional[int] = None):
        """刷新内存和redis缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: Redis TTL 覆盖值。None 表示使用 self.redis_ttl；
                 正整数表示自定义秒数；-1 表示永不过期(ex=None)。
        """
        try:
            effective_ttl = self.redis_ttl
            if ttl is not None:
                effective_ttl = None if ttl == -1 else ttl
            unique_key = self._generate_unique_key(key)
            self._update_memory_cache(unique_key, value)
            if self.should_serialize:
                self.redis_cache.set(
                    unique_key, serialize_object(value), ex=effective_ttl
                )
            else:
                self.redis_cache.set(unique_key, value, ex=effective_ttl)
            logger.info(
                f"put {key} in {self.cache_name} memory and redis, "
                f"memory size {self.memory_cache.currsize}/{self.memory_cache.maxsize}"
            )
        except Exception as e:
            logger.error(f"cache put error, exception {e}", exc_info=True)

    async def aget(self, key: str, should_refresh_ttl: bool = False) -> Any:
        """根据key读元素，顺序memory->redis"""
        try:
            unique_key = self._generate_unique_key(key)
            value = self._get_from_memory_cache(unique_key)
            if value is not None:
                logger.info(f"memory hit {key} in {self.cache_name} memory")
                self._update_memory_cache(unique_key, value)
                return value

            value = await self.async_redis_cache.get(unique_key)
            if value is not None:
                if should_refresh_ttl:
                    await self.async_redis_cache.expire(unique_key, self.redis_ttl)
                value = deserialize_object(value) if self.should_serialize else value
                self._update_memory_cache(unique_key, value)
                logger.info(
                    f"redis hit, put {key} in {self.cache_name} memory, "
                    f"size {self.memory_cache.currsize}/{self.memory_cache.maxsize}"
                )
            return value
        except Exception as e:
            logger.error(f"cache get error, exception {e}", exc_info=True)
            return None

    def get(self, key: str, should_refresh_ttl: bool = False) -> Any:
        """根据key读元素，顺序memory->redis"""
        try:
            unique_key = self._generate_unique_key(key)
            value = self._get_from_memory_cache(unique_key)
            if value is not None:
                logger.info(f"memory hit {key} in {self.cache_name} memory")
                return value

            value = self.redis_cache.get(unique_key)
            if value is not None:
                if should_refresh_ttl:
                    self.redis_cache.expire(unique_key, self.redis_ttl)
                value = deserialize_object(value) if self.should_serialize else value
                self._update_memory_cache(unique_key, value)
                logger.info(
                    f"redis hit, put {key} in {self.cache_name} memory, "
                    f"size {self.memory_cache.currsize}/{self.memory_cache.maxsize}"
                )
            return value
        except Exception as e:
            logger.error(f"cache get error, exception {e}", exc_info=True)
            return None

    async def apop(self, key: str):
        """删除元素"""
        try:
            unique_key = self._generate_unique_key(key)
            if self.memory_cache.get(unique_key) is not None:
                self.memory_cache.pop(unique_key)
            value = await self.async_redis_cache.get(unique_key)
            if value is not None:
                await self.async_redis_cache.delete(unique_key)
            logger.info(f"pop {key} from {self.cache_name}")
        except Exception as e:
            logger.error(f"cache pop error, exception {e}", exc_info=True)

    def pop(self, key: str):
        """删除元素"""
        try:
            unique_key = self._generate_unique_key(key)
            if self.memory_cache.get(unique_key) is not None:
                self.memory_cache.pop(unique_key)
            if self.redis_cache.get(unique_key) is not None:
                self.redis_cache.delete(unique_key)
            logger.info(f"pop {key} from {self.cache_name}")
        except Exception as e:
            logger.error(f"cache pop error, exception {e}", exc_info=True)

    def update_capacity(self, cache_num=None):
        """更新LRU容量"""
        if cache_num and cache_num != self.memory_cache.maxsize:
            self.memory_cache = LRUCache(cache_num)

    def _update_memory_cache(self, key: str, value: Any):
        """刷新内存缓存"""
        expire_time = (
            int((time.time() + self.memory_ttl) * 1000)
            if self.memory_ttl > 0
            else -1
        )
        self.memory_cache[key] = {"expire_time": expire_time, "data": value}

    def _get_from_memory_cache(self, key: str) -> Any:
        """从内存读取缓存"""
        cached_value = self.memory_cache.get(key)
        if cached_value is not None:
            current_time = int(time.time() * 1000)
            if cached_value["expire_time"] <= 0:
                return cached_value["data"]
            if current_time > cached_value.get("expire_time"):
                self.memory_cache.pop(key)
                return None
            else:
                return cached_value["data"]
        return None

    def _generate_unique_key(self, key: str) -> str:
        """生成key"""
        return f"agent_runtime:{self.cache_name}:{key}"

    async def aget_with_source(self, key: str) -> tuple[Any, str]:
        """异步按层级查找缓存，返回 (value, source)。

        source 为 'memory' / 'redis' / 'obs'，用于性能日志区分缓存来源。
        未命中任何缓存时返回 (None, '')，调用方需自行从存储加载。
        """
        unique_key = self._generate_unique_key(key)

        # memory 缓存
        value = self._get_from_memory_cache(unique_key)
        if value is not None:
            self._update_memory_cache(unique_key, value)
            return value, "memory"

        # redis 缓存（Redis 故障包装为带错误码的框架异常，与 RedisUtils 源头包装约定一致；
        # 传播行为不变：上层 ir_load_failed / run_check 契约均预期 JiuWenBaseException）
        try:
            value = await self.async_redis_cache.get(unique_key)
        except RedisError as e:
            logger.error(f"cache get error, exception {e}", exc_info=True)
            raise JiuWenBaseException(
                StatusCode.REDIS_SERVICE_NOT_FOUND.code,
                StatusCode.REDIS_SERVICE_NOT_FOUND.errmsg,
            ) from e
        if value is not None:
            value = deserialize_object(value) if self.should_serialize else value
            self._update_memory_cache(unique_key, value)
            return value, "redis"

        return None, ""


# 缓存队列实例
cache_ir_queue = CacheUtils(
    capacity=settings.cache.max_ir_cache_num,
    should_serialize=True,
    cache_name="ir",
    memory_ttl=settings.cache.mem_cache_ttl_seconds,
    redis_ttl=settings.cache.cache_ttl_seconds,
)
cache_workflow_queue = CacheUtils(
    capacity=settings.cache.max_workflow_cache_num,
    should_serialize=True,
    cache_name="workflow",
    redis_ttl=settings.cache.cache_ttl_seconds,
)
cache_agent_queue = CacheUtils(
    capacity=settings.cache.max_agent_cache_num,
    should_serialize=True,
    cache_name="agent",
    redis_ttl=settings.cache.cache_ttl_seconds,
)
cache_agent_group_queue = CacheUtils(
    capacity=settings.cache.max_agent_group_cache_num,
    should_serialize=True,
    cache_name="agent_group",
    redis_ttl=settings.cache.cache_ttl_seconds,
)
cache_intent_rule_queue = CacheUtils(
    capacity=settings.cache.max_intent_rule_cache_num,
    should_serialize=True,
    cache_name="intent_rule",
    redis_ttl=settings.cache.cache_ttl_seconds,
)
cache_model_service_queue = CacheUtils(
    capacity=settings.cache.max_model_service_cache_num,
    should_serialize=True,
    cache_name="model_service",
    memory_ttl=settings.cache.model_cache_mem_ttl,
    redis_ttl=settings.cache.model_cache_redis_ttl,
)
cache_model_auth_queue = CacheUtils(
    capacity=settings.cache.max_model_auth_cache_num,
    should_serialize=True,
    cache_name="model_auth",
    memory_ttl=settings.cache.model_cache_mem_ttl,
    redis_ttl=settings.cache.model_cache_redis_ttl,
)


def _log_ir_content(source: str, path: str, ir_data: dict):
    try:
        if not workflow_logger.logger().isEnabledFor(logging.DEBUG):
            return

        _ir_json = json.dumps(ir_data, ensure_ascii=False, default=str)
        workflow_logger.debug(
            "IR content from %s: path=%s, size=%d bytes, content=%s",
            source, path, len(_ir_json), _ir_json,
        )
    except Exception as e:
        logger.warning("Failed to log IR content: source=%s, path=%s, error=%s", source, path, e)


def _get_request_ir_load_cache() -> Optional[dict[str, asyncio.Task]]:
    """Return the current request's in-flight/completed IR load cache."""
    try:
        from agent_runtime.context.request_context import _request_ctx

        cache = getattr(_request_ctx.get(), "ir_load_cache", None)
    except (AttributeError, LookupError):
        return None
    return cache if isinstance(cache, dict) else None


def _discard_failed_request_ir_load(
    request_cache: dict[str, asyncio.Task],
    path: str,
    load_task: asyncio.Task,
) -> None:
    """Evict failed request-local loads while keeping successful results memoized."""
    if not load_task.done():
        return

    try:
        failed = load_task.cancelled() or load_task.exception() is not None
    except asyncio.CancelledError:
        failed = True

    if failed and request_cache.get(path) is load_task:
        request_cache.pop(path, None)


@log_function_timing
async def async_ir_load(path: str) -> dict:
    """Load one IR at most once per request for a given path."""
    request_cache = _get_request_ir_load_cache()
    if request_cache is None:
        return await _async_ir_load_uncached(path)

    load_task = request_cache.get(path)
    if load_task is None:
        load_task = asyncio.create_task(_async_ir_load_uncached(path))
        request_cache[path] = load_task
        load_task.add_done_callback(
            lambda task: _discard_failed_request_ir_load(request_cache, path, task)
        )

    try:
        return await asyncio.shield(load_task)
    except BaseException:
        _discard_failed_request_ir_load(request_cache, path, load_task)
        raise


async def _async_ir_load_uncached(path: str) -> dict:
    """异步加载IR内容，支持任意Python对象缓存。

    查找顺序：memory → redis → obs
    性能日志格式: ir_load|{ms}|{memory|redis|obs}
    """
    from openjiuwen.core.common.logging import performance_logger

    t_start = time.perf_counter()
    # 每次 IR 加载都打 INFO 过于频繁（621 次/10k 行），普通命中只保留 DEBUG。
    logger.debug("Async Loading IR content from %s", path)

    ir_value, source = await cache_ir_queue.aget_with_source(path)
    if ir_value is not None:
        source_label = "OBS" if source == "obs" else source.capitalize()
        if source == "memory":
            # 内存缓存命中（0ms）为预期路径，降级为 DEBUG。
            logger.debug("Cache HIT! Process %d async got cached data: %s", os.getpid(), path)
        else:
            # Redis/OBS 命中同样是常态路径，先用 DEBUG 记录；慢命中在计时后补 INFO。
            logger.debug(
                "%s HIT! Process %d async got cached data: %s, "
                "memory size %d/%d",
                source_label, os.getpid(), path,
                cache_ir_queue.memory_cache.currsize, cache_ir_queue.memory_cache.maxsize,
            )
        cache_elapsed_ms = (
            round((time.perf_counter() - t_start) * 1000)
            if source != "memory"
            else None
        )
        _log_ir_content(source, path, ir_value)
        elapsed_ms = round((time.perf_counter() - t_start) * 1000)
        if cache_elapsed_ms is not None and cache_elapsed_ms > _IR_LOAD_SLOW_CACHE_HIT_MS:
            logger.info(
                "Slow %s HIT! Process %d async got cached data: %s in %d ms, "
                "memory size %d/%d",
                source_label, os.getpid(), path, cache_elapsed_ms,
                cache_ir_queue.memory_cache.currsize, cache_ir_queue.memory_cache.maxsize,
            )
        performance_logger.info(f"ir_load|{elapsed_ms}|{source}")
        return ir_value

    # obs 存储
    logger.info("Cache MISS! Process %d async loading from OBS: %s", os.getpid(), path)
    from agent_runtime.serve.apis.orchestration import _load_ir_json

    ir_data = await _load_ir_json(path)

    _log_ir_content("obs", path, ir_data)

    ir_data["ir_path"] = path
    ir_data["is_published"] = is_ir_published(path)

    if settings.cache.ir_cache_enable and ir_data["is_published"]:
        await cache_ir_queue.aput(path, ir_data)
        logger.info("Process %d async cached data: %s", os.getpid(), path)

    performance_logger.info(f"ir_load|{round((time.perf_counter() - t_start) * 1000)}|obs")
    return ir_data


async def async_ir_load_batch(
    paths: list,
    *,
    return_exceptions: bool = False,
    max_concurrency: int = 10,
) -> list:
    """并发批量加载多个 IR，返回与 paths 按位对齐的结果列表。

    用于构建期一次性拉取多个子 IR（多智能体成员、挂载工作流、子工作流
    定义等），替代 for 循环内逐个 await 的串行 IO 往返；每次加载仍走
    async_ir_load（层级查找 内存 → Redis → OBS 与 TTL 续期行为不变），
    转换/递归逻辑由调用方在预取完成后按原顺序串行执行。

    Args:
        paths: IR 路径列表，可含重复与 None（语义与逐个调用 async_ir_load
            一致，None 会走加载并按各自异常策略处理）。
        return_exceptions: True 时加载失败项以异常对象占位、其余正常返回
            （调用方自行跳过）；False 时首个异常直接抛出（对齐串行版
            逐个 await "首错即断"语义）。
        max_concurrency: 并发上限，防几十个子 IR 同时打满 Redis 连接池
            或 OBS 客户端。

    Returns:
        与 paths 等长、按位对齐的结果列表；重复路径返回同一共享对象
        （与缓存返回共享引用一致，调用方不可原地修改）。
    """
    # 去重保序：相同 path 只发一次实际加载。缓存语义下重复路径本就返回
    # 同一共享对象，去重不改变可见行为，只省重复 IO；不可哈希的畸形
    # path 退化为不去重逐个加载，保持与串行版一致的失败语义
    try:
        unique_paths = list(dict.fromkeys(paths))
        dedup = True
    except TypeError:
        unique_paths = list(paths)
        dedup = False
    if not unique_paths:
        return []
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _load_one(path):
        async with semaphore:
            return await async_ir_load(path)

    unique_results = await asyncio.gather(
        *(_load_one(p) for p in unique_paths),
        return_exceptions=return_exceptions,
    )
    if not dedup:
        # 退化模式未去重，结果已与输入按位对齐，直接返回
        return unique_results
    result_map = dict(zip(unique_paths, unique_results))
    return [result_map[p] for p in paths]


@log_function_timing
def ir_load(path: str) -> dict:
    """同步加载IR内容，支持任意Python对象缓存。

    查找顺序：L1 内存 → L2 Redis → L3 OBS/S3
    """
    logger.info("Loading IR content from %s", path)

    ir_value = cache_ir_queue.get(path)
    if ir_value:
        logger.info("Cache HIT! Process %d got cached data: %s", os.getpid(), path)
        _log_ir_content("cache", path, ir_value)
        return ir_value

    logger.info("Cache MISS! Process %d loading from OBS: %s", os.getpid(), path)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            ir_json_str = pool.submit(
                asyncio.run, get_storage_provider().get_content(path)
            ).result()
    else:
        ir_json_str = asyncio.run(get_storage_provider().get_content(path))

    try:
        ir_data = safe_json_loads_raise_exception(ir_json_str)
    except ValueError as e:
        raise JiuWenBaseException(
            error_code=StatusCode.IR_DATA_JSON_LOAD_FAILED.code,
            message=StatusCode.IR_DATA_JSON_LOAD_FAILED.errmsg
        ) from e

    _log_ir_content("obs", path, ir_data)

    ir_data["ir_path"] = path
    ir_data["is_published"] = is_ir_published(path)

    if str(settings.cache.ir_cache_enable).lower() == "true" and ir_data["is_published"]:
        cache_ir_queue.put(path, ir_data)
        logger.info("Process %d pickled and cached data: %s", os.getpid(), path)

    return ir_data


def is_ir_published(ir_path: str):
    """根据ir_path判断是否为已发布应用"""
    ir_file_name = ir_path.split("/")[-1].split(".")[0]
    if "_" not in ir_file_name:
        return False
    file_name_suffix = ir_file_name.split("_")[-1]
    if file_name_suffix.isdigit() and len(file_name_suffix) == 13:
        return True
    return False


@log_function_timing
def serialize_object(obj):
    """Serializes the given object to bytes using pickle."""
    try:
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        logger.error(
            f"serialize_object failed: type={type(e).__name__}, "
            f"message={str(e)}, obj_type={type(obj).__name__}",
            exc_info=True,
        )
        raise JiuWenBaseException(
            error_code=StatusCode.SERIALIZATION_ERROR.code,
            message=StatusCode.SERIALIZATION_ERROR.errmsg,
        ) from e


class RestrictedUnpickler(pickle.Unpickler):
    """安全反序列化 — 允许所有自定义类型"""

    _class_cache = {}

    def find_class(self, module, name):
        if module == "builtins":
            return getattr(builtins, name)
        cache_key = (module, name)
        if cache_key not in self._class_cache:
            module_obj = importlib.import_module(module)
            self._class_cache[cache_key] = getattr(module_obj, name)
        return self._class_cache[cache_key]


@log_function_timing
def deserialize_object(serialized_data: bytes):
    """Deserializes the given bytes object using RestrictedUnpickler."""
    try:
        return RestrictedUnpickler(io.BytesIO(serialized_data)).load()
    except Exception as e:
        logger.error(
            f"deserialize_object failed: type={type(e).__name__}, "
            f"message={str(e)}, data_len={len(serialized_data) if serialized_data else 0}",
            exc_info=True,
        )
        raise JiuWenBaseException(
            error_code=StatusCode.DESERIALIZATION_ERROR.code,
            message=StatusCode.DESERIALIZATION_ERROR.errmsg,
        ) from e
