# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Conversation manager

使用单个Redis key存储完整Conversation对象（含messageList + dialogueCount），
Redis key格式: {conversationId}_{instanceId}_{userId}[_{versionId}]
"""

import json
import os
import time
import traceback

from openjiuwen.core.common.logging import workflow_logger
from agent_runtime.event_handler.base.trace import Trace

# 会话历史最大消息数
MAX_MESSAGE_NUM = int(os.getenv("MAX_MESSAGE_NUM", "100"))
# 会话历史消息内容最大总字节数
MAX_MESSAGE_SIZE = int(os.getenv("MAX_MESSAGE_SIZE", "5000000"))
# Redis key 前缀
KEY_PREFIX = "agentBuilder:conversation"
# 默认 TTL 24小时
DEFAULT_TTL = 86400


def _get_redis_client():
    """获取 Redis 客户端，不可用则返回 None."""
    try:
        from common_utils.redis_manager import RedisClientManager
        mgr = RedisClientManager.get_instance()
        if mgr.is_initialized:
            return mgr.get_client()
    except Exception as e:
        workflow_logger.error(f"Failed to get Redis client: {e}")
    return None


def _conversation_key(
    conversation_id: str, instance_id: str, user_id: str, version_id: str = ""
) -> str:
    """{conversationId}_{id}_{userId}[_{versionId}]"""
    key = f"{conversation_id}_{instance_id}_{user_id}"
    if version_id:
        key = f"{key}_{version_id}"
    return key


def _new_conversation() -> dict:
    """创建新的空Conversation对象."""
    return {
        "lastUpdateTime": int(time.time() * 1000),
        "messageList": [],
        "dialogueCount": 1,
    }


def _get_trimmed_message_list(message_list: list, offset: int) -> list:
    """根据offset从尾部截取消息列表，对齐Java getTrimmedMessageList."""
    if not message_list:
        return message_list
    if offset > 0:
        return message_list[-offset:]
    return message_list[-1:]


class ConversationManager:
    """对话历史管理器"""

    _instance = None
    _is_initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            self._is_initialized = True

    async def get_conversation(
        self,
        conversation_id: str,
        instance_id: str,
        user_id: str,
        version_id: str = "",
    ) -> dict:
        """加载完整Conversation对象.

        Returns:
            {"lastUpdateTime": int, "messageList": [...], "dialogueCount": int}
        """
        key = _conversation_key(conversation_id, instance_id, user_id, version_id)
        try:
            redis = _get_redis_client()
            if redis is not None:
                raw = await redis.get(key)
                if raw is not None:
                    data = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                    conversation = json.loads(data)
                    # 刷新TTL
                    await redis.expire(key, DEFAULT_TTL)
                    return conversation
                return _new_conversation()
            return _new_conversation()
        except Exception as e:
            workflow_logger.error(
                f"get_conversation failed, key={key}"
            )
            workflow_logger.error("".join(traceback.format_exception(e)))
            return _new_conversation()

    async def get_conversation_data(
        self,
        conversation_id: str,
        instance_id: str,
        user_id: str,
        version_id: str = "",
    ) -> tuple[list, int]:
        """一次Redis读取同时返回messageList和dialogueCount."""
        conversation = await self.get_conversation(
            conversation_id, instance_id, user_id, version_id
        )
        message_list = conversation.get("messageList", [])
        message_list.sort(key=lambda m: m.get("create_time") or 0)
        dialogue_count = max(1, int(conversation.get("dialogueCount", 1)))
        return message_list, dialogue_count

    async def update_conversation(
        self,
        trace: Trace,
        messages: list,
        dialogue_end: bool = False,
    ) -> list:
        """追加消息、裁剪、递增dialogueCount、写回Redis，返回裁剪后的messageList."""
        if not messages:
            return []
        key = _conversation_key(
            trace.conversation_id, trace.instance_id, trace.user_id, trace.version_id
        )
        start_time = time.time()
        try:
            redis = _get_redis_client()
            if redis is None:
                workflow_logger.warning(
                    f"Redis not available, skip update_conversation, key={key}"
                )
                return []

            # 加载已有Conversation
            raw = await redis.get(key)
            # controller类型或无历史时新建会话，对齐Java executeType==CONTROLLER逻辑
            if raw is not None and trace.handler_type != "Controller":
                data = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                conversation = json.loads(data)
                message_list = conversation.get("messageList", [])
            else:
                conversation = _new_conversation()
                message_list = conversation["messageList"]

            # 追加新消息
            message_list.extend(messages)

            # 超过MAX_MESSAGE_NUM时按条数裁剪保留最新
            if len(message_list) >= MAX_MESSAGE_NUM:
                message_list = message_list[-(MAX_MESSAGE_NUM):]

            # 按内容总大小裁剪：从尾部累计content长度，超过MAX_MESSAGE_SIZE则截断
            size = 0
            offset = 0
            for i in range(len(message_list) - 1, -1, -1):
                msg = message_list[i]
                if isinstance(msg, dict):
                    content = str(msg.get("content", ""))
                    size += len(content)
                elif hasattr(msg, "content"):
                    content = str(msg.content) if msg.content else ""
                    size += len(content)

                if size > MAX_MESSAGE_SIZE:
                    workflow_logger.warning(
                        f"Conversation message size exceed limit. size={size} limit={MAX_MESSAGE_SIZE}"
                    )
                    break
                offset += 1

            message_list = _get_trimmed_message_list(message_list, offset)

            # 更新messageList和lastUpdateTime
            conversation["messageList"] = message_list
            conversation["lastUpdateTime"] = int(time.time() * 1000)

            # dialogue_end=True时dialogueCount++
            if dialogue_end:
                conversation["dialogueCount"] = conversation.get("dialogueCount", 1) + 1

            # 写回Redis并设置TTL
            await redis.set(key, json.dumps(conversation, ensure_ascii=False), ex=DEFAULT_TTL)
            workflow_logger.info(
                f"update: conversationId={trace.conversation_id}, messagesSize={len(message_list)}"
            )
            return message_list
        except Exception as e:
            workflow_logger.error(f"update_conversation failed, key={key}")
            workflow_logger.error("".join(traceback.format_exception(e)))
            return []
        finally:
            cost_ms = int((time.time() - start_time) * 1000)
            workflow_logger.info(
                f"update conversation cost {cost_ms}ms, conversation id: {trace.conversation_id}"
            )
