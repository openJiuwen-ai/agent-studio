# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder 模型服务 facade — 移植自 Java ``RuntimeModelServiceController``。

将原 Java 网关的三个模型调用接口下沉到 agent_builder 进程内直连真实模型，机制层
（OBS 解析 / 鉴权 / 策略 / 审计）复用共享包 ``packages.model_service``：

- POST /v1/agent-builder/chat/completions  — 对应 Java ``chatCompletions``（支持流式/非流式 + ROUTER failover）
- POST /v1/agent-builder/embeddings        — 对应 Java ``textEmbeddings``
- POST /v1/agent-builder/rerank             — 对应 Java ``rerank``
- POST /v1/{project_id}/model-service/status/check — 对应 Java ``ModelServiceController.modelServiceStatusCheck``
  （连通性探针：请求体直传待测模型配置，不走 OBS 策略解析）

实现要点（与 Java ``RuntimeModelServiceManager`` / 各 ``Maas*RequestAdaptor`` 对齐）：
- model 字段是 modelServiceId（UUID），可能带 ``prefix|`` 签名前缀，取 ``split('|')[0]`` 作为 OBS key
  （对应 ref-commit ``OBSModelConfigProvider`` 的 ``model_service_id`` 归一）。
- 真实 model_name / api_url / auth 由 ``resolver.resolve_strategy`` 在 OBS 解析后得到，
  上游请求体的 ``model`` 用解析出的真实 ``model_name`` 覆写。
- 上游 URL 取 ``detail.model.api_url`` verbatim（对应 Java ``model.getApiUrl()``，adapter 不追加 path）。
- 鉴权：``API_KEY`` → ``Authorization: Bearer <api_key>``；``CUSTOM_APIKEY`` → ``auth_info`` 各项作自定义头。
- chat 上游请求体去掉 ``refresh``；``thinking`` 字段按客户端传入透传（不再置 ``null``，
  否则会丢弃前端的关闭思考开关、导致关闭思考模式不生效）。
- rerank 响应按 ``index`` 升序排序后截断到 ``top_n``（对应 Java ``MaasRerankRequestAdaptor.resBodyConvert``）。
"""

from typing import Dict, List, Optional, Union

import httpx
import logging
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# 导入 model_service 即触发 StudioModelClient 注册（client_provider="studio"），
# 并复用 resolver / policy / dispatch 机制层。
import model_service  # noqa: F401
from model_service import dispatch, policy, resolver

from agent_builder.common.exception.model_codes import (
    INVOKE_MODEL_SERVICE_FAIL,
    MODEL_SERVICE_NOT_PUBLISH,
    get_model_error_spec,
)

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


class ModelServiceCheckReq(BaseModel):
    """对应 Java ``ModelServiceCheckReq``（``@JsonNaming`` snake_case）。

    与 chat/embed/rerank facade 的关键区别：请求体直接携带待测模型配置
    （apiUrl/authType/authInfo/modelName/interfaceProtocol），**不走 OBS 策略解析**，
    对应 Java ``createModelServiceDetail`` 由 req 直接构造 ``ModelServiceDetail``。
    """

    model_type: str
    api_url: str
    auth_type: str
    auth_info: Dict[str, str]
    model_name: str
    interface_protocol: str


class ModelServiceCheckRsp(BaseModel):
    """对应 Java ``ModelServiceCheckRsp``（snake_case）。"""

    success: bool
    reason: Optional[str] = None
    detail: Optional[str] = None
    status_code: int = 0


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


# 上游模型调用失败的对齐契约（移植自 Java ``GlobalExceptionHandler`` + i18n
# ``studio-messages_zh_CN.properties``）由 ``model_codes.MODEL_ERROR_SPECS`` 登记表驱动：
# error_code/error_msg/error_reason/error_suggestion + details[]，透传上游真实 status。
# 新增/调整 MD_* 错误码响应契约一律改 ``model_codes.py``，勿在此手搓封包。


def _error_response(exc: Exception) -> JSONResponse:
    code = getattr(exc, "code", "INTERNAL_ERROR")
    msg = getattr(exc, "msg", str(exc))
    logger.warning("model-service facade error: code=%s msg=%s", code, msg)
    spec = get_model_error_spec(code)
    if spec.full_code:
        # 旧 Java ErrorRsp 契约：error_code/error_msg/error_reason/error_suggestion + details?。
        upstream_status = getattr(exc, "upstream_status", None)
        upstream_body = getattr(exc, "upstream_body", None)
        content = {
            "error_code": spec.full_code,
            "error_msg": spec.error_msg,
            "error_reason": spec.error_reason,
            "error_suggestion": spec.error_suggestion,
        }
        if spec.with_details and upstream_body:
            content["details"] = [{"error_msg": upstream_body}]
        status = upstream_status if (spec.use_upstream_status and upstream_status) else spec.http_status
        return JSONResponse(status_code=status, content=content)
    return JSONResponse(
        status_code=spec.http_status,
        content={"error": {"code": code, "message": msg}},
    )


def _upstream_transport_error(url: str, exc: httpx.HTTPError) -> resolver.ModelServiceError:
    """把 httpx 传输异常（DNS/连接/超时等，无上游响应）转成 ``ModelServiceError``。

    MODEL 策略下 ``policy.invoke_with_strategy`` 不 catch，裸 httpx 异常会逃逸到 FastAPI
    默认 500（``{error:{code:"internal_error",message:"Internal server error"}}``），页面
    看不到原因。此处统一转成 ``MD_INVOKE_MODEL_SERVICE_FAIL``，经 ``_error_response`` 走
    ``openjiuwen.02501049`` 契约，把异常文本放进 ``details[0].error_msg`` 让前端可见。
    无上游响应故 ``upstream_status`` 留空（退回 spec.http_status）。ROUTER 策略下
    ``policy`` 已用 ``except Exception`` 兜底重试，本转换不影响其 failover 行为。
    """
    detail = f"upstream {url} request failed: {exc}"
    return resolver.ModelServiceError(
        INVOKE_MODEL_SERVICE_FAIL,
        detail,
        upstream_body=detail,
    )


def _check_auth_headers(auth_type: str, auth_info: Optional[Dict[str, str]]) -> dict:
    """鉴权头（对应 Java ``AuthAdapterFactory`` 三种 adapter，使用请求体原始 auth_info）。

    与 OBS 路径的 ``_auth_headers`` 区别：status check 的 auth_info 由调用方直传，
    - ``API_KEY`` 取 ``"API Key"`` 键（Java ``ApiKeyAuthInfo`` 的 ``@JsonProperty("API Key")``），
      不走 OBS resolver 的 ``api_key`` 归一。
    - ``CUSTOM_APIKEY``：auth_info 各项作为自定义头，``cust-token``/``cust-userid`` 剥离
      ``cust-`` 前缀并小写（对应 Java ``CustomApiKeyAuthAdapter.customHeadersReplace``）。
    - ``NO_AUTH`` / 其它：不加任何鉴权头（对应 Java ``NoAuthAdapter``）。
    """
    headers = {"Content-Type": "application/json"}
    atype = (auth_type or "").upper()
    if atype == "API_KEY":
        api_key = (auth_info or {}).get("API Key", "")
        headers["Authorization"] = f"Bearer {api_key}"
    elif atype == "CUSTOM_APIKEY":
        for k, v in (auth_info or {}).items():
            lk = k.lower()
            real = lk[5:] if lk in ("cust-token", "cust-userid") else lk
            headers[real] = v
    return headers


def _build_check_invoke_body(model_type: str, model_name: str) -> Optional[dict]:
    """按 model_type 构造最小探针请求体（对应 Java ``createModelInvokeBase``）。

    返回 None 表示该 model_type 不支持 check（对应 Java ``default`` 分支 →
    "model type is not support to check."）。
    """
    mt = (model_type or "").upper()
    if mt in ("IMAGE-TO-TEXT", "LLM"):
        return {
            "model": model_name,
            "stream": False,
            "messages": [{"role": "user", "content": "你好"}],
        }
    if mt == "TEXT-EMBEDDING":
        return {"model": model_name, "input": "你好"}
    if mt == "RERANK":
        return {"model": model_name, "query": "a", "documents": ["a", "b"]}
    return None


def _build_chat_upstream_body(body: dict, model_name: str, is_stream: bool) -> dict:
    """构造 chat 上游请求体（对应 Java ``OpenApiRequestAdapter``）。

    去掉 ``refresh``；``model``/``stream`` 用本地解析值覆写。``thinking`` 字段按客户端
    传入透传（``{"type": "disabled" | "enabled"}``）——历史上置 ``null`` 会丢弃前端的
    关闭思考开关，导致「关闭思考模式」不生效（上游回退到默认，对 Qwen3 等即思考开启）。
    与 IR 运行时路径（``model_providers`` / ``model_bridge`` 经 ``extra_body`` 透传 ``thinking``）
    保持一致。
    """
    up_body = {**body, "model": model_name, "stream": is_stream}
    up_body.pop("refresh", None)
    return up_body


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
                MODEL_SERVICE_NOT_PUBLISH, f"model service not found: {msid}"
            )

        async def invoke_one(detail, is_stream):
            conn = dispatch.get_chat_connection(detail.model, detail.auth)
            url = detail.model.api_url
            client = dispatch.build_httpx_client(url, conn.verify_ssl)
            headers = _auth_headers(conn)
            up_body = _build_chat_upstream_body(body, conn.model_name, is_stream)
            if not is_stream:
                try:
                    resp = await client.post(
                        url, json=up_body, headers=headers, timeout=conn.timeout
                    )
                    if resp.status_code >= 300:
                        raise resolver.ModelServiceError(
                            INVOKE_MODEL_SERVICE_FAIL,
                            f"upstream {url} returned {resp.status_code}: {resp.text}",
                            upstream_status=resp.status_code,
                            upstream_body=resp.text,
                        )
                    return resp.json()
                except httpx.HTTPError as exc:
                    raise _upstream_transport_error(url, exc) from exc
                finally:
                    await client.aclose()
            # 流式：连接错误在 send 时抛出（可被 policy failover）；流中途错误不重试。
            req = client.build_request(
                "POST", url, json=up_body, headers=headers, timeout=conn.timeout
            )
            try:
                resp = await client.send(req, stream=True)
            except httpx.HTTPError as exc:
                await client.aclose()
                raise _upstream_transport_error(url, exc) from exc
            except Exception:
                await client.aclose()
                raise
            if resp.status_code >= 300:
                text = (await resp.aread()).decode("utf-8", "ignore")
                await resp.aclose()
                await client.aclose()
                raise resolver.ModelServiceError(
                    INVOKE_MODEL_SERVICE_FAIL,
                    f"upstream {url} returned {resp.status_code}: {text}",
                    upstream_status=resp.status_code,
                    upstream_body=text,
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
                MODEL_SERVICE_NOT_PUBLISH, f"model service not found: {msid}"
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
                    INVOKE_MODEL_SERVICE_FAIL,
                    f"upstream {url} returned {resp.status_code}: {resp.text}",
                    upstream_status=resp.status_code,
                    upstream_body=resp.text,
                )
            return JSONResponse(content=resp.json())
        except httpx.HTTPError as exc:
            raise _upstream_transport_error(url, exc) from exc
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
    url = ""  # dispatch.rerank 抛 httpx 时用于错误信息；httpx 仅可能发生在下方赋值之后
    try:
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf
        )
        if strategy is None:
            raise resolver.ModelServiceError(
                MODEL_SERVICE_NOT_PUBLISH, f"model service not found: {msid}"
            )
        detail = strategy.models[0]
        url = detail.model.api_url
        data = await dispatch.rerank(detail.model, detail.auth, body)
        return JSONResponse(content=data)
    except resolver.ModelServiceError as exc:
        return _error_response(exc)
    except httpx.HTTPError as exc:
        logger.warning("model-service rerank upstream transport error: %s", exc)
        return _error_response(_upstream_transport_error(url, exc))


# ----------------------------- status check -----------------------------


@model_service_router.post("/v1/{project_id}/model-service/status/check")
async def model_service_status_check(
    project_id: str,
    body: ModelServiceCheckReq,
):
    """模型服务连通性探针 — 对应 Java ``ModelServiceController.modelServiceStatusCheck``。

    与 chat/embed/rerank facade 的区别：不走 OBS 策略解析，请求体直接携带待测模型的
    apiUrl/authType/authInfo/modelName/interfaceProtocol，构造探针请求直连上游，按上游
    响应码判定 ``success``（对应 Java ``commonInvoke`` + 异常映射）：

    - 2xx → success=true, status_code=200（Java 成功分支硬编码 200）
    - 400 → success=true, status_code=400, reason=上游错误体（端点可达即视为通过）
    - 其它 4xx/5xx → success=false, status_code=上游码, reason=上游错误体
    - 协议/鉴权异常（``ModelServiceError``，对应 Java ``AgentStudioException``）→
      success=false, status_code=500, reason=msg
    - 网络/超时/URL 非法（对应 Java ``Exception`` 分支）→ success=false, status_code=500
    """
    probe = _build_check_invoke_body(body.model_type, body.model_name)
    if probe is None:
        logger.warning("Model type is not support to check. type=%s", body.model_type)
        return JSONResponse(content=ModelServiceCheckRsp(
            success=True, reason="model type is not support to check."
        ).model_dump())

    # 复用 dispatch 的连接参数（timeout/verify_ssl）与协议归一；auth 头按请求体原值构造
    # （对应 Java ``createModelServiceDetail`` + ``AuthAdapterFactory``）。
    model = resolver.ModelServiceBase(
        id="",
        model_name=body.model_name,
        api_url=body.api_url,
        provider_id="",
        interface_protocol=dispatch.normalize_protocol(body.interface_protocol),
        project_id=project_id,
        workspace_id="",
        auth_id="",
    )
    auth = resolver.ProviderAuth(auth_id="", auth_type=body.auth_type, auth_info=body.auth_info)

    try:
        conn = dispatch.get_chat_connection(model, auth)
        url = body.api_url  # 对应 Java ``model.getApiUrl()`` verbatim，不追加 path
        client = dispatch.build_httpx_client(url, conn.verify_ssl)
        headers = _check_auth_headers(body.auth_type, body.auth_info)
        try:
            resp = await client.post(url, json=probe, headers=headers, timeout=conn.timeout)
            status = resp.status_code
            if status < 300:
                return JSONResponse(content=ModelServiceCheckRsp(
                    success=True, status_code=200
                ).model_dump())
            return JSONResponse(content=ModelServiceCheckRsp(
                success=(status == 400), status_code=status, reason=resp.text
            ).model_dump())
        finally:
            await client.aclose()
    except resolver.ModelServiceError as exc:
        # PROTOCOL_NOT_SUPPORTED 等（对应 Java factory 不支持协议 → AgentStudioException）
        logger.warning("Model service check failed. code=%s msg=%s", exc.code, exc.msg)
        return JSONResponse(content=ModelServiceCheckRsp(
            success=False, status_code=500, reason=exc.msg or exc.code
        ).model_dump())
    except Exception:  # noqa: BLE001  网络/超时/URL 非法（对应 Java Exception 分支）
        logger.warning("Model api url is invalid. url=%s", body.api_url, exc_info=True)
        return JSONResponse(content=ModelServiceCheckRsp(
            success=False, status_code=500
        ).model_dump())
