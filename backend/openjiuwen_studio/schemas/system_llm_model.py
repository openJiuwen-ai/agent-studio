from typing import List

from pydantic import Field

from openjiuwen_studio.schemas import ModelConfigUpdate, ModelConfigCreate, ModelConfigResponse
from openjiuwen_studio.schemas.model_config import ModelConfigList


class SystemLLMModelCreate(ModelConfigCreate):
    """Request schema for create system llm model"""
    space_id: str = Field(default=0, exclude=True)


class SystemLLMModelUpdate(ModelConfigUpdate):
    """Request schema for update system llm model"""
    id: int = Field(..., ge=0, description="Model auto_increment id", exclude=True)
    space_id: str = Field(default=0, exclude=True)


class SystemLLMModelResponse(ModelConfigResponse):
    """Response schema for create/update system llm model"""
    space_id: str = Field(exclude=True)


class SystemLLMModelRespList(ModelConfigList):
    """Response schema for listing system llm models"""
    items: List[SystemLLMModelResponse]
