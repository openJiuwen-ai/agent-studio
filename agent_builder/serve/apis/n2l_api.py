# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder FastAPI router — n2l chat + health (moved out of agent_runtime)."""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse

from agent_builder.adapter.config_bridge import settings
from agent_builder.common.error_contract import factory as error_factory
from agent_builder.common.error_contract.descriptor import ErrorDetail
from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat

builder_router = APIRouter(tags=["builder"])

# COM-05: conversation_id（路径 {cid}）合法性——与 inbound header ID 同字符集，长度上限 128
_CID_ALLOWED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
)
_CID_MAX_LEN = 128


def _valid_cid(value: str) -> bool:
    return bool(value) and len(value) <= _CID_MAX_LEN and frozenset(value) <= _CID_ALLOWED_CHARS


def _safe_reject(message: str) -> JSONResponse:
    """{cid} 校验失败的安全 400 canonical 响应（不回显原值，COM-03 五字段）。"""
    from dataclasses import replace

    from agent_builder.adapter.request_context_bridge import get_request_id

    rid = get_request_id() or None
    descriptor = error_factory.from_http_status(400, rid)
    descriptor = replace(descriptor, safe_details=[ErrorDetail("openjiuwen.13100001", message)])
    return error_factory.build_json_response(descriptor, "zh-cn")


@builder_router.get("/v1/health", response_class=PlainTextResponse)
async def health():
    """Restful API for server health."""
    return (
        settings.health_check.custom_rsp
        if settings.health_check.custom_rsp
        else "the health is good"
    )


@builder_router.post(
    "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"
)
async def chat_n2l(
    project_id: str,
    agent_type: str,
    cid: str,
    body: N2LRequestBody,
    request: Request,
) -> StreamingResponse:
    """NL2 chat — natural-language to agent generation (moved from
    agent_runtime/serve/apis/orchestration.py).

    COM-05: 路径 ``{cid}`` 是权威 conversation_id；兼容 body.conversationId
    缺失/相等通过，存在但不同则 400（不回显原值）。
    """
    # 1. {cid} 合法性校验
    if not _valid_cid(cid):
        return _safe_reject("Conversation id in path is missing or invalid")
    # 2. 兼容 body conversationId：缺失或等于 {cid} 通过；不同则安全拒绝
    compat_cid = getattr(body, "conversationId", None)
    if compat_cid is not None and str(compat_cid) != cid:
        return _safe_reject("Conversation id in request body conflicts with path")
    payload = _n2l_json_wapper(
        project_id,
        agent_type,
        cid,
        body.model_dump(exclude_unset=True),
        request,
    )
    return await _chat(payload)
