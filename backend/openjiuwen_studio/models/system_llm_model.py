from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func

from .db_fun_base import Base, DBFunBase


class SystemLLMModelDB(Base, DBFunBase):
    """系统预置LLM模型表"""
    __tablename__ = "system_llm_model"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    provider = Column(String(50), nullable=False, index=True)  # openai, anthropic, deepseek, qwen, etc.
    model_type = Column(String(100), nullable=False)  # gpt-4, claude-3, etc.
    description = Column(Text, nullable=True)  # 模型描述

    # API configuration
    api_key = Column(Text, nullable=True)  # encrypted in production
    base_url = Column(String(500), nullable=True)  # for custom endpoints
    is_active = Column(Boolean, server_default="1", index=True)

    # Model parameters (stored as JSON)
    parameters = Column(JSON, default=dict)  # temperature, max_tokens, etc.

    # Connection settings
    timeout = Column(Integer, default=60)  # Request timeout in seconds

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemLLMModel(id={self.id}, name='{self.name}', provider='{self.provider}')>"
