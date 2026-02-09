from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator, validator


class EmbeddingProtocol(str, Enum):
    """Embedding 协议类型"""
    OPENAI = "openai"


class EmbeddingModelConfigBase(BaseModel):
    """Embedding 模型配置基础Schema"""
    model_name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    space_id: str = Field(..., description="空间ID")
    protocol: EmbeddingProtocol = Field(..., description="协议类型：openai")
    model_id: str = Field(..., min_length=1, max_length=100, description="模型ID，如text-embedding-v3")
    api_base: str = Field(..., description="API端点URL")
    max_batch_size: int = Field(default=8, ge=1, le=100, description="最大批处理大小")
    is_active: bool = Field(default=True, description="是否激活")
    
    @validator('api_base')
    def validate_api_base(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('API base URL must start with http:// or https://')
        return v


class EmbeddingModelConfigCreate(EmbeddingModelConfigBase):
    """创建 Embedding 模型配置"""
    api_key: str = Field(..., min_length=1, description="API密钥（必填）")


class EmbeddingModelConfigUpdate(BaseModel):
    """更新 Embedding 模型配置"""
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    protocol: Optional[EmbeddingProtocol] = Field(None)
    model_id: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, description="API密钥")
    api_base: Optional[str] = Field(None)
    max_batch_size: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = Field(None)
    
    @validator('api_base')
    def validate_api_base(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('API base URL must start with http:// or https://')
        return v


class EmbeddingModelConfigResponse(EmbeddingModelConfigBase):
    """Embedding 模型配置响应"""
    id: int
    created_at: datetime
    updated_at: datetime
    api_key_masked: Optional[str] = Field(None, description="脱敏的API密钥")
    is_system_model: Optional[bool] = Field(None, description="是否系统预置模型")
    system_model_id: Optional[int] = Field(None, description="系统模型id")

    class Config:
        from_attributes = True


class EmbeddingModelConfigRequest(BaseModel):
    """Embedding 模型配置请求"""
    config_id: int
    space_id: str


class EmbeddingModelConfigUpdateRequest(BaseModel):
    """更新 Embedding 模型配置请求"""
    config_id: int = Field(..., description="配置ID")
    space_id: str = Field(..., description="空间ID")
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    protocol: Optional[EmbeddingProtocol] = Field(None)
    model_id: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, description="API密钥")
    api_base: Optional[str] = Field(None)
    max_batch_size: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = Field(None)
    
    @validator('api_base')
    def validate_api_base(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('API base URL must start with http:// or https://')
        return v


class EmbeddingModelConfigList(BaseModel):
    """Embedding 模型配置列表响应"""
    items: list[EmbeddingModelConfigResponse]
    total: int
    page: int
    size: int


class EmbeddingModelTestRequest(BaseModel):
    """Embedding 模型测试请求"""
    text: Optional[str] = Field(None, min_length=1, max_length=1000, description="测试文本（单文本测试）")
    texts: Optional[list[str]] = Field(None, min_length=1, description="测试文本列表（批量测试）")
    
    @model_validator(mode='after')
    def validate_text_input(self):
        """确保至少提供 text 或 texts 之一，且不能同时提供"""
        if not self.text and not self.texts:
            raise ValueError('Either text or texts must be provided')
        if self.text and self.texts:
            raise ValueError('Cannot provide both text and texts, choose one')
        return self


class EmbeddingModelTestResponse(BaseModel):
    """Embedding 模型测试响应"""
    success: bool = Field(..., description="测试是否成功")
    embedding: Optional[list[float]] = Field(None, description="单文本的 embedding 向量")
    embeddings: Optional[list[list[float]]] = Field(None, description="批量文本的 embedding 向量列表")
    dimension: Optional[int] = Field(None, description="Embedding 向量维度")
    error: Optional[str] = Field(None, description="错误信息（如果测试失败）")
    latency: float = Field(..., description="响应延迟（秒）")

