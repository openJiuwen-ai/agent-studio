# coding: utf-8
"""代码执行节点结果缓存：基于 (code, exec_env, inputs, outputs_schema) hash 的进程内 LRU。

命中时跳过执行直接返回 (result_dict, function_log)，用于降低代码节点重复执行的时延。
仅缓存成功结果；读写均做 deepcopy，避免上游对返回值的修改污染缓存。
通过 CODE_EXECUTION_RESULT_CACHE_ENABLE 开关控制，默认关闭。
"""

import copy
import hashlib
import json
import threading
from collections import OrderedDict

from openjiuwen.core.common.logging import workflow_logger

# 每累计 N 次访问（hits+misses）输出一次汇总统计
_STATS_LOG_INTERVAL = 1000


class CodeResultCache:
    """进程内 LRU 结果缓存，线程安全。

    value 为 (result_dict, function_log) 元组；result_dict 为已做过
    outputs schema 类型转换的最终结果。

    日志：命中/写入/汇总为 WARNING（对齐默认日志级别），未命中为 DEBUG，
    每累计 _STATS_LOG_INTERVAL 次访问输出一次命中率汇总。
    """

    def __init__(self, maxsize: int = 256):
        self.maxsize = max(0, int(maxsize))
        self._store: "OrderedDict[str, tuple[dict, str]]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        """查询缓存。

        Returns:
            命中返回 (result_dict, function_log)（result 为 deepcopy 副本）；未命中返回 None。
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                workflow_logger.debug(
                    "[FlowCodeCache] MISS key=%s total_access=%d",
                    key[:12],
                    self.hits + self.misses,
                )
                return None
            self._store.move_to_end(key)
            self.hits += 1
            total = self.hits + self.misses
            size = len(self._store)
            summary_due = total % _STATS_LOG_INTERVAL == 0
        # 日志与 deepcopy 均在锁外执行，避免日志 I/O / 拷贝开销占锁
        workflow_logger.warning(
            "[FlowCodeCache] HIT key=%s (skip code execution)",
            key[:12],
        )
        if summary_due:
            workflow_logger.warning(
                "[FlowCodeCache] summary: access=%d hit=%d miss=%d "
                "hit_rate=%.1f%% size=%d/%d",
                total,
                self.hits,
                self.misses,
                self.hits / total * 100,
                size,
                self.maxsize,
            )
        result, function_log = entry
        return copy.deepcopy(result), function_log

    def put(self, key: str, result: dict, function_log: str) -> None:
        """写入缓存（maxsize<=0 时为空操作）。"""
        if self.maxsize <= 0 or not isinstance(result, dict):
            return
        with self._lock:
            self._store[key] = (copy.deepcopy(result), function_log)
            self._store.move_to_end(key)
            while len(self._store) > self.maxsize:
                self._store.popitem(last=False)
            size = len(self._store)
        workflow_logger.warning(
            "[FlowCodeCache] PUT key=%s size=%d/%d",
            key[:12],
            size,
            self.maxsize,
        )

    def stats(self) -> dict:
        """返回命中统计，用于验证优化效果。"""
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self.hits,
                "misses": self.misses,
            }


def make_cache_key(
    code: str, exec_env: str, inputs: dict, outputs_schema
) -> str:
    """生成缓存 key：对 code + exec_env + 规范化 inputs + outputs schema 求摘要。

    inputs 为 coerce 之后的输入；outputs_schema 参与hash以覆盖
    _coerce_outputs 语义变化（同一代码不同输出 schema 结果不同）。
    """
    payload = json.dumps(
        {
            "code": code,
            "exec_env": exec_env or "local",
            "inputs": inputs if isinstance(inputs, dict) else {"__raw__": inputs},
            "outputs_schema": outputs_schema or [],
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_instance: CodeResultCache = None
_instance_lock = threading.Lock()


def get_code_result_cache():
    """返回全局结果缓存实例；开关未开启时返回 None。

    开关：CODE_EXECUTION_RESULT_CACHE_ENABLE（默认 false）。
    """
    from agent_runtime.common.config import settings

    if not settings.code_execution.result_cache_enabled:
        return None
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = CodeResultCache(
                    maxsize=settings.code_execution.result_cache_maxsize
                )
                workflow_logger.warning(
                    "[FlowCodeCache] enabled: maxsize=%d",
                    _instance.maxsize,
                )
    return _instance
