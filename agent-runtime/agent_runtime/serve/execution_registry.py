# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""执行注册表：进程内 task 映射 + Redis 双层（终止接口的归属校验与取消信令数据源）。

双层结构：
- 进程内：conversation_id -> asyncio.Task 映射，供本实例 ``task.cancel()`` 尽力即时取消；
- Redis： ``exec:{conv}`` hash 归属四元组（instance_id/project_id/agent_id/user_id）、
          ``cancel:{conv}`` 协作式取消标记（中断节点场景持久化）、
          ``runtime:cancel`` 频道（多实例广播，持有实例本地取消）。

注意：Redis 客户端为 decode_responses=False（值为 bytes），读写一律按 bytes 语义比较。
"""

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Optional

from openjiuwen.core.common.logging import workflow_logger

EXEC_KEY_PREFIX = "exec:"  # hash: instance_id/project_id/agent_id/user_id
CANCEL_KEY_PREFIX = "cancel:"  # string 标记: "true"/"false"
CANCEL_CHANNEL = "runtime:cancel"  # pub/sub 频道：广播会话取消
EXEC_TTL_SECONDS = 3600  # 注册记录/标记 TTL 兜底（进程崩溃后键自动过期）
_TRUE_BYTES = b"true"
_TRUE_STR = "true"


@dataclass
class ExecutionRecord:
    """进程内在飞执行记录。"""

    task: asyncio.Task
    instance_id: str
    execution_id: str
    started_at: float


class ExecutionRegistry:
    """执行注册表（进程内单例，经 ``get_execution_registry`` 获取）。"""

    def __init__(self):
        self._records: dict = {}
        self._lock = asyncio.Lock()
        self._instance_id = os.getenv("RUNTIME_INSTANCE_ID", "single")

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @staticmethod
    def _redis():
        # 惰性获取：客户端由 server lifespan 初始化（未初始化时 get_redis_client 抛错）
        from common_utils.redis_manager import get_redis_client

        return get_redis_client()

    async def register(
        self,
        conversation_id: str,
        task: asyncio.Task,
        execution_id: str = "",
        project_id: str = "",
        agent_id: str = "",
        user_id: str = "",
    ) -> None:
        """注册在飞执行：本地 task 映射 + Redis hash 归属四元组 + 初始化取消标记。

        agent_id 语义（契约 v0.6）：执行智能体时=agent_id、执行工作流时=workflow_id。
        """
        if not conversation_id:
            return
        async with self._lock:
            self._records[conversation_id] = ExecutionRecord(
                task=task,
                instance_id=self._instance_id,
                execution_id=execution_id,
                started_at=time.time(),
            )
        exec_key = f"{EXEC_KEY_PREFIX}{conversation_id}"
        client = self._redis()
        await client.hset(
            exec_key,
            mapping={
                "instance_id": self._instance_id,
                "project_id": project_id or "",
                "agent_id": agent_id or "",
                "user_id": user_id or "",
            },
        )
        await client.expire(exec_key, EXEC_TTL_SECONDS)
        # 初始化取消标记仅在键不存在时执行（nx）：挂起期间被取消的执行先置标记 true
        # 后注销，重发时 register 若无条件覆盖会把 true 抹成 false，workflow_runner
        # 恢复分支（_is_session_cancelled）随即失明，US3"从入口重新执行"失效
        await client.set(
            f"{CANCEL_KEY_PREFIX}{conversation_id}", "false", ex=EXEC_TTL_SECONDS, nx=True
        )
        workflow_logger.info(
            "Execution registered: conv=%s entry=%s instance=%s exec=%s",
            conversation_id,
            agent_id,
            self._instance_id,
            execution_id,
        )

    async def unregister(self, conversation_id: str, task: Optional[asyncio.Task] = None) -> None:
        """注销在飞执行（stream_response finally 首行调用）：删本地记录 + 删 Redis 注册键。

        task 提供时校验所有权：同会话已被新执行注册则保留新记录，避免旧流晚到的
        finally 误删新执行（取消失效窗口）。

        注意：cancel:{conv} 终止标记不随注销删除——挂起期间被取消的执行先置标记
        后注销，标记必须留存到恢复路径消费（workflow_runner._is_session_cancelled
        命中后清除并从入口重跑），否则 US3 恢复语义失明；未消费的标记经 TTL 过期。
        """
        async with self._lock:
            record = self._records.get(conversation_id)
            if record is not None and task is not None and record.task is not task:
                return
            self._records.pop(conversation_id, None)
        client = self._redis()
        await client.delete(f"{EXEC_KEY_PREFIX}{conversation_id}")
        workflow_logger.info("Execution unregistered: conv=%s", conversation_id)

    async def get_registration(self, conversation_id: str) -> dict:
        """读取归属注册记录（check_before_cancel 数据源）；无在飞返回 {}。

        decode_responses=False：hash 字段/值均为 bytes，此处统一解码为 str。
        """
        raw = await self._redis().hgetall(f"{EXEC_KEY_PREFIX}{conversation_id}")
        if not raw:
            return {}
        return {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in raw.items()
        }

    async def mark_cancelled(self, conversation_id: str) -> None:
        """置协作式取消标记（幂等，TTL 兜底）+ runtime:cancel 频道广播尽力即时取消。"""
        client = self._redis()
        await client.set(f"{CANCEL_KEY_PREFIX}{conversation_id}", _TRUE_STR, ex=EXEC_TTL_SECONDS)
        await client.publish(CANCEL_CHANNEL, conversation_id)
        workflow_logger.info("Cancel marked: conv=%s", conversation_id)

    async def is_cancelled(self, conversation_id: str) -> bool:
        """查询协作式取消标记（bytes 语义比较，兼容 str 客户端）。"""
        value = await self._redis().get(f"{CANCEL_KEY_PREFIX}{conversation_id}")
        if isinstance(value, bytes):
            return value == _TRUE_BYTES
        return value == _TRUE_STR

    async def clear_cancelled(self, conversation_id: str) -> None:
        """清除协作式取消标记（恢复路径检测到取消后调用）。"""
        await self._redis().delete(f"{CANCEL_KEY_PREFIX}{conversation_id}")

    async def has_execution(self, conversation_id: str) -> bool:
        """是否存在在飞注册记录。"""
        return bool(await self._redis().exists(f"{EXEC_KEY_PREFIX}{conversation_id}"))

    async def cancel_local(self, conversation_id: str) -> bool:
        """本实例本地取消（task.cancel 仅首次生效：task.done() 幂等保护）。"""
        async with self._lock:
            record = self._records.get(conversation_id)
        if record is not None and not record.task.done():
            record.task.cancel()
            workflow_logger.info("Local cancel executed: conv=%s", conversation_id)
            return True
        return False

    async def subscribe_runtime_cancel(self) -> None:
        """订阅 runtime:cancel 频道（server lifespan 后台 task）。

        收到会话取消广播 → 本地注册表命中则 task.cancel()；未命中（本实例非持有方
        或执行已挂起/结束）忽略。关闭时取消订阅并释放连接。
        """
        client = self._redis()
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(CANCEL_CHANNEL)
            workflow_logger.info(
                "Subscribed runtime cancel channel: %s (instance=%s)",
                CANCEL_CHANNEL,
                self._instance_id,
            )
            async for message in pubsub.listen():
                if not isinstance(message, dict) or message.get("type") != "message":
                    continue
                data = message.get("data")
                conversation_id = data.decode() if isinstance(data, bytes) else data
                if not conversation_id:
                    continue
                local_cancelled = await self.cancel_local(conversation_id)
                workflow_logger.info(
                    "Cancel broadcast received: conv=%s local_cancelled=%s",
                    conversation_id,
                    local_cancelled,
                )
        except asyncio.CancelledError:
            workflow_logger.info("Runtime cancel subscriber stopping (instance=%s)", self._instance_id)
            raise
        finally:
            try:
                await pubsub.unsubscribe(CANCEL_CHANNEL)
                await pubsub.aclose()
            except Exception:  # noqa: BLE001 关闭路径容错
                pass


_registry: Optional[ExecutionRegistry] = None


def get_execution_registry() -> ExecutionRegistry:
    """获取进程内单例（惰性创建；Redis 依赖在使用时才解析）。"""
    global _registry
    if _registry is None:
        _registry = ExecutionRegistry()
    return _registry


def reset_execution_registry() -> None:
    """重置单例（仅测试使用）。"""
    global _registry
    _registry = None
