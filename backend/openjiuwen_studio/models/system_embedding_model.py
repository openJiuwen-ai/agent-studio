from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from .db_fun_base import Base, DBFunBase


class SystemEmbeddingModelDB(Base, DBFunBase):
    """系统预置Embedding模型表"""
    __tablename__ = "system_embedding_model"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, unique=True)  # 配置名称
    protocol = Column(String(50), nullable=False, index=True)  # 协议：openai

    model_id = Column(String(100), nullable=False)  # 模型ID：text-embedding-v3等
    api_key = Column(Text, nullable=True)  # API密钥（加密存储）
    api_base = Column(String(500), nullable=False)  # API端点URL
    max_batch_size = Column(Integer, default=8, nullable=False)  # 最大批处理大小
    is_active = Column(Boolean, server_default="1", index=True)  # 是否激活

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemEmbeddingModel(id={self.id}, model_name='{self.model_name}', protocol='{self.protocol}')>"
