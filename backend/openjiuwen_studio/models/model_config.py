from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db_fun_base import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"
    
    # Basic information
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    space_id = Column(String(50), nullable=False, index=True)  # sapce_id, etc.
    provider = Column(String(50), nullable=False, index=True)  # openai, anthropic, deepseek, qwen, etc.
    model_type = Column(String(100), nullable=False)  # gpt-4, claude-3, etc.
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # List of tags for categorization
    
    # API configuration
    api_key = Column(Text, nullable=True)  # encrypted in production
    base_url = Column(String(500), nullable=True)  # for custom endpoints
    is_active = Column(Boolean, default=True, index=True)
    
    # Model parameters (stored as JSON)
    parameters = Column(JSON, default=dict)  # temperature, max_tokens, etc.
    
    # Connection settings
    timeout = Column(Integer, default=60)  # Request timeout in seconds
    retry_count = Column(Integer, default=3)  # Number of retry attempts
    enable_streaming = Column(Boolean, default=True)
    enable_function_calling = Column(Boolean, default=False)
    
    # Usage statistics
    total_requests = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    avg_response_time = Column(Float, default=0.0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    daily_requests = Column(Integer, default=0)
    daily_tokens = Column(Integer, default=0)
    daily_cost = Column(Float, default=0.0)
    monthly_requests = Column(Integer, default=0)
    monthly_tokens = Column(Integer, default=0)
    monthly_cost = Column(Float, default=0.0)

    # 是否预置模型相关字段
    is_system_model = Column(Boolean, server_default="0")  # 是否预置
    system_model_id = Column(Integer, index=True)  # 系统模型的id
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    usage_logs = relationship("ModelUsageLog", back_populates="model_config", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ModelConfig(id={self.id}, name='{self.name}', provider='{self.provider}')>"
    
    def mask_api_key(self) -> str:
        """Return masked API key for display purposes"""
        if not self.api_key:
            return None
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]
    
    def update_usage_stats(self, tokens_used: int, cost: float, response_time: float, success: bool):
        """Update usage statistics"""
        self.total_requests += 1
        self.total_tokens += tokens_used
        self.total_cost += cost
        self.daily_requests += 1
        self.daily_tokens += tokens_used
        self.daily_cost += cost
        self.monthly_requests += 1
        self.monthly_tokens += tokens_used
        self.monthly_cost += cost
        
        # Update success rate
        if self.total_requests > 0:
            current_success_count = self.success_rate * (self.total_requests - 1)
            if success:
                current_success_count += 1
            self.success_rate = current_success_count / self.total_requests
        
        # Update average response time
        if self.total_requests > 0:
            total_time = self.avg_response_time * (self.total_requests - 1) + response_time
            self.avg_response_time = total_time / self.total_requests
        
        self.last_used = func.now()


class ModelUsageLog(Base):
    """Log individual model usage for detailed tracking"""
    __tablename__ = "model_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    model_config_id = Column(Integer, ForeignKey("model_configs.id"), nullable=False, index=True)
    # user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)  # Optional user tracking
    
    # Request details
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    response_time = Column(Float, default=0.0)  # in seconds
    
    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    model_config = relationship("ModelConfig", back_populates="usage_logs")
    
    def __repr__(self):
        return f"<ModelUsageLog(id={self.id}, model_config_id={self.model_config_id}, tokens={self.total_tokens})>"