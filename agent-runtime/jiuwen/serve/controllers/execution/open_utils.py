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
import threading
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

# 内存命中节流续期：同一 key 两次后台 EXPIRE 的最小间隔（秒）。
# 语义目标："只要条目未过期，调用就会保活它"——300s 合并窗口把热路径的
# Redis 命令量控制在每 key 每 5 分钟一条 EXPIRE，同时保证调用间隔小于
# redis_ttl 的条目在 Redis 中永不过期。
_TTL_REFRESH_INTERVAL_SECONDS = 300

# 后台续期失败后的重试冷却（秒）：短于正常节流窗口，兼顾"尽快重试"与
# "Redis 故障期间不放大任务量与日志量"
_TTL_RETRY_COOLDOWN_SECONDS = 30

# 后台续期任务引用（事件循环对 task 仅持弱引用，须自持防任务中途被 GC）；
# 服务事件循环线程与 APS worker 线程会并发 add/discard/遍历，须加锁
_BACKGROUND_TTL_TASKS: set = set()
_BACKGROUND_TTL_TASKS_LOCK = threading.Lock()


def _discard_background_task(task):
    """任务完成回调：从引用集合移除（加锁防与 drain 的遍历竞态）"""
    with _BACKGROUND_TTL_TASKS_LOCK:
        _BACKGROUND_TTL_TASKS.discard(task)


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
        # Redis 命中直接续期的节流记录：L1 容量不足导致同 key 反复回源时，
        # 避免每次命中都发 EXPIRE；LRU 化防止无限增长。
        # 加锁：APS worker 线程（sync_build_workflow 的临时 loop）与服务事件
        # 循环线程会并发访问，cachetools.LRUCache 非线程安全
        self._renew_ts = LRUCache(max(capacity * 2, 16))
        self._renew_lock = threading.Lock()
        # 内存层锁：APS worker 线程（sync_build_workflow 的临时 loop）与服务
        # 事件循环线程会并发读写 memory_cache（cachetools.LRUCache 非线程安全）；
        # 锁内只做纯内存操作（无 await），无竞争时开销纳秒级
        self._mem_lock = threading.Lock()

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
                 注意：自定义 ttl 的条目不适用滑动续期——后续 should_refresh_ttl
                 续期将统一使用队列级 redis_ttl 重置 TTL（ttl=-1 的永不过期
                 语义会被覆盖），如需保持自定义 TTL 请勿对该队列启用续期。
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
            self._mark_redis_refreshed(unique_key)
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
            self._mark_redis_refreshed(unique_key)
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
                if should_refresh_ttl:
                    self._try_background_ttl_refresh(unique_key, key)
                return value

            value = await self.async_redis_cache.get(unique_key)
            if value is not None:
                # deserialize 先于续期：损坏数据不得续命，且删除以使下次读取回源
                # 重建（与 aget_with_source 一致）；删除后 raise 落入外层 except
                # 返回 None（aget 契约不变）
                try:
                    value = deserialize_object(value) if self.should_serialize else value
                except Exception:
                    try:
                        await self.async_redis_cache.delete(unique_key)
                    except Exception as del_err:
                        logger.warning(
                            f"failed to drop corrupted cache entry {key}: {del_err}"
                        )
                    raise
                refreshed = False
                if (
                    should_refresh_ttl
                    and self.redis_ttl > 0
                    and not self._renew_throttled(unique_key)
                ):
                    # 独立防御：续期失败不能影响已取到的数据返回
                    # （外层 except 会把整个 aget 变成 None，导致上层误判 MISS 回源）；
                    # redis_ttl>0 防护：expire 负 TTL 在 Redis 中会直接删除条目
                    try:
                        # expire 对不存在的 key 返回 False（非异常），仅在续期成功时才标记
                        refreshed = bool(
                            await self.async_redis_cache.expire(
                                unique_key, self.redis_ttl
                            )
                        )
                        if refreshed:
                            self._record_direct_renew(unique_key)
                    except Exception as e:
                        logger.warning(f"cache ttl refresh failed for {key}: {e}")
                self._update_memory_cache(unique_key, value)
                # 回填之后再标记（此刻条目必存在）；expire 失败不标记，下次命中重试；
                # 被节流跳过时从直接续期记录恢复标记（双轨节流互通）
                if refreshed:
                    self._mark_redis_refreshed(unique_key)
                else:
                    self._restore_marker_from_renew_ts(unique_key)
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
                # deserialize 先于续期且失败删 key（与 aget/aget_with_source 一致）：
                # 损坏条目删除后 raise 落入外层 except 返回 None（get 契约不变）
                try:
                    value = deserialize_object(value) if self.should_serialize else value
                except Exception:
                    try:
                        self.redis_cache.delete(unique_key)
                    except Exception as del_err:
                        logger.warning(
                            f"failed to drop corrupted cache entry {key}: {del_err}"
                        )
                    raise
                if (
                    should_refresh_ttl
                    and self.redis_ttl > 0
                    and not self._renew_throttled(unique_key)
                ):
                    # 与 aget 同款防护：redis_ttl>0 防 expire 负 TTL 删 key；
                    # 独立 try 防续期失败拖垮整个 get（外层 except 会误返回 None）
                    try:
                        self.redis_cache.expire(unique_key, self.redis_ttl)
                        self._record_direct_renew(unique_key)
                    except Exception as e:
                        logger.warning(f"cache ttl refresh failed for {key}: {e}")
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
            with self._mem_lock:
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
            with self._mem_lock:
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
            with self._mem_lock:
                self.memory_cache = LRUCache(cache_num)

    def _update_memory_cache(self, key: str, value: Any):
        """刷新内存缓存（保留 Redis 续期时间标记）"""
        expire_time = (
            int((time.time() + self.memory_ttl) * 1000)
            if self.memory_ttl > 0
            else -1
        )
        with self._mem_lock:
            entry = self.memory_cache.get(key) or {}
            self.memory_cache[key] = {
                "expire_time": expire_time,
                "data": value,
                # 上次 Redis TTL 被实际重置的时刻（epoch 秒）；-1 表示从未刷新
                "last_refresh": entry.get("last_refresh", -1.0),
            }

    def _mark_redis_refreshed(self, unique_key: str):
        """记录 Redis TTL 已于此刻重置（aput set / 命中续期成功后调用）"""
        with self._mem_lock:
            entry = self.memory_cache.get(unique_key)
            if entry is not None:
                entry["last_refresh"] = time.time()

    def _refresh_throttle_interval(self) -> float:
        """节流窗口：不超过 redis_ttl 的一半（小 TTL 配置下自动收紧，
        保证续期在条目尚存活时仍可触发，而非静默失效）"""
        return min(_TTL_REFRESH_INTERVAL_SECONDS, self.redis_ttl / 2)

    def _renew_throttled(self, unique_key: str) -> bool:
        """Redis 命中直接续期的节流判断（与内存命中的节流窗口一致）。

        L1 容量不足时同 key 会被反复淘汰回源，若不节流则每次 Redis 命中
        都多发一条 EXPIRE，热路径 Redis 命令量随访问频率成倍增长。
        """
        with self._renew_lock:
            last = self._renew_ts.get(unique_key, -1.0)
        return last > 0 and (time.time() - last) < self._refresh_throttle_interval()

    def _record_direct_renew(self, unique_key: str) -> None:
        """记录一次直接续期（加锁防 worker 线程并发写）"""
        with self._renew_lock:
            self._renew_ts[unique_key] = time.time()

    def _restore_marker_from_renew_ts(self, unique_key: str) -> None:
        """L1 淘汰回填后，从直接续期节流记录恢复 last_refresh。

        Redis 命中被节流跳过续期时回填的内存条目 last_refresh 为 -1，
        下一次内存命中会立即再发一条后台 EXPIRE，弱化节流目标——
        此处将直接续期的时间戳同步过来，使双轨节流互通。
        """
        with self._renew_lock:
            ts = self._renew_ts.get(unique_key, -1.0)
        if ts <= 0:
            return
        with self._mem_lock:
            entry = self.memory_cache.get(unique_key)
            if entry is not None:
                entry["last_refresh"] = ts

    def _try_background_ttl_refresh(self, unique_key: str, key: str):
        """内存命中时节流续期 Redis TTL：后台任务执行，不阻塞读取路径。

        每 _TTL_REFRESH_INTERVAL_SECONDS 至多发起一次，保证"有调用即保活"
        语义的同时，热路径的 Redis 命令量可控（每 key 每 5 分钟一条 EXPIRE）。
        """
        if self.redis_ttl <= 0:
            # 永不过期/未配置 TTL 的队列无续期语义（且 expire 负 TTL 会删 key）
            return
        with self._mem_lock:
            entry = self.memory_cache.get(unique_key)
            if entry is None:
                return
            last_refresh = entry.get("last_refresh", -1.0)
            if (
                last_refresh > 0
                and (time.time() - last_refresh) < self._refresh_throttle_interval()
            ):
                return
            # 乐观标记防止并发协程重复发起；失败由后台任务回滚为冷却时间戳
            entry["last_refresh"] = time.time()
        try:
            task = asyncio.create_task(self._background_expire(unique_key, key))
            with _BACKGROUND_TTL_TASKS_LOCK:
                _BACKGROUND_TTL_TASKS.add(task)
            task.add_done_callback(_discard_background_task)
        except RuntimeError:
            # 无运行中的事件循环（防御）：回滚标记，读取不受影响
            with self._mem_lock:
                cur = self.memory_cache.get(unique_key)
                if cur is not None:
                    cur["last_refresh"] = last_refresh

    async def _background_expire(self, unique_key: str, key: str):
        """后台执行 EXPIRE 续期；失败/超时回滚冷却时间戳，冷却期后自动重试"""
        try:
            # 超时保护：防 Redis 半开连接（TCP 建立但不应答）导致后台任务
            # 长期挂起、_BACKGROUND_TTL_TASKS 缓慢累积
            refreshed = await asyncio.wait_for(
                self.async_redis_cache.expire(unique_key, self.redis_ttl),
                timeout=5,
            )
            if not refreshed:
                # key 已丢失（TTL 过期/淘汰/显式删除）：使内存条目立即过期，
                # 下次读取 miss 后从 OBS 权威源重建（不用内存值直接回写——
                # 内存对象可能已被调用方原地修改；key 为版本化不可变数据，
                # 重建写回同版本相同数据，不影响 apop 显式失效；
                # 且保证 MEM_CACHE_TTL_SECONDS=0 配置下仍能自愈）
                with self._mem_lock:
                    entry = self.memory_cache.get(unique_key)
                    if entry is not None:
                        # 置为过去时间戳使其立即过期（勿用 0/-1：那是永不过期语义）
                        entry["expire_time"] = 1
        except asyncio.CancelledError:
            # 外部取消（如事件循环收尾）：回滚乐观标记，避免节流窗口内漏续期
            # 导致 Redis 条目提前过期；re-raise 保持任务的取消语义
            with self._mem_lock:
                entry = self.memory_cache.get(unique_key)
                if entry is not None:
                    entry["last_refresh"] = -1.0
            raise
        except Exception as e:
            logger.warning(f"cache ttl refresh failed for {key}: {e}")
            with self._mem_lock:
                entry = self.memory_cache.get(unique_key)
                if entry is not None:
                    # 回滚为冷却时间戳而非 -1：Redis 故障期间保留节流，避免每次
                    # 内存命中都新建任务并放大日志；冷却期过后自动重试
                    interval = self._refresh_throttle_interval()
                    cooldown = min(_TTL_RETRY_COOLDOWN_SECONDS, interval / 2)
                    entry["last_refresh"] = time.time() - interval + cooldown

    def _get_from_memory_cache(self, key: str) -> Any:
        """从内存读取缓存"""
        with self._mem_lock:
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

    async def aget_with_source(
        self, key: str, should_refresh_ttl: bool = False
    ) -> tuple[Any, str]:
        """异步按层级查找缓存，返回 (value, source)。

        source 为 'memory' / 'redis' / 'obs'，用于性能日志区分缓存来源。
        未命中任何缓存时返回 (None, '')，调用方需自行从存储加载。
        should_refresh_ttl=True 时 Redis 命中会续期 TTL（expire 失败仅告警）。
        """
        unique_key = self._generate_unique_key(key)

        # memory 缓存
        value = self._get_from_memory_cache(unique_key)
        if value is not None:
            self._update_memory_cache(unique_key, value)
            if should_refresh_ttl:
                self._try_background_ttl_refresh(unique_key, key)
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
            # deserialize 必须先于续期：损坏数据不得续命（否则条目被无限刷新、永不自愈）
            try:
                value = deserialize_object(value) if self.should_serialize else value
            except Exception:
                # 损坏条目：删除以使下次读取回源重建，再抛出原异常（异常契约不变）
                try:
                    await self.async_redis_cache.delete(unique_key)
                except Exception as del_err:
                    logger.warning(
                        f"failed to drop corrupted cache entry {key}: {del_err}"
                    )
                raise
            refreshed = False
            if (
                should_refresh_ttl
                and self.redis_ttl > 0
                and not self._renew_throttled(unique_key)
            ):
                # 独立防御：续期失败不影响已取到的数据（与 aget 同款）；
                # redis_ttl>0 防护：expire 负 TTL 在 Redis 中会直接删除条目
                try:
                    # expire 对不存在的 key 返回 False（非异常），仅在续期成功时才标记
                    refreshed = bool(
                        await self.async_redis_cache.expire(
                            unique_key, self.redis_ttl
                        )
                    )
                    if refreshed:
                        self._record_direct_renew(unique_key)
                except Exception as e:
                    logger.warning(f"cache ttl refresh failed for {key}: {e}")
            self._update_memory_cache(unique_key, value)
            # 回填之后再标记（此刻条目必存在）；expire 失败不标记，下次命中重试；
            # 被节流跳过时从直接续期记录恢复标记（双轨节流互通）
            if refreshed:
                self._mark_redis_refreshed(unique_key)
            else:
                self._restore_marker_from_renew_ts(unique_key)
            return value, "redis"

        return None, ""


def drain_background_ttl_tasks(loop) -> bool:
    """在指定事件循环上运行其挂起的后台续期任务，返回是否有任务被执行。

    供同步桥接函数（如 sync_build_workflow）在关闭临时事件循环前调用：
    后台续期任务绑定创建时的循环，若循环在任务执行前停止，任务会悬挂且
    被 _BACKGROUND_TTL_TASKS 持强引用（阻止循环对象及其 fd 被 GC 回收），
    重复同步构建会持续累积。本函数只处理属于该循环的任务，不影响其他循环。
    """
    with _BACKGROUND_TTL_TASKS_LOCK:
        pending = [
            task
            for task in _BACKGROUND_TTL_TASKS
            if not task.done() and task.get_loop() is loop
        ]
    if not pending:
        return False
    for task in pending:
        try:
            # 逐个运行而非 gather：本函数常在非主线程（如 APS worker）被调用，
            # 无默认事件循环，gather 会触发 get_event_loop 报错
            loop.run_until_complete(task)
        except Exception:
            pass  # 后台续期失败不影响调用方
    return True


def _warn_legacy_cache_ttl(value: int) -> None:
    """启动告警：CACHE_TTL_SECONDS 已不再控制 ir/workflow/agent 三队列。

    显式调优过该变量的部署升级后会静默落到新默认 24h，此告警使变更可感知
    （值等于默认 3600 时不告警——行为无差异）。
    """
    if value != 3600:
        logger.warning(
            "CACHE_TTL_SECONDS=%s no longer controls the ir/workflow/agent "
            "definition caches; they now default to 24h via IR/WORKFLOW/"
            "AGENT_CACHE_TTL_SECONDS. Migrate your tuning to the new "
            "variables to keep the previous behavior",
            value,
        )


# 缓存队列实例
_warn_legacy_cache_ttl(settings.cache.cache_ttl_seconds)
cache_ir_queue = CacheUtils(
    capacity=settings.cache.max_ir_cache_num,
    should_serialize=True,
    cache_name="ir",
    memory_ttl=settings.cache.mem_cache_ttl_seconds,
    redis_ttl=settings.cache.ir_cache_ttl_seconds,
)
cache_workflow_queue = CacheUtils(
    capacity=settings.cache.max_workflow_cache_num,
    should_serialize=True,
    cache_name="workflow",
    # memory_ttl 为内存层 1h 滑动窗口：控制冷 key 的进程内存占用；
    # 后台续期不依赖它（内存命中即可触发，见 _try_background_ttl_refresh）
    memory_ttl=settings.cache.mem_cache_ttl_seconds,
    redis_ttl=settings.cache.workflow_cache_ttl_seconds,
)
cache_agent_queue = CacheUtils(
    capacity=settings.cache.max_agent_cache_num,
    should_serialize=True,
    cache_name="agent",
    # 同上：内存层滑动窗口，控制冷 key 内存占用
    memory_ttl=settings.cache.mem_cache_ttl_seconds,
    redis_ttl=settings.cache.agent_cache_ttl_seconds,
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

    ir_value, source = await cache_ir_queue.aget_with_source(
        path, should_refresh_ttl=True
    )
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
    max_concurrency: Optional[int] = None,
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
            逐个 await "首错即断"语义）。注意三点与串行版的可观测差异：
            ①抛出的是"完成序"首个异常而非"声明序"首个；②fail-fast 时
            其余在飞加载不会被取消，会继续完成并写入缓存（利于重试）。
            故障期流量放大已评估有界：每失败请求额外尝试 ≤ N-k 次且均为
            快速失败（Redis 拒连/OBS 404），瞬时并发恒 ≤ max_concurrency，
            与正常冷构建同处连接池容量包络、不产生新上限；典型一层子节点
            N≤5 时全批已在飞、取消无净收益，大 batch 的 cancel-remaining
            列为后续候选；
            ③同批重复路径共享同一次加载的结果/异常占位，串行版"循环内
            再次遇到同路径时重新加载"的偶发重试在批内不再发生（并发化
            固有：请求级缓存按任务合并同路径的在飞加载，与是否去重无关；
            失败项仍会被剔除出请求级缓存，跨批次再次访问会重新加载）。
        max_concurrency: 单批并发上限，必须 ≥1（<1 抛 ValueError：0 会
            使信号量 acquire 永久阻塞且无报错）。None 表示读
            settings.cache.ir_load_max_concurrency（env
            IR_LOAD_MAX_CONCURRENCY，默认 5，pydantic ge=1 保证非法 env
            启动即报错）。该上限是"每次批量调用"的
            约束而非全局预算：冷缓存下瞬时 Redis 连接需求 ≈ 并发构建
            请求数 × 本值，与 REDIS_MAX_CONNECTIONS（共享池，默认 50，
            池耗尽抛 "Too many connections" 不排队）核算后调整。

    Returns:
        与 paths 等长、按位对齐的结果列表；重复路径返回同一共享对象
        （与缓存返回共享引用一致，调用方不可原地修改）。
    """
    if max_concurrency is None:
        max_concurrency = settings.cache.ir_load_max_concurrency
    if max_concurrency < 1:
        # fail-fast：0 会使 Semaphore acquire 永久阻塞（请求挂起无报错），
        # 负数在 Semaphore 构造处抛错但消息不指向配置项——统一在此显式校验
        raise ValueError(
            f"max_concurrency must be >= 1, got {max_concurrency} "
            "(settings.cache.ir_load_max_concurrency / env IR_LOAD_MAX_CONCURRENCY)"
        )
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
    result_map = dict(zip(unique_paths, unique_results, strict=True))
    return [result_map[p] for p in paths]


@log_function_timing
def ir_load(path: str) -> dict:
    """同步加载IR内容，支持任意Python对象缓存。

    查找顺序：L1 内存 → L2 Redis → L3 OBS/S3
    """
    logger.info("Loading IR content from %s", path)

    # 同步路径不接续期：本函数无调用方，且真实部署的 Redis 客户端为异步实现，
    # 同步 get/put 在其上无法工作（存量限制）；缓存续期仅由异步路径承担
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
