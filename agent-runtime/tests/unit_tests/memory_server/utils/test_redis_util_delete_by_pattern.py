# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""RedisClient.delete_by_pattern 超限保护分支（MR #2749 检视补充）。

修复前：该分支日志 f-string 引用未定义的 prefix（函数参数为 pattern），
total_batch > 100 时抛 NameError，无法按设计记录警告并停止。

注：redis_util 顶层 import 的 memory_service 包为外部件（本仓与本地
venv 均不存在），测试以 monkeypatch 向 sys.modules 注入桩模块后再导入
被测模块——这也是该分支 CI 环境的真实约束（无法依赖真实 memory_service）。
"""
import importlib
import logging
import sys
from unittest.mock import MagicMock

import pytest

_MEMORY_SERVICE_STUBS = [
    "memory_service",
    "memory_service.i18n",
    "memory_service.i18n.i18n_constant",
    "memory_service.i18n.i18n_util",
    "memory_service.config",
    "memory_service.config.settings",
    "memory_service.exception",
    "memory_service.exception.memory_service_exception",
    "memory_service.exception.error_code",
    "memory_service.scc",
    "memory_service.scc.crypto_utils",
]

BATCH_LIMIT = 100


@pytest.fixture
def redis_client_cls(monkeypatch):
    """桩掉 memory_service 后导入被测模块，返回 RedisClient 类。"""
    for mod in _MEMORY_SERVICE_STUBS:
        monkeypatch.setitem(sys.modules, mod, MagicMock())
    module = importlib.import_module("agent_runtime.memory_server.utils.redis_util")
    return module.RedisClient


class _StubPipeline:
    """记录 delete 次数、execute 返回每键删除 1 的假管道。"""

    def __init__(self, batch_size: int):
        self.batch_size = batch_size
        self.deleted = 0

    def delete(self, key):
        self.deleted += 1
        return self

    def execute(self):
        return [1] * self.batch_size


class _EndlessScanClient:
    """scan_iter 永远吐键的假 client：驱动外层循环跑满 100 批上限。

    scan_iter 产出满批（batch_size 个）后外层因 len(keys_batch) ==
    batch_size 不退出，循环只能由超限保护分支终止。
    """

    def __init__(self, batch_size: int):
        self._batch_size = batch_size
        self.pipeline_calls = 0

    @staticmethod
    def scan_iter(match=None):
        key = b"k"
        while True:
            yield key

    def pipeline(self):
        self.pipeline_calls += 1
        return _StubPipeline(self._batch_size)


def test_over_limit_branch_logs_pattern_and_stops(redis_client_cls, monkeypatch, caplog):
    """超限分支：不抛 NameError、日志带 pattern 值、循环在 101 批终止。"""
    rc = redis_client_cls()
    stub = _EndlessScanClient(batch_size=1000)

    def _fake_get_client():
        return stub

    # 按名替换受保护成员（G.CLS.11：不在类外直接访问；monkeypatch 自动还原）
    monkeypatch.setattr(rc, "_get_client", _fake_get_client)

    logger_name = "agent_runtime.memory_server.utils.redis_util"
    with caplog.at_level(logging.WARNING, logger=logger_name):
        deleted = rc.delete_by_pattern("mem:*")

    # 修复前此处抛 NameError（prefix 未定义），能到这里即已修复
    assert isinstance(deleted, int)
    assert deleted > 0
    # 101 批上限：第 101 批删完后保护分支触发并 break（无无限循环）
    assert stub.pipeline_calls == BATCH_LIMIT + 1
    # 日志引用函数参数 pattern（非未定义的 prefix）
    assert any("pattern=mem:*" in r.message for r in caplog.records)
