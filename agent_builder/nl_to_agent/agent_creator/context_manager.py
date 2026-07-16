# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


@dataclass
class DialogueMessage:
    """对话消息类"""

    content: str  # 消息内容
    role: str  # 发送者角色 (user/assistant/function)
    name: str
    timestamp: datetime  # 时间戳
    intent_label: Optional[str] = None  # 消息对应的意图标签
    function_call: Optional[Dict[str, Any]] = None  # 意图信息


class DialogueHistoryCache:
    """对话历史缓存类"""

    def __init__(self, max_history_per_session: int = 50):
        self.session_histories: Dict[str, List[DialogueMessage]] = {}  # 会话历史记录
        self.latest_queries: Dict[str, str] = {}  # 每个会话的最新查询
        self.max_history_per_session = max_history_per_session

    def set_latest_query(self, session_id: str, query: str) -> None:
        """设置会话的最新查询"""
        self.latest_queries[session_id] = query

    def get_latest_query(self, session_id: str) -> Optional[str]:
        """获取会话的最新查询"""
        return self.latest_queries.get(session_id)

    def add_message(self, session_id: str, message: DialogueMessage) -> None:
        """添加新消息到指定会话"""
        if session_id not in self.session_histories:
            self.session_histories[session_id] = []

        # 添加消息
        self.session_histories[session_id].append(message)

        # 如果超过最大容量，移除最早的消息
        if len(self.session_histories[session_id]) > self.max_history_per_session:
            self.session_histories[session_id].pop(0)

    def get_history(self, session_id: str) -> List[DialogueMessage]:
        """获取指定会话的历史记录"""
        return self.session_histories.get(session_id, [])

    def get_latest_k_messages(self, session_id: str, k: int) -> List[Dict[str, Any]]:
        """获取最近k条消息，按API格式返回"""
        if session_id not in self.session_histories:
            return []

        history = self.session_histories[session_id]
        # 获取最近k条消息
        latest_messages = history[-k:] if k < len(history) else history

        # 转换为所需格式
        formatted_messages = []
        for msg in latest_messages:
            message_dict = {"role": msg.role, "content": msg.content}

            # 如果有意图信息，添加到消息中
            if msg.function_call:
                message_dict["function_call"] = msg.function_call

            formatted_messages.append(message_dict)

        return formatted_messages

    def clear_session(self, session_id: str) -> bool:
        """清除指定会话的历史记录和意图"""
        deleted = False

        if session_id in self.session_histories:
            del self.session_histories[session_id]
            deleted = True

        return deleted


class ContextManager:
    """管理对话控制器上下文。

    该类用于维护会话相关的信息，包括对话历史缓存和意图管理。
    提供接口更新、查询和管理用户对话及其意图。

    Attributes:
        dialogue_history (DialogueHistoryCache): 对话历史缓存对象，按会话ID存储消息。
    """

    ROLE_MAP = {"user": "用户", "assistant": "助手", "system": "系统"}

    def __init__(self):
        """初始化 ContextManager 对象。"""
        self.dialogue_history = DialogueHistoryCache()  # 对话历史缓存

    def update_latest_message_intent(self, session_id: str, intent: str) -> bool:
        """
        更新指定会话中最后一条消息的意图标签

        Args:
            session_id: 会话ID
            intent: 新的意图标签

        Returns:
            是否成功更新
        """
        # 检查会话是否存在
        if session_id not in self.dialogue_history.session_histories:
            return False

        messages = self.dialogue_history.session_histories[session_id]

        # 检查是否有消息
        if not messages:
            return False

        # 更新最后一条消息的意图标签
        latest_message = messages[-1]
        latest_message.intent_label = intent

        return True

    # 查询相关方法
    def set_latest_query(self, session_id: str, query: str) -> None:
        """设置会话的最新查询"""
        self.dialogue_history.set_latest_query(session_id, query)

    def get_latest_query(self, session_id: str) -> Optional[str]:
        """获取会话的最新查询"""
        return self.dialogue_history.get_latest_query(session_id)

    def get_formatted_history(self, session_id: str, intent: str = None) -> str:
        """获取格式化的对话历史"""
        # 检查会话是否存在
        if session_id not in self.dialogue_history.session_histories:
            return ""

        messages = self.dialogue_history.session_histories[session_id]
        if intent is not None:
            messages = [msg for msg in messages if msg.intent_label == intent]
        formatted_messages = "\n".join(
            f"{ContextManager.ROLE_MAP.get(msg.role, '用户')}: {msg.content}"
            for msg in messages
        )
        return formatted_messages

    def get_filtered_messages(
        self, session_id: str, intent: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取会话中的消息，支持按意图过滤

        Args:
            session_id: 会话ID
            intent: 要过滤的意图标签，如果为None则不按意图过滤

        Returns:
            符合条件的消息列表，按API格式返回
        """
        # 检查会话是否存在
        if session_id not in self.dialogue_history.session_histories:
            return []

        messages = self.dialogue_history.session_histories[session_id]

        # 应用过滤条件
        filtered_messages = messages

        # 如果指定了意图，按意图过滤
        if intent is not None:
            filtered_messages = [
                msg for msg in filtered_messages if msg.intent_label == intent
            ]

        # 转换为API格式
        formatted_messages = []
        for msg in filtered_messages:
            message_dict = {"role": msg.role, "content": msg.content}

            formatted_messages.append(message_dict)

        return formatted_messages

    def add_message(
        self,
        session_id: str,
        content: str,
        role: str,
        name: str = "",
        timestamp: Optional[datetime] = None,
        intent_label: Optional[str] = None,
    ) -> None:
        """添加消息到对话历史"""
        message = DialogueMessage(
            content=content,
            role=role,
            name=name,
            timestamp=timestamp or datetime.now(tz=timezone.utc),
            intent_label=intent_label,
        )
        self.dialogue_history.add_message(session_id, message)

    def add_user_message(
        self, session_id: str, content: str, intent_label: Optional[str] = None
    ) -> None:
        """添加用户消息"""
        self.add_message(
            session_id=session_id,
            content=content,
            role="user",
            intent_label=intent_label,
        )

    def add_assistant_message(self, session_id: str, content: str, intent: str) -> None:
        """添加助手消息"""
        self.add_message(
            session_id=session_id,
            content=content,
            role="assistant",
            intent_label=intent,
        )

    def get_dialogue_history(self, session_id: str) -> List[DialogueMessage]:
        """获取指定会话的对话历史"""
        return self.dialogue_history.get_history(session_id)

    def get_latest_k_chat_history(
        self, session_id: str, k: int
    ) -> List[Dict[str, Any]]:
        """获取最近k条消息，按标准格式返回"""
        return self.dialogue_history.get_latest_k_messages(session_id, k)

    def get_non_function_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取不是function角色且不包含function_call的所有消息，并按API格式返回

        Args:
            session_id: 会话ID

        Returns:
            不包含function角色和function_call的消息列表，按API格式返回
        """
        if session_id not in self.dialogue_history.session_histories:
            return []

        messages = self.dialogue_history.session_histories[session_id]

        # 过滤出非function角色且不包含function_call的消息
        filtered_messages = [
            msg for msg in messages if msg.role != "function" and not msg.function_call
        ]

        # 转换为API格式
        formatted_messages = []
        for msg in filtered_messages:
            message_dict = {"role": msg.role, "content": msg.content}

            formatted_messages.append(message_dict)

        return formatted_messages

    def clear_dialogue(self, session_id: str):
        """清除指定会话的对话历史"""
        self.dialogue_history.clear_session(session_id)
