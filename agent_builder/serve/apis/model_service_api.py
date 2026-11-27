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

import json
import logging
from typing import Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# 导入 model_service 即触发 StudioModelClient 注册（client_provider="studio"），
# 并复用 resolver / policy / dispatch 机制层。
import model_service  # noqa: F401
from model_service import dispatch, env_resolver, policy, resolver
from model_service.ports import get_request_customer_headers
from common_utils.customer_header import resolve, get_capture_keys, get_config
from agent_builder.common.exception.model_codes import (
    INVOKE_MODEL_SERVICE_FAIL,
    MODEL_SERVICE_NOT_PUBLISH,
    get_model_error_spec,
)

model_service_router = APIRouter(tags=["model-service"])

logger = logging.getLogger("agent_builder.model_service_api")


def _merge_env_var_overrides(base_env_vars: Optional[dict], api_url_env_vars: Optional[str]) -> dict:
    """合并调测时的占位符真实值（query 参数 `api_url_env_vars`=JSON map）进 env_vars。

    base_env_vars 来自请求上下文（X-Environment-Id 加载），api_url_env_vars 是用户在
    调测页面为每个 {VAR} 占位符填入的临时值。后者覆盖前者同名键；仅调测用、不落库。
    key 须匹配 ``[A-Za-z0-9_-]+``，否则 warn 丢弃；不 log value（可能敏感）。
    """
    env_vars = dict(base_env_vars or {})
    if not api_url_env_vars:
        return env_vars
    try:
        override = json.loads(api_url_env_vars)
    except (ValueError, TypeError) as e:
        logger.warning("invalid api_url_env_vars query (not JSON): %s", e)
        return env_vars
    if not isinstance(override, dict):
        logger.warning("invalid api_url_env_vars query (not a JSON object)")
        return env_vars
    import re
    pup = dict(env_vars.get("plugin_url_params") or {})
    for k, v in override.items():
        if re.fullmatch(r"[A-Za-z0-9_-]+", str(k)):
            pup[str(k)] = v
        else:
            logger.warning("invalid api_url_env_vars key discarded: %s", k)
    env_vars["plugin_url_params"] = pup
    return env_vars


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
    """鉴权头：API_KEY → Bearer；CUSTOM_APIKEY → auth_info 各项（对应 Java AuthAdapterFactory）。

    CUSTOM_APIKEY 模式下 auth_info 含 capture_keys 时，通过 resolve 剥前缀（配置驱动）。
    """
    headers = {"Content-Type": "application/json"}
    if conn.custom_headers:
        cfg = get_config()
        cap_lower = [k.lower() for k in get_capture_keys()] if cfg.enabled else []
        to_rename = {}
        to_pass = {}
        for k, v in conn.custom_headers.items():
            if k.lower() in cap_lower:
                to_rename[k] = v
            else:
                to_pass[k] = v
        headers.update(to_pass)
        if to_rename:
            renamed = resolve(to_rename)
            if renamed:
                headers.update(renamed)
            else:
                headers.update(to_rename)
    else:
        headers["Authorization"] = f"Bearer {conn.api_key}"
    return headers


def _project_customer_headers(target, conn=None) -> dict:
    """返回 customer rename 后的 header（不含静态 Bearer）。

    优先用上游 captured；无 captured 时（页面试运行）用 conn 静态值做 rename。
    """
    captured = get_request_customer_headers()
    if captured:
        projected = resolve(captured)
        if projected:
            logger.info(
                f"[customer-header] Builder customer header rename: target={target}, "
                f"captured_keys={list(captured.keys())}, projected_keys={list(projected.keys())}"
            )
            return projected
    # 页面试运行 fallback：用 conn 静态值做 rename
    if conn and getattr(conn, "custom_headers", None):
        cfg = get_config()
        cap_lower = [k.lower() for k in get_capture_keys()] if cfg.enabled else []
        to_rename = {k: v for k, v in conn.custom_headers.items() if k.lower() in cap_lower}
        if to_rename:
            projected = resolve(to_rename)
            if projected:
                logger.info(
                    f"[customer-header] Builder static rename: target={target}, "
                    f"static_keys={list(to_rename.keys())}, projected_keys={list(projected.keys())}"
                )
                return projected
    return {}


def _merge_customer(headers: dict, projected: dict) -> dict:
    """将 customer rename 结果合并进 headers，上游 captured 覆盖静态认证"""
    headers.update(projected)
    return headers


def _build_model_headers(conn, auth, target) -> dict:
    """构建模型上游 header = 静态认证（已 rename） + 上游 captured rename（覆盖）"""
    headers = _auth_headers(conn)
    return _merge_customer(headers, _project_customer_headers(target, conn))


def _build_chat_headers(conn, auth) -> dict:
    """构建 chat 调用 header"""
    return _build_model_headers(conn, auth, "BUILDER_LLM_CHAT")


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
        if spec.with_details:
            if upstream_body:
                content["details"] = [{"error_msg": upstream_body}]
            elif msg:
                # 上游无响应体（如 API 地址/endpoint 配错返回 404 空 body）时，
                # 回退透出 msg（含上游 URL + 状态码），让调测页能看到是哪个地址、什么状态码，
                # 避免前端只剩通用文案、无法定位是 API 地址配置问题。
                content["details"] = [{"error_msg": msg}]
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


_MAX_SSE_LINE_BUFFER = 1 << 20  # 1 MiB：单行 SSE 缓冲上限，超限降级为字节直通，防内存无界增长


def _fill_reasoning_content(msg: dict) -> bool:
    """缺 ``reasoning_content``（缺失/``null``/空串均视为未提供）且 ``reasoning`` 非空时补齐。

    原地变更 ``msg``，返回是否发生过补齐；``reasoning_content`` 已有真值时以其为准不覆盖，
    ``reasoning`` 原样保留不删除。
    """
    reasoning = msg.get("reasoning")
    if reasoning and not msg.get("reasoning_content"):
        msg["reasoning_content"] = reasoning
        return True
    return False


def _normalize_reasoning_fields(obj) -> bool:
    """把 vLLM/DeepSeek 类上游的思考内容从 ``reasoning`` 归一为 ``reasoning_content``。

    前端/运行时的调测链路只消费 ``reasoning_content``；vLLM（DeepSeek-V4-Flash 等）在
    流式 ``delta.reasoning`` 与非流式 ``message.reasoning`` 返回思考，导致调测页不显示。
    仅处理 OpenAI chat/completions 约定承载思考的两个位点——``choices[].message`` 与
    ``choices[].delta``；不做全 JSON 递归，避免把 ``tool_calls``/``usage``/日志/元数据中
    可能存在的同名 ``reasoning`` 子结构一起改写、造成本函数职责外的影响面。
    原地变更 ``obj``，返回是否发生过补齐，供调用方决定是否需要重序列化（未补齐即字节
    可原样直通）。
    """
    if not isinstance(obj, dict):
        return False
    choices = obj.get("choices")
    if not isinstance(choices, list):
        return False
    changed = False
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        for field in ("message", "delta"):
            target = choice.get(field)
            if isinstance(target, dict) and _fill_reasoning_content(target):
                changed = True
    return changed


def _transform_chat_sse_line(line: bytes) -> bytes:
    """单行 SSE 变换：仅当该行确实需要补齐 ``reasoning_content`` 时才重序列化。

    非 ``data:`` 行、``data: [DONE]``/``[ERROR]``、非 JSON 行、以及无需补齐的 JSON 行一律
    按原始字节（含原行终止符）直通，避免对上游未变内容做无谓的重新序列化（原样保留
    上游空白/换行、``\\uXXXX`` 转义风格、重复键与数字字面量），与改造前的字节透明转发
    保持一致。``payload`` 先 ``strip`` 去掉行尾换行再比对 [DONE]/[ERROR]，让显式守卫
    真正生效（避免依赖 json.loads 失败兜底）。解析、归一、重序列化任一环节异常一律降级
    为原样透传该行：常见失败（畸形 JSON，及孤立代理项导致 ``.encode('utf-8')`` 抛出的
    UnicodeEncodeError——其本身即 ValueError 子类，无需再单独列出，避免同一 except 块
    父子异常重复捕获）静默透传；未预期异常（深嵌套 JSON 触发 ``RecursionError``、
    ``MemoryError`` 等）同样透传并记 warning，绝不因单行转换失败中断整条 SSE 流。
    仅捕获 ``Exception`` 不含 ``BaseException``，``asyncio.CancelledError``/
    ``KeyboardInterrupt`` 等取消信号仍可正常向上传播，不会被当作转换失败吞掉。
    """
    data_marker = b"data:"
    if not line.startswith(data_marker):
        return line
    payload = line[len(data_marker):].strip()
    if payload in (b"[DONE]", b"[ERROR]"):
        return line
    try:
        obj = json.loads(payload)
        if not _normalize_reasoning_fields(obj):
            return line
        return b"data: " + json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
    except (ValueError, TypeError):
        return line
    except Exception as exc:  # noqa: BLE001 - 兜底任意未预期异常，保证 SSE 流不因单行转换失败而中断
        logger.warning(
            "SSE line reasoning-normalize unexpected failure, pass line through: %s: %s",
            type(exc).__name__, exc,
        )
        return line


def _find_sse_line_end(buffer: bytes):
    """定位最早的 SSE 行终止符，支持 ``\\n``、``\\r\\n`` 与裸 ``\\r`` 三种行尾。

    返回 ``(终止符起始下标, 终止符长度)``；未找到返回 ``(-1, 0)``。``\\r`` 恰位于缓冲区
    末尾时暂不判定（可能是跨包拆分的 ``\\r\\n`` 前半），等待下一 chunk 再决定，避免误切。
    """
    lf = buffer.find(b"\n")
    cr = buffer.find(b"\r")
    if cr == -1:
        return (lf, 1) if lf != -1 else (-1, 0)
    if lf == -1 or cr < lf:
        if cr == len(buffer) - 1:
            return (-1, 0)
        if buffer[cr + 1:cr + 2] == b"\n":
            return (cr, 2)
        return (cr, 1)
    return (lf, 1)


async def _iter_relay_with_reasoning_transform(response: httpx.Response):
    """按行缓冲转发流式响应：跨包拆行、``\\r\\n``/裸 ``\\r`` 行尾重组为完整行后走归一变换。

    使用 ``aiter_bytes`` 读取已按 ``Content-Encoding`` 解码的响应体。若使用
    ``aiter_raw``，gzip 压缩的 SSE 会被原样转发，下游 SSE 解析器将无法识别
    ``data:`` 帧。

    保留原始行终止符字节，无需补齐的行原样直通；单行超过 ``_MAX_SSE_LINE_BUFFER`` 时把
    已缓冲字节直接放行并清空缓冲（该行整体降级为字节直通、不再累积后续字节参与拼接），
    防止异常或恶意上游持续发送无换行数据导致内存无界增长。流结束时若仍有残余缓冲
    （末行无终止符），按原样再走一次变换，不额外补 ``\\n``。
    """
    buffer = b""
    async for chunk in response.aiter_bytes():
        buffer += chunk
        while True:
            idx, sep = _find_sse_line_end(buffer)
            if idx == -1:
                if len(buffer) > _MAX_SSE_LINE_BUFFER:
                    yield buffer
                    buffer = b""
                break
            raw_line = buffer[:idx + sep]
            buffer = buffer[idx + sep:]
            yield _transform_chat_sse_line(raw_line)
    if buffer:
        yield _transform_chat_sse_line(buffer)


# ----------------------------- chat -----------------------------


@model_service_router.post("/v1/agent-builder/chat/completions")
async def chat_completions(
    request: Request,
    body: dict = Body(...),
    workspace_id: Optional[str] = Query(default=None, pattern=r"^[a-zA-Z0-9_()-]+$", max_length=64),
    refresh: Optional[bool] = Query(default=None),
    api_url_env_vars: Optional[str] = Query(default=None),
):
    """模型调测 — 对应 Java ``RuntimeModelServiceController.chatCompletions``。

    ``body`` 以 dict 透传（保留 OpenAI 全量字段）；``stream`` 取自 body.stream。
    ``api_url_env_vars`` 为调测时用户为 {VAR} 占位符填入的临时值（JSON map），
    merge 进 env_vars 后再 resolve_strategy（仅本次调测用，不落库）。
    """
    model_field = body.get("model", "")
    msid, project_id, workspace, auth_id, rf = _resolve_request_ctx(
        request, model_field, refresh, body.get("refresh")
    )
    workspace = workspace_id or workspace
    stream = bool(body.get("stream"))

    try:
        env_vars = _merge_env_var_overrides(
            model_service.ports.get_env_variables(), api_url_env_vars
        )
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf,
            env_vars=env_vars,
        )
        if strategy is None:
            raise resolver.ModelServiceError(
                MODEL_SERVICE_NOT_PUBLISH, f"model service not found: {msid}"
            )

        async def invoke_one(detail, is_stream):
            conn = dispatch.get_chat_connection(detail.model, detail.auth)
            url = detail.model.api_url
            client = dispatch.build_httpx_client(url, conn.verify_ssl)
            headers = _build_chat_headers(conn, detail.auth)
            up_body = _build_chat_upstream_body(body, conn.model_name, is_stream)
            if not is_stream:
                try:
                    resp = await client.post(
                        url, json=up_body, headers=headers, timeout=conn.timeout
                    )
                    if resp.status_code >= 300:
                        raise resolver.ModelServiceError(
                            INVOKE_MODEL_SERVICE_FAIL,
                            f"upstream {url} returned {resp.status_code}: {resp.text}"
                            + env_resolver.env_url_error_hint(
                                detail.model.api_url_env_placeholders),
                            upstream_status=resp.status_code,
                            upstream_body=resp.text,
                        )
                    # vLLM 类上游把思考放 message.reasoning，归一为 reasoning_content 供前端消费
                    resp_data = resp.json()
                    _normalize_reasoning_fields(resp_data)
                    return resp_data
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
                    f"upstream {url} returned {resp.status_code}: {text}"
                    + env_resolver.env_url_error_hint(
                        detail.model.api_url_env_placeholders),
                    upstream_status=resp.status_code,
                    upstream_body=text,
                )

            async def _relay_with_reasoning():
                try:
                    # 逐行归一 vLLM 的 delta.reasoning → delta.reasoning_content
                    async for line in _iter_relay_with_reasoning_transform(resp):
                        yield line
                finally:
                    await resp.aclose()
                    await client.aclose()

            return _relay_with_reasoning()

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
    api_url_env_vars: Optional[str] = Query(default=None),
):
    """文本向量化 — 对应 Java ``textEmbeddings``。上游 body 仅 ``{model, input}``。"""
    msid, project_id, workspace, auth_id, rf = _resolve_request_ctx(
        request, body.model, refresh, None
    )
    workspace = workspace_id or workspace
    try:
        env_vars = _merge_env_var_overrides(
            model_service.ports.get_env_variables(), api_url_env_vars
        )
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf,
            env_vars=env_vars,
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
        headers = _build_model_headers(conn, detail.auth, "BUILDER_MODEL_EMBEDDING")
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
    api_url_env_vars: Optional[str] = Query(default=None),
):
    """重排序 — 对应 Java ``rerank``。上游 body ``{model, query, documents}``，响应按 index 升序 + top_n 截断。"""
    msid, project_id, workspace, auth_id, rf = _resolve_request_ctx(
        request, body.model, refresh, None
    )
    workspace = workspace_id or workspace
    url = ""  # dispatch.rerank 抛 httpx 时用于错误信息；httpx 仅可能发生在下方赋值之后
    try:
        env_vars = _merge_env_var_overrides(
            model_service.ports.get_env_variables(), api_url_env_vars
        )
        strategy = await resolver.resolve_strategy(
            msid, project_id, workspace, auth_id, refresh=rf,
            env_vars=env_vars,
        )
        if strategy is None:
            raise resolver.ModelServiceError(
                MODEL_SERVICE_NOT_PUBLISH, f"model service not found: {msid}"
            )
        detail = strategy.models[0]
        url = detail.model.api_url
        #  把 customer rename（cust→userid/token）作为 projected_headers 显式传给 dispatch.rerank
        # （dispatch 是共享包、不依赖宿主请求上下文，按设计  由 facade 投影后显式传入）
        conn = dispatch.get_chat_connection(detail.model, detail.auth)
        projected = _project_customer_headers("BUILDER_MODEL_RERANK", conn)
        data = await dispatch.rerank(detail.model, detail.auth, body, projected_headers=projected)
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
        url = body.api_url  # 对应 Java ``model.getApiUrl`` verbatim，不追加 path
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


