# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""会话历史后台落库跨轮竞态回归测试（PR 2330 检视报告 §2/§7）。

用真实 ConversationManager 读改写代码，仅将 Redis 客户端替换为可控时序的
内存假实现（SET 注入延迟模拟大会话历史写耗时）。三场景：
1. 旧序（await 落库完再放行下一轮）——消息完整；
2. 后台落库未完成即开始下一轮（无 join）——脏读 + 丢消息（竞态文档化）；
3. 后台落库 + 下一轮入口 await_pending join——消息完整（修复验证）。
"""

import asyncio
import json
from unittest.mock import patch

import pytest

from agent_runtime.common.background_task import await_pending, run_in_background
from agent_runtime.event_handler.base import conversation as conv_mod
from agent_runtime.event_handler.base.conversation import ConversationManager
from agent_runtime.event_handler.base.trace import Trace

FULL_HISTORY = ["t0-q", "t0-a", "t1-q", "t1-a", "t2-q", "t2-a"]


class FakeRedis:
    """内存 Redis：set 支持注入延迟模拟大 payload 写耗时。"""

    def __init__(self):
        self.store = {}
        self.set_delay = 0.0

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        if self.set_delay:
            await asyncio.sleep(self.set_delay)
        self.store[key] = value
        return True

    async def expire(self, key, ttl):
        return True


def _seed(fake: FakeRedis, key: str) -> None:
    fake.store.clear()
    fake.store[key] = json.dumps({
        "lastUpdateTime": 1,
        "messageList": [
            {"role": "user", "content": "t0-q"},
            {"role": "assistant", "content": "t0-a"},
        ],
        "dialogueCount": 1,
    })


def _contents(msgs: list) -> list:
    return [m["content"] for m in msgs]


def _trace(conversation_id: str) -> Trace:
    return Trace(
        conversation_id=conversation_id,
        instance_id="inst-1",
        user_id="user-1",
        version_id="",
        handler_type="ReAct",
    )


def _key(conversation_id: str) -> str:
    return f"{conversation_id}_inst-1_user-1"


class TestConversationPersistRace:
    """后台落库跨轮竞态与 join 保护。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_sequential_persist_keeps_all_messages():
        """旧序基线：N 轮 await 落库完成后 N+1 轮才开始，消息完整。"""
        fake = FakeRedis()
        mgr = ConversationManager()
        conv_id = "conv-race-seq"
        _seed(fake, _key(conv_id))
        with patch.object(conv_mod, "_get_redis_client", new=lambda: fake):
            await mgr.update_conversation(
                _trace(conv_id),
                [{"role": "user", "content": "t1-q"},
                 {"role": "assistant", "content": "t1-a"}],
                dialogue_end=True,
            )
            messages, _ = await mgr.get_conversation_data(
                conv_id, "inst-1", "user-1", "")
            await mgr.update_conversation(
                _trace(conv_id),
                [{"role": "user", "content": "t2-q"},
                 {"role": "assistant", "content": "t2-a"}],
                dialogue_end=True,
            )
        assert _contents(messages) == ["t0-q", "t0-a", "t1-q", "t1-a"]
        assert _contents(json.loads(fake.store[_key(conv_id)])["messageList"]) == FULL_HISTORY

    @staticmethod
    @pytest.mark.asyncio
    async def test_background_persist_without_join_loses_messages():
        """竞态文档化：后台落库未完成即开始下一轮，脏读且后写覆盖丢消息。"""
        fake = FakeRedis()
        mgr = ConversationManager()
        conv_id = "conv-race-nojoin"
        _seed(fake, _key(conv_id))
        with patch.object(conv_mod, "_get_redis_client", new=lambda: fake):
            fake.set_delay = 0.2
            task_n = asyncio.create_task(mgr.update_conversation(
                _trace(conv_id),
                [{"role": "user", "content": "t1-q"},
                 {"role": "assistant", "content": "t1-a"}],
                dialogue_end=True,
            ))
            await asyncio.sleep(0.05)  # N 轮 GET 完成、SET 在飞（finish 已发出）
            fake.set_delay = 0.0
            messages, _ = await mgr.get_conversation_data(
                conv_id, "inst-1", "user-1", "")
            stale_read = "t1-q" not in _contents(messages)
            await mgr.update_conversation(
                _trace(conv_id),
                [{"role": "user", "content": "t2-q"},
                 {"role": "assistant", "content": "t2-a"}],
                dialogue_end=True,
            )
            await task_n  # N 轮后台 SET 此刻才落地，覆盖 N+1 已写消息
        final = _contents(json.loads(fake.store[_key(conv_id)])["messageList"])
        assert stale_read, "N+1 轮应读到缺 t1 的旧历史（脏读）"
        assert "t2-q" not in final and "t2-a" not in final, "t2 轮消息应被覆盖丢失"

    @staticmethod
    @pytest.mark.asyncio
    async def test_background_persist_with_join_keeps_all_messages():
        """修复验证：后台落库 + 下一轮入口 await_pending，无脏读且消息完整。"""
        fake = FakeRedis()
        mgr = ConversationManager()
        conv_id = "conv-race-join"
        _seed(fake, _key(conv_id))
        with patch.object(conv_mod, "_get_redis_client", new=lambda: fake):
            fake.set_delay = 0.2
            run_in_background(
                mgr.update_conversation(
                    _trace(conv_id),
                    [{"role": "user", "content": "t1-q"},
                     {"role": "assistant", "content": "t1-a"}],
                    dialogue_end=True,
                ),
                name=f"persist-{conv_id}",
                track_key=conv_id,
            )
            await asyncio.sleep(0.05)  # finish 已发出，后台 SET 在飞
            fake.set_delay = 0.0
            # 下一轮入口：生产路径 _load_conversation_data 同款 join
            await await_pending(conv_id)
            messages, _ = await mgr.get_conversation_data(
                conv_id, "inst-1", "user-1", "")
            await mgr.update_conversation(
                _trace(conv_id),
                [{"role": "user", "content": "t2-q"},
                 {"role": "assistant", "content": "t2-a"}],
                dialogue_end=True,
            )
        assert "t1-q" in _contents(messages), "join 后应读到含 t1 的完整历史"
        assert _contents(json.loads(fake.store[_key(conv_id)])["messageList"]) == FULL_HISTORY
