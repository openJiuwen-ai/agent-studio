"""
Orchestration API — MVP implementation of /v1/orchestration/ir/execute
"""

import json
import os
import time
import uuid
from copy import deepcopy
from typing import Union

from agent_runtime.common.config import settings, ModelConfigStrategyType
from agent_runtime.common.ir_exceptions import IRBuildException
from agent_runtime.common.ir_interfaces import (
    StorageConfigError,
    StorageReadError,
)
from agent_runtime.runner.controller_runner import ControllerRunner
from agent_runtime.runner.react_agent_runner import ReActAgentRunner
from agent_runtime.runner.workflow_runner import WorkflowRunner, ModelConfigStrategy
from agent_runtime.schemas.orchestration_mgr import (
    ComponentDebugRequest,
    ExecutionRequest,
    ResponseMode,
    DeleteExecutionInstanceRequest,
)
from agent_runtime.schemas.additional_questions import (
    AdditionalQuestionsContext,
    AdditionalQuestionsRequest,
    AdditionalQuestionsResponse,
)
from agent_runtime.additional_questions.service import (
    AdditionalQuestionsService,
)
from agent_runtime.storage import get_storage_provider
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.open_utils import async_ir_load, cache_workflow_queue
from openjiuwen.core.common.logging import workflow_logger
from pydantic import ValidationError
from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat


execution_app = APIRouter(tags=["execution_app"])

# Shared runner singletons; created lazily so env vars are loaded.
_workflow_runner: WorkflowRunner | None = None
_react_runner: ReActAgentRunner | None = None
_controller_runner: ControllerRunner | None = None
_DEFAULT = "default"


def _get_workflow_runner() -> WorkflowRunner:
    global _workflow_runner
    if _workflow_runner is None:
        strategy_env = settings.llm.model_config_strategy
        strategy_map = {
            ModelConfigStrategyType.ENV: ModelConfigStrategy.ENV,
            ModelConfigStrategyType.IR: ModelConfigStrategy.IR,
            ModelConfigStrategyType.OBS: ModelConfigStrategy.OBS,
        }
        _workflow_runner = WorkflowRunner(
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
            model_strategy=strategy_map.get(strategy_env, ModelConfigStrategy.IR),
        )
    return _workflow_runner


def _get_react_runner() -> ReActAgentRunner:
    global _react_runner
    if _react_runner is None:
        # 确保 model config provider factory 已初始化
        _get_workflow_runner()
        _react_runner = ReActAgentRunner(
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
        )
    return _react_runner


def _get_controller_runner() -> ControllerRunner:
    global _controller_runner
    if _controller_runner is None:
        # 确保 model config provider factory 已初始化
        _get_workflow_runner()
        _controller_runner = ControllerRunner(
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
        )
    return _controller_runner


def _get_runner_by_type(agent_type: str):
    """根据agent_type返回对应的runner"""
    if agent_type == "ReAct":
        return _get_react_runner()
    if agent_type in ("Controller", "PlanExecute"):
        return _get_controller_runner()
    return _get_workflow_runner()


@execution_app.get("/v1/health", response_class=PlainTextResponse)
async def health():
    """Restful API for server health."""
    return (
        settings.health_check.custom_rsp
        if settings.health_check.custom_rsp
        else "the health is good"
    )


@execution_app.post("/v1/orchestration/ir/execute")
async def ir_execute(req_json: dict, request: Request):
    """
    IR execute endpoint.
    直接透传 openjiuwen 原生格式，不做额外包装
    """
    workflow_logger.debug(
        "IR Execute Request - URL: %s %s", request.method, request.url
    )
    workflow_logger.debug(
        "IR Execute Request - Headers: %s",
        json.dumps(dict(request.headers), ensure_ascii=False),
    )
    workflow_logger.debug(
        "IR Execute Request - Query Params: %s",
        json.dumps(dict(request.query_params), ensure_ascii=False),
    )
    workflow_logger.debug(
        "IR Execute Request - Body: %s", json.dumps(req_json, ensure_ascii=False)
    )

    try:
        req = ExecutionRequest.model_validate(req_json)
        req.headers = {**request.headers, **req.headers}
        req.params = prepare_params(req)
        req.params.global_variables = {
            "sys": {
                "conversationHistory": req.params.conversation_history,
                "conversationId": req.conversation_id,
                "userId": req.user_id,
                "dialogueCount": req_json.get("dialogueCount", 1),
                "currentTime": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "conversationId": req.conversation_id,
            "userId": req.user_id,
        } | req.params.global_variables
        req.params.is_debug = req.headers.get("x-invoke-mode", "").lower() == "debug"
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "details": str(e)},
        )

    execution_id = req.headers.get("x-execution-id", "")

    # 只读一次 IR（避免重复读取）
    exec_id = execution_id
    ir_path = req.ir_path
    try:
        ir_json = await async_ir_load(ir_path)
    except Exception as e:
        workflow_logger.error(f"Failed to load IR from {ir_path}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "ir_load_failed", "details": str(e)},
        )

    mode = (ir_json.get("configs") or {}).get("mode", "workflow")
    runner = _get_runner_by_type(mode)

    if req.response_mode == ResponseMode.STREAMING:
        return StreamingResponse(
            content=stream_response(req, execution_id, runner),
            media_type="text/event-stream",
        )
    else:
        full_text = await runner.run_blocking(req)
        now_ms = int(time.time() * 1000)
        return JSONResponse(
            content={
                "event": "done",
                "createdTime": now_ms,
                "executionId": execution_id,
                "data": {"text": full_text},
            }
        )


async def stream_response(req: ExecutionRequest, execution_id: str, runner):
    """
    透传 OutputSchema 格式
    输出格式: data: {"type": "end node stream", "index": 0, "payload": {"response": "text"}}\n\n
    """
    execution_id = execution_id or str(uuid.uuid4())
    last_event = ""
    async for chunk in runner.run_streaming(req, execution_id):
        if chunk is None:
            continue
        if isinstance(chunk, bytes):
            yield chunk
        else:
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if isinstance(chunk, dict):
                last_event = chunk.get("event", "")

    # 兜底 done：runner 仅在异常处理中自行发送 done（见 workflow_runner.py except 块），
    # 正常完成时 runner 不发 done，由这里补发。
    if last_event != "done":
        done_payload = {
            "event": "done",
            "data": {},
            "index": 0,
            "executionId": execution_id,
            "createdTime": int(time.time()),
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


@execution_app.post("/v1/orchestration/ir/component/{component_id}/execute")
async def component_debug_execute(component_id: str, req_json: dict, request: Request):
    """单组件调试端点"""
    try:
        req = ComponentDebugRequest.model_validate(req_json)
        req.params = prepare_params(req)
        req.params.global_variables = {
            "sys": {
                "conversationHistory": req.params.conversation_history,
                "conversationId": req.conversation_id,
                "userId": req.user_id,
            },
            "conversationId": req.conversation_id,
            "userId": req.user_id,
        } | req.params.global_variables
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "details": str(e)},
        )

    execution_id = getattr(request.state, "execution_id", None) or str(uuid.uuid4())
    runner = _get_workflow_runner()

    return StreamingResponse(
        content=debug_stream_response(req, component_id, execution_id, runner),
        media_type="text/event-stream",
    )


async def debug_stream_response(
    req: ComponentDebugRequest,
    component_id: str,
    execution_id: str,
    runner: WorkflowRunner,
):
    """单组件调试 SSE 流"""
    async for chunk in runner.run_debug_streaming(req, component_id, execution_id):
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def prepare_params(req: Union[ExecutionRequest, ComponentDebugRequest]):
    """
    格式化请求参数并将请求头中的信息添加到参数中。

    此函数用于处理请求参数，特别是插件配置部分。它将请求头中的信息合并到插件配置中，并返回处理后的参数。

    Args:
        req (Union[ExecutionRequest, ComponentDebugRequest]): 执行请求或组件执行请求对象，包含请求参数和请求头。

    Returns:
        ExecutionParams 或 ComponentParams: 处理后的请求参数，包含更新后的插件配置。

    Raises:
        无特定异常抛出。

    Notes:
        - 函数首先创建请求参数的深拷贝以避免修改原始参数。
        - 将请求头中的信息转换为小写，并合并到每个插件配置中。
        - 如果请求中没有插件配置，则至少为默认配置添加请求头信息。
    """
    params = deepcopy(req.params)

    # 处理插件鉴权信息，需要将请求头中所带的信息加入params
    headers_dict = {key.lower(): value for key, value in dict(req.headers).items()}
    prepared_plugin_configs = {}
    if req.params.plugin_configs:
        for plugin_config in req.params.plugin_configs:
            prepared_plugin_configs[plugin_config.plugin_id] = {
                **headers_dict,
                **plugin_config.config,
            }
    prepared_plugin_configs[_DEFAULT] = {**headers_dict}
    params.plugin_configs = prepared_plugin_configs

    return params


async def _load_ir_json(ir_path: str) -> dict:
    """从对象存储读取 IR JSON，返回解析后的 dict

    ir_runner 只做 dict → workflow；存储读取由 Runner 编排。
    """
    provider = get_storage_provider()
    try:
        ir_json_str = await provider.get_content(ir_path)
    except (StorageConfigError, StorageReadError) as e:
        workflow_logger.error(f"Failed to read IR file from storage: {ir_path}, {e}")
        raise IRBuildException(
            f"Failed to read IR file from storage: {ir_path}, {e}"
        ) from e

    try:
        return json.loads(ir_json_str)
    except json.JSONDecodeError as e:
        workflow_logger.error(f"IR file JSON format error: {ir_path}, {e}")
        raise IRBuildException(f"IR file JSON format error: {ir_path}, {e}") from e


@execution_app.delete("/v1/orchestration/ir/execute")
async def delete_ir_execution_instance(req_json: dict):
    """
    Restful API for delete Agent instance and Workflow instance by executionId.
    """
    # Verifying and preprocessing the user request
    try:
        req = DeleteExecutionInstanceRequest.model_validate(req_json)
    except ValidationError as e:
        raise JiuWenBaseException(
            error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
            message=StatusCode.PARAM_CHECK_FAILED_ERROR.errmsg,
        ) from e
    await AsyncStateManager().delete_state(key=req.conversation_id)
    # 清除 WorkFlow spec缓存
    if req.ir_path:
        await cache_workflow_queue.apop(req.ir_path)
    return {
        "code": StatusCode.SUCCESS.code,
        "message": StatusCode.SUCCESS.errmsg,
    }


@execution_app.post("/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat")
async def chat_n2l(project_id: str, agent_type: str, cid: str, body: N2LRequestBody,
                   request: Request) -> StreamingResponse:
    workflow_logger.debug(
        "NL2 Chat Request - URL: %s %s", request.method, request.url
    )
    workflow_logger.debug(
        "NL2 Chat Request - Headers: %s",
        json.dumps(dict(request.headers), ensure_ascii=False),
    )
    workflow_logger.debug(
        "NL2 Chat Request - Body: %s",
        json.dumps(body.model_dump(exclude_unset=True), ensure_ascii=False),
    )
    # 包装req_json，使得和jiuwen的chat_build接口保持json格式一致
    payload = _n2l_json_wapper(project_id, agent_type, cid, body.model_dump(exclude_unset=True), request)
    # run chat
    chat_response = await _chat(payload)
    return chat_response

# ── Additional Questions (追问) ──────────────────────────────────────
_additional_questions_service: AdditionalQuestionsService | None = None


def _get_additional_questions_service() -> AdditionalQuestionsService:
    global _additional_questions_service
    if _additional_questions_service is None:
        _additional_questions_service = AdditionalQuestionsService()
    return _additional_questions_service


@execution_app.post(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/additional-questions"
)
async def agent_additional_questions(
    project_id: str,
    agent_id: str,
    conversation_id: str,
    workspace_id: str = Query(...),
    req_json: dict = Body(...),
):
    """自动生成追问（Agent 场景）。"""
    ctx = AdditionalQuestionsContext(
        resource_type="agent",
        resource_id=agent_id,
        project_id=project_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )
    return await _handle_additional_questions(ctx=ctx, req_json=req_json)


@execution_app.post(
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/additional-questions"
)
async def workflow_additional_questions(
    project_id: str,
    workflow_id: str,
    conversation_id: str,
    workspace_id: str = Query(...),
    req_json: dict = Body(...),
):
    """自动生成追问（Workflow 场景）。"""
    ctx = AdditionalQuestionsContext(
        resource_type="workflow",
        resource_id=workflow_id,
        project_id=project_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )
    return await _handle_additional_questions(ctx=ctx, req_json=req_json)


async def _handle_additional_questions(
    ctx: AdditionalQuestionsContext,
    req_json: dict,
):
    """追问接口统一处理入口 — 解析请求、调用 Service、返回响应。"""
    workflow_logger.debug(
        "Additional questions request: resource_type=%s, resource_id=%s, "
        "conversation_id=%s, workspace_id=%s",
        ctx.resource_type, ctx.resource_id, ctx.conversation_id, ctx.workspace_id,
    )
    try:
        req = AdditionalQuestionsRequest.model_validate(req_json)
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "details": str(e)},
        )

    service = _get_additional_questions_service()
    try:
        from agent_runtime.context.request_context import _request_ctx
        req_ctx = _request_ctx.get()
        headers = req_ctx.headers if req_ctx else {}
        result = await service.generate(
            ctx=ctx,
            request=req,
            headers=headers,
        )
        return JSONResponse(content=result.model_dump())
    except JiuWenBaseException as e:
        workflow_logger.error(
            "Additional questions error: code=%s, message=%s",
            e.error_code, e.message,
        )
        return JSONResponse(
            status_code=400,
            content={"code": e.error_code, "message": e.message},
        )
    except Exception as e:
        workflow_logger.error(
            "Unexpected error in additional questions: %s", e, exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "details": str(e)},
        )

