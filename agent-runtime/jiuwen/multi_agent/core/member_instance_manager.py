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
from jiuwen.serve.controllers.execution.open_utils import (
    cache_agent_config,
    cache_agent_queue,
)


class MemberInstanceManager:
    """成员实例管理器"""

    def __init__(self, conversation_id: str = ""):
        self._conversation_id = conversation_id
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
                # 防御：conversation_id 为空时退化为按 ir_path 共享，会触发 R07 串会话，强制关闭实例缓存
                if cache_enabled and not self._conversation_id:
                    logger.warning(
                        "sub_agent cache enabled but conversation_id is empty, "
                        "skip L1 instance cache to avoid cross-session leak, "
                        "member_id=%s, ir_path=%s",
                        member_id, config.ir_path,
                        simple_log=(
                            "sub_agent cache enabled but conversation_id is empty, "
                            "skip L1 instance cache, member_id=%s, ir_path=%s"
                        ),
                    )
                    cache_enabled = False
                logger.debug(
                    "sub_agent cache check: cache_enabled=%s, env=%s=%s, "
                    "is_published=%s, member_id=%s, ir_path=%s, conversation_id=%s",
                    cache_enabled, AGENT_CACHE_ENABLE_KEY,
                    os.environ.get(AGENT_CACHE_ENABLE_KEY, '<unset>'),
                    config.is_published, member_id, config.ir_path, self._conversation_id,
                    simple_log=(
                        "sub_agent cache check: cache_enabled=%s, env=%s=%s, "
                        "is_published=%s, member_id=%s, ir_path=%s, conversation_id=%s"
                    ),
                )

                # 二级缓存：AgentConfig 单例（跨会话共享，key=ir_path）
                if cache_enabled:
                    cached_config = await timed_cache_op(
                        "Sub-agent config retrieval",
                        cache_agent_config.aget(config.ir_path),
                        config.ir_path,
                    )
                    if cached_config is not None:
                        logger.debug(
                            "L2_HIT audit: cached_task_id=%s, conversation_id=%s, "
                            "ir_path=%s, has_parent_meta=%s",
                            cached_config.task_id, self._conversation_id,
                            cached_config.ir_path,
                            cached_config.parent_agent_metadata is not None,
                            simple_log=(
                                "L2_HIT audit: cached_task_id=%s, "
                                "conversation_id=%s, ir_path=%s"
                            ),
                        )
                        config = cached_config
                        logger.debug(
                            "sub_agent config cache hit: member_id=%s, ir_path=%s",
                            member_id, config.ir_path,
                            simple_log="sub_agent config cache hit: member_id=%s, ir_path=%s",
                        )
                    else:
                        await timed_cache_op(
                            "Caching sub-agent config",
                            cache_agent_config.aput(config.ir_path, config),
                            config.ir_path,
                        )
                        logger.debug(
                            "sub_agent config cache miss+put: member_id=%s, ir_path=%s",
                            member_id, config.ir_path,
                            simple_log="sub_agent config cache miss+put: member_id=%s, ir_path=%s",
                        )

                # 一级缓存：会话级 Agent 实例
                # key=f"{conversation_id}:{ir_path}" 实现 B/A 会话隔离
                agent_session_key = f"{self._conversation_id}:{config.ir_path}"
                agent_instance = None
                if cache_enabled:
                    agent_instance = await timed_cache_op(
                        "Agent instance retrieval",
                        cache_agent_queue.aget(agent_session_key),
                        agent_session_key,
                    )
                    logger.debug(
                        "sub_agent cache %s: member_id=%s, session_key=%s",
                        'hit' if agent_instance is not None else 'miss',
                        member_id, agent_session_key,
                        simple_log=(
                            "sub_agent cache %s: member_id=%s, session_key=%s"
                        ),
                    )

                # 如果没有缓存，则新建实例并加入缓存队列
                if agent_instance is not None:
                    cm = getattr(agent_instance, "context_manager", None)
                    hist_len = 0
                    mem_cached = False
                    if cm is not None:
                        if cm.engine is not None:
                            try:
                                hist_len = len(cm.engine.get_messages())
                            except Exception:
                                hist_len = -1
                        mem_cached = getattr(cm, "_memory_message", None) is not None
                    logger.debug(
                        "L1_HIT audit: member_id=%s, conversation_id=%s, "
                        "engine_history_len=%s, memory_message_cached=%s",
                        member_id, self._conversation_id, hist_len, mem_cached,
                        simple_log=(
                            "L1_HIT audit: member_id=%s, conversation_id=%s, "
                            "engine_history_len=%s, memory_message_cached=%s"
                        ),
                    )

                if agent_instance is None:
                    agent_instance = member_class(config)
                    if cache_enabled:
                        await timed_cache_op(
                            "Caching agent instance",
                            cache_agent_queue.aput(agent_session_key, agent_instance),
                            agent_session_key,
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
