from functools import wraps
from typing import Dict, Any, Callable
from httpx import HTTPStatusError
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from openjiuwen_studio.core.thirdparty_client import DeepSearchAgentClient
from openjiuwen_studio.core.manager.convertor.components.llm import get_model_config
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.common.exceptions import DeepSearchClientError
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.deepsearch import (
    DeepSearchRequest,
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
    ReportConvertReq,
    ReportConvertRes,
)

deepsearch_router = APIRouter()


# 依赖注入（或直接使用单例）
def get_agent_client():
    return DeepSearchAgentClient()  # 或全局单例


def get_model_configs(model_id, space_id):
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


def handle_deepsearch_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    装饰器：自动捕获 HTTPStatusError 并返回 DeepSearch 原始错误响应。
    适用于返回 JSONResponse 或 dict 的非流式接口。
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPStatusError as exc:
            try:
                content = exc.response.json()
            except Exception:
                content = {"detail": exc.response.text or "DeepSearch service error"}
            return JSONResponse(
                status_code=exc.response.status_code,
                content=content,
            )
    return wrapper


@deepsearch_router.post("/run", response_model=ResponseModel[dict])
async def run(
        request: DeepSearchRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
) -> StreamingResponse:
    payload = request.model_dump(exclude_none=True)
    _ = check_user_space(payload["space_id"], current_user)

    model_config = get_model_configs(payload["model_config_id"], payload["space_id"])
    payload["llm_config"] = model_config

    async def stream():
        try:
            async for line in client.run_deepsearch_stream(payload):
                if line:
                    yield line + "\n\n"
        except Exception as e:
            if isinstance(e, DeepSearchClientError):
                error = e
            else:
                error = DeepSearchClientError(
                    error_code="CLIENT_INIT_ERROR",
                    message=str(e)
                )
            conversation_id = payload.get("conversation_id", "")
            for event_str in error.generate_error_stream(conversation_id):
                yield event_str

    return StreamingResponse(stream(), media_type="text/event-stream")


@deepsearch_router.post("/template", response_model=TemplateImportResponse)
@handle_deepsearch_errors
async def import_template(
        request: TemplateImportRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
):
    """导入模板"""
    payload = request.model_dump()
    _ = check_user_space(payload["space_id"], current_user)

    model_config = get_model_configs(payload["model_config_id"], payload["space_id"])
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

