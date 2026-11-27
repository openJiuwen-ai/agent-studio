# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
A2A JSON-RPC service face — exposes low-code published agents/workflows
to high-code callers via the A2A (Agent-to-Agent) protocol.

Endpoints:
  POST /a2a                           — JSON-RPC entry point (SendMessage / SendStreamingMessage)
  GET  /.well-known/agent-card.json   — Agent Card (reads from Redis)
  GET  /a2a/agents/{agent_id}/card    — Per-agent card

This module performs **protocol translation only** — it does NOT modify
the IR execution chain or node semantics.
"""

import json
import uuid

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openjiuwen.core.common.logging import workflow_logger
from redis_spi import accessor

from agent_runtime.serve.a2a.error_codes import make_rpc_error, A2aErrorCode
from agent_runtime.serve.a2a.context_mapper import resolve_conversation_id
from agent_runtime.serve.a2a.event_mapper import A2aEventMapper
from agent_runtime.serve.apis.orchestration import execute_ir_events
from agent_runtime.serve.apis.app_run import build_agent_ir_path, build_workflow_ir_path
from agent_runtime.serve.apis.publish_version_cache import PublishVersionCache
from agent_runtime.serve.execution_events import ExecutionEventStream
from agent_runtime.schemas.orchestration_mgr import (
    ExecutionRequest,
    ExecutionParams,
    ResponseMode,
)
from agent_runtime.context.request_context import _request_ctx

a2a_app = APIRouter(tags=["a2a"])

A2A_ENDPOINT = "/a2a"
WELL_KNOWN_PATH = "/.well-known/agent-card.json"

_WORKFLOW_APP_TYPES = frozenset({"WORKFLOW", "workflow"})
_AGENT_CARD_KEY_PREFIX = "a2a:agent-card:"


# ── JSON-RPC entry point ──────────────────────────────────────────────

@a2a_app.post(A2A_ENDPOINT)
async def handle_a2a(
    request: Request,
    agent_id: str = Query(default=None, description="目标智能体/工作流ID"),
):
    """A2A JSON-RPC 2.0 entry point.

    Supports methods:
      - SendMessage          → sync JSON-RPC response
      - SendStreamingMessage → SSE stream of JSON-RPC frames
    """
    # 1. Parse JSON-RPC body
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            make_rpc_error(A2aErrorCode.INVALID_PARAMS, "Invalid JSON body", None)
        )

    request_id = body.get("id")
    method = body.get("method", "")

    # 2. Validate method
    if method not in ("SendMessage", "SendStreamingMessage"):
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.METHOD_NOT_FOUND,
                f"Method not supported: {method}",
                request_id,
            )
        )

    # 3. Extract params and message
    params = body.get("params", {})
    message = params.get("message", {})
    if not message:
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.INVALID_PARAMS,
                "Missing 'message' in params",
                request_id,
            )
        )

    # 4. Resolve agent_id (query param → params.agentId → params.metadata.agentId → error)
    metadata = params.get("metadata", {}) or {}
    resolved_agent_id = agent_id or params.get("agentId") or metadata.get("agentId") or ""
    if not resolved_agent_id:
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.INVALID_PARAMS,
                "Missing agent_id (provide ?agent_id= query param)",
                request_id,
            )
        )

    # 5. Extract user message text from params.message.parts[].text
    parts = message.get("parts", [])
    text_parts = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            text_parts.append(part["text"])
    user_text = " ".join(text_parts)

    # 6. Extract contextId → resolve conversation_id
    context_id = message.get("contextId", "")
    try:
        if context_id:
            conv_id = await resolve_conversation_id(context_id, resolved_agent_id)
        else:
            conv_id = str(uuid.uuid4())
    except Exception as e:
        workflow_logger.error(f"A2A context resolution failed: {e}", exc_info=True)
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.INTERNAL_ERROR,
                "Failed to resolve conversation",
                request_id,
            )
        )

    # 7. Resolve metadata + IR path
    try:
        metadata = await PublishVersionCache.get_publish_metadata(resolved_agent_id)
    except Exception as e:
        workflow_logger.error(f"A2A metadata resolution failed: {e}", exc_info=True)
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.INTERNAL_ERROR,
                "Failed to resolve agent metadata",
                request_id,
            )
        )

    if metadata is None:
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.TASK_NOT_FOUND,
                f"Agent not found or not published: {resolved_agent_id}",
                request_id,
            )
        )

    version = metadata.version_id
    app_type = (metadata.app_type or "").strip()
    is_workflow = app_type in _WORKFLOW_APP_TYPES

    if is_workflow:
        ir_path = build_workflow_ir_path(resolved_agent_id, version)
        entry_type = "workflow"
    else:
        ir_path = build_agent_ir_path(resolved_agent_id, version)
        entry_type = "agent"

    workflow_logger.info(
        f"A2A request: agent_id={resolved_agent_id}, method={method}, "
        f"app_type={app_type}, ir_path={ir_path}, conv_id={conv_id}"
    )

    # 8. Set request.state for execution chain (same as app_run.py)
    try:
        req_ctx = _request_ctx.get()
        user_id = req_ctx.user_id
    except LookupError:
        user_id = "anonymous"

    request.state.instance_id = resolved_agent_id
    request.state.entry_type = entry_type
    request.state.project_id = metadata.project_id or ""
    request.state.user_id = user_id
    request.state.version_id = version or ""
    request.state.enable_history = True

    # 9. Construct ExecutionRequest
    if is_workflow:
        # WORKFLOW: map parts to global_variables (structured inputs)
        exec_params = ExecutionParams(global_variables={"query": user_text})
    else:
        # AGENT/MULTI_AGENTS: message text → query
        exec_params = ExecutionParams()

    request_model = ExecutionRequest(
        conversationId=conv_id,
        userId=user_id,
        irPath=ir_path,
        query=user_text,
        responseMode=ResponseMode.STREAMING,
        params=exec_params,
    )

    # 10. Execute via private structured-event entry
    try:
        response = await execute_ir_events(request_model, request)
    except Exception as e:
        workflow_logger.error(f"A2A execution failed: {e}", exc_info=True)
        return JSONResponse(
            make_rpc_error(
                A2aErrorCode.INTERNAL_ERROR,
                f"Execution failed: {e}",
                request_id,
            )
        )

    # 11. Map events to A2A frames
    task_id = str(uuid.uuid4())
    mapper = A2aEventMapper(task_id)

    if method == "SendMessage":
        return await _handle_sync_response(response, mapper, request_id)
    else:
        return StreamingResponse(
            _handle_streaming_response(response, mapper, request_id),
            media_type="text/event-stream",
        )


# ── Sync / streaming event consumers ──────────────────────────────────

async def _handle_sync_response(
    response,
    mapper: A2aEventMapper,
    request_id,
) -> JSONResponse:
    """Consume ExecutionEventStream and return final JSON-RPC response."""
    final_frame = None
    last_artifact_text = ""

    try:
        if isinstance(response, ExecutionEventStream):
            async for event_data in response.body_iterator:
                if not isinstance(event_data, dict):
                    continue
                frame = mapper.map_event(event_data, request_id)
                if frame:
                    final_frame = frame
                    result = frame.get("result", {})
                    artifact = result.get("artifact", {})
                    for p in artifact.get("parts", []):
                        if isinstance(p, dict) and p.get("text"):
                            last_artifact_text = p["text"]
        elif isinstance(response, JSONResponse):
            # Error response from _execute_ir (IR load failure, pre-fetch failure)
            try:
                content = (
                    json.loads(response.body.decode("utf-8"))
                    if isinstance(response.body, bytes)
                    else response.body
                )
            except Exception:
                content = {}
            error_msg = content.get("detail", content.get("message", str(content)))
            return JSONResponse(
                make_rpc_error(
                    A2aErrorCode.INTERNAL_ERROR,
                    f"Execution error: {error_msg}",
                    request_id,
                )
            )
        elif isinstance(response, StreamingResponse):
            # Moderation block or other streaming response — consume bytes
            async for chunk in response.body_iterator:
                text = (
                    chunk.decode("utf-8")
                    if isinstance(chunk, (bytes, bytearray))
                    else str(chunk)
                )
                if text.startswith("data: "):
                    try:
                        event_data = json.loads(text[6:].strip())
                        frame = mapper.map_event(event_data, request_id)
                        if frame:
                            final_frame = frame
                            result = frame.get("result", {})
                            artifact = result.get("artifact", {})
                            for p in artifact.get("parts", []):
                                if isinstance(p, dict) and p.get("text"):
                                    last_artifact_text = p["text"]
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        workflow_logger.error(f"A2A sync event consumption failed: {e}", exc_info=True)
        return JSONResponse(
            make_rpc_error(A2aErrorCode.INTERNAL_ERROR, f"Event consumption failed: {e}", request_id)
        )

    # If no terminal frame was produced, synthesize a COMPLETED frame
    if final_frame is None:
        final_frame = mapper.make_completed_frame(last_artifact_text, request_id)
    elif "method" in final_frame:
        # Last frame was an intermediate notification — upgrade to completed
        final_frame = mapper.make_completed_frame(last_artifact_text, request_id)

    return JSONResponse(content=final_frame)


async def _handle_streaming_response(
    response,
    mapper: A2aEventMapper,
    request_id,
):
    """Consume ExecutionEventStream and yield SSE frames."""
    try:
        if isinstance(response, ExecutionEventStream):
            async for event_data in response.body_iterator:
                if not isinstance(event_data, dict):
                    continue
                frame = mapper.map_event(event_data, request_id)
                if frame:
                    yield f"event:jsonrpc\ndata:{json.dumps(frame, ensure_ascii=False)}\n\n"
        elif isinstance(response, JSONResponse):
            # Error — yield as failed frame
            try:
                content = (
                    json.loads(response.body.decode("utf-8"))
                    if isinstance(response.body, bytes)
                    else response.body
                )
            except Exception:
                content = {}
            error_msg = content.get("detail", content.get("message", str(content)))
            frame = mapper.make_failed_frame(f"Execution error: {error_msg}", request_id)
            yield f"event:jsonrpc\ndata:{json.dumps(frame, ensure_ascii=False)}\n\n"
        elif isinstance(response, StreamingResponse):
            # Moderation block — consume bytes and map
            async for chunk in response.body_iterator:
                text = (
                    chunk.decode("utf-8")
                    if isinstance(chunk, (bytes, bytearray))
                    else str(chunk)
                )
                if text.startswith("data: "):
                    try:
                        event_data = json.loads(text[6:].strip())
                        frame = mapper.map_event(event_data, request_id)
                        if frame:
                            yield f"event:jsonrpc\ndata:{json.dumps(frame, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError:
                        pass

        # If no terminal frame was produced, synthesize one
        if mapper._status not in ("COMPLETED", "FAILED"):
            frame = mapper.make_completed_frame("", request_id)
            yield f"event:jsonrpc\ndata:{json.dumps(frame, ensure_ascii=False)}\n\n"
    except Exception as e:
        workflow_logger.error(f"A2A streaming error: {e}", exc_info=True)
        if mapper._status not in ("COMPLETED", "FAILED"):
            frame = mapper.make_failed_frame(str(e), request_id)
            yield f"event:jsonrpc\ndata:{json.dumps(frame, ensure_ascii=False)}\n\n"


# ── Agent Card endpoints ──────────────────────────────────────────────

@a2a_app.get(WELL_KNOWN_PATH)
async def get_agent_card(
    request: Request,
    agent_id: str = Query(default=None, description="智能体ID"),
):
    """Agent Card endpoint — reads card JSON from Redis."""
    if not agent_id:
        return JSONResponse(
            status_code=400,
            content={"error": "agent_id query parameter is required"},
        )
    card = await _read_agent_card(agent_id)
    if card is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Agent card not found for agent_id={agent_id}"},
        )
    return JSONResponse(content=card)


@a2a_app.get("/a2a/agents/{agent_id}/card")
async def get_agent_card_by_id(agent_id: str):
    """Per-agent card endpoint — reads card JSON from Redis."""
    card = await _read_agent_card(agent_id)
    if card is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Agent card not found for agent_id={agent_id}"},
        )
    return JSONResponse(content=card)


async def _read_agent_card(agent_id: str) -> dict | None:
    """Read agent card JSON from Redis key 'a2a:agent-card:{agentId}'."""
    try:
        if not accessor.is_initialized():
            workflow_logger.warning("Redis not initialized, cannot read agent card")
            return None
        redis = accessor.get_redis()
        key = f"{_AGENT_CARD_KEY_PREFIX}{agent_id}"
        raw = await redis.get(key)
        if not raw:
            return None
        data = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(data)
    except Exception as e:
        workflow_logger.error(f"Failed to read agent card from Redis: {e}", exc_info=True)
        return None
