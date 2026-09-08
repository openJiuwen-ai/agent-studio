#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""消息队列核心类"""

import asyncio
from asyncio import Event
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List

from jiuwen.common.log.base import logger
from jiuwen.multi_agent.core.common.message_type import MessageEnvelope
from jiuwen.multi_agent.core.enums import MessageState


class QueueStoppedError(RuntimeError):
    """Raised when operations are attempted on a stopped queue."""

    pass


@dataclass(kw_only=True)
class MessageQueueState:
    """Message queue state for serialization and persistence."""

    receive_queue_messages: List[Dict[str, Any]] = field(default_factory=list)
    processing_queue_messages: List[Dict[str, Any]] = field(default_factory=list)
    snapshot_time: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageQueueState":
        """Create from dictionary."""
        if not data:
            return cls()

        return cls(
            receive_queue_messages=data.get("receive_queue_messages", []),
            processing_queue_messages=data.get("processing_queue_messages", []),
            snapshot_time=data.get(
                "snapshot_time", datetime.now(tz=timezone.utc).isoformat()
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "receive_queue_messages": self.receive_queue_messages,
            "processing_queue_messages": self.processing_queue_messages,
            "snapshot_time": self.snapshot_time,
        }


@dataclass
class PendingMessage:
    """挂起消息数据结构"""

    message_id: str
    envelope: MessageEnvelope
    state: MessageState
    suspension_reason: Optional[str] = None
    user_question: Optional[str] = None
    suspended_at: datetime = field(default_factory=datetime.now)
    execution_context: Dict[str, Any] = field(default_factory=dict)


class AgentMessageQueue:
    """Agent message queue manager"""

    # 用于停止阻塞get的空消息
    shutdown_sentinel = None

    def __init__(self):
        # 接收队列和处理队列
        self._receive_queue: asyncio.Queue[MessageEnvelope] = asyncio.Queue()
        self._processing_queue: asyncio.Queue[MessageEnvelope] = asyncio.Queue()

        # 队列状态锁
        self._queue_lock = asyncio.Lock()
        self._stopped = Event()

    def is_stopped(self):
        """队列是否已关闭"""
        return self._stopped.is_set()

    async def put(self, envelope: MessageEnvelope) -> None:
        """添加消息到接收队列"""
        if self._stopped.is_set() and envelope != self.shutdown_sentinel:
            raise QueueStoppedError("Queue has been stopped")
        await self._receive_queue.put(envelope)

    async def get_next_for_processing(self) -> Optional[MessageEnvelope]:
        """获取下一个待处理的消息"""
        # 处理接收队列中的新消息 - 使用阻塞方式
        if self._stopped.is_set() and self.qsize() == 0:
            raise QueueStoppedError("Queue has been stopped and is empty")
        envelope = await self._receive_queue.get()
        if envelope is self.shutdown_sentinel:
            self._receive_queue.task_done()
            return None
        message_id = envelope.message_id
        logger.info(f"processing message id: {message_id}")
        return envelope

    async def mark_message_completed(self, message_id: str) -> None:
        """标记消息为已完成"""
        try:
            self._receive_queue.task_done()
        except Exception as cleanup_error:
            logger.error(
                f"Failed to cleanup message: {message_id} state: {cleanup_error}",
                simple_log=f"Failed to cleanup message: {message_id}",
            )

    async def mark_message_failed(self, message_id: str, error: str) -> None:
        """标记消息为失败"""
        try:
            self._receive_queue.task_done()
        except Exception as cleanup_error:
            logger.error(
                f"Failed to cleanup message: {message_id} state: {cleanup_error}",
                simple_log=f"Failed to cleanup message: {message_id}",
            )

    async def swap_queues(self) -> None:
        """交换接收队列和处理队列（用于批量处理）"""
        async with self._queue_lock:
            # 将接收队列中的所有消息移动到处理队列
            while not self._receive_queue.empty():
                envelope = await self._receive_queue.get()
                await self._processing_queue.put(envelope)

            # 交换队列引用
            self._receive_queue, self._processing_queue = (
                self._processing_queue,
                self._receive_queue,
            )

    def qsize(self) -> int:
        """获取总队列大小"""
        return self._receive_queue.qsize() + self._processing_queue.qsize()

    async def join(self) -> None:
        """等待队列处理完成"""
        logger.info("Waiting for receive queue to join...")
        await self._receive_queue.join()
        logger.info("Waiting for processing queue to join...")
        await self._processing_queue.join()
        logger.info("Message queues joined successfully.")

    async def clear(self) -> None:
        """清理队列"""
        self._stopped.clear()
        async with self._queue_lock:
            while not self._receive_queue.empty():
                try:
                    self._receive_queue.get_nowait()
                    self._receive_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            logger.debug("_receive_queue cleared")
            while not self._processing_queue.empty():
                try:
                    self._processing_queue.get_nowait()
                    self._processing_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            logger.debug("_processing_queue cleared")

    async def shutdown(self) -> None:
        """关闭队列"""
        await self.clear()
        # 设置为已停止，禁止put
        self._stopped.set()
        await self._receive_queue.put(self.shutdown_sentinel)
        logger.info("send shutdown sentinel to _receive_queue success")

    async def get_state(self) -> MessageQueueState:
        """
        Get queue state as MessageQueueState object

        Returns:
            MessageQueueState object
        """
        async with self._queue_lock:
            # 序列化等待处理的消息
            receive_queue_messages = []
            processing_queue_messages = []

            # 临时存储接收队列中的消息
            temp_receive = []
            while not self._receive_queue.empty():
                try:
                    envelope = self._receive_queue.get_nowait()
                    temp_receive.append(envelope)
                    receive_queue_messages.append(envelope.to_dict())
                except asyncio.QueueEmpty:
                    break

            # 将消息放回接收队列
            for envelope in temp_receive:
                await self._receive_queue.put(envelope)

            # 临时存储处理队列中的消息
            temp_processing = []
            while not self._processing_queue.empty():
                try:
                    envelope = self._processing_queue.get_nowait()
                    if envelope is not self.shutdown_sentinel:
                        temp_processing.append(envelope)
                        processing_queue_messages.append(envelope.to_dict())
                except asyncio.QueueEmpty:
                    break

            # 将消息放回处理队列
            for envelope in temp_processing:
                await self._processing_queue.put(envelope)

            return MessageQueueState(
                receive_queue_messages=receive_queue_messages,
                processing_queue_messages=processing_queue_messages,
                snapshot_time=datetime.now(tz=timezone.utc).isoformat(),
            )

    async def load_state(self, state: MessageQueueState) -> None:
        """
        Load queue state

        Args:
            state: MessageQueueState object
        """
        if not state:
            return

        # 清空当前状态
        await self.clear()

        async with self._queue_lock:
            # 恢复接收队列消息
            for msg_data in state.receive_queue_messages:
                try:
                    envelope = MessageEnvelope.create_envelope_from_dict(msg_data)
                    await self._receive_queue.put(envelope)
                except Exception as e:
                    logger.error(
                        f"Failed to restore receive queue message: {e}",
                        simple_log="Failed to restore receive queue message",
                    )

            # 恢复处理队列消息
            for msg_data in state.processing_queue_messages:
                try:
                    envelope = MessageEnvelope.create_envelope_from_dict(msg_data)
                    await self._processing_queue.put(envelope)
                except Exception as e:
                    logger.error(
                        f"Failed to restore processing queue message: {e}",
                        simple_log="Failed to restore processing queue message",
                    )
