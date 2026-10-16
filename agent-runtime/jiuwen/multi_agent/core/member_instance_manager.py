#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
from typing import Callable, Dict, Optional, Type, Any

from jiuwen.common.configs.env_constants import AGENT_CACHE_ENABLE_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import timed_cache_op
from jiuwen.controller.common.config import AgentConfig
from jiuwen.multi_agent.core.member import Member
from jiuwen.serve.controllers.execution.open_utils import cache_agent_queue


class MemberInstanceManager:
    """成员实例管理器"""

    def __init__(self):
        self._member_factories: Dict[str, Callable] = {}
        # 注册的成员类型及其配置
        self._member_registrations: Dict[str, Dict[str, Any]] = {}
        # 活跃实例 - 运行时懒加载
        self._active_members: Dict[str, Member] = {}

    def register_member_factory(self, member_type: str, factory: Callable) -> None:
        """注册成员工厂函数"""
        self._member_factories[member_type] = factory

    def register_member_type(
        self, member_id: str, member_class: Type, config: Any = None
    ) -> None:
        """注册成员类型和配置（一步到位）"""
        self._member_registrations[member_id] = {
            "member_class": member_class,
            "config": config,
        }

    async def get_member_instance(self, member_id: str) -> Optional[Member]:
        """获取成员实例（懒加载）"""
        # 如果已经实例化，直接返回
        if member_id in self._active_members:
            return self._active_members[member_id]

        # 如果注册了，进行懒加载
        if member_id in self._member_registrations:
            return await self._lazy_load_member(member_id)

        return None

    def remove_member(self, member_id: str) -> bool:
        """移除成员实例"""
        if member_id in self._active_members:
            del self._active_members[member_id]
            return True
        return False

    def list_members(self) -> Dict[str, str]:
        """列出所有活跃成员"""
        return {
            member_id: type(member).__name__
            for member_id, member in self._active_members.items()
        }

    def get_active_members(self) -> Dict[str, Member]:
        """Get active members"""
        return self._active_members

    async def _lazy_load_member(self, member_id: str) -> Optional[Member]:
        """懒加载成员实例"""
        try:
            registration = self._member_registrations[member_id]
            member_class = registration["member_class"]
            config = registration["config"]

            if isinstance(config, AgentConfig):
                cache_enabled = (
                    str(os.environ.get(AGENT_CACHE_ENABLE_KEY, "false")).lower()
                    == "true"
                    and config.is_published
                )

                agent_instance = None
                if cache_enabled:
                    agent_instance = await timed_cache_op(
                        "Agent instance retrieval",
                        cache_agent_queue.aget(config.ir_path, should_refresh_ttl=True),
                        config.ir_path,
                    )

                # 如果没有缓存，则新建实例并加入缓存队列
                if agent_instance is None:
                    agent_instance = member_class(config)
                    if cache_enabled:
                        await timed_cache_op(
                            "Caching agent instance",
                            cache_agent_queue.aput(config.ir_path, agent_instance),
                            config.ir_path,
                        )

                member = Member(member_id, agent_instance)
            elif issubclass(member_class, Member):
                member = member_class(member_id, **config)
            else:
                error_msg = f"Failed to load member {member_id}: Undefined config or member class!"
                logger.error(error_msg)
                raise JiuWenBaseException(error_code=-1, message=error_msg)

            # 缓存实例
            self._active_members[member_id] = member

            return member

        except Exception as e:
            import traceback

            error_msg = f"Failed to load member {member_id}: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise JiuWenBaseException(error_code=-1, message=error_msg) from e
