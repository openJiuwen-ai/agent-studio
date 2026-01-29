from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from .db_fun_base import Base


class EmbeddingModelConfig(Base):
    """Embedding 模型配置表 - 简化版，只包含必要的5个字段"""
    __tablename__ = "embedding_model_configs"

    # Basic information
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, index=True)  # 配置名称
    space_id = Column(String(50), nullable=False, index=True)  # 空间ID

    # 5个核心配置字段
    protocol = Column(String(50), nullable=False, index=True)  # 协议：openai
    model_id = Column(String(100), nullable=False)  # 模型ID：text-embedding-v3等
    api_key = Column(Text, nullable=True)  # API密钥（加密存储）
    api_base = Column(String(500), nullable=False)  # API端点URL
    max_batch_size = Column(Integer, default=8, nullable=False)  # 最大批处理大小

    # 状态
    is_active = Column(Boolean, default=True, index=True)  # 是否激活

    # 是否预置模型相关字段
    is_system_model = Column(Boolean, server_default="0")  # 是否预置
    system_model_id = Column(Integer, index=True)  # 系统模型的id

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<EmbeddingModelConfig(id={self.id}, model_name='{self.model_name}', protocol='{self.protocol}')>"

    def mask_api_key(self) -> str:
        """返回脱敏的API密钥用于显示"""
        if not self.api_key:
            return None
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]
