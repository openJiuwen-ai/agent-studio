from typing import List

from pydantic import Field

from openjiuwen_studio.schemas.embedding_model_config import EmbeddingModelConfigCreate, EmbeddingModelConfigResponse, \
    EmbeddingModelConfigUpdateRequest, EmbeddingModelConfigList


class SystemEmbeddingModelCreate(EmbeddingModelConfigCreate):
    """Request schema for create system embedding model"""
    space_id: str = Field(default=0, exclude=True)


class SystemEmbeddingModelUpdate(EmbeddingModelConfigUpdateRequest):
    """Request schema for create system embedding model"""
    id: int = Field(..., ge=0, description="Model auto_increment id", exclude=True)
    space_id: str = Field(default=0, exclude=True)
    config_id: int = Field(default=0, exclude=True)


class SystemEmbeddingModelResponse(EmbeddingModelConfigResponse):
    """Response schema for create/update system embedding model"""
    space_id: str = Field(exclude=True)


class SystemEmbeddingModelRespList(EmbeddingModelConfigList):
    """Response schema for listing system embedding models"""
    items: List[SystemEmbeddingModelResponse]
