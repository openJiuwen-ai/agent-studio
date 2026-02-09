#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# 记忆库名称中不允许的特殊字符正则表达式
INVALID_MEMORY_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_memory_name(name: str) -> str:
    """验证记忆库名称，不允许包含特殊字符"""
    if not name or not name.strip():
        raise ValueError("记忆库名称不能为空")

    trimmed_name = name.strip()

    if trimmed_name != name:
        raise ValueError("记忆库名称不能以空格开头或结尾")

    if INVALID_MEMORY_NAME_CHARS.search(trimmed_name):
        raise ValueError('记忆库名称不能包含以下字符: < > : " / \\ | ? * 以及控制字符')

    return name


class MemoryBaseCreate(BaseModel):
    """创建记忆库请求"""
    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    name: str = Field(..., min_length=1, max_length=100, description="记忆库名称")
    description: str = Field(..., max_length=2000, description="记忆库描述")
    embedding_model_config_id: int = Field(..., description="Embedding 模型配置ID（必填，记忆库创建时选择，后续不可更改）")
    llm_model_config_id: int = Field(..., description="LLM 模型配置ID（必填，记忆库创建时选择)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证记忆库名称"""
        return validate_memory_name(v)


class MemoryBaseResponseCreate(BaseModel):
    """创建记忆库响应"""
    mdb_id: str = Field(..., description="记忆库ID")

    class Config:
        populate_by_name = True


class MemoryBaseGet(BaseModel):
    """获取/删除记忆库请求"""
    space_id: str = Field(..., min_length=0, max_length=100, description="空间ID")
    mdb_id: str = Field(..., min_length=1, max_length=100, description="记忆库ID")


class MemoryBaseUpdateRequest(BaseModel):
    """更新记忆库请求"""
    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    mdb_id: str = Field(..., min_length=1, max_length=100, description="记忆库ID")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="新的名字")
    description: Optional[str] = Field(None, description="新的描述")
    llm_model_config_id: Optional[int] = Field(None, description="LLM 模型配置ID)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证记忆库名称"""
        return validate_memory_name(v)


class MemoryBaseInfo(BaseModel):
    """记忆库信息"""
    mdb_id: str = Field(...)
    space_id: str = Field(..., description="空间ID")
    name: str = Field(..., description="记忆库名称")
    description: str = Field(..., description="记忆库描述")
    embedding_model_config_id: int = Field(..., description="Embedding 模型配置ID")
    llm_model_config_id: int = Field(..., description="LLM 模型配置ID（必填，记忆库创建时选择)")
    create_time: int = Field(..., description="创建时间")
    update_time: int = Field(..., description="更新时间")

    class Config:
        populate_by_name = True


class MemoryBaseListRequest(BaseModel):
    """记忆库列表请求"""
    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    page: int = Field(1, ge=1, description="页码，默认1")
    page_size: int = Field(10, ge=1, le=100, description="每页大小，默认10")


class MemoryBaseListItem(BaseModel):
    """记忆库列表项"""
    mdb_id: str = Field(..., description="记忆库ID")
    space_id: str = Field(..., description="空间ID")
    name: str = Field(..., description="记忆库名称")
    description: str = Field(..., description="记忆库描述")
    embedding_model_config_id: int = Field(..., description="Embedding 模型配置ID")
    llm_model_config_id: int = Field(..., description="LLM 模型配置ID（必填，记忆库创建时选择)")
    created_at: str = Field(..., description="创建时间，格式：YYYY-MM-DD HH:MM:SS")
    updated_at: str = Field(..., description="更新时间，格式：YYYY-MM-DD HH:MM:SS")


class MemoryBaseListResponse(BaseModel):
    """记忆库列表响应"""
    items: list[MemoryBaseListItem] = Field(..., description="记忆库列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


class MemoryBaseSearchRequest(BaseModel):
    """记忆库查询请求"""
    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    query: str = Field(..., min_length=1, max_length=500,
                       description="查询词（查询词完整出现在记忆库名称或描述中，大小写不敏感）")
    page: Optional[int] = Field(1, ge=1, description="页码，从1开始")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="每页大小，最大100")


class MemoryBaseSearchResponse(BaseModel):
    """记忆库查询响应"""
    memory_bases: list[MemoryBaseListItem] = Field(..., description="匹配的记忆库列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")