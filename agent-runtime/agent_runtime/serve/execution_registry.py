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
SUBSCRIBER_RETRY_SECONDS = 5  # 订阅断开后重连退避间隔（单测可 patch 为 0）
_TRUE_BYTES = b"true"
_TRUE_STR = "true"


@dataclass
class ExecutionRecord:
    """进程内在飞执行记录。"""

    task: asyncio.Task
    instance_id: str
    execution_id: str
    started_at: float


@dataclass
class RegistrationInfo:
    """执行归属三元组（Redis ``exec:{conv}`` hash 的数据源，register 参数封装）。"""

    project_id: str = ""
    agent_id: str = ""  # 契约 v0.6：执行智能体时=agent_id、执行工作流时=workflow_id
    user_id: str = ""


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
        info: Optional["RegistrationInfo"] = None,
    ) -> None:
        """注册在飞执行：本地 task 映射 + Redis hash 归属四元组 + 初始化取消标记。

        agent_id 语义（契约 v0.6）：执行智能体时=agent_id、执行工作流时=workflow_id。
        归属三元组经 RegistrationInfo 封装（G.FNM.03：6 参收敛为具名参数组）。
        """
        if not conversation_id:
            return
        info = info or RegistrationInfo()
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
                "project_id": info.project_id or "",
                "agent_id": info.agent_id or "",
                "user_id": info.user_id or "",
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
            info.agent_id,
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
        # 跨实例晚删保护：注册键仍归本实例时才删。多实例同会话重叠执行时，旧实例
        # 晚到的 finally 若无条件 delete，会删掉新实例刚写入的注册键（归属校验/
        # 取消失效，检视意见④）；instance 不匹配则保留新实例的注册记录
        exec_key = f"{EXEC_KEY_PREFIX}{conversation_id}"
        registration = await self.get_registration(conversation_id)
        if registration.get("instance_id", self._instance_id) != self._instance_id:
            workflow_logger.info(
                "Skip unregister: exec key owned by instance=%s (stale finally), conv=%s",
                registration.get("instance_id"),
                conversation_id,
            )
            return
        await client.delete(exec_key)
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
        """订阅 runtime:cancel 频道（server lifespan 后台 task，断开后自动重连）。

        收到会话取消广播 → 本地注册表命中则 task.cancel()；未命中（本实例非持有方
        或执行已挂起/结束）忽略。连接级异常（Redis 断连等）不终止订阅：退避后
        重建 pubsub 续订，仅 CancelledError（shutdown task.cancel）退出循环——
        否则订阅单点静默失效，跨实例取消广播将永远无人消费。
        """
        while True:
            pubsub = None
            try:
                pubsub = self._redis().pubsub()
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
            except Exception as err:  # noqa: BLE001 订阅须自愈：任何连接级异常退避重连
                workflow_logger.warning(
                    "Runtime cancel subscriber failed (instance=%s), resubscribe in %ss: %s",
                    self._instance_id,
                    SUBSCRIBER_RETRY_SECONDS,
                    err,
                )
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe(CANCEL_CHANNEL)
                        await pubsub.aclose()
                    except Exception:  # noqa: BLE001 关闭路径容错
                        pass
            await asyncio.sleep(SUBSCRIBER_RETRY_SECONDS)


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
