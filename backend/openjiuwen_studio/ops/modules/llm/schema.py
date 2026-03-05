#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""llm service schema"""

from typing import Optional
from pydantic import BaseModel, Field


class ListModelRequest(BaseModel):
    """
    列出可用模型信息列表的请求结构
    """
    workspace_id: str = Field(...)
    scenario: str = Field(default="prompt_debug", description="调用场景")
    page_size: int = Field(default=100, ge=1, le=100, description="Page size")
    page_token: str = Field(default="0")
    is_active: bool = Field(default=True)
    page_num: int = Field(default=1, ge=1, description="Page num")


class GetModelRequest(BaseModel):
    """
    查询某个空间中模型信息列表的请求结构
    """
    workspace_id: str = Field(...)
    model_from: Optional[str] = None
