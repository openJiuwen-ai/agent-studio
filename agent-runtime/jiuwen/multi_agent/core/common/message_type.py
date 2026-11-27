#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import secrets
from abc import ABC, abstractmethod
from asyncio import Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from jiuwen.multi_agent.core.stream.stream_handler import StreamHandler


@dataclass(kw_only=True)
class EnvelopeMetadata:
    """Metadata for an envelope."""

    created_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvelopeMetadata":
        """from dict"""
        return cls(
            created_at=data.get(
                "created_at", datetime.now(tz=timezone.utc).isoformat()
            ),
            extra=data.get("extra", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """to dict"""
        return {"created_at": self.created_at, "extra": self.extra}


@dataclass(kw_only=True)
class MessageEnvelope(ABC):
    """Base class for message envelopes."""

    message: Any
    sender: Any | None
    recipient: Any
    metadata: EnvelopeMetadata | None = None
    message_id: str = field(default_factory=lambda: str(secrets.token_hex(24)))
    future: Future[Any] | None = None  # Future 不参与序列化

    @staticmethod
    def _serialize_message(message: Any) -> Dict[str, Any]:
        """Serialize message content."""
        if isinstance(message, list):
            return {
                "type": "list",
                "data": [MessageEnvelope._serialize_message(msg) for msg in message],
            }
        if isinstance(message, dict):
            return {"type": "dict", "data": message}
        if hasattr(message, "to_dict"):
            return {"type": message.__class__.__name__, "data": message.to_dict()}
        return {
            "type": "primitive",
            "data": str(message),  # 确保可序列化
        }

    @staticmethod
    def _deserialize_message(data: Dict[str, Any]) -> Any:
        """Deserialize message content."""
        if not data:
            return None

        msg_type = data.get("type")
        msg_data = data.get("data")

        if msg_type == "list":
            return [MessageEnvelope._deserialize_message(item) for item in msg_data]
        if msg_type == "dict":
            return msg_data
        if msg_type == "primitive":
            return msg_data
        # 对于自定义类型，这里简化处理，返回原始数据
        return msg_data

    @staticmethod
    def _serialize_actor(actor: Any) -> Any:
        """Serialize actor (sender/recipient)."""
        if actor is None:
            return None
        if isinstance(actor, str):
            return actor
        if hasattr(actor, "to_dict"):
            return actor.to_dict()
        return str(actor)

    @staticmethod
    def _deserialize_actor(data: Any) -> Any:
        """Deserialize actor (sender/recipient)."""
        return data  # 简化处理，直接返回

    @classmethod
    def create_envelope_from_dict(cls, data: Dict[str, Any]):
        """Factory function to create envelope from dictionary based on type."""
        envelope_type = data.get("type")

        if envelope_type == "SendMessageEnvelope":
            return SendMessageEnvelope.from_dict(data)
        if envelope_type == "ResponseMessageEnvelope":
            return ResponseMessageEnvelope.from_dict(data)
        raise ValueError(f"Unknown envelope type: {envelope_type}")

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert envelope to dictionary for serialization."""
        pass


@dataclass(kw_only=True)
class SendMessageEnvelope(MessageEnvelope):
    """A message envelope for sending a message to a specific agent."""

    stream_handler: StreamHandler | None = None  # 流处理函数，用于处理流式消息
    # 发送时刻的用户 id：消息经队列与 asyncio.create_task 投递，处理任务
    # 继承的是消费循环上下文（用户事实为空），由本字段携带过界、在
    # _process_send_message 入口回绑 ContextVar，供遥测身份（gen_ai.user.id）读取。
    user_id: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SendMessageEnvelope":
        """Create SendMessageEnvelope from dictionary."""
        return cls(
            message_id=data["message_id"],
            message=cls._deserialize_message(data["message"]),
            sender=cls._deserialize_actor(data["sender"]),
            recipient=cls._deserialize_actor(data["recipient"]),
            metadata=EnvelopeMetadata.from_dict(data["metadata"])
            if data.get("metadata")
            else None,
            future=None,  # Future 不能序列化，恢复时为 None
            stream_handler=None,  # StreamHandler 不能序列化，恢复时为 None
            user_id=data.get("user_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert SendMessageEnvelope to dictionary."""
        return {
            "type": "SendMessageEnvelope",
            "message_id": self.message_id,
            "message": self._serialize_message(self.message),
            "sender": self._serialize_actor(self.sender),
            "recipient": self._serialize_actor(self.recipient),
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "user_id": self.user_id,
        }


@dataclass(kw_only=True)
class ResponseMessageEnvelope(MessageEnvelope):
    """A message envelope for sending a response to a message."""

    original_message_id: str  # 关联到原始发送消息的ID

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResponseMessageEnvelope":
        """Create ResponseMessageEnvelope from dictionary."""
        return cls(
            message_id=data["message_id"],
            message=cls._deserialize_message(data["message"]),
            sender=cls._deserialize_actor(data["sender"]),
            recipient=cls._deserialize_actor(data["recipient"]),
            metadata=EnvelopeMetadata.from_dict(data["metadata"])
            if data.get("metadata")
            else None,
            original_message_id=data["original_message_id"],
            future=None,  # Future 不能序列化，恢复时为 None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ResponseMessageEnvelope to dictionary."""
        return {
            "type": "ResponseMessageEnvelope",
            "message_id": self.message_id,
            "message": self._serialize_message(self.message),
            "sender": self._serialize_actor(self.sender),
            "recipient": self._serialize_actor(self.recipient),
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "original_message_id": self.original_message_id,
        }
