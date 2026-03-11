#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
低代码模式数据模型定义
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelReference(BaseModel):
    """模型引用定义"""
    provider: str
    model_type: str
    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 300
    parameters: Optional[Dict[str, Any]] = None


class ModelOverride(BaseModel):
    """模型配置覆盖"""
    provider: Optional[str] = None
    model_type: Optional[str] = None
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None


class AgentDependencies(BaseModel):
    """Agent依赖项"""
    workflows: List[Dict[str, Any]] = Field(default_factory=list)
    plugins: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_bases: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_templates: List[Dict[str, Any]] = Field(default_factory=list)


class AgentExportMetadata(BaseModel):
    """导出元数据"""
    export_time: str
    export_by: str
    agent_studio_version: Optional[str] = None


class AgentExportData(BaseModel):
    """Agent导出数据结构"""
    version: str = "1.0.0"
    agent: Dict[str, Any]
    dependencies: AgentDependencies = Field(default_factory=AgentDependencies)
    metadata: Optional[AgentExportMetadata] = None
    model_references: Optional[Dict[str, ModelReference]] = None


class CompileRequest(BaseModel):
    """编译请求"""
    export_data: AgentExportData
    model_overrides: Optional[Dict[str, ModelOverride]] = None
    space_id: Optional[str] = None


class CompileResponse(BaseModel):
    """编译响应"""
    agent_id: str
    agent_type: str
    agent_name: str
    status: str
    compile_time: str
    model_info: Dict[str, Any]
    dependencies_count: Dict[str, int]


class RunRequest(BaseModel):
    """运行请求"""
    export_data: AgentExportData
    model_overrides: Optional[Dict[str, ModelOverride]] = None
    inputs: Dict[str, Any]
    conversation_id: str
    space_id: Optional[str] = None


class ValidateRequest(BaseModel):
    """验证请求"""
    export_data: AgentExportData
    model_overrides: Optional[Dict[str, ModelOverride]] = None


class ValidationError(BaseModel):
    """验证错误"""
    field: str
    message: str
    severity: str = "error"  # error, warning, info


class ValidationResult(BaseModel):
    """验证结果"""
    valid: bool
    checks: Dict[str, str]
    errors: List[ValidationError] = Field(default_factory=list)


class ExecuteResponse(BaseModel):
    """执行响应"""
    type: str  # AGENT | WORKFLOW | TRACE | INTERACTION | start | finish | error
    payload: Dict[str, Any]
