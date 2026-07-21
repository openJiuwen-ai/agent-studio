# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
ConversationVariable API — 会话全局变量管理

读写 Redis 中 global.vals.{resourceId}.{conversationId} 的会话变量，
供前端查看和修改工作流/智能体执行过程中的全局变量。
"""

import json
from typing import Any, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openjiuwen.core.common.logging import workflow_logger
from pydantic import BaseModel, Field, ConfigDict

from agent_runtime.common.config import settings
from agent_runtime.context.request_context import _request_ctx
from agent_runtime.event_handler.base.mappers import ErrorContextBuilder


# Redis key 格式: global.vals.{resourceId}.{conversationId}
_GLOBAL_VALS_KEY_TEMPLATE = "global.vals.%s.%s"

# 会话变量过期时间（秒），默认3天，通过 CONVERSATION_VARIABLE_STORE_TIME 环境变量配置
_DEFAULT_CONVERSATION_VARIABLE_TTL = settings.conversation_variable.ttl_seconds

# 错误码 key（对齐 StudioError AGENT 1035/1036）
_CODE_GET_VARIABLE_FAILED = "02101035"
_CODE_PARSE_VARIABLE_FAILED = "02101036"

conversation_variable_router = APIRouter(tags=["conversation_variable"])


class VariableInfo(BaseModel):
    """变量信息"""

    name: str = Field(default="")
    value: Optional[Any] = Field(default=None)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ConversationVariableRsp(BaseModel):
    """获取会话变量响应"""

    status: str = Field(default="success")
    data: List[VariableInfo] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class UpdateVariableReq(BaseModel):
    """更新变量请求体"""

    value: Any = Field(default=None)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


def _build_error_response(
    status_code: int, code_key: str, language: str = "zh-cn"
) -> JSONResponse:
    """构建错误响应."""
    error_code, error_msg, error_reason, error_suggestion = (
        ErrorContextBuilder.get_language_context(language, code_key)
    )
    content = {
        "error_code": error_code,
        "error_msg": error_msg,
        "error_reason": error_reason,
        "error_suggestion": error_suggestion,
    }
    return JSONResponse(status_code=status_code, content=content)


def _build_redis_key(resource_id: str, conversation_id: str) -> str:
    """构造 Redis key."""
    return _GLOBAL_VALS_KEY_TEMPLATE % (resource_id, conversation_id)


def _parse_variables_from_json(raw_json: str) -> list[VariableInfo]:
    """将 JSON 字符串解析为 VariableInfo 列表."""
    if not raw_json or not raw_json.strip():
        return []

    obj = json.loads(raw_json)
    if not isinstance(obj, dict):
        return []

    return [VariableInfo(name=k, value=v) for k, v in obj.items()]


@conversation_variable_router.get(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/variables"
)
async def get_conversation_variables(
    project_id: str,
    agent_id: str,
    conversation_id: str,
    resource_type: str = "workflow",
):
    """获取会话全局变量"""
    language = _request_ctx.get().headers.get("x-language", "zh-cn")
    redis_key = _build_redis_key(agent_id, conversation_id)

    try:
        from agent_runtime.common.redis_manager import get_redis_client

        redis_client = get_redis_client()
        raw = await redis_client.get(redis_key)
    except Exception as e:
        workflow_logger.error(
            "Failed to get conversation variables: key=%s, error=%s",
            redis_key,
            e,
        )
        return _build_error_response(500, _CODE_GET_VARIABLE_FAILED, language)

    if raw is None:
        return ConversationVariableRsp(status="success", data=[])

    raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw

    try:
        variables = _parse_variables_from_json(raw_str)
    except ValueError as e:
        workflow_logger.error(
            "Failed to parse conversation variables: key=%s, error=%s",
            redis_key,
            e,
        )
        return _build_error_response(400, _CODE_PARSE_VARIABLE_FAILED, language)

    return ConversationVariableRsp(status="success", data=variables)


@conversation_variable_router.put(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/variables/{var_id}"
)
async def update_conversation_variable(
    body: UpdateVariableReq,
    project_id: str,
    agent_id: str,
    conversation_id: str,
    var_id: str,
):
    """更新会话全局变量"""
    language = _request_ctx.get().headers.get("x-language", "zh-cn")
    redis_key = _build_redis_key(agent_id, conversation_id)

    try:
        from agent_runtime.common.redis_manager import get_redis_client

        redis_client = get_redis_client()
        raw = await redis_client.get(redis_key)
    except Exception as e:
        workflow_logger.error(
            "Failed to get conversation variables for update: key=%s, error=%s",
            redis_key,
            e,
        )
        return _build_error_response(500, _CODE_GET_VARIABLE_FAILED, language)

    if raw is None:
        return _build_error_response(400, _CODE_GET_VARIABLE_FAILED, language)

    raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw

    try:
        obj = json.loads(raw_str)
    except ValueError as e:
        workflow_logger.error(
            "Failed to parse conversation variables for update: key=%s, error=%s",
            redis_key,
            e,
        )
        return _build_error_response(400, _CODE_PARSE_VARIABLE_FAILED, language)

    # 更新顶层 key
    obj[var_id] = body.value

    try:
        await redis_client.set(
            redis_key, json.dumps(obj, ensure_ascii=False),
            ex=_DEFAULT_CONVERSATION_VARIABLE_TTL,
        )
    except Exception as e:
        workflow_logger.error(
            "Failed to set conversation variables: key=%s, error=%s",
            redis_key,
            e,
        )
        return _build_error_response(500, _CODE_GET_VARIABLE_FAILED, language)

    return VariableInfo(name=var_id, value=body.value)
