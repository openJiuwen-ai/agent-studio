# agent_runtime/schemas/additional_questions.py
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Pydantic schemas for additional-questions (追问) API."""

from dataclasses import dataclass

from pydantic import BaseModel, Field


class AdditionalQuestionsRequest(BaseModel):
    """追问请求体 — 精简版，模型配置统一从 IR 读取，不依赖前端传入。"""

    name: str = Field(..., min_length=1, description="应用名称")
    enable: bool = Field(True, description="追问是否启用")
    prompt: str = Field("", description="追问自定义 prompt 规则")
    version_id: str = Field("", description="版本号")


class AdditionalQuestionsResponse(BaseModel):
    """追问响应体 — 与 Java AutoAddResultJsonObject.questions 一致。"""

    questions: list[str] = Field(default_factory=list, description="追问列表")


@dataclass
class AdditionalQuestionsModelConfig:
    """追问场景的模型配置 — 从 IR 中提取的 model_service_id + auth_id。"""

    model_service_id: str
    auth_id: str = ""


@dataclass
class AdditionalQuestionsContext:
    """追问请求的上下文信息 — 封装资源标识与工作空间。"""

    resource_type: str
    resource_id: str
    project_id: str
    conversation_id: str
    workspace_id: str
