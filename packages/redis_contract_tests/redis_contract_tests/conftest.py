# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""契约套件 fixture：目标 Provider 由 REDIS_CONTRACT_TARGET 注入（设计文档 §七）。

未设置 REDIS_CONTRACT_TARGET 时全部用例 skip（套件是骨架/待命状态）。

事件循环约束（契约总则 #5）：客户端绑定创建它的事件循环，跨循环调用是
未定义行为。本套件全程使用**会话级单循环**——fixture 创建与用例执行共用
同一 loop，杜绝 asyncio.run() 每用例新建循环导致的跨循环调用。
"""

import asyncio
import logging
import os

import pytest

from redis_spi.config import RedisProviderSettings
from redis_spi.factory import RedisProviderFactory
from redis_spi.types import SCAN_START

#: 目标 Provider 说明（四形态见包 docstring）。
TARGET_ENV = "REDIS_CONTRACT_TARGET"

logger = logging.getLogger(__name__)

#: 清理扫描的匹配前缀（与 key_prefix fixture 约定一致）。
_CLEANUP_MATCH = b"contract:*"

#: 单批 delete 上限（集群同槽考量之外的防御性分批）。
_DELETE_BATCH = 500


def _target() -> str:
    return os.environ.get(TARGET_ENV, "").strip()


@pytest.fixture(scope="session")
def loop():
    """会话级事件循环：provider_client 在此创建、用例在此执行、销毁也在此。"""
    session_loop = asyncio.new_event_loop()
    yield session_loop
    session_loop.close()


@pytest.fixture(scope="session")
def provider_client(loop):
    """会话级客户端：整个契约跑批复用同一实例（与运行时生命周期一致）。"""
    target = _target()
    if not target:
        pytest.skip(
            f"{TARGET_ENV} not set — contract suite runs against an explicitly "
            f"injected provider target (native / module:Class / file.py:Class / "
            f"registered name)"
        )
    settings = RedisProviderSettings(REDIS_PROVIDER=target)
    client = loop.run_until_complete(RedisProviderFactory.create(settings))
    yield client
    try:
        loop.run_until_complete(_cleanup_keys(client))
    except Exception as exc:  # noqa: BLE001 - 清理失败不得掩盖用例结果
        logger.warning("contract key cleanup failed: %s", exc)
    loop.run_until_complete(client.aclose())


@pytest.fixture()
def key_prefix() -> str:
    """每用例唯一 key 前缀（弱一致 SCAN 与残留数据隔离）。"""
    import uuid

    return f"contract:{uuid.uuid4().hex}:"


async def _cleanup_keys(client) -> None:
    """清理套件写入的 ``contract:*`` key：全量 SCAN → 去重 → 分批 delete。

    循环上限须覆盖整个键空间（真实 Redis SCAN 游标走全部桶，match 只过滤产出）。
    """
    collected: set = set()
    cursor = SCAN_START
    for _ in range(50_000):  # 防御性上限
        batch = await client.scan(cursor, match=_CLEANUP_MATCH)
        collected.update(batch.items)
        cursor = batch.cursor
        if cursor == SCAN_START:
            break
    items = list(collected)
    for start in range(0, len(items), _DELETE_BATCH):
        await client.delete(*items[start:start + _DELETE_BATCH])
