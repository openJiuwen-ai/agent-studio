# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
App Release Service — 应用发布信息查询

从 Redis 查询 short_code 对应的 ReleaseInfo，供网页执行接口使用。
"""

import json
from typing import Optional

from fastapi.responses import JSONResponse
from openjiuwen.core.common.logging import workflow_logger
from pydantic import BaseModel, Field, ConfigDict

# Redis key 格式：release_web_rel_{short_code}
_RELEASE_WEB_REL_KEY = "release_web_rel_%s"


class ReleaseInfo(BaseModel):
    """应用发布信息"""

    app_id: str = Field(alias="app_id", default="")
    app_type: str = Field(alias="app_type", default="")
    version_id: str = Field(alias="version_id", default="")
    channel_type: Optional[str] = Field(alias="channel_type", default=None)
    short_code: Optional[str] = Field(alias="short_code", default=None)
    project_id: str = Field(alias="project_id", default="")
    workspace_id: str = Field(alias="workspace_id", default="")
    domain_id: str = Field(alias="domain_id", default="")
    visibility_scope: Optional[str] = Field(alias="visibility_scope", default=None)
    call_count: Optional[int] = Field(alias="call_count", default=None)
    already_been_called: Optional[int] = Field(alias="already_been_called", default=None)
    update_time: Optional[int] = Field(alias="update_time", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


# 错误码 key
_CODE_RELEASE_NOT_FOUND = "02201022"
_CODE_REDIS_QUERY_FAILED = "02201023"


def _build_error_response(
    status_code: int, code_key: str, language: str = "zh-cn"
) -> JSONResponse:
    """ErrorRsp 格式的错误响应。"""
    from agent_runtime.event_handler.base.mappers import ErrorContextBuilder

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


class AppRelease:
    """应用发布信息查询 — 从 Redis 获取 short_code 对应的 ReleaseInfo。"""

    async def get_release_info(
        self, short_code: str, language: str = "zh-cn"
    ) -> ReleaseInfo | JSONResponse:
        """查询 short_code 对应的 ReleaseInfo。

        Args:
            short_code: 网页发布短码
            language: 请求语言偏好（用于 i18n 错误消息）

        Returns:
            ReleaseInfo 实例；查询失败时返回 JSONResponse 错误响应。

        """
        from common_utils.redis_manager import get_redis_client

        release_key = _RELEASE_WEB_REL_KEY % short_code
        redis_client = get_redis_client()

        try:
            raw = await redis_client.get(release_key)
        except Exception as e:
            workflow_logger.error(
                "Failed to query release info from Redis: key=%s, error=%s",
                release_key,
                e,
            )
            return _build_error_response(500, _CODE_REDIS_QUERY_FAILED, language)

        if not raw:
            workflow_logger.error(
                "Release info not found in Redis: key=%s, short_code=%s",
                release_key,
                short_code,
            )
            return _build_error_response(404, _CODE_RELEASE_NOT_FOUND, language)

        try:
            data = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            release_info = ReleaseInfo.model_validate(json.loads(data))
        except Exception as e:
            workflow_logger.error(
                "Failed to parse release info: key=%s, error=%s",
                release_key,
                e,
            )
            return _build_error_response(500, _CODE_REDIS_QUERY_FAILED, language)

        if not release_info.app_id:
            workflow_logger.error(
                "Release info has empty app_id: key=%s, short_code=%s",
                release_key,
                short_code,
            )
            return _build_error_response(404, _CODE_RELEASE_NOT_FOUND, language)

        workflow_logger.info(
            "Release info loaded: short_code=%s, app_id=%s, version_id=%s",
            short_code,
            release_info.app_id,
            release_info.version_id,
        )
        return release_info
