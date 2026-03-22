from functools import wraps
from typing import Dict, Any, Callable
import httpx
from httpx import HTTPStatusError
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.thirdparty_client import DeepSearchAgentClient
from openjiuwen_studio.core.manager.convertor.components.llm import get_model_config
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.common.exceptions import DeepSearchClientError
from openjiuwen_studio.core.config import settings
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


def get_model_configs(
    general_model_id,
    space_id,
    plan_understanding_model_id=None,
    info_collecting_model_id=None,
    writing_checking_model_id=None
):
    """构建 llm_config 结构，高级配置仅在有值时添加"""
    # llm_config = build_single_model_config(general_model_id, space_id)
    llm_config = {}
    llm_config["general"] = build_single_model_config(general_model_id, space_id)

    # 高级配置：仅在有值时添加
    if plan_understanding_model_id:
        llm_config["plan_understanding"] = build_single_model_config(plan_understanding_model_id, space_id)
    if info_collecting_model_id:
        llm_config["info_collecting"] = build_single_model_config(info_collecting_model_id, space_id)
    if writing_checking_model_id:
        llm_config["writing_checking"] = build_single_model_config(writing_checking_model_id, space_id)

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


@deepsearch_router.post("/run", response_model=ResponseModel[dict])
async def run(
        request: DeepSearchRequest,
        client: DeepSearchAgentClient = Depends(get_agent_client),
        current_user: dict = Depends(get_current_user)
) -> StreamingResponse:
    # 使用 request.model_dump() 保留前端传递的所有字段（除了 *_model_config_id）
    payload = request.model_dump(
        exclude_none=True,
        exclude={
            'general_model_config_id',
            'plan_understanding_model_id',
            'info_collecting_model_id',
            'writing_checking_model_id',
        }
    )
    # 取消请求不需要获取模型配置，直接转发到 deepsearch 服务
    if request.interrupt_feedback == "cancel":
        logger.info(f"[DeepSearch Cancel] Received cancel request for conversation_id={payload.get('conversation_id')}")
        # 取消请求：不需要 llm_config，直接转发
        pass
    else:
        # 构建完整的 llm_config（包含 general, plan_understanding 等）
        model_config = get_model_configs(
            request.general_model_config_id,
            request.space_id,
            request.plan_understanding_model_id,
            request.info_collecting_model_id,
            request.writing_checking_model_id
        )
        # 用构建好的 model_config 覆盖 llm_config
        payload["llm_config"] = model_config

    _ = check_user_space(payload["space_id"], current_user)

    async def stream():
        try:
            async for line in client.run_deepsearch_stream(payload):
                if line:
                    yield line + "\n\n"
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
    # 构建 llm_config（模板导入只需要 general 模型配置）
    model_config = get_model_configs(request.model_config_id, request.space_id)

    # 使用 request.model_dump() 保留前端传递的所有字段（除了 model_config_id）
    payload = request.model_dump(exclude={'model_config_id'})
    # 用构建好的 model_config 覆盖 llm_config
    payload["llm_config"] = model_config

    _ = check_user_space(payload["space_id"], current_user)
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


@deepsearch_router.get("/heartbeat")
async def deepsearch_heartbeat():
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
            response = await client.get(f"{base_url}/api/health")
            response.raise_for_status()

        # 检查响应内容
        data = response.json()
        if data.get("status") == "healthy":
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
