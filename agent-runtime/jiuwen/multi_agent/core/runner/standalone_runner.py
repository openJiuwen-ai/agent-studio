#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""StandaloneRunner core class"""

import asyncio
import secrets
from asyncio import Event, Future, Task
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any, Type, Set

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.multi_agent.core.common.message_type import (
    ResponseMessageEnvelope,
    SendMessageEnvelope,
    MessageEnvelope,
)
from jiuwen.multi_agent.core.enums import ProcessStatus
from jiuwen.multi_agent.core.member import MemberMessageType, Message
from jiuwen.multi_agent.core.member_instance_manager import MemberInstanceManager
from jiuwen.multi_agent.core.runner.agent_message_queue import (
    AgentMessageQueue,
    QueueStoppedError,
)
from jiuwen.multi_agent.core.runner.agent_run_space import AgentRunSpace
from jiuwen.multi_agent.core.state_manager.run_state import RunState
from jiuwen.multi_agent.core.stream.stream_handler import (
    StreamHandler,
    STREAM_END_FRAME,
)


@dataclass(kw_only=True)
class ProcessResult:
    """Message processing result"""

    status: ProcessStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None


class StandaloneRunner:
    """StandaloneRunner main runner"""

    def __init__(self, conversation_id: str = ""):
        self._message_queue = AgentMessageQueue()
        self._run_state: Optional[RunState] = None
        self._agent_run_space: Optional[AgentRunSpace] = None
        self._stopped = Event()
        self._conversation_id = conversation_id
        self._member_instance_manager = MemberInstanceManager(conversation_id)
        self._running_tasks: Set[Task[Any]] = set()
        self._background_exception: Optional[Exception] = None
        self._intervention_handlers: list = []

    def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def message_queue(self) -> AgentMessageQueue:
        """message queue"""
        return self._message_queue

    async def start(self, run_state: RunState = None) -> None:
        """Start the runner"""
        if self._run_state is not None:
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_RUNNER_ALREADY_STARTED.code,
                message="Runner is already started",
            )

        self._run_state = run_state or RunState()
        self._run_state.is_running = True
        self._run_state.start_time = datetime.now(tz=timezone.utc)
        self._stopped.clear()
        # Create and start AgentRunSpace
        self._agent_run_space = AgentRunSpace(self)

    async def close(self) -> None:
        """Close the runner"""
        await self.stop()

    async def stop(self, immediately: bool = True) -> None:
        """Stop the runner"""
        # 等待队列任务完成
        if not immediately:
            await self._message_queue.join()

        if self._run_state is not None:
            self._run_state.is_running = False

        self._stopped.set()

        # 终止队列和事件循环
        await self._agent_run_space.stop()

        logger.info(f"Start to cancel running tasks. len:{len(self._running_tasks)}")
        # Cancel all running tasks
        for task in list(self._running_tasks):
            if not task.done():
                task.cancel()

    async def process_next(self) -> ProcessResult:
        """Process the next message, supports interruption"""
        return await self._process_next()

    async def send_message(
        self,
        message: Any,
        recipient: str,
        sender: Optional[str] = None,
        message_id: Optional[str] = None,
        stream_handler: Optional[StreamHandler] = None,
    ) -> list[Message]:
        """Send message"""
        if self._run_state is None or self._stopped.is_set():
            error_msg = (
                "Runner is not started. Please call start() before sending messages."
            )
            logger.error(error_msg)
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_RUNNER_NOT_STARTED.code,
                message=error_msg,
            )

        if message_id is None:
            message_id = str(secrets.token_hex(24))

        future = Future()

        envelope = SendMessageEnvelope(
            message=message,
            sender=sender,
            recipient=recipient,
            future=future,
            stream_handler=stream_handler,
            message_id=message_id,
        )
        # Add message to queue
        logger.info(
            f"Send message from [{sender}] to [{recipient}], message_id: {message_id}",
            simple_log="Send message",
        )
        await self._message_queue.put(envelope)

        return await future

    def register_member(
        self, member_id: str, member_class: Type, config: Any
    ) -> "StandaloneRunner":
        """Register member (method chaining)"""
        self._member_instance_manager.register_member_type(
            member_id, member_class, config
        )
        return self

    async def get_state(self):
        """Get state"""
        await self._run_state.save_runner_state(
            self._member_instance_manager, self._message_queue
        )
        return self._run_state

    async def load_state(self, state: RunState) -> None:
        """Load state"""
        await state.restore_runner_state(
            self._message_queue, self._member_instance_manager
        )

    def add_intervention_handler(self, handler) -> None:
        """Add intervention handler"""
        if handler not in self._intervention_handlers:
            self._intervention_handlers.append(handler)

    def remove_intervention_handler(self, handler) -> None:
        """Remove intervention handler"""
        if handler in self._intervention_handlers:
            self._intervention_handlers.remove(handler)

    async def _process_next(self) -> ProcessResult:
        """Process the next message in the queue."""
        # Check if stopped
        if self._stopped.is_set():
            return ProcessResult(
                status=ProcessStatus.INTERRUPTED,
                error_message="Runner has been stopped",
            )

        try:
            # Get next message to process
            envelope = await self._message_queue.get_next_for_processing()

            if envelope is None:
                return ProcessResult(status=ProcessStatus.NO_MESSAGES)

            # Create processing task based on message type (following Autogen pattern)
            if isinstance(envelope, SendMessageEnvelope):
                logger.info(
                    "process send message from [{}] to [{}]".format(
                        envelope.sender, envelope.recipient
                    )
                )
                task = asyncio.create_task(self._process_send_message(envelope))
                self._running_tasks.add(task)
                task.add_done_callback(self._envelope_asynctask_callback(envelope))
            elif isinstance(envelope, ResponseMessageEnvelope):
                logger.info(
                    "process response message from [{}] to [{}]".format(
                        envelope.sender, envelope.recipient
                    )
                )
                task = asyncio.create_task(self._process_response_message(envelope))
                self._running_tasks.add(task)
                task.add_done_callback(self._envelope_asynctask_callback(envelope))
            else:
                return ProcessResult(
                    status=ProcessStatus.ERROR,
                    error_message=f"Unknown message envelope type: {type(envelope)}",
                )
            return ProcessResult(
                status=ProcessStatus.COMPLETED,
            )

        except Exception as e:
            logger.error(
                f"Error occurred while processing message: {str(e)}",
                exc_info=True,
                simple_log="Error occurred while processing message",
            )
            return ProcessResult(status=ProcessStatus.ERROR, error_message=str(e))

    async def _process_send_message(self, envelope: SendMessageEnvelope) -> Any:
        """Process send message"""
        message = envelope.message
        recipient = envelope.recipient
        sender = envelope.sender
        message_id = envelope.message_id

        try:
            # Get target member instance
            member = await self._member_instance_manager.get_member_instance(recipient)
            if not member:
                error_msg = f"Target member not found: {recipient}"
                exception = JiuWenBaseException(
                    error_code=StatusCode.MULTI_AGENT_TARGET_MEMBER_NOT_FOUND.code,
                    message=error_msg,
                )
                if envelope.future and not envelope.future.done():
                    envelope.future.set_exception(exception)
                raise exception

            # Call intervention handlers for send
            for handler in self._intervention_handlers:
                try:
                    message = await handler.on_send(
                        message, sender, recipient, message_id
                    )
                except Exception as e:
                    logger.warning(
                        f"Intervention handler {handler.__class__.__name__} execution failed: {str(e)}",
                        simple_log="Intervention handler execution failed",
                    )

            # Wrap single message as message sequence
            messages = [message] if not isinstance(message, list) else message

            # Build context
            context = {
                "sender": sender,
                "message_id": message_id,
                "recipient": recipient,
            }

            # Process message and collect results
            results = []
            async for msg in member.on_messages_stream(messages, context):
                if envelope and envelope.stream_handler:
                    await envelope.stream_handler.on_stream(msg)
                results.append(msg)
            if envelope and envelope.stream_handler:
                await envelope.stream_handler.on_stream(STREAM_END_FRAME)

            # 创建 ResponseMessageEnvelope 并放入队列进行进一步处理
            await self._message_queue.put(
                ResponseMessageEnvelope(
                    message=results,
                    sender=recipient,
                    recipient=sender,
                    original_message_id=message_id,  # 关联到原始发送消息
                    future=envelope.future,
                )
            )

            # 标记发送消息处理完成
            logger.info(f"Send response message from [{recipient}] to [{sender}]")
            await self._message_queue.mark_message_completed(message_id)
            return results
        except QueueStoppedError as e:
            logger.error(
                f"_process_send_message err: {e}",
                simple_log="_process_send_message err",
            )
            error_msg = (
                "Runner is not started. Please call start() before sending messages."
            )
            envelope.future.set_exception(
                JiuWenBaseException(
                    error_code=StatusCode.MULTI_AGENT_RUNNER_NOT_STARTED.code,
                    message=error_msg,
                )
            )
            await self._message_queue.mark_message_failed(message_id, str(e))
            return
        except Exception as e:
            logger.error(
                f"_process_send_message err: {e}",
                simple_log="_process_send_message err",
            )
            # 确保在异常情况下也清理状态
            await self._message_queue.mark_message_failed(message_id, str(e))
            # Set Future exception
            if envelope.future and not envelope.future.done():
                envelope.future.set_exception(e)

    async def _process_response_message(self, envelope: ResponseMessageEnvelope) -> Any:
        """处理响应消息"""
        response_message_id = envelope.message_id
        # 检查是否有中断消息
        has_interrupt = False
        try:
            for msg in envelope.message:
                if msg.type == MemberMessageType.INTERRUPT:
                    has_interrupt = True
                    logger.info(
                        "Interrupt message found in response: {}".format(
                            msg.data.data["reason"]
                        ),
                        simple_log="Interrupt message found in response",
                    )

            # 无论是否有中断，都标记消息处理完成
            # 因为这是 agent 的正常处理结果
            await self._message_queue.mark_message_completed(response_message_id)

            # 设置 Future 结果
            if envelope.future and not envelope.future.done():
                envelope.future.set_result(envelope.message)

            # 如果有中断，这里可以触发一些清理或通知逻辑
            if has_interrupt:
                # 可以在这里触发状态保存、清理资源等
                # 但不需要挂起消息，因为处理已经完成
                logger.info("Processing completed with interrupt signal")

            return envelope.message

        except Exception as e:
            await self._message_queue.mark_message_failed(response_message_id, str(e))
            if envelope.future and not envelope.future.done():
                envelope.future.set_exception(e)
            raise

    def _envelope_asynctask_callback(self, envelope: MessageEnvelope):
        """统一处理任务完成后的清理、异常和取消逻辑"""

        def callback(task: asyncio.Task):
            # 从运行任务集合中移除
            self._running_tasks.discard(task)

            message_info = f"[message_id={envelope.message_id}, sender={envelope.sender}, to={envelope.recipient}]"

            if envelope.future.cancelled():
                task.cancel()
                logger.info(
                    f"Envelope future was cancelled {message_info}",
                    simple_log="Envelope future was cancelled",
                )
                return
            try:
                exc = task.exception()
                if exc:
                    logger.warning(
                        f"Exception during message processing {message_info}: {exc}",
                        exc_info=True,
                        simple_log="Exception during message processing",
                    )
            except asyncio.CancelledError as e:
                # shutdown场景内层协程被取消也取消外层用户的future
                logger.warning(
                    f"Task was cancelled {message_info}: {e}",
                    simple_log="Task was cancelled",
                )
                if not envelope.future.done():
                    envelope.future.cancel()

        return callback
