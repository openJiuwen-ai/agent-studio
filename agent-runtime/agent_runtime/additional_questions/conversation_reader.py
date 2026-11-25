# agent_runtime/serve/apis/additional_questions/conversation_reader.py
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""追问功能 — 从 Redis 读取会话历史消息。

Redis key 格式与 Java ConversationManagementService.getConversationKey() 一致：
    {conversationId}_{resourceId}_{userId}
    {conversationId}_{resourceId}_{userId}_{versionId}  (带版本号时)

Value: JSON 序列化的 Conversation { messageList: [{role, content, createTime, ...}] }
"""

import json
import logging

from common_utils.redis_manager import get_redis_client
from agent_runtime.context.request_context import _request_ctx

logger = logging.getLogger(__name__)


class ConversationReader:
    """从 Redis 读取会话历史消息，兼容旧版 Java 存储格式。"""

    async def get_history(
        self,
        resource_id: str,
        conversation_id: str,
        version_id: str = "",
    ) -> list[dict]:
        """获取会话消息列表，按 createTime 排序。

        Args:
            resource_id: agent_id 或 workflow_id
            conversation_id: 会话 ID
            version_id: 版本号（可选）

        Returns:
            消息字典列表，每个消息含 role, content, createTime 等字段。
            Redis 无数据或解析失败时返回空列表。
        """
        try:
            user_id = self._get_user_id()
            key = self.build_key(conversation_id, resource_id, version_id, user_id)
            client = get_redis_client()
            data = await client.get(key)
            if not data:
                logger.info(
                    "Conversation not found in Redis: key=%s", key,
                )
                return []
            raw = data if isinstance(data, str) else data.decode("utf-8")
            logger.debug("Conversation raw data type: %s, length: %d", type(data).__name__, len(raw))
            conversation = json.loads(raw)
            # conversation 可能是 str（双重编码）或 dict
            if isinstance(conversation, str):
                conversation = json.loads(conversation)
            if not isinstance(conversation, dict):
                logger.warning(
                    "Unexpected conversation data type: %s", type(conversation).__name__,
                )
                return []
            messages = conversation.get("messageList", [])
            # 过滤掉非 dict 的消息条目（Java 端某些场景可能存入异常数据）
            messages = [m for m in messages if isinstance(m, dict)]
            messages.sort(key=lambda m: m.get("createTime", 0))
            return messages
        except Exception as e:
            logger.warning(
                "Failed to read conversation history: "
                "resource_id=%s, conversation_id=%s, error=%s",
                resource_id, conversation_id, e,
            )
            return []

    @staticmethod
    def build_key(
        conversation_id: str,
        resource_id: str,
        version_id: str,
        user_id: str,
    ) -> str:
        """构建 Redis key — 与 Java getConversationKey 一致。"""
        key = f"{conversation_id}_{resource_id}_{user_id}"
        if version_id:
            key = f"{key}_{version_id}"
        return key

    @staticmethod
    def _get_user_id() -> str:
        """从请求上下文获取用户 ID。

        优先级：
        1. 请求体中的 userId（由中间件解析写入 ctx.user_id）
        2. 请求头 x-user-id
        3. Cookie AGENT_SID（格式: userId|xxx，取 | 前的部分）
        """
        ctx = _request_ctx.get()
        if ctx and ctx.user_id:
            return ctx.user_id
        # 回退到请求头
        if ctx and ctx.headers:
            uid = ctx.headers.get("x-user-id", "") or ctx.headers.get("X-User-Id", "")
            if uid:
                return uid
            # 从 Cookie AGENT_SID 解析 userId（格式: userId|xxx）
            cookie = ctx.headers.get("cookie", "") or ctx.headers.get("Cookie", "")
            if cookie:
                for part in cookie.split(";"):
                    part = part.strip()
                    if part.startswith("AGENT_SID="):
                        sid_value = part[len("AGENT_SID="):]
                        # 格式: userId|其他信息，取 | 前的部分
                        if "|" in sid_value:
                            return sid_value.split("|", 1)[0]
                        return sid_value
        return ""
