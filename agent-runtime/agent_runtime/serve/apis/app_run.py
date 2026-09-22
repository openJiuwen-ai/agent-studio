# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
App Run API — 试运行接口

提供工作流和智能体的试运行执行端点，将请求转换为 ExecutionRequest 格式后
调用 orchestration.py 的 ir_execute 接口，再通过 EventHandler 封装流式结果。
"""

import os
from dataclasses import dataclass
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
from agent_runtime.schemas.orchestration_mgr import ExecutionRequest
from agent_runtime.serve.error_rsp import build_error_response
from pydantic import ValidationError
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
    load_default_environment_id,
    _SECRET_ENV_KEYS_KEY,
)
from agent_runtime.event_handler.event_handler import EventHandler
from agent_runtime.event_handler.base.conversation import (
    ConversationManager,
)
from agent_runtime.context.request_context import _request_ctx
from fastapi import APIRouter, Depends, Header, Path, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
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

# 对话类接口：默认 SSE 流式，stream=false 时返回非流式 JSON
_STREAMING_RESPONSES_200 = {
    200: {
        "description": "流式响应（Server-Sent Events），stream=false 时返回 JSON。\n"
        "SSE 帧事件（event 字段）枚举：\n"
        "- agent 链路：start、message、agent_node_message、function_call_end、plugin_start、plugin_end、"
        "statistic_data、summary_response、done（终态）\n"
        "- workflow 链路：workflow_started、message、error、exception、workflow_finished、end（终态）\n"
        "注：agent 链路流式终态为 done，workflow 链路终态为 end；内容审核阻断流仅产生 message（拦截话术）与 "
        "done 帧，帧字段为 event/data/executionId/index/createdTime 子集。",
        "content": {
            "text/event-stream": {"schema": {"type": "string"}},
            "application/json": {"schema": {}},
        },
    },
}

# 单节点执行：固定 SSE 流式
_NODE_EXECUTE_RESPONSES_200 = {
    200: {
        "description": "流式响应（Server-Sent Events）",
        "content": {
            "text/event-stream": {"schema": {"type": "string"}},
        },
    },
}


@dataclass
class WorkflowRunPathParams:
    """工作流对话接口 path 参数封装."""

    project_id: str
    workflow_id: str
    conversation_id: str

    @classmethod
    async def as_dependency(
        cls,
        project_id: str = Path(..., description="项目ID"),
        workflow_id: str = Path(..., description="工作流ID"),
        conversation_id: str = Path(..., description="会话ID"),
    ) -> "WorkflowRunPathParams":
        return cls(project_id=project_id, workflow_id=workflow_id, conversation_id=conversation_id)


@dataclass
class WorkflowRunQueryParams:
    """工作流对话接口 query 参数封装."""

    version: Optional[str] = None
    environment_id: Optional[str] = None
    workspace_id: Optional[str] = None

    @classmethod
    async def as_dependency(
        cls,
        version: Optional[str] = Query(default=None, description="发布版本号"),
        environment_id: Optional[str] = Query(default=None, description="环境ID"),
        workspace_id: Optional[str] = Query(default=None, description="工作空间ID"),
    ) -> "WorkflowRunQueryParams":
        return cls(version=version, environment_id=environment_id, workspace_id=workspace_id)


@dataclass
class WorkflowRunParams:
    """工作流对话接口路由参数（path + query + stream header）封装."""

    project_id: str
    workflow_id: str
    conversation_id: str
    version: Optional[str] = None
    environment_id: Optional[str] = None
    workspace_id: Optional[str] = None
    stream: str = "true"

    @classmethod
    async def as_dependency(
        cls,
        path: WorkflowRunPathParams = Depends(WorkflowRunPathParams.as_dependency),
        query: WorkflowRunQueryParams = Depends(WorkflowRunQueryParams.as_dependency),
        stream: str = Header(default="true", description="是否流式响应"),
    ) -> "WorkflowRunParams":
        return cls(
            project_id=path.project_id,
            workflow_id=path.workflow_id,
            conversation_id=path.conversation_id,
            version=query.version,
            environment_id=query.environment_id,
            workspace_id=query.workspace_id,
            stream=stream,
        )


@dataclass
class AgentRunPathParams:
    """智能体对话接口 path 参数封装."""

    project_id: str
    agent_id: str
    conversation_id: str

    @classmethod
    async def as_dependency(
        cls,
        project_id: str = Path(..., description="项目ID"),
        agent_id: str = Path(..., description="智能体ID"),
        conversation_id: str = Path(..., description="会话ID"),
    ) -> "AgentRunPathParams":
        return cls(project_id=project_id, agent_id=agent_id, conversation_id=conversation_id)


@dataclass
class AgentRunQueryParams:
    """智能体对话接口 query 参数封装."""

    version: Optional[str] = None
    environment_id: Optional[str] = None
    workspace_id: Optional[str] = None

    @classmethod
    async def as_dependency(
        cls,
        version: Optional[str] = Query(default=None, description="发布版本号"),
        environment_id: Optional[str] = Query(default=None, description="环境ID"),
        workspace_id: Optional[str] = Query(default=None, description="工作空间ID"),
    ) -> "AgentRunQueryParams":
        return cls(version=version, environment_id=environment_id, workspace_id=workspace_id)


@dataclass
class AgentRunParams:
    """智能体对话接口路由参数（path + query + stream header）封装."""

    project_id: str
    agent_id: str
    conversation_id: str
    version: Optional[str] = None
    environment_id: Optional[str] = None
    workspace_id: Optional[str] = None
    stream: str = "true"

    @classmethod
    async def as_dependency(
        cls,
        path: AgentRunPathParams = Depends(AgentRunPathParams.as_dependency),
        query: AgentRunQueryParams = Depends(AgentRunQueryParams.as_dependency),
        stream: str = Header(default="true", description="是否流式响应"),
    ) -> "AgentRunParams":
        return cls(
            project_id=path.project_id,
            agent_id=path.agent_id,
            conversation_id=path.conversation_id,
            version=query.version,
            environment_id=query.environment_id,
            workspace_id=query.workspace_id,
            stream=stream,
        )


@dataclass
class NodeRunParams:
    """单节点执行接口路由参数（path）封装."""

    project_id: str
    workflow_id: str
    conversation_id: str
    node_id: str

    @classmethod
    async def as_dependency(
        cls,
        project_id: str = Path(..., description="项目ID"),
        workflow_id: str = Path(..., description="工作流ID"),
        conversation_id: str = Path(..., description="会话ID"),
        node_id: str = Path(..., description="节点ID"),
    ) -> "NodeRunParams":
        return cls(
            project_id=project_id,
            workflow_id=workflow_id,
            conversation_id=conversation_id,
            node_id=node_id,
        )


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


def _long_term_memory_params(long_term_memory: Optional[dict]) -> dict:
    """前端 long_term_memory（enable_retrieve/enable_extract）→ ExecutionParams 别名键。

    必须写别名键 enableMemoryRetrieve/enableMemoryExtract：params 会被
    ExecutionParams（按 alias 构造）校验，其余键名会被 pydantic 静默丢弃。
    memory_repo_id 不映射：workflow_runner/controller_runner 回退读 IR
    configs.memory.memory_repo_id（Java Adapter 写入）。
    """
    ltm = long_term_memory or {}
    return {
        "enableMemoryRetrieve": bool(ltm.get("enable_retrieve", False)),
        "enableMemoryExtract": bool(ltm.get("enable_extract", False)),
    }


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
        **_long_term_memory_params(body.long_term_memory),
    }
    # Pass long_term_memory config (enable_memory_retrieve/extract + memory_repo_id)
    # to runtime params so the workflow runner can trigger memory retrieval/extraction.
    if body.long_term_memory:
        ltm = body.long_term_memory
        params["enableMemoryRetrieve"] = ltm.get("enable_retrieve", False)
        params["enableMemoryExtract"] = ltm.get("enable_extract", False)
        if ltm.get("memory_repo_id"):
            params["memoryRepoId"] = ltm["memory_repo_id"]
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
        **_long_term_memory_params(body.long_term_memory),
    }
    # Pass long_term_memory config (enable_memory_retrieve/extract + memory_repo_id)
    if body.long_term_memory:
        ltm = body.long_term_memory
        params["enableMemoryRetrieve"] = ltm.get("enable_retrieve", False)
        params["enableMemoryExtract"] = ltm.get("enable_extract", False)
        if ltm.get("memory_repo_id"):
            params["memoryRepoId"] = ltm["memory_repo_id"]
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


async def _resolve_env_scope(
    project_id: Optional[str],
    environment_id: Optional[str],
    workspace_id: Optional[str],
    ir_path: str,
) -> tuple[Optional[str], Optional[str]]:
    """兜底解析环境作用域：直连 runtime 未传 environment_id / workspace_id 时补齐。

    - environment_id 缺省 → 从 Redis 读项目默认环境（manager 环境管理侧维护，
      key: project:{projectId}:default_environment）
    - workspace_id 缺省 → 从 IR metadata.workspaceId 取（工作流/智能体归属空间）

    读不到时保持原值（None），由调用方按现状降级（占位符解析失败报错），
    不借用其它项目/其它空间的变量，也不新增异常路径。

    Returns:
        (environment_id, workspace_id) 兜底后的二元组。
    """
    resolved_env_id = environment_id
    if not resolved_env_id:
        resolved_env_id = await load_default_environment_id(project_id)

    resolved_ws_id = workspace_id
    if not resolved_ws_id:
        try:
            ir_json = await async_ir_load(ir_path)
            ir_ws_id = (ir_json.get("metadata") or {}).get("workspaceId")
            if ir_ws_id:
                resolved_ws_id = str(ir_ws_id)
        except Exception as e:
            workflow_logger.debug(f"Failed to load workspace id from IR: {ir_path}, error: {e}")

    return resolved_env_id, resolved_ws_id


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
    stream_header: str = "true",
    resolve_env: bool = True,
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

    # environment_id / workspace_id 兜底：仅直连入口启用（resolve_env=True）。
    # 网页入口（run_web_workflow）传 resolve_env=False，environment_id 是否注入由
    # manager 决定（无鉴权，请求 workspace 不可信），避免用请求 workspace 拼接默认
    # 环境加载变量造成跨空间变量外流。
    if resolve_env:
        environment_id, workspace_id = await _resolve_env_scope(
            ctx.project_id, ctx.environment_id, ctx.workspace_id, ir_path,
        )
        if environment_id != ctx.environment_id or workspace_id != ctx.workspace_id:
            workflow_logger.info(
                "Resolved env scope for workflow run: project=%s, environment=%s->%s, workspace=%s->%s",
                ctx.project_id, ctx.environment_id, environment_id, ctx.workspace_id, workspace_id,
            )
    else:
        environment_id = ctx.environment_id
        workspace_id = ctx.workspace_id

    instance_id = ctx.workflow_id
    user_id = _request_ctx.get().user_id
    version_id = resolved_version or ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    request.state.instance_id = instance_id
    # 入口类型标注（cancel 响应按此选择回显 key：workflow_id/agent_id）
    request.state.entry_type = "workflow"
    # 注册 project 与 cancel 路径校验同口径（路径值）：stream_response 注册时优先取，
    # 避免 token 解析的 project 与路径不一致导致合法取消被误判 403
    request.state.project_id = ctx.project_id
    # 请求级 enable_history 透传给 EventHandler，落库补写本轮 query 时保持标志位
    request.state.enable_history = body.enable_history

    # body已携带会话历史时跳过Redis加载
    if body.messages:
        conversation_history = [msg.model_dump(by_alias=True) for msg in body.messages]
        dialogue_count = 1
    else:
        conversation_history, dialogue_count = await _load_conversation_data(
            ctx.conversation_id, instance_id, user_id, version_id
        )

    # 从请求头读取stream参数，默认为True
    stream = stream_header.lower() == "true"

    exec_ctx = ExecutionContext(
        conversation_id=ctx.conversation_id,
        ir_path=ir_path,
        conversation_history=conversation_history,
        dialogue_count=dialogue_count,
        user_id=user_id,
    )

    # 根据 environment_id 从 Redis 加载环境变量
    env_vars = await load_environment_variables(
        environment_id, workspace_id,
    )
    # 写入请求上下文，供 StudioModelClient 解析 apiUrl 中的 ${_env.plugin_url_params.VAR} 占位符
    _request_ctx.get().env_variables = env_vars
    req_json = build_req_json_from_workflow(body, exec_ctx, env_vars=env_vars)

    try:
        request_model = ExecutionRequest.model_validate(req_json)
    except ValidationError as e:
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        return build_error_response(400, "02001003", language=language, reason=str(e))

    response = await ir_execute(request_model, request)

    # 工作流固定使用 workflow handler_type
    if stream:
        return await _encapsulate_stream_response(
            response, IRType.Workflow.value, request, ir_path, query
        )
    return await _encapsulate_non_stream_response(
        response, IRType.Workflow.value, request, ir_path, query
    )


@app_run_app.post(
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}",
    summary="工作流对话",
    description="通过 workflow_id 和 conversation_id 发起工作流对话（流式响应）。"
                "设置请求头 stream=false 可切换为非流式响应。"
                "version=latest 时使用最新发布版本的 IR。",
    responses=_STREAMING_RESPONSES_200,
)
async def run_workflow_app(
    body: WorkflowAppRunRequest,
    request: Request,
    params: WorkflowRunParams = Depends(WorkflowRunParams.as_dependency),
):
    """工作流试运行接口"""
    ctx = WorkflowRunContext(
        project_id=params.project_id,
        workflow_id=params.workflow_id,
        conversation_id=params.conversation_id,
        version=params.version,
        environment_id=params.environment_id,
        workspace_id=params.workspace_id,
    )
    return await _execute_workflow_run(ctx, body, request, params.stream)


async def _execute_agent_run(
    ctx: AgentRunContext,
    body: AgentAppRunRequest,
    request: Request,
    stream_header: str = "true",
    resolve_env: bool = True,
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

    # environment_id / workspace_id 兜底：仅直连入口启用（resolve_env=True）。
    # 网页入口（run_web_agent）传 resolve_env=False，environment_id 是否注入由
    # manager 决定（无鉴权，请求 workspace 不可信），避免用请求 workspace 拼接默认
    # 环境加载变量造成跨空间变量外流。
    if resolve_env:
        environment_id, workspace_id = await _resolve_env_scope(
            ctx.project_id, ctx.environment_id, ctx.workspace_id, ir_path,
        )
        if environment_id != ctx.environment_id or workspace_id != ctx.workspace_id:
            workflow_logger.info(
                "Resolved env scope for agent run: project=%s, environment=%s->%s, workspace=%s->%s",
                ctx.project_id, ctx.environment_id, environment_id, ctx.workspace_id, workspace_id,
            )
    else:
        environment_id = ctx.environment_id
        workspace_id = ctx.workspace_id

    instance_id = ctx.agent_id
    user_id = _request_ctx.get().user_id
    version_id = resolved_version or ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    request.state.instance_id = instance_id
    # 入口类型标注（cancel 响应按此选择回显 key：workflow_id/agent_id）
    request.state.entry_type = "agent"
    # 注册 project 与 cancel 路径校验同口径（路径值）：stream_response 注册时优先取，
    # 避免 token 解析的 project 与路径不一致导致合法取消被误判 403
    request.state.project_id = ctx.project_id
    # 请求级 enable_history 透传给 EventHandler，落库补写本轮 query 时保持标志位
    request.state.enable_history = body.enable_history

    # body已携带会话历史时跳过Redis加载
    if body.histories:
        conversation_history = [msg.model_dump(by_alias=True) for msg in body.histories]
        dialogue_count = 1
    else:
        conversation_history, dialogue_count = await _load_conversation_data(
            ctx.conversation_id, instance_id, user_id, version_id
        )

    # 从请求头读取stream参数，默认为True
    stream = stream_header.lower() == "true"

    exec_ctx = ExecutionContext(
        conversation_id=ctx.conversation_id,
        ir_path=ir_path,
        conversation_history=conversation_history,
        dialogue_count=dialogue_count,
        user_id=user_id,
    )

    # 根据 environment_id 从 Redis 加载环境变量
    env_vars = await load_environment_variables(
        environment_id, workspace_id,
    )
    # 写入请求上下文，供 StudioModelClient 解析 apiUrl 中的 ${_env.plugin_url_params.VAR} 占位符
    _request_ctx.get().env_variables = env_vars
    req_json = build_req_json_from_agent(body, exec_ctx, env_vars=env_vars)

    try:
        request_model = ExecutionRequest.model_validate(req_json)
    except ValidationError as e:
        language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
        return build_error_response(400, "02001003", language=language, reason=str(e))

    response = await ir_execute(request_model, request)

    # 从IR中确定handler_type
    try:
        handler_type = await _resolve_handler_type(ir_path)
    except Exception as e:
        workflow_logger.error(f"Failed to resolve handler type from IR: {ir_path}, error: {e}")
        raise JiuWenBaseException(
            error_code=StatusCode.IR_DATA_JSON_LOAD_FAILED.code,
            message=f"resolve handler type failed: {e}",
        ) from e

    if stream:
        return await _encapsulate_stream_response(
            response, handler_type, request, ir_path, query
        )
    return await _encapsulate_non_stream_response(
        response, handler_type, request, ir_path, query
    )


@app_run_app.post(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}",
    summary="智能体对话（单智能体/多智能体）",
    description="通过 agent_id 和 conversation_id 发起智能体对话。"
                "支持单智能体（ReAct）和多智能体（Controller），由 IR 文件的 mode 字段自动决定执行模式。"
                "设置请求头 stream=false 可切换为非流式响应。"
                "version=latest 时使用最新发布版本的 IR。",
    responses=_STREAMING_RESPONSES_200,
)
async def run_agent_app(
    body: AgentAppRunRequest,
    request: Request,
    params: AgentRunParams = Depends(AgentRunParams.as_dependency),
):
    """智能体试运行接口"""
    ctx = AgentRunContext(
        project_id=params.project_id,
        agent_id=params.agent_id,
        conversation_id=params.conversation_id,
        version=params.version,
        environment_id=params.environment_id,
        workspace_id=params.workspace_id,
    )
    return await _execute_agent_run(ctx, body, request, params.stream)


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
    # 注：单节点执行走 component_debug_execute → debug_stream_response，不经
    # stream_response 注册链路（不落 exec/suspend 快照，cancel 对其无感知），
    # 故此处不标注 entry_type（写入也无消费者）
    # 注册 project 与 cancel 路径校验同口径（路径值）：stream_response 注册时优先取，
    # 避免 token 解析的 project 与路径不一致导致合法取消被误判 403
    request.state.project_id = ctx.project_id

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
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/node_execute/{node_id}",
    summary="工作流单节点执行",
    description="对指定工作流中的单个节点进行独立调试执行，使用开发版 IR（无 version）。"
                "固定 SSE 流式响应，忽略 stream 请求头。",
    responses=_NODE_EXECUTE_RESPONSES_200,
)
async def run_node_execute(
    body: NodeExecuteRequest,
    request: Request,
    params: NodeRunParams = Depends(NodeRunParams.as_dependency),
):
    """工作流单节点执行接口"""
    ctx = NodeRunContext(
        project_id=params.project_id,
        workflow_id=params.workflow_id,
        conversation_id=params.conversation_id,
        node_id=params.node_id,
    )
    return await _execute_node_run(ctx, body, request)

