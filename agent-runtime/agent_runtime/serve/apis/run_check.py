# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
运行前校验 — 对齐Java checkBeforeRun逻辑

4项校验：
1. Query长度校验
2. Chat工作流query必填
3. 项目权限校验
4. 版本新鲜度校验
"""

import os
from dataclasses import dataclass
from typing import Optional, Union

from fastapi import Request
from fastapi.responses import JSONResponse
from openjiuwen.core.common.logging import workflow_logger
from agent_runtime.event_handler.base.mappers import ErrorContextBuilder


# 错误码key（对齐Java StudioError，用于ErrorContextBuilder查询i18n消息）
_CODE_METHOD_ARGUMENT = "02001003"
_CODE_WORKFLOW_PERMISSION = "02201020"
_CODE_AGENT_PERMISSION = "02101016"
_CODE_NOT_LATEST = "02201021"

# 可配置参数
_MAX_QUERY_LENGTH = int(os.environ.get("RUN_MAX_QUERY_LENGTH", "100000"))


def _get_language(request: Request) -> str:
    """从请求头获取语言偏好."""
    return request.headers.get("x-language", "zh-cn") if request else "zh-cn"


def _is_empty_query(query: Optional[str]) -> bool:
    """判断query是否为空（None或纯空白字符串）."""
    return query is None or (isinstance(query, str) and query.strip() == "")


@dataclass
class RunCheckContext:
    """运行校验上下文 — 封装校验所需的公共参数."""
    query: Optional[str]
    project_id: str
    ir_path: str
    body_version: Optional[Union[str, int]]
    has_published_version: bool
    request: Request = None
    is_node_execute: bool = False


def _build_error_response(
    status_code: int, code_key: str, language: str = "zh-cn"
) -> JSONResponse:
    """构建对齐Java ErrorRsp格式的错误响应，通过i18n获取消息."""
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


async def _load_ir_metadata(ir_path: str) -> dict:
    """从IR文件加载metadata字段."""
    from agent_runtime.serve.apis.orchestration import async_ir_load
    ir_json = await async_ir_load(ir_path)
    return ir_json.get("metadata") or {}


async def check_query_length(
    query: Optional[str],
    language: str = "zh-cn",
    is_agent: bool = False,
) -> Optional[JSONResponse]:
    """校验1: Query长度不超过上限."""
    if query and isinstance(query, str) and len(query) > _MAX_QUERY_LENGTH:
        workflow_logger.error(
            "%s query param exceed max length %s",
            "agent" if is_agent else "workflow",
            _MAX_QUERY_LENGTH,
        )
        return _build_error_response(400, _CODE_METHOD_ARGUMENT, language)
    return None


async def check_chat_workflow_query(
    query: Optional[str],
    ir_path: str,
    language: str = "zh-cn",
    is_node_execute: bool = False,
) -> Optional[JSONResponse]:
    """校验2: Chat类型工作流query必填（非单节点执行时）."""
    if is_node_execute:
        return None
    metadata = await _load_ir_metadata(ir_path)
    app_type = metadata.get("type", "")
    if app_type == "chat" and _is_empty_query(query):
        workflow_logger.error("query param is empty: %s", query)
        return _build_error_response(400, _CODE_METHOD_ARGUMENT, language)
    return None


async def check_project_permission(
    request_project_id: str,
    ir_path: str,
    language: str = "zh-cn",
    is_agent: bool = False,
) -> Optional[JSONResponse]:
    """校验3: 请求的project_id与IR metadata中的projectId匹配."""
    metadata = await _load_ir_metadata(ir_path)
    ir_project_id = metadata.get("projectId", "")
    if request_project_id != ir_project_id:
        code_key = _CODE_AGENT_PERMISSION if is_agent else _CODE_WORKFLOW_PERMISSION
        workflow_logger.error(
            "Project permission denied: request=%s, ir=%s",
            request_project_id,
            ir_project_id,
        )
        return _build_error_response(403, code_key, language)
    return None


async def check_version_freshness(
    body_version: Optional[Union[str, int]],
    ir_path: str,
    language: str = "zh-cn",
) -> Optional[JSONResponse]:
    """校验4: draft模式下body.version与IR metadata.updatedAt不一致则拒绝.

    仅在draft模式（无publishedVersion）且有body.version时触发。
    已发布版本的IR不可变，无需校验。
    """
    if body_version is None:
        return None
    metadata = await _load_ir_metadata(ir_path)
    ir_updated_at = metadata.get("updatedAt")
    if ir_updated_at is None:
        return None
    # updatedAt在workflow IR中为number，agent IR中为string，统一转str比较
    str_body_version = str(body_version)
    str_ir_updated = str(ir_updated_at)
    if str_body_version != str_ir_updated:
        workflow_logger.error(
            "Not latest version. execute version:%s updateAt:%s",
            str_body_version,
            str_ir_updated,
        )
        return _build_error_response(403, _CODE_NOT_LATEST, language)
    return None


async def check_before_workflow_run(ctx: RunCheckContext) -> Optional[JSONResponse]:
    """工作流运行前综合校验 — 合并IR加载为一次."""
    language = _get_language(ctx.request)

    # 校验1: query长度
    err = await check_query_length(ctx.query, language)
    if err:
        return err

    # 校验2/3/4需要读取IR metadata，合并为一次加载
    metadata = await _load_ir_metadata(ctx.ir_path)

    # 校验2: chat工作流query必填
    if not ctx.is_node_execute:
        app_type = metadata.get("type", "")
        if app_type == "chat" and _is_empty_query(ctx.query):
            workflow_logger.error("query param is empty: %s", ctx.query)
            return _build_error_response(400, _CODE_METHOD_ARGUMENT, language)

    # 校验3: 项目权限
    ir_project_id = metadata.get("projectId", "")
    if ctx.project_id != ir_project_id:
        workflow_logger.error(
            "Project permission denied: request=%s, ir=%s",
            ctx.project_id,
            ir_project_id,
        )
        return _build_error_response(403, _CODE_WORKFLOW_PERMISSION, language)

    # 校验4: 版本新鲜度（仅draft模式）
    if not ctx.has_published_version and ctx.body_version is not None:
        ir_updated_at = metadata.get("updatedAt")
        if ir_updated_at is not None:
            str_body_version = str(ctx.body_version)
            str_ir_updated = str(ir_updated_at)
            if str_body_version != str_ir_updated:
                workflow_logger.error(
                    "Not latest version. execute version:%s updateAt:%s",
                    str_body_version,
                    str_ir_updated,
                )
                return _build_error_response(403, _CODE_NOT_LATEST, language)

    return None


async def check_before_agent_run(ctx: RunCheckContext) -> Optional[JSONResponse]:
    """智能体运行前综合校验 — 合并IR加载为一次."""
    language = _get_language(ctx.request)

    # 校验1: query长度
    err = await check_query_length(ctx.query, language, is_agent=True)
    if err:
        return err

    # 校验2: agent query必填
    if _is_empty_query(ctx.query):
        workflow_logger.error("Agent query param is empty: %s", ctx.query)
        return _build_error_response(400, _CODE_METHOD_ARGUMENT, language)

    # 校验3/4需要读取IR metadata，合并为一次加载
    metadata = await _load_ir_metadata(ctx.ir_path)

    # 校验3: 项目权限
    ir_project_id = metadata.get("projectId", "")
    if ctx.project_id != ir_project_id:
        workflow_logger.error(
            "Project permission denied: request=%s, ir=%s",
            ctx.project_id,
            ir_project_id,
        )
        return _build_error_response(403, _CODE_AGENT_PERMISSION, language)

    # 校验4: 版本新鲜度（仅draft模式）
    if not ctx.has_published_version and ctx.body_version is not None:
        ir_updated_at = metadata.get("updatedAt")
        if ir_updated_at is not None:
            str_body_version = str(ctx.body_version)
            str_ir_updated = str(ir_updated_at)
            if str_body_version != str_ir_updated:
                workflow_logger.error(
                    "Not latest version. execute version:%s updateAt:%s",
                    str_body_version,
                    str_ir_updated,
                )
                return _build_error_response(403, _CODE_NOT_LATEST, language)

    return None
