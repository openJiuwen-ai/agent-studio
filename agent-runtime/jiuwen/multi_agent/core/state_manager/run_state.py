#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""运行状态核心类"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.multi_agent.core.member_instance_manager import MemberInstanceManager
from jiuwen.multi_agent.core.runner.agent_message_queue import (
    AgentMessageQueue,
    MessageQueueState,
)
from jiuwen.serve.controllers.execution.manager import AsyncStateManager


@dataclass
class RunState:
    """运行状态核心类"""

    # 消息队列状态
    message_queue_state: MessageQueueState = field(default_factory=MessageQueueState)
    # 成员状态
    members_state: Dict[str, Any] = field(default_factory=dict)
    # 运行时间信息
    start_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    is_running: bool = False

    @classmethod
    async def load_from_redis(cls, conversation_id: str) -> Optional["RunState"]:
        """从 Redis 加载"""
        return await AsyncStateManager().get_state(conversation_id)

    @classmethod
    async def get_or_create(cls, conversation_id: str) -> "RunState":
        """获取或创建运行状态"""
        existing_state = await cls.load_from_redis(conversation_id)
        if existing_state:
            return existing_state

        new_state = cls()
        return new_state

    async def restore_runner_state(
        self, message_queue, member_instance_manager
    ) -> None:
        """恢复状态到运行时组件"""

        async def load_members_state(
            manager: MemberInstanceManager, members_state: Dict[str, Any]
        ) -> None:
            if manager is None:
                raise JiuWenBaseException(
                    StatusCode.MULTI_AGENT_RUNNER_NOT_STARTED.code,
                    "Member instance manager must exist",
                )
            if members_state is None:
                logger.warning("Members state not found")
                return
            for member_id, state in members_state.items():
                member = await manager.get_member_instance(member_id)
                if member is None:
                    logger.warning(
                        f"Member {member_id} does not exist, unable to restore state"
                    )
                    continue
                await member.load_state(state)

        async def load_queue_state(
            queue: AgentMessageQueue, queue_state: MessageQueueState
        ) -> None:
            if queue is None:
                raise JiuWenBaseException(
                    StatusCode.MULTI_AGENT_RUNNER_NOT_STARTED.code,
                    "Message queue must exist",
                )
            if queue_state is None:
                logger.warning("Message queue state not found")
                return
            await queue.load_state(queue_state)

        try:
            await asyncio.gather(
                load_members_state(member_instance_manager, self.members_state),
                load_queue_state(message_queue, self.message_queue_state),
            )
        except Exception as e:
            logger.error(
                f"Failed to restore runner state: {e}",
                simple_log="Failed to restore runner state",
            )
            raise JiuWenBaseException(
                -1, f"Failed to restore runner state: {type(e).__name__}"
            ) from e

    async def save_runner_state(
        self,
        member_instance_manager: MemberInstanceManager,
        message_queue: AgentMessageQueue,
    ) -> None:
        """Save the state of the runner."""

        async def get_members_state(
            member_instance_manager,
        ) -> Optional[Dict[str, Any]]:
            active_members = member_instance_manager.get_active_members()
            if active_members:
                state_dict = {
                    member.member_id: await member.get_state()
                    for member in active_members.values()
                }
                return state_dict
            return None

        async def get_queue_state(
            queue: AgentMessageQueue,
        ) -> Optional[MessageQueueState]:
            return await queue.get_state()

        members_state, queue_state = await asyncio.gather(
            get_members_state(member_instance_manager), get_queue_state(message_queue)
        )
        if members_state:
            self.members_state = members_state
        if queue_state:
            self.message_queue_state = queue_state

    def update_timestamp(self) -> None:
        """更新时间戳"""
        self.last_update_time = datetime.now(tz=timezone.utc)
