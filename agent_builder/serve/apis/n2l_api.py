# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder FastAPI router — n2l chat + health (moved out of agent_runtime)."""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat

builder_router = APIRouter(tags=["builder"])


@builder_router.get("/v1/health", response_class=PlainTextResponse)
async def health():
    """Restful API for server health."""
    return "the health is good"


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
    agent_runtime/serve/apis/orchestration.py)."""
    payload = _n2l_json_wapper(
        project_id,
        agent_type,
        cid,
        body.model_dump(exclude_unset=True),
        request,
    )
    return await _chat(payload)
