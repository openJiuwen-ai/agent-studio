from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    GOOGLE = "google"
    BAIDU = "baidu"
    ZHIPU = "zhipu"
    SILICONFLOW = "siliconflow"
    CUSTOM = "custom"


class ModelParameters(BaseModel):
    """Model-specific parameters"""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling to generate")


class ModelConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Model configuration name")
    provider: ModelProvider = Field(..., description="AI model provider")
    space_id: str = Field("0", description="belong to spacific space")
    model_type: str = Field(..., min_length=1, max_length=100, description="Specific model name")
    base_url: str = Field(..., min_length=1, description="Custom API endpoint URL")
    is_active: Optional[bool] = Field(default=True, description="Whether the model is active")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    tags: List[str] = Field(default_factory=list, description="Model tags for categorization")

    # Model parameters
    parameters: Optional[ModelParameters] = Field(default_factory=ModelParameters)

    # Connection settings
    timeout: Optional[int] = Field(default=60, ge=1, le=3600, description="Request timeout in seconds")
    retry_count: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    enable_streaming: bool = Field(default=True, description="Enable streaming responses")
    enable_function_calling: bool = Field(default=False, description="Enable function calling")

    @validator('base_url')
    def validate_base_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return [tag.strip() for tag in v if tag.strip()]


class ModelUsageStats(BaseModel):
    """Model usage statistics"""
    total_requests: int = Field(default=0, description=" Total number of requests")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate (0-1)")
    avg_response_time: float = Field(default=0.0, description="Average response time in seconds")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    daily_requests: int = Field(default=0, description="Requests today")
    daily_tokens: int = Field(default=0, description="Tokens consumed today")
    daily_cost: float = Field(default=0.0, description="Cost today in USD")
    monthly_requests: int = Field(default=0, description="Requests this month")
    monthly_tokens: int = Field(default=0, description="Tokens consumed this month")
    monthly_cost: float = Field(default=0.0, description="Cost this month in USD")


class ModelConfigCreate(ModelConfigBase):
    api_key: Optional[str] = Field(None, description="API key for the model provider")

    @validator('api_key')
    def validate_api_key(cls, v, values):
        provider = values.get('provider')
        if provider and provider != ModelProvider.CUSTOM and not v:
            raise ValueError(f'API key is required for {provider} provider')
        return v


class ModelConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[ModelProvider] = Field(None)
    model_type: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, description="API key for the model provider")
    base_url: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(None)
    parameters: Optional[ModelParameters] = Field(None)
    timeout: Optional[int] = Field(None, ge=1, le=3600)
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    enable_streaming: Optional[bool] = Field(None)
    enable_function_calling: Optional[bool] = Field(None)

    @validator('base_url')
    def validate_base_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return [tag.strip() for tag in v if tag.strip()] if v else v


class ModelConfigResponse(ModelConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime
    usage_stats: ModelUsageStats = Field(default_factory=ModelUsageStats)
    # API key is masked in response for security
    api_key_masked: Optional[str] = Field(None, description="Masked API key for display")
    is_system_model: Optional[bool] = Field(None, description="是否系统预置模型")
    system_model_id: Optional[int] = Field(None, description="系统模型id")

    class Config:
        from_attributes = True


class ModelConfigRequest(BaseModel):
    config_id: int
    space_id: str


class ModelTestRequest(BaseModel):
    """Request schema for testing model configuration"""
    prompt: str = Field(..., min_length=1, max_length=1000, description="Test prompt")
    parameters: Optional[ModelParameters] = Field(None, description="Override parameters for test")


class ModelTestResponse(BaseModel):
    """Response schema for model test results"""
    success: bool = Field(..., description="Whether the test was successful")
    response: Optional[str] = Field(None, description="Model response")
    error: Optional[str] = Field(None, description="Error message if test failed")
    latency: float = Field(..., description="Response latency in seconds")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    cost: Optional[float] = Field(None, description="Estimated cost in USD")


class ModelConfigList(BaseModel):
    """Response schema for listing model configurations"""
    items: List[ModelConfigResponse]
    total: int
    page: int
    size: int


class ModelConfigFilter(BaseModel):
    """Filter parameters for model configurations"""
    provider: Optional[ModelProvider] = Field(None)
    is_active: Optional[bool] = Field(None)
    tags: Optional[List[str]] = Field(None)
    search: Optional[str] = Field(None, description="Search in name, description, model_type")
