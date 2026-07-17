# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder 模型服务 facade — 移植自 Java ``RuntimeModelServiceController``。

将原 Java 网关的三个模型调用接口下沉到 agent_builder 进程内直连真实模型，机制层
（OBS 解析 / 鉴权 / 策略 / 审计）复用共享包 ``packages.model_service``：

- POST /v1/agent-builder/chat/completions  — 对应 Java ``chatCompletions``（支持流式/非流式 + ROUTER failover）
- POST /v1/agent-builder/embeddings        — 对应 Java ``textEmbeddings``
- POST /v1/agent-builder/rerank             — 对应 Java ``rerank``

实现要点（与 Java ``RuntimeModelServiceManager`` / 各 ``Maas*RequestAdaptor`` 对齐）：
- model 字段是 modelServiceId（UUID），可能带 ``prefix|`` 签名前缀，取 ``split('|')[0]`` 作为 OBS key
  （对应 ref-commit ``OBSModelConfigProvider`` 的 ``model_service_id`` 归一）。
- 真实 model_name / api_url / auth 由 ``resolver.resolve_strategy`` 在 OBS 解析后得到，
  上游请求体的 ``model`` 用解析出的真实 ``model_name`` 覆写。
- 上游 URL 取 ``detail.model.api_url`` verbatim（对应 Java ``model.getApiUrl()``，adapter 不追加 path）。
- 鉴权：``API_KEY`` → ``Authorization: Bearer <api_key>``；``CUSTOM_APIKEY`` → ``auth_info`` 各项作自定义头。
- chat 上游请求体去掉 ``refresh``、置 ``thinking=null``（对应 Java ``OpenApiRequestAdapter``）。
- rerank 响应按 ``index`` 升序排序后截断到 ``top_n``（对应 Java ``MaasRerankRequestAdaptor.resBodyConvert``）。
"""

from typing import List, Optional, Union

import httpx
import logging
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# 导入 model_service 即触发 StudioModelClient 注册（client_provider="studio"），
# 并复用 resolver / policy / dispatch 机制层。
import model_service  # noqa: F401
from model_service import dispatch, policy, resolver

model_service_router = APIRouter(tags=["model-service"])

logger = logging.getLogger("agent_builder.model_service_api")


# ----------------------------- DTO -----------------------------


class EmbeddingRequest(BaseModel):
    """对应 Java ``EmbeddingRequest``。上游仅用 ``{model, input}``，``user``/``truncate`` 丢弃。"""

    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None
    truncate: Optional[str] = None


class RankDocumentsRequest(BaseModel):
    """对应 Java ``RankDocumentsRequest``。``top_n`` 不上传上游，仅用于响应截断。"""

    model: str
    query: str
    docs: List[str]
    top_n: Optional[int] = Field(default=None, ge=1, le=512)


# ----------------------------- 工具 -----------------------------


def _model_service_id(model_field: str) -> str:
    """取 ``split('|')[0]`` 作为 OBS modelServiceId（对应 OBSModelConfigProvider 归一）。"""
    return (model_field or "").split("|")[0]


def _resolve_request_ctx(request: Request, body_model: str, refresh_query: Optional[bool],
                         body_refresh: Optional[str]):
    """从请求头/查询参数/请求体提取 model_service 调用上下文。

    对应 Java 控制器对 ``workspace_id`` / ``X-Workspace-Id`` / ``X-Auth-Id`` /
    ``X-Owner-Project-Id`` / ``refresh`` 的归一逻辑。
    """
    headers = request.headers
    workspace_id = request.query_params.get("workspace_id") or headers.get(
        "X-Workspace-Id", ""
    ) or ""
    auth_id = headers.get("X-Auth-Id", "") or ""
    project_id = headers.get("X-Owner-Project-Id", "") or "0"
    rf = bool(refresh_query) or (str(body_refresh).lower() == "true")
    return _model_service_id(body_model), project_id, workspace_id, auth_id, rf


def _auth_headers(conn) -> dict:
    """鉴权头：API_KEY → Bearer；CUSTOM_APIKEY → auth_info 各项（对应 Java AuthAdapterFactory）。"""
    headers = {"Content-Type": "application/json"}
    if conn.custom_headers:
        headers.update(conn.custom_headers)
    else:
        headers["Authorization"] = f"Bearer {conn.api_key}"
    return headers


def _error_response(exc: Exception) -> JSONResponse:
    code = getattr(exc, "code", "INTERNAL_ERROR")
    msg = getattr(exc, "msg", str(exc))
    logger.warning("model-service facade error: code=%s msg=%s", code, msg)
    status = 404 if code == "MD_MODEL_SERVICE_NOT_PUBLISH" else 400
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": msg}})


# ----------------------------- chat -----------------------------


@model_service_router.post("/v1/agent-builder/chat/completions")
async def chat_completions(
    request: Request,
    body: dict = Body(...),
    workspace_id: Optional[str] = Query(default=None, pattern=r"^[a-zA-Z0-9_()-]+$", max_length=64),
    refresh: Optional[bool] = Query(default=None),
):
    """模型调测 — 对应 Java ``RuntimeModelServiceController.chatCompletions``。

    ``body`` 以 dict 透传（保留 OpenAI 全量字段）；``stream`` 取自 body.stream。
    """
    model_field = body.get("model", "")
    msid, project_id, workspace, auth_id, rf = _resolve_request_ctx(
        request, model_field, refresh, body.get("refresh")
    )
    workspace = workspace_id or workspace
    stream = bool(body.get("stream"))

    try:
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf
        )
        if strategy is None:
            raise resolver.ModelServiceError(
                "MD_MODEL_SERVICE_NOT_PUBLISH", f"model service not found: {msid}"
            )

        async def invoke_one(detail, is_stream):
            conn = dispatch.get_chat_connection(detail.model, detail.auth)
            url = detail.model.api_url
            client = dispatch.build_httpx_client(url, conn.verify_ssl)
            headers = _auth_headers(conn)
            up_body = {**body, "model": conn.model_name, "stream": is_stream}
            up_body.pop("refresh", None)
            up_body["thinking"] = None
            if not is_stream:
                try:
                    resp = await client.post(
                        url, json=up_body, headers=headers, timeout=conn.timeout
                    )
                    if resp.status_code >= 300:
                        raise resolver.ModelServiceError(
                            "MD_INVOKE_MODEL_SERVICE_FAIL",
                            f"upstream {url} returned {resp.status_code}: {resp.text}",
                        )
                    return resp.json()
                finally:
                    await client.aclose()
            # 流式：连接错误在 send 时抛出（可被 policy failover）；流中途错误不重试。
            req = client.build_request(
                "POST", url, json=up_body, headers=headers, timeout=conn.timeout
            )
            try:
                resp = await client.send(req, stream=True)
            except Exception:
                await client.aclose()
                raise
            if resp.status_code >= 300:
                text = (await resp.aread()).decode("utf-8", "ignore")
                await resp.aclose()
                await client.aclose()
                raise resolver.ModelServiceError(
                    "MD_INVOKE_MODEL_SERVICE_FAIL",
                    f"upstream {url} returned {resp.status_code}: {text}",
                )

            async def _relay():
                try:
                    async for chunk in resp.aiter_raw():
                        yield chunk
                finally:
                    await resp.aclose()
                    await client.aclose()

            return _relay()

        result = await policy.invoke_with_strategy(strategy, invoke_one, stream=stream)
    except resolver.ModelServiceError as exc:
        return _error_response(exc)

    if stream:
        return StreamingResponse(content=result, media_type="text/event-stream")
    return JSONResponse(content=result)


# ----------------------------- embeddings -----------------------------


@model_service_router.post("/v1/agent-builder/embeddings")
async def text_embeddings(
    request: Request,
    body: EmbeddingRequest,
    workspace_id: Optional[str] = Query(default=None, pattern=r"^[a-zA-Z0-9_()-]+$", max_length=64),
    refresh: Optional[bool] = Query(default=None),
):
    """文本向量化 — 对应 Java ``textEmbeddings``。上游 body 仅 ``{model, input}``。"""
    msid, project_id, workspace, auth_id, rf = _resolve_request_ctx(
        request, body.model, refresh, None
    )
    workspace = workspace_id or workspace
    try:
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf
        )
        if strategy is None:
            raise resolver.ModelServiceError(
                "MD_MODEL_SERVICE_NOT_PUBLISH", f"model service not found: {msid}"
            )
        # embed 仅支持 MODEL 策略（对应 Java commonInvoke 断言 type==MODEL）
        detail = strategy.models[0]
        conn = dispatch.get_chat_connection(detail.model, detail.auth)
        url = detail.model.api_url
        client = dispatch.build_httpx_client(url, conn.verify_ssl)
        headers = _auth_headers(conn)
        up_body = {"model": conn.model_name, "input": body.input}
        try:
            resp = await client.post(url, json=up_body, headers=headers, timeout=conn.timeout)
            if resp.status_code >= 300:
                raise resolver.ModelServiceError(
                    "MD_INVOKE_MODEL_SERVICE_FAIL",
                    f"upstream {url} returned {resp.status_code}: {resp.text}",
                )
            return JSONResponse(content=resp.json())
        finally:
            await client.aclose()
    except resolver.ModelServiceError as exc:
        return _error_response(exc)


# ----------------------------- rerank -----------------------------


@model_service_router.post("/v1/agent-builder/rerank")
async def rerank(
    request: Request,
    body: RankDocumentsRequest,
    workspace_id: Optional[str] = Query(default=None, pattern=r"^[a-zA-Z0-9_()-]+$", max_length=64),
    refresh: Optional[bool] = Query(default=None),
):
    """重排序 — 对应 Java ``rerank``。上游 body ``{model, query, documents}``，响应按 index 升序 + top_n 截断。"""
    msid, project_id, workspace, auth_id, rf = _resolve_request_ctx(
        request, body.model, refresh, None
    )
    workspace = workspace_id or workspace
    try:
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf
        )
        if strategy is None:
            raise resolver.ModelServiceError(
                "MD_MODEL_SERVICE_NOT_PUBLISH", f"model service not found: {msid}"
            )
        detail = strategy.models[0]
        data = await dispatch.rerank(detail.model, detail.auth, body)
        return JSONResponse(content=data)
    except resolver.ModelServiceError as exc:
        return _error_response(exc)
