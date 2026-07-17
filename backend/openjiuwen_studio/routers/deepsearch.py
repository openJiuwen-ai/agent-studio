from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable
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
from openjiuwen_studio.core.common.url_validator import validate_plugin_url
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
    TaskSpaceWebFetchProviderAccessRequestDTO,
    TaskSpaceProviderAccessRes,
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
PROVIDER_TEST_TIMEOUT_SECONDS = 30.0
PROVIDER_TEST_HTTPX_TIMEOUT = httpx.Timeout(PROVIDER_TEST_TIMEOUT_SECONDS, connect=10.0)


def get_agent_client():
    return DeepSearchAgentClient()


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
    llm_config = {"general": build_single_model_config(query.general_model_id, query.space_id)}

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
    """Normalize downstream DeepSearch failures for non-streaming endpoints."""
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
            logger.error(
                "DeepSearch service error: status=%s, body=%s",
                exc.response.status_code,
                exc.response.text[:1000] if exc.response.text else "",
            )
            status_code = exc.response.status_code if 400 <= exc.response.status_code < 500 else 502
            return JSONResponse(
                status_code=status_code,
                content={"detail": "DeepSearch service request failed. Please try again later."},
            )
    return wrapper


def validate_search_run_tool_credentials(request: DeepSearchSearchRunRequest) -> None:
    if request.tool_map == "search_fetch":
        has_search_config = request.web_search_engine_config is not None
        has_fetch_config = request.web_fetch_provider_config is not None

        if not has_search_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_map=search_fetch requires web_search_engine_config",
            )
        if not has_fetch_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_map=search_fetch requires web_fetch_provider_config",
            )
        if not request.web_search_engine_config.search_api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="web_search_engine_config.search_api_key must be non-empty",
            )
        if not request.web_fetch_provider_config.api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="web_fetch_provider_config.api_key must be non-empty",
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


PROVIDER_TEST_RESERVED_EXTENSION_KEYS = frozenset({
    "api_key",
    "authorization",
    "headers",
    "url",
    "endpoint",
    "query",
    "q",
    "messages",
    "model",
})
PROVIDER_TEST_SENSITIVE_RESULT_KEY_PARTS = ("api_key", "authorization", "token", "secret", "password")


def sanitize_provider_test_extension(extension: dict[str, Any]) -> dict[str, Any]:
    """Keep provider options while preventing extension data from replacing request controls."""
    return {
        key: value
        for key, value in extension.items()
        if isinstance(key, str) and key.lower() not in PROVIDER_TEST_RESERVED_EXTENSION_KEYS
    }


def redact_provider_test_result(value: Any, credential: str) -> Any:
    """Redact credentials from provider payloads before they reach the browser."""
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if isinstance(key, str) and any(part in key.lower() for part in PROVIDER_TEST_SENSITIVE_RESULT_KEY_PARTS)
                else redact_provider_test_result(item, credential)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_provider_test_result(item, credential) for item in value]
    if isinstance(value, str) and credential:
        return value.replace(credential, "[REDACTED]")
    return value


def _search_results_from_keys(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        items = payload.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return [payload]


def _normalize_perplexity_results(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return [payload]
    results: list[dict[str, Any]] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            results.append({"content": content})
    return results


def _build_q_request(
    api_key: str,
    query: str,
    extension: dict[str, Any],
    auth_header: str = "Authorization",
) -> tuple[dict[str, str], dict[str, Any]]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    headers[auth_header] = f"Bearer {api_key}" if auth_header == "Authorization" else api_key
    return headers, {"q": query, **sanitize_provider_test_extension(extension)}


def _build_tavily_request(
    api_key: str,
    query: str,
    extension: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    return (
        {"Accept": "application/json", "Content-Type": "application/json"},
        {"api_key": api_key, "query": query, **sanitize_provider_test_extension(extension)},
    )


def _build_serper_request(
    api_key: str,
    query: str,
    extension: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Match Deep Research's GoogleSearchAPIWrapper request payload."""
    options = sanitize_provider_test_extension(extension)
    options.pop("type", None)  # Selects the endpoint path, not a request-body field.
    return (
        {"Accept": "application/json", "Content-Type": "application/json", "X-API-KEY": api_key},
        {"q": query, "gl": options.pop("gl", "us"), "hl": options.pop("hl", "en"), **options},
    )


def _build_bocha_request(
    api_key: str,
    query: str,
    extension: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    return headers, {"query": query, **sanitize_provider_test_extension(extension)}


def _build_perplexity_request(
    api_key: str,
    query: str,
    extension: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    options = sanitize_provider_test_extension(extension)
    return (
        {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        {
            "model": "sonar",
            "messages": [{"role": "user", "content": query}],
            **options,
        },
    )


@dataclass(frozen=True)
class SearchProviderTestAdapter:
    name: str
    default_endpoint: str | None
    build_request: Callable[[str, str, dict[str, Any]], tuple[dict[str, str], dict[str, Any]]]
    normalize_results: Callable[[Any], list[dict[str, Any]]]

    def resolve_endpoint(self, submitted_endpoint: str | None, extension: dict[str, Any]) -> str:
        endpoint = (submitted_endpoint or self.default_endpoint or "").strip()
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Search provider '{self.name}' requires search_url",
            )
        try:
            endpoint = validate_plugin_url(endpoint)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search_url for provider '{self.name}'",
            ) from exc

        endpoint = endpoint.rstrip("/")
        if self.name == "tavily":
            # The runtime Tavily wrapper stores a base URL and appends `/search`.
            return endpoint if endpoint.endswith("/search") else f"{endpoint}/search"

        if self.name in {"google", "serper"}:
            # Deep Research routes both providers through GoogleSearchAPIWrapper,
            # which appends the configured result type to the base URL.
            search_type = extension.get("type", "search")
            if search_type not in {"search", "news", "places", "images"}:
                search_type = "search"
            if endpoint.rsplit("/", 1)[-1] not in {"search", "news", "places", "images"}:
                return f"{endpoint}/{search_type}"
        return endpoint


SEARCH_PROVIDER_TEST_ADAPTERS: dict[str, SearchProviderTestAdapter] = {
    "xunfei": SearchProviderTestAdapter(
        "xunfei", "https://api.xunfei.cn", _build_q_request, lambda payload: _search_results_from_keys(payload, ("data", "results", "items")),
    ),
    "petal": SearchProviderTestAdapter(
        "petal", "https://api.petal.dev", _build_q_request, lambda payload: _search_results_from_keys(payload, ("data", "results", "items")),
    ),
    "tavily": SearchProviderTestAdapter(
        "tavily", "https://api.tavily.com", _build_tavily_request, lambda payload: _search_results_from_keys(payload, ("results",)),
    ),
    "google": SearchProviderTestAdapter(
        "google", "https://google.serper.dev", _build_serper_request,
        lambda payload: _search_results_from_keys(payload, ("organic", "results")),
    ),
    "jina": SearchProviderTestAdapter(
        "jina", "https://s.jina.ai", _build_q_request, lambda payload: _search_results_from_keys(payload, ("data", "results", "items")),
    ),
    "serper": SearchProviderTestAdapter(
        "serper", "https://google.serper.dev", _build_serper_request,
        lambda payload: _search_results_from_keys(payload, ("organic", "results")),
    ),
    "bocha": SearchProviderTestAdapter(
        "bocha", "https://api.bocha.cn/v1/web-search", _build_bocha_request, lambda payload: _search_results_from_keys(payload, ("data", "results", "items")),
    ),
    "perplexity": SearchProviderTestAdapter(
        "perplexity", "https://api.perplexity.ai/chat/completions", _build_perplexity_request, _normalize_perplexity_results,
    ),
    "custom": SearchProviderTestAdapter(
        "custom", None, _build_q_request, lambda payload: _search_results_from_keys(payload, ("data", "results", "items")),
    ),
}


async def _post_generic_provider_test(
    endpoint: str,
    headers: dict[str, str],
    request_body: dict[str, Any],
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=PROVIDER_TEST_HTTPX_TIMEOUT, follow_redirects=False) as client:
            response = await client.post(endpoint, headers=headers, json=request_body)
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Provider test request failed provider_endpoint=%s error_type=%s", endpoint, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider test failed: unable to reach provider",
        ) from exc

    if response.status_code in (401, 403):
        raise HTTPException(status_code=response.status_code, detail="Provider authentication failed")
    if 400 <= response.status_code < 500:
        raise HTTPException(status_code=response.status_code, detail="Provider rejected the test request")
    if response.status_code >= 500:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Provider test failed: provider unavailable")
    return response


async def perform_web_search_provider_test(
    provider_name: str,
    api_key: str,
    search_url: str | None,
    extension: dict[str, Any],
    query: str,
) -> list[dict[str, Any]]:
    adapter = SEARCH_PROVIDER_TEST_ADAPTERS.get(provider_name)
    if adapter is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported search provider '{provider_name}'")

    endpoint = adapter.resolve_endpoint(search_url, extension)
    headers, request_body = adapter.build_request(api_key, query, extension)
    response = await _post_generic_provider_test(endpoint, headers, request_body)
    try:
        return redact_provider_test_result(adapter.normalize_results(response.json()), api_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider test returned a non-JSON response",
        ) from exc


@dataclass(frozen=True)
class FetchProviderTestAdapter:
    name: str
    default_base_url: str

    def resolve_base_url(self, submitted_base_url: str | None) -> str:
        base_url = (submitted_base_url or self.default_base_url).strip()
        try:
            return validate_plugin_url(base_url).rstrip("/")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base_url for provider '{self.name}'",
            ) from exc

    async def test(
        self,
        api_key: str,
        base_url: str | None,
        extension: dict[str, Any],
        test_url: str,
    ) -> list[dict[str, Any]]:
        try:
            safe_test_url = validate_plugin_url(test_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid test_url") from exc

        endpoint = f"{self.resolve_base_url(base_url)}/{safe_test_url}"
        params = sanitize_provider_test_extension(extension)
        try:
            async with httpx.AsyncClient(timeout=PROVIDER_TEST_HTTPX_TIMEOUT, follow_redirects=False) as client:
                response = await client.get(
                    endpoint,
                    headers={"Accept": "text/plain", "Authorization": f"Bearer {api_key}"},
                    params=params,
                )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Fetch provider test request failed provider=%s error_type=%s", self.name, type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Fetch provider test failed: unable to reach provider",
            ) from exc

        if response.status_code in (401, 403):
            raise HTTPException(status_code=response.status_code, detail="Provider authentication failed")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=response.status_code, detail="Provider rejected the test request")
        if response.status_code >= 500:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Fetch provider test failed: provider unavailable")

        return redact_provider_test_result([{"url": safe_test_url, "content": response.text[:2000]}], api_key)


FETCH_PROVIDER_TEST_ADAPTERS: dict[str, FetchProviderTestAdapter] = {
    "jina": FetchProviderTestAdapter(name="jina", default_base_url="https://r.jina.ai"),
}


async def perform_web_fetch_provider_test(
    provider_name: str,
    api_key: str,
    base_url: str | None,
    extension: dict[str, Any],
    test_url: str,
) -> list[dict[str, Any]]:
    adapter = FETCH_PROVIDER_TEST_ADAPTERS.get(provider_name)
    if adapter is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported fetch provider '{provider_name}'")
    return await adapter.test(api_key, base_url, extension, test_url)


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
    response_model=TaskSpaceProviderAccessRes,
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

    provider_name = payload["search_engine_name"]
    api_key = payload["search_api_key"].strip()
    query = payload["query"].strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search provider test requires a non-empty search_api_key",
        )
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search provider test requires a non-empty query",
        )

    datas = await perform_web_search_provider_test(
        provider_name=provider_name,
        api_key=api_key,
        search_url=payload["search_url"],
        extension=payload["extension"],
        query=query,
    )
    return {
        "code": status.HTTP_200_OK,
        "msg": "success",
        "provider_name": provider_name,
        "datas": datas,
    }


@deepsearch_router.post(
    "/task_space/web_fetch/provider_test",
    response_model=TaskSpaceProviderAccessRes,
    status_code=status.HTTP_200_OK,
)
@handle_deepsearch_errors
async def access_task_space_web_fetch_provider(
        request: TaskSpaceWebFetchProviderAccessRequestDTO,
        current_user: dict = Depends(get_current_user),
):
    payload = request.model_dump()
    space_id = payload["space_id"]
    _ = check_user_space(space_id, current_user)

    provider_name = payload["provider_name"]
    api_key = payload["api_key"].strip()
    test_url = payload["test_url"].strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fetch provider test requires a non-empty api_key",
        )
    if not test_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fetch provider test requires a non-empty test_url",
        )

    datas = await perform_web_fetch_provider_test(
        provider_name=provider_name,
        api_key=api_key,
        base_url=payload["base_url"],
        extension=payload["extension"],
        test_url=test_url,
    )
    return {
        "code": status.HTTP_200_OK,
        "msg": "success",
        "provider_name": provider_name,
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
