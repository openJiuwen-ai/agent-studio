# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
App Run API — 试运行接口

提供工作流和智能体的试运行执行端点，将请求转换为 ExecutionRequest 格式后
调用 orchestration.py 的 ir_execute 接口，再通过 EventHandler 封装流式结果。
"""

import os
from typing import Optional

from agent_runtime.serve.apis.app_run_request import (
    WorkflowAppRunRequest,
    AgentAppRunRequest,
    WorkflowRunContext,
    AgentRunContext,
    ExecutionContext,
    NodeRunContext,
    NodeExecuteRequest,
)
from agent_runtime.serve.apis.orchestration import ir_execute, component_debug_execute
from agent_runtime.serve.apis.publish_version_cache import (
    LATEST_PUBLISH_VERSION,
    resolve_published_version,
)
from agent_runtime.serve.apis.run_check import (
    RunCheckContext,
    check_before_workflow_run,
    check_before_agent_run,
)
from agent_runtime.common.env_variables_loader import (
    load_environment_variables,
    _SECRET_ENV_KEYS_KEY,
)
from agent_runtime.event_handler.event_handler import EventHandler
from agent_runtime.event_handler.base.conversation import (
    ConversationManager,
)
from agent_runtime.context.request_context import _request_ctx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from jiuwen.serve.controllers.execution.enum import PlanModeType, IRType
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from openjiuwen.core.common.logging import workflow_logger, set_session_id

# USER_MSG_FIELD
_USER_MSG_FIELD = "query"

# 从inputs中排除的系统字段
_AGENT_SYSTEM_INPUTS = {_USER_MSG_FIELD, "workflowSequence", "activeWorkflows", "intent"}

# 文件URL后缀分类
_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff"})
_VIDEO_EXTENSIONS = frozenset({".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"})

app_run_app = APIRouter(tags=["app_run"])

_conv_manager = ConversationManager()


def _get_url_extension(url: str) -> str:
    """从URL中提取文件后缀（去除查询参数后取路径最后一段的后缀）."""
    clean_path = url.split("?")[0]
    filename = clean_path.rsplit("/", 1)[-1]
    dot_idx = filename.rfind(".")
    if dot_idx >= 0:
        return filename[dot_idx:].lower()
    return ""


def process_file_urls(file_urls: list[str]) -> list[dict]:
    """将文件URL字符串列表转换为多模态结构化对象列表.

    对齐Java AgentRuntimeService.extractUrlFromQuery逻辑：
    - 图片URL → {"type": "image_url", "image_url": {"url": "..."}}
    - 视频URL → {"type": "video_url", "video_url": {"url": "..."}}
    - 其他URL忽略
    """
    if not file_urls:
        return []
    media_objs = []
    for url in file_urls:
        ext = _get_url_extension(url)
        if ext in _IMAGE_EXTENSIONS:
            media_objs.append({"type": "image_url", "image_url": {"url": url}})
        elif ext in _VIDEO_EXTENSIONS:
            media_objs.append({"type": "video_url", "video_url": {"url": url}})
        else:
            workflow_logger.warning(f"Unsupported file URL extension: {ext}, url: {url}")
    return media_objs


async def _load_conversation_data(
    conversation_id: str, instance_id: str, user_id: str, version_id: str = ""
) -> tuple[list, int]:
    """从Redis一次加载会话历史和对话轮次.

    Returns:
        (conversation_history, dialogue_count)
    """
    try:
        messages, dialogue_count = await _conv_manager.get_conversation_data(
            conversation_id, instance_id, user_id, version_id
        )
        if messages:
            workflow_logger.debug(
                f"Loaded {len(messages)} conversation messages from Redis "
                f"for instance={instance_id}, conversation={conversation_id}"
            )
        return messages, dialogue_count
    except Exception as e:
        workflow_logger.warning(
            f"Failed to load conversation data from Redis: {e}"
        )
        return [], 1


def build_workflow_ir_path(workflow_id: str, version: Optional[str]) -> str:
    """构造工作流IR存储路径"""
    prefix = os.environ.get("WORKFLOW_IR_OBS_PATH", "workflow/ir")
    if version:
        return f"{prefix}/{workflow_id}/{workflow_id}_{version}.json"
    return f"{prefix}/{workflow_id}/{workflow_id}.json"


def build_agent_ir_path(agent_id: str, version: Optional[str]) -> str:
    """构造智能体IR存储路径"""
    prefix = os.environ.get("AGENT_IR_OBS_PATH", "agent/ir")
    if version:
        return f"{prefix}/{agent_id}/{agent_id}_{version}.json"
    return f"{prefix}/{agent_id}/{agent_id}.json"


def build_req_json_from_workflow(
    body: WorkflowAppRunRequest,
    exec_ctx: ExecutionContext,
    env_vars: dict = None,
) -> dict:
    """WorkflowAppRunRequest → ExecutionRequest dict."""
    global_vars = {**body.inputs}
    if body.memory_inputs:
        global_vars.update(body.memory_inputs)
    global_vars.pop(_USER_MSG_FIELD, None)

    # 环境变量：env_vars（从 Redis 按 environment_id 加载）优先，否则用 body.environment
    environment_variables = env_vars or body.environment
    secret_env_keys = []
    if env_vars and _SECRET_ENV_KEYS_KEY in env_vars:
        secret_env_keys = env_vars.pop(_SECRET_ENV_KEYS_KEY)

    params = {
        "globalVariables": global_vars,
        "environmentVariables": environment_variables,
        "conversationHistory": exec_ctx.conversation_history,
        "pluginConfigs": [pc.model_dump(by_alias=True) for pc in (body.plugin_configs or [])],
        "enableHistory": body.enable_history,
        # "long_term_memory"
    }
    if secret_env_keys:
        params["secretEnvKeys"] = secret_env_keys

    return {
        "conversationId": exec_ctx.conversation_id,
        "userId": exec_ctx.user_id,
        "irPath": exec_ctx.ir_path,
        "params": params,
        "query": body.inputs.get(_USER_MSG_FIELD, ""),
        "responseMode": "streaming",
        "dialogueCount": exec_ctx.dialogue_count,
    }


def build_req_json_from_agent(
    body: AgentAppRunRequest,
    exec_ctx: ExecutionContext,
    env_vars: dict = None,
) -> dict:
    """AgentAppRunRequest → ExecutionRequest dict."""
    global_vars = {k: v for k, v in body.inputs.items() if k not in _AGENT_SYSTEM_INPUTS}

    secret_env_keys = []
    environment_variables = env_vars or {}
    if env_vars and _SECRET_ENV_KEYS_KEY in env_vars:
        secret_env_keys = env_vars.pop(_SECRET_ENV_KEYS_KEY)

    params = {
        "globalVariables": global_vars,
        "conversationHistory": exec_ctx.conversation_history,
        "toolSwitchDict": body.tool_switch_dict,
        "files": process_file_urls(body.files),
        "enableHistory": body.enable_history,
        # "long_term_memory"
    }
    if environment_variables:
        params["environmentVariables"] = environment_variables
    if secret_env_keys:
        params["secretEnvKeys"] = secret_env_keys
    # Controller 参数：从 inputs 中提取，单独写入 params
    intent = body.inputs.get("intent")
    if intent is not None:
        params["intent"] = str(intent)
    workflow_sequence = body.inputs.get("workflowSequence")
    if workflow_sequence is not None:
        params["workflowSequence"] = workflow_sequence
    active_workflows = body.inputs.get("activeWorkflows")
    if active_workflows is not None:
        params["activeWorkflows"] = active_workflows

    return {
        "conversationId": exec_ctx.conversation_id,
        "userId": exec_ctx.user_id,
        "irPath": exec_ctx.ir_path,
        "params": params,
        "query": body.query or body.inputs.get(_USER_MSG_FIELD, ""),
        "resumeInput": body.resume_input,
        "responseMode": "streaming",
        "dialogueCount": exec_ctx.dialogue_count,
    }


async def _resolve_handler_type(ir_path: str) -> str:
    """从IR文件中读取mode，确定handler_type.

    Returns:
        handler_type: "workflow" / "ReAct" / "Controller" / "PlanExecute"

    Raises:
        Exception: IR加载失败时向上抛出，避免静默降级导致事件封装错误
    """
    ir_json = await async_ir_load(ir_path)
    mode = (ir_json.get("configs") or {}).get("mode", "workflow")
    # 映射: mode → handler_type
    mode_to_handler = {
        "workflow": IRType.Workflow.value,
        "react": PlanModeType.ReAct.value,
        "ReAct": PlanModeType.ReAct.value,
        "controller": PlanModeType.Controller.value,
        "Controller": PlanModeType.Controller.value,
        "planexecute": PlanModeType.PlanExecute.value,
        "PlanExecute": PlanModeType.PlanExecute.value,
    }
    return mode_to_handler.get(mode, IRType.Workflow.value)


def _extract_instance_id(ir_path: str) -> str:
    """从IR路径提取instance_id (最后一个/到.json之间的部分)."""
    last_slash_index = ir_path.rfind("/")
    if last_slash_index >= 0:
        remainder = ir_path[last_slash_index + 1:]
    else:
        remainder = ir_path
    if remainder.endswith(".json"):
        remainder = remainder[:-5]
    return remainder


async def _encapsulate_stream_response(
    response,
    handler_type: str,
    request: Request,
    ir_path: str,
    query: str = "",
):
    """对 ir_execute 返回的 StreamingResponse 进行流式事件封装.

    非 StreamingResponse（如 JSONResponse）直接透传。
    """
    if not isinstance(response, StreamingResponse):
        return response
    return await EventHandler.encapsulate_stream_response(
        response=response,
        handler_type=handler_type,
        request=request,
        ir_path=ir_path,
        query=query,
    )


async def _encapsulate_non_stream_response(
    response,
    handler_type: str,
    request: Request,
    ir_path: str,
    query: str = "",
):
    """对 ir_execute 返回的 StreamingResponse 进行非流式事件封装.

    非 StreamingResponse（如 JSONResponse）直接透传。
    """
    if not isinstance(response, StreamingResponse):
        return response
    return await EventHandler.encapsulate_non_stream_response(
        response=response,
        handler_type=handler_type,
        request=request,
        ir_path=ir_path,
        query=query,
    )


async def _execute_workflow_run(
    ctx: WorkflowRunContext,
    body: WorkflowAppRunRequest,
    request: Request,
):
    """工作流试运行核心逻辑."""
    # 中间件在路由匹配前执行、拿不到 path_params，trace_id 会回退成 execution_id；
    # 此处路由已匹配、ctx.conversation_id 已从 path 取到，覆盖日志上下文使日志按会话可追踪
    set_session_id(ctx.conversation_id or getattr(request.state, "execution_id", "") or "")
    workflow_logger.info(
        f"Workflow app run request: project={ctx.project_id}, workflow={ctx.workflow_id}, "
        f"conversation={ctx.conversation_id}, version={ctx.version}"
    )

    # version=latest 时从发布缓存解析实际版本号
    resolved_version = await resolve_published_version(ctx.workflow_id, ctx.version)
    if ctx.version == LATEST_PUBLISH_VERSION and resolved_version is None:
        workflow_logger.error(
            "Failed to resolve latest publish version: workflow_id=%s",
            ctx.workflow_id,
        )
        return JSONResponse(
            status_code=400,
            content={"error": "use latest publish version need republish first"},
        )

    ir_path = build_workflow_ir_path(ctx.workflow_id, resolved_version)
    workflow_logger.debug(f"Built IR path: {ir_path}")

    # 运行前校验
    query = body.inputs.get("query", "")
    err = await check_before_workflow_run(RunCheckContext(
        query=query,
        project_id=ctx.project_id,
        ir_path=ir_path,
        body_version=body.version,
        has_published_version=resolved_version is not None,
        request=request,
    ))
    if err:
        return err

    instance_id = ctx.workflow_id
    user_id = _request_ctx.get().user_id
    version_id = resolved_version or ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    request.state.instance_id = instance_id

    # body已携带会话历史时跳过Redis加载
    if body.messages:
        conversation_history = [msg.model_dump(by_alias=True) for msg in body.messages]
        dialogue_count = 1
    else:
        conversation_history, dialogue_count = await _load_conversation_data(
            ctx.conversation_id, instance_id, user_id, version_id
        )

    # 从请求头读取stream参数，默认为True
    stream = request.headers.get("stream", "true").lower() == "true"

    exec_ctx = ExecutionContext(
        conversation_id=ctx.conversation_id,
        ir_path=ir_path,
        conversation_history=conversation_history,
        dialogue_count=dialogue_count,
        user_id=user_id,
    )

    # 根据 environment_id 从 Redis 加载环境变量
    env_vars = await load_environment_variables(
        ctx.environment_id, ctx.workspace_id,
    )
    req_json = build_req_json_from_workflow(body, exec_ctx, env_vars=env_vars)

    response = await ir_execute(req_json, request)

    # 工作流固定使用 workflow handler_type
    if stream:
        return await _encapsulate_stream_response(
            response, IRType.Workflow.value, request, ir_path, query
        )
    return await _encapsulate_non_stream_response(
        response, IRType.Workflow.value, request, ir_path, query
    )


@app_run_app.post(
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}"
)
async def run_workflow_app(
    body: WorkflowAppRunRequest,
    request: Request,
    version: Optional[str] = None,
    environment_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
):
    """工作流试运行接口"""
    # 从路径参数提取上下文
    path_params = request.path_params
    ctx = WorkflowRunContext(
        project_id=path_params["project_id"],
        workflow_id=path_params["workflow_id"],
        conversation_id=path_params["conversation_id"],
        version=version,
        environment_id=environment_id,
        workspace_id=workspace_id,
    )
    return await _execute_workflow_run(ctx, body, request)


async def _execute_agent_run(
    ctx: AgentRunContext,
    body: AgentAppRunRequest,
    request: Request,
):
    """智能体试运行核心逻辑."""
    # 同 _execute_workflow_run：路由匹配后用 path 的 conversation_id 覆盖 trace_id
    set_session_id(ctx.conversation_id or getattr(request.state, "execution_id", "") or "")
    workflow_logger.info(
        f"Agent app run request: project={ctx.project_id}, agent={ctx.agent_id}, "
        f"conversation={ctx.conversation_id}, version={ctx.version}"
    )

    if body.agent_type.lower() == "deepresearch":
        return JSONResponse(
            status_code=400,
            content={"error": "DeepResearch mode is not supported"},
        )

    # version=latest 时从发布缓存解析实际版本号
    resolved_version = await resolve_published_version(ctx.agent_id, ctx.version)
    if ctx.version == LATEST_PUBLISH_VERSION and resolved_version is None:
        workflow_logger.error(
            "Failed to resolve latest publish version: agent_id=%s",
            ctx.agent_id,
        )
        return JSONResponse(
            status_code=400,
            content={"error": "use latest publish version need republish first"},
        )

    ir_path = build_agent_ir_path(ctx.agent_id, resolved_version)
    workflow_logger.debug(f"Built IR path: {ir_path}")

    # 运行前校验
    query = body.resume_input or body.query or body.inputs.get("query", "")
    err = await check_before_agent_run(RunCheckContext(
        query=query,
        project_id=ctx.project_id,
        ir_path=ir_path,
        body_version=body.version,
        has_published_version=resolved_version is not None,
        request=request,
    ))
    if err:
        return err

    instance_id = ctx.agent_id
    user_id = _request_ctx.get().user_id
    version_id = resolved_version or ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    request.state.instance_id = instance_id

    # body已携带会话历史时跳过Redis加载
    if body.histories:
        conversation_history = [msg.model_dump(by_alias=True) for msg in body.histories]
        dialogue_count = 1
    else:
        conversation_history, dialogue_count = await _load_conversation_data(
            ctx.conversation_id, instance_id, user_id, version_id
        )

    # 从请求头读取stream参数，默认为True
    stream = request.headers.get("stream", "true").lower() == "true"

    exec_ctx = ExecutionContext(
        conversation_id=ctx.conversation_id,
        ir_path=ir_path,
        conversation_history=conversation_history,
        dialogue_count=dialogue_count,
        user_id=user_id,
    )

    # 根据 environment_id 从 Redis 加载环境变量
    env_vars = await load_environment_variables(
        ctx.environment_id, ctx.workspace_id,
    )
    req_json = build_req_json_from_agent(body, exec_ctx, env_vars=env_vars)

    response = await ir_execute(req_json, request)

    # 从IR中确定handler_type
    try:
        handler_type = await _resolve_handler_type(ir_path)
    except Exception as e:
        workflow_logger.error(f"Failed to resolve handler type from IR: {ir_path}, error: {e}")
        raise

    if stream:
        return await _encapsulate_stream_response(
            response, handler_type, request, ir_path, query
        )
    return await _encapsulate_non_stream_response(
        response, handler_type, request, ir_path, query
    )


@app_run_app.post(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}"
)
async def run_agent_app(
    body: AgentAppRunRequest,
    request: Request,
    version: Optional[str] = None,
    environment_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
):
    """智能体试运行接口"""
    # 从路径参数提取上下文
    path_params = request.path_params
    ctx = AgentRunContext(
        project_id=path_params["project_id"],
        agent_id=path_params["agent_id"],
        conversation_id=path_params["conversation_id"],
        version=version,
        environment_id=environment_id,
        workspace_id=workspace_id,
    )
    return await _execute_agent_run(ctx, body, request)


async def _execute_node_run(
    ctx: NodeRunContext,
    body: NodeExecuteRequest,
    request: Request,
):
    """工作流单节点执行核心逻辑."""
    workflow_logger.info(
        f"Node execute request: project={ctx.project_id}, workflow={ctx.workflow_id}, "
        f"conversation={ctx.conversation_id}, node={ctx.node_id}"
    )

    # 单节点执行使用开发版IR（无version）
    ir_path = build_workflow_ir_path(ctx.workflow_id, None)
    workflow_logger.debug(f"Built IR path: {ir_path}")

    instance_id = ctx.workflow_id
    # Profile 启用时使用 ctx.user_id（effective userId，不让 body 优先）
    from common_utils.customer_header import get_config
    if get_config().enabled:
        user_id = _request_ctx.get().user_id
    else:
        user_id = body.user_id or _request_ctx.get().user_id
    version_id = ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    request.state.instance_id = instance_id

    # 加载会话历史
    conversation_history, dialogue_count = await _load_conversation_data(
        ctx.conversation_id, instance_id, user_id, version_id
    )

    # 构建 ComponentDebugRequest dict
    params = {
        "conversationHistory": conversation_history,
        "pluginConfigs": [pc.model_dump(by_alias=True) for pc in (body.plugin_configs or [])],
        "globalVariables": body.inputs,
    }

    req_json = {
        "conversationId": ctx.conversation_id,
        "userId": user_id,
        "irPath": ir_path,
        "inputs": body.inputs,
        "params": params,
    }

    # 调用底层 component execute
    response = await component_debug_execute(ctx.node_id, req_json, request)

    # 单节点执行固定 workflow handler_type，始终流式
    if isinstance(response, StreamingResponse):
        return await EventHandler.encapsulate_stream_response(
            response=response,
            handler_type=IRType.Workflow.value,
            request=request,
            ir_path=ir_path,
        )
    return response


@app_run_app.post(
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/node_execute/{node_id}"
)
async def run_node_execute(
    body: NodeExecuteRequest,
    request: Request,
):
    """工作流单节点执行接口"""
    path_params = request.path_params
    ctx = NodeRunContext(
        project_id=path_params["project_id"],
        workflow_id=path_params["workflow_id"],
        conversation_id=path_params["conversation_id"],
        node_id=path_params["node_id"],
    )
    return await _execute_node_run(ctx, body, request)

