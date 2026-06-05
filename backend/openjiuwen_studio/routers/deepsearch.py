from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable
import asyncio
import httpx
from httpx import HTTPStatusError
from fastapi import APIRouter, Depends, status, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.database import get_db
from openjiuwen_studio.core.thirdparty_client import DeepSearchAgentClient
from openjiuwen_studio.core.manager.convertor.components.llm import get_model_config
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.model_manager.managers.vlm_model_config_manager import VLMModelConfigManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.utils.deepsearch_payload import (
    apply_interaction_defaults,
    get_local_search_kb_ids,
    classify_local_search_kbs,
)
from openjiuwen_studio.core.utils.deepsearch_stream import normalize_relay_stream_line
from openjiuwen_studio.core.common.exceptions import DeepSearchClientError
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.deepsearch import (
    DeepSearchRequest,
    DeepSearchSearchRunRequest,
    DeepSearchSearchRunResponse,
    DeepSearchTelemetryResponse,
    TemplateImportRequest,
    TemplateImportResponse,
    TemplateListResponse,
    TemplateGetResponse,
    TemplateDeleteResponse,
    TemplateUpdateRequest,
    TemplateUpdateResponse,
    WebSearchEngineCreateRes,
    WebSearchEngineCreateRequestDTO,
    WebSearchEngineGetRes,
    WebSearchEngineListRes,
    WebSearchEngineUpdateRes,
    WebSearchEngineUpdateRequestDTO,
    WebSearchEngineDeleteRes,
    WebSearchEngineAccessRequestDTO,
    WebSearchEngineAccessRes,
    TaskSpaceWebSearchProviderAccessRequestDTO,
    ReportConvertReq,
    ReportConvertRes,
)
from openjiuwen_studio.routers.deepsearch_logger import (
    cleanup_logs_async,
    log_deepsearch_request,
    log_deepsearch_sse,
    DeepSearchLogger,
)

deepsearch_router = APIRouter()
TASK_SPACE_PROVIDER_TEST_PRESETS: dict[str, dict[str, str]] = {
    "jina": {"engine_name": "jina", "endpoint": "https://s.jina.ai/"},
    "serper": {"engine_name": "google", "endpoint": "https://google.serper.dev/search"},
}
# Jina / Serper API key credential test timeout (seconds).
PROVIDER_TEST_TIMEOUT_SECONDS = 30.0
PROVIDER_TEST_HTTPX_TIMEOUT = httpx.Timeout(PROVIDER_TEST_TIMEOUT_SECONDS, connect=10.0)
# Jina Search: try China first, then global mirror (same API key & payload).
JINA_SEARCH_PROVIDER_ENDPOINTS: tuple[str, ...] = (
    "https://s.jinaai.cn/",
    "https://s.jina.ai/",
)


@dataclass
class DeepSearchModelConfigQuery:
    general_model_id: int
    space_id: str
    plan_understanding_model_id: int | None = None
    info_collecting_model_id: int | None = None
    writing_checking_model_id: int | None = None
    vlm_model_config_id: int | None = None


@dataclass
class DeepSearchTelemetryRangeQuery:
    run_id: str
    start_seq: int = Query(..., ge=0)
    end_seq: int = Query(..., ge=0)
    space_id: str | None = Query(default=None)


# 依赖注入（或直接使用单例）
def get_agent_client():
    return DeepSearchAgentClient()  # 或全局单例


def build_single_model_config(model_id, space_id):
    """构建单个模型配置"""
    model_config = get_model_config(model_id, space_id)
    return {
        "model_name": model_config.model_type,
        "model_type": model_config.provider,
        "base_url": model_config.base_url,
        "api_key": model_config.api_key,
        "hyper_parameters": {
            "top_p": model_config.parameters.get("top_p"),
            "frequency_penalty": 0,
            "max_tokens": model_config.parameters.get("max_tokens"),
            "temperature": model_config.parameters.get("temperature"),
        }
    }


def build_single_vlm_model_config(model_id: int, space_id: str, db: Session):
    """Build the VLM model config DeepSearch expects for chart generation."""
    model_config = VLMModelConfigManager(db).get_config_by_id(model_id, space_id)
    if not model_config.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VLM model config is inactive",
        )

    api_key = model_config.api_key
    if api_key:
        api_key = SecurityUtils().decrypt_api_key(api_key)

    return {
        "model_name": model_config.model_id,
        "model_type": model_config.provider,
        "base_url": model_config.base_url,
        "api_key": api_key,
        "hyper_parameters": {
            "timeout": model_config.timeout,
            "retry_count": model_config.retry_count,
        }
    }


def get_model_configs(query: DeepSearchModelConfigQuery, db: Session = None):
    """构建 llm_config 结构，高级配置仅在有值时添加"""
    # llm_config = build_single_model_config(general_model_id, space_id)
    llm_config = {}
    llm_config["general"] = build_single_model_config(query.general_model_id, query.space_id)

    # 高级配置：仅在有值时添加
    if query.plan_understanding_model_id:
        llm_config["plan_understanding"] = build_single_model_config(
            query.plan_understanding_model_id,
            query.space_id,
        )
    if query.info_collecting_model_id:
        llm_config["info_collecting"] = build_single_model_config(
            query.info_collecting_model_id,
            query.space_id,
        )
    if query.writing_checking_model_id:
        llm_config["writing_checking"] = build_single_model_config(
            query.writing_checking_model_id,
            query.space_id,
        )
    if query.vlm_model_config_id:
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database session is required for VLM model config",
            )
        llm_config["vlm_chart_generating"] = build_single_vlm_model_config(
            query.vlm_model_config_id,
            query.space_id,
            db,
        )

    return llm_config


def handle_deepsearch_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    装饰器：自动捕获 HTTPStatusError 并返回通用错误响应。
    适用于返回 JSONResponse 或 dict 的非流式接口。
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DeepSearchClientError as exc:
            logger.error("DeepSearch client error: %s", exc.message, exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": exc.message},
            )
        except HTTPStatusError as exc:
            # 记录原始错误详情到服务器日志，便于排查问题
            logger.error(
                "DeepSearch service error: status=%s, body=%s",
                exc.response.status_code,
                exc.response.text[:1000] if exc.response.text else "",
            )
            # 状态码规范化：内部服务的5xx错误统一返回502，4xx错误保留原始状态码
            status_code = exc.response.status_code if 400 <= exc.response.status_code < 500 else 502
            return JSONResponse(
                status_code=status_code,
                content={"detail": "DeepSearch service request failed. Please try again later."},
            )
    return wrapper


def validate_search_run_tool_credentials(request: DeepSearchSearchRunRequest) -> None:
    if request.tool_map == "search_fetch":
        has_jina_key = bool((request.jina_api_key or "").strip())
        has_serper_key = bool((request.serper_api_key or "").strip())
        if not has_jina_key or not has_serper_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_map=search_fetch requires both jina_api_key and serper_api_key",
            )
        return

    if request.tool_map == "retrieve":
        if not request.milvus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_map=retrieve requires milvus config",
            )
        if not request.milvus.embedder_api_key or not request.milvus.embedder_base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_map=retrieve requires milvus.embedder_api_key and milvus.embedder_base_url",
            )


def extract_http_status_error_detail(exc: HTTPStatusError) -> str | None:
    response = exc.response
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        for key in ("detail", "msg", "message", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if payload:
            return str(payload)
    if isinstance(payload, list):
        return "; ".join(str(item) for item in payload if item)

    text = (response.text or "").strip()
    return text if text else None


def raise_provider_test_http_error(exc: HTTPStatusError, fallback_detail: str) -> None:
    downstream_detail = extract_http_status_error_detail(exc)
    detail = fallback_detail
    if downstream_detail:
        detail = f"{fallback_detail}: {downstream_detail}"
    raise HTTPException(
        status_code=(
            exc.response.status_code
            if 400 <= exc.response.status_code < 500
            else status.HTTP_502_BAD_GATEWAY
        ),
        detail=detail,
    ) from exc


def normalize_provider_test_results(response_payload: Any, provider: str) -> list[dict[str, Any]]:
    if isinstance(response_payload, list):
        return [item for item in response_payload if isinstance(item, dict)]

    if not isinstance(response_payload, dict):
        return []

    if provider == "serper":
        organic_results = response_payload.get("organic")
        if isinstance(organic_results, list):
            return [item for item in organic_results if isinstance(item, dict)]

    for key in ("data", "results", "items"):
        value = response_payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return [response_payload]


async def _post_provider_test(
    endpoint: str,
    headers: dict[str, str],
    request_body: dict[str, Any],
    timeout: httpx.Timeout | float,
    client: httpx.AsyncClient | None = None,
) -> httpx.Response:
    if client is not None:
        return await client.post(endpoint, headers=headers, json=request_body)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
        return await http_client.post(endpoint, headers=headers, json=request_body)


def _jina_provider_auth_failure(response: httpx.Response) -> bool:
    if response.status_code in (401, 403):
        return True
    if response.status_code < 500:
        return False
    body = (response.text or "").lower()
    return "authenticate" in body or "authenticationrequired" in body


async def _perform_jina_provider_test(
    headers: dict[str, str],
    request_body: dict[str, Any],
) -> httpx.Response:
    """Race Jina CN/global endpoints; return as soon as one succeeds or auth fails."""
    async with httpx.AsyncClient(timeout=PROVIDER_TEST_HTTPX_TIMEOUT, follow_redirects=True) as client:

        async def probe(endpoint: str) -> tuple[str, httpx.Response | None, BaseException | None]:
            try:
                response = await _post_provider_test(
                    endpoint,
                    headers,
                    request_body,
                    PROVIDER_TEST_HTTPX_TIMEOUT,
                    client=client,
                )
                return endpoint, response, None
            except (httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadTimeout) as exc:
                logger.warning(
                    "Provider credential test connect failed provider=jina endpoint=%s: %s",
                    endpoint,
                    exc,
                )
                return endpoint, None, exc

        tasks = [asyncio.create_task(probe(endpoint)) for endpoint in JINA_SEARCH_PROVIDER_ENDPOINTS]
        connect_errors: list[BaseException] = []
        server_error_response: httpx.Response | None = None

        try:
            for finished in asyncio.as_completed(tasks):
                _endpoint, response, error = await finished
                if error is not None:
                    connect_errors.append(error)
                    continue
                if response.status_code == 200:
                    return response
                if _jina_provider_auth_failure(response):
                    try:
                        response.raise_for_status()
                    except HTTPStatusError as exc:
                        raise_provider_test_http_error(exc, "Provider credential test failed")
                if response.status_code >= 500 and server_error_response is None:
                    logger.warning(
                        "Provider credential test server error provider=jina endpoint=%s status=%s",
                        _endpoint,
                        response.status_code,
                    )
                    server_error_response = response
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    if server_error_response is not None:
        return server_error_response
    if connect_errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider credential test failed: unable to reach Jina endpoints",
        ) from connect_errors[0]
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Provider credential test failed",
    )


async def perform_provider_test(provider: str, api_key: str, query: str) -> list[dict[str, Any]]:
    provider_preset = TASK_SPACE_PROVIDER_TEST_PRESETS[provider]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    request_body: dict[str, Any] = {"q": query}

    if provider == "jina":
        headers["Authorization"] = f"Bearer {api_key}"
    elif provider == "serper":
        headers["X-API-KEY"] = api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{provider}' for credential test",
        )

    if provider == "jina":
        response = await _perform_jina_provider_test(headers, request_body)
    else:
        endpoint = provider_preset["endpoint"]
        try:
            response = await _post_provider_test(
                endpoint,
                headers,
                request_body,
                PROVIDER_TEST_HTTPX_TIMEOUT,
            )
        except (httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadTimeout) as exc:
            logger.warning(
                "Provider credential test connect failed provider=%s endpoint=%s: %s",
                provider,
                endpoint,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Provider credential test failed: unable to reach provider endpoint",
            ) from exc

    try:
        response.raise_for_status()
    except HTTPStatusError as exc:
        raise_provider_test_http_error(exc, "Provider credential test failed")

    try:
        response_payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider credential test returned a non-JSON response",
        ) from exc

    return normalize_provider_test_results(response_payload, provider)


@deepsearch_router.post("/run", response_model=ResponseModel[dict])
async def run(
        request: DeepSearchRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
) -> StreamingResponse:
    # 使用 request.model_dump() 保留前端传递的所有字段（除了 *_model_config_id）
    payload = request.model_dump(
        exclude_none=True,
        exclude={
            'general_model_config_id',
            'plan_understanding_model_id',
            'info_collecting_model_id',
            'writing_checking_model_id',
            'vlm_model_config_id',
        }
    )
    
    # 先检查用户权限
    _ = check_user_space(payload["space_id"], current_user)
    
    apply_interaction_defaults(
        payload,
        fields_set=request.model_fields_set,
        interrupt_feedback=request.interrupt_feedback,
    )

    # 取消请求不需要获取模型配置，直接转发到 deepsearch 服务
    if request.interrupt_feedback == "cancel":
        logger.info(f"[DeepSearch Cancel] Received cancel request for conversation_id={payload.get('conversation_id')}")
        # 取消请求：不需要 llm_config，直接转发
        pass
    else:
        if payload.get("info_collector_search_method") == "local":
            local_kb_ids = get_local_search_kb_ids(payload)
            if not local_kb_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "At least one local knowledge base is required when "
                        "info_collector_search_method is 'local'."
                    ),
                )

            with_docs_kb_ids, empty_kb_ids, unavailable_kb_ids = await classify_local_search_kbs(
                space_id=request.space_id,
                kb_ids=local_kb_ids,
                list_documents=client.list_documents,
            )
            if not with_docs_kb_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Selected local knowledge bases contain no available indexed documents. "
                        f"empty_kb_ids={empty_kb_ids}, unavailable_kb_ids={unavailable_kb_ids}"
                    ),
                )
            if empty_kb_ids or unavailable_kb_ids:
                local_cfg = payload.get("local_search_config")
                if isinstance(local_cfg, dict):
                    local_cfg["local_search_config_ids"] = with_docs_kb_ids
                logger.warning(
                    "[DeepSearch Run] Filtered local knowledge bases without indexed documents. "
                    f"conversation_id={payload.get('conversation_id')}, "
                    f"kept_kb_ids={with_docs_kb_ids}, empty_kb_ids={empty_kb_ids}, "
                    f"unavailable_kb_ids={unavailable_kb_ids}"
                )

        if (
            request.vlm_chart_generator_enable
            and request.vlm_chart_generator_max_iterations > 0
            and not request.vlm_model_config_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VLM model config is required when VLM chart generator is enabled with iterations > 0",
            )

        # 构建完整的 llm_config（包含 general, plan_understanding 等）
        model_config = get_model_configs(
            DeepSearchModelConfigQuery(
                general_model_id=request.general_model_config_id,
                space_id=request.space_id,
                plan_understanding_model_id=request.plan_understanding_model_id,
                info_collecting_model_id=request.info_collecting_model_id,
                writing_checking_model_id=request.writing_checking_model_id,
                vlm_model_config_id=request.vlm_model_config_id,
            ),
            db,
        )
        # 用构建好的 model_config 覆盖 llm_config
        payload["llm_config"] = model_config

    # 获取 conversation_id
    conversation_id = payload.get("conversation_id", "")

    # 清理过期日志（使用默认的 10 天过期时间）
    try:
        await cleanup_logs_async(DeepSearchLogger.DEFAULT_LOG_EXPIRE_DAYS)
    except Exception as e:
        logger.warning(f"Failed to cleanup old logs: {e}")

    # 记录请求数据到日志
    try:
        await log_deepsearch_request(conversation_id, payload, DeepSearchLogger.DEFAULT_LOG_EXPIRE_DAYS)
    except Exception as e:
        logger.warning(f"Failed to log request data: {e}")

    async def stream():
        try:
            async for line in client.run_deepsearch_stream(payload):
                relay_line = normalize_relay_stream_line(line, payload.get("search_mode"))
                if relay_line:
                    # 记录 SSE 数据到日志
                    try:
                        await log_deepsearch_sse(
                            conversation_id, relay_line, DeepSearchLogger.DEFAULT_LOG_EXPIRE_DAYS
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log SSE data: {e}")

                    yield relay_line + "\n\n"
        except Exception as e:
            # 记录原始错误详情到服务器日志
            logger.error("DeepSearch client init error: %s", str(e))
            if isinstance(e, DeepSearchClientError):
                error = e
            else:
                error = DeepSearchClientError(
                    error_code="CLIENT_INIT_ERROR",
                    message="Failed to connect to DeepSearch service"
                )
            for event_str in error.generate_error_stream(conversation_id):
                yield event_str

    return StreamingResponse(stream(), media_type="text/event-stream")


@deepsearch_router.post("/runs", response_model=DeepSearchSearchRunResponse)
@handle_deepsearch_errors
async def create_search_run(
        request: DeepSearchSearchRunRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user),
):
    _ = check_user_space(request.space_id, current_user)
    validate_search_run_tool_credentials(request)
    payload = request.model_dump(exclude={"space_id"}, exclude_none=True)
    return await client.create_deepsearch_run(payload)


@deepsearch_router.post("/runs/{run_id}/cancel")
@handle_deepsearch_errors
async def cancel_search_run(
        run_id: str,
        space_id: str | None = Query(default=None),
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user),
):
    if space_id:
        _ = check_user_space(space_id, current_user)
    return await client.cancel_deepsearch_run(run_id)


@deepsearch_router.get("/telemetry/recent", response_model=DeepSearchTelemetryResponse)
@handle_deepsearch_errors
async def get_recent_telemetry(
        n: int = Query(default=1, ge=1, le=1000),
        run_id: str | None = Query(default=None),
        space_id: str | None = Query(default=None),
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user),
):
    if space_id:
        _ = check_user_space(space_id, current_user)
    return await client.get_deepsearch_telemetry_recent(n=n, run_id=run_id)


@deepsearch_router.get("/telemetry/range", response_model=DeepSearchTelemetryResponse)
@handle_deepsearch_errors
async def get_telemetry_range(
        query: DeepSearchTelemetryRangeQuery = Depends(),
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user),
):
    if query.end_seq < query.start_seq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_seq must be greater than or equal to start_seq",
        )
    if query.space_id:
        _ = check_user_space(query.space_id, current_user)
    return await client.get_deepsearch_telemetry_range(
        run_id=query.run_id,
        start_seq=query.start_seq,
        end_seq=query.end_seq,
    )


@deepsearch_router.post("/template", response_model=TemplateImportResponse)
@handle_deepsearch_errors
async def import_template(
        request: TemplateImportRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """导入模板"""
    # 先检查用户权限
    _ = check_user_space(request.space_id, current_user)
    
    # 构建 llm_config（模板导入只需要 general 模型配置）
    model_config = get_model_configs(
        DeepSearchModelConfigQuery(
            general_model_id=request.model_config_id,
            space_id=request.space_id,
        )
    )

    # 使用 request.model_dump() 保留前端传递的所有字段（除了 model_config_id）
    payload = request.model_dump(exclude={'model_config_id'})
    # 用构建好的 model_config 覆盖 llm_config
    payload["llm_config"] = model_config

    result = await client.import_templates(payload)
    # 直接返回，FastAPI 会自动校验并序列化为 TemplateImportResponse
    return result


@deepsearch_router.get("/template/{space_id}", response_model=TemplateListResponse)
@handle_deepsearch_errors
async def list_templates(
        space_id: str,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Get template list by space_id"""
    _ = check_user_space(space_id, current_user)
    return await client.list_templates(space_id)


@deepsearch_router.get("/template/{space_id}/{template_id}", response_model=TemplateGetResponse)
@handle_deepsearch_errors
async def get_template(
        space_id: str,
        template_id: int,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Get template content by space_id and template_id"""
    _ = check_user_space(space_id, current_user)
    return await client.get_templates(space_id, template_id)


@deepsearch_router.delete("/template/{space_id}/{template_id}", response_model=TemplateDeleteResponse)
@handle_deepsearch_errors
async def delete_template(
        space_id: str,
        template_id: int,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Delete a specific template"""
    _ = check_user_space(space_id, current_user)
    return await client.delete_templates(space_id, template_id)


@deepsearch_router.put("/template", response_model=TemplateUpdateResponse)
@handle_deepsearch_errors
async def update_template(
        request: TemplateUpdateRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Update a specific template"""
    payload = request.model_dump()
    _ = check_user_space(payload["space_id"], current_user)
    return await client.update_templates(payload)


@deepsearch_router.post("/web_search", response_model=WebSearchEngineCreateRes, status_code=status.HTTP_201_CREATED)
@handle_deepsearch_errors
async def create_web_search_engine(
        request: WebSearchEngineCreateRequestDTO,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Create a specific template"""
    payload = request.model_dump()
    _ = check_user_space(payload["space_id"], current_user)
    return await client.create_web_searchs(payload)


@deepsearch_router.get("/web_search/{space_id}/{web_search_engine_id}",
            response_model=WebSearchEngineGetRes, status_code=status.HTTP_200_OK)
@handle_deepsearch_errors
async def get_web_search_engine(
        space_id: str,
        web_search_engine_id: int,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Get web search by space_id and web_search_engine_id"""
    _ = check_user_space(space_id, current_user)
    return await client.get_web_search_engines(space_id, web_search_engine_id)


@deepsearch_router.get("/web_search/{space_id}",
            response_model=WebSearchEngineListRes, status_code=status.HTTP_200_OK)
@handle_deepsearch_errors
async def get_web_search_engine_list(
        space_id: str,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Get web search list"""
    _ = check_user_space(space_id, current_user)
    return await client.get_web_search_engine_lists(space_id)


@deepsearch_router.delete("/web_search/{space_id}/{web_search_engine_id}",
               response_model=WebSearchEngineDeleteRes, status_code=status.HTTP_200_OK)
@handle_deepsearch_errors
async def delete_web_search_engine(
        space_id: str,
        web_search_engine_id: int,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Delete web search by space_id and web_search_engine_id"""
    _ = check_user_space(space_id, current_user)
    return await client.delete_web_search_engines(space_id, web_search_engine_id)


@deepsearch_router.put("/web_search", response_model=WebSearchEngineUpdateRes, status_code=status.HTTP_200_OK)
@handle_deepsearch_errors
async def update_web_search_engine(
        request: WebSearchEngineUpdateRequestDTO,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """Update a specific web search"""
    payload = request.model_dump()
    _ = check_user_space(payload["space_id"], current_user)
    return await client.update_web_search_engines(payload)


@deepsearch_router.post("/web_search/{space_id}/{web_search_engine_id}",
             response_model=WebSearchEngineAccessRes, status_code=status.HTTP_201_CREATED)
@handle_deepsearch_errors
async def access_web_search_engine(
        space_id: str,
        web_search_engine_id: int,
        request: WebSearchEngineAccessRequestDTO,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """test web search"""
    payload = request.model_dump()
    _ = check_user_space(space_id, current_user)
    res = await client.access_web_search_engines(space_id, web_search_engine_id, payload)
    return res


@deepsearch_router.post(
    "/task_space/web_search/provider_test",
    response_model=WebSearchEngineAccessRes,
    status_code=status.HTTP_200_OK,
)
@handle_deepsearch_errors
async def access_task_space_web_search_provider(
        request: TaskSpaceWebSearchProviderAccessRequestDTO,
        current_user: dict = Depends(get_current_user)
):
    payload = request.model_dump()
    space_id = payload["space_id"]
    _ = check_user_space(space_id, current_user)

    provider = payload["provider"]
    api_key = payload["api_key"].strip()
    query = payload["query"].strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider credential test requires a non-empty api_key",
        )
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider credential test requires a non-empty query",
        )

    datas = await perform_provider_test(provider=provider, api_key=api_key, query=query)
    return {
        "code": status.HTTP_200_OK,
        "msg": "success",
        "search_engine_name": TASK_SPACE_PROVIDER_TEST_PRESETS[provider]["engine_name"],
        "datas": datas,
    }


@deepsearch_router.post("/reports/convert", response_model=ReportConvertRes)
@handle_deepsearch_errors
async def report_convert(
        request: ReportConvertReq,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """转换生成的markdown报告的格式"""
    payload = request.model_dump()
    _ = check_user_space(payload["space_id"], current_user)
    return await client.report_converts(payload)


@deepsearch_router.get("/heartbeat")
@handle_deepsearch_errors
async def deepsearch_heartbeat(
        current_user: dict = Depends(get_current_user)
):
    """检查 DeepSearch 服务是否可用"""
    try:
        # 检查配置
        if not settings.deepsearch_agent_host or not settings.deepsearch_agent_port:
            return {
                "status": "unavailable",
                "message": "DeepSearch service not configured"
            }

        # 直接向 DeepSearch 服务发送健康检查请求
        base_url = f"http://{settings.deepsearch_agent_host}:{settings.deepsearch_agent_port}"
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = None
            for health_path in ("/health", "/api/health"):
                try:
                    candidate = await client.get(f"{base_url}{health_path}")
                    candidate.raise_for_status()
                    response = candidate
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        continue
                    raise

        # 检查响应内容
        if response is None:
            return {
                "status": "unavailable",
                "message": "DeepSearch health endpoint not found"
            }

        data = response.json()
        if data.get("status") in {"healthy", "ok", "available"}:
            return {
                "status": "available",
                "message": "DeepSearch service is available"
            }
        else:
            return {
                "status": "unavailable",
                "message": "DeepSearch service is not healthy"
            }
    except httpx.ConnectError:
        logger.error("DeepSearch heartbeat: connection error")
        return {
            "status": "unavailable",
            "message": "Cannot connect to DeepSearch service"
        }
    except httpx.TimeoutException:
        logger.error("DeepSearch heartbeat: timeout")
        return {
            "status": "unavailable",
            "message": "DeepSearch service timeout"
        }
    except Exception as e:
        logger.error("DeepSearch heartbeat: %s", str(e))
        return {
            "status": "unavailable",
            "message": "DeepSearch service error"
        }
