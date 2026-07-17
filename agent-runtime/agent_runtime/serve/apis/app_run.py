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
)
from agent_runtime.serve.apis.orchestration import ir_execute
from agent_runtime.event_handler.event_handler import EventHandler
from agent_runtime.event_handler.base.conversation import (
    ConversationManager,
)
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from jiuwen.serve.controllers.execution.enum import PlanModeType, IRType
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from openjiuwen.core.common.logging import workflow_logger

app_run_app = APIRouter(tags=["app_run"])

_conv_manager = ConversationManager()


async def _load_conversation_history(
    conversation_id: str, instance_id: str, user_id: str, version_id: str = ""
) -> list:
    """从Redis加载会话历史消息列表."""
    try:
        messages = await _conv_manager.get_latest_messages(
            conversation_id, instance_id, user_id, version_id
        )
        if messages:
            workflow_logger.debug(
                f"Loaded {len(messages)} conversation messages from Redis "
                f"for instance={instance_id}, conversation={conversation_id}"
            )
        return messages or []
    except Exception as e:
        workflow_logger.warning(
            f"Failed to load conversation history from Redis: {e}"
        )
        return []


async def _load_dialogue_count(
    conversation_id: str, instance_id: str, user_id: str, version_id: str = ""
) -> int:
    """从Redis加载对话轮次数."""
    try:
        count = await _conv_manager.get_dialogue_count(
            conversation_id, instance_id, user_id, version_id
        )
        return count
    except Exception as e:
        workflow_logger.warning(
            f"Failed to load dialogue count from Redis: {e}"
        )
        return 1


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
    conversation_id: str,
    ir_path: str,
    conversation_history: list,
    dialogue_count: int,
) -> dict:
    """WorkflowAppRunRequest → ExecutionRequest dict.
    """
    global_vars = {**body.globals}
    if body.memory_inputs:
        global_vars.update(body.memory_inputs)

    # body.messages 非空时优先使用body，否则用Redis加载的历史
    if body.messages:
        history = [msg.model_dump(by_alias=True) for msg in body.messages]
    else:
        history = conversation_history

    params = {
        "globalVariables": global_vars,
        "environmentVariables": body.environment,
        "conversationHistory": history,
        "pluginConfigs": [pc.model_dump(by_alias=True) for pc in (body.plugin_configs or [])],
        "enableHistory": body.enable_history,
        # "long_term_memory"
    }

    return {
        "conversationId": conversation_id,
        "userId": body.user_id or "anonymous",
        "irPath": ir_path,
        "params": params,
        "query": body.inputs.get("query", ""),
        "responseMode": "streaming",
        "dialogueCount": dialogue_count,
    }


def build_req_json_from_agent(
    body: AgentAppRunRequest,
    conversation_id: str,
    ir_path: str,
    conversation_history: list,
    dialogue_count: int,
) -> dict:
    """AgentAppRunRequest → ExecutionRequest dict.
    """
    # body.histories 非空时覆盖Redis历史，否则用Redis加载的
    if body.histories:
        history = [msg.model_dump(by_alias=True) for msg in body.histories]
    else:
        history = conversation_history

    params = {
        "globalVariables": body.inputs,
        "conversationHistory": history,
        "toolSwitchDict": body.tool_switch_dict,
        "files": body.files,
        "enableHistory": body.enable_history,
        # "long_term_memory"
    }

    return {
        "conversationId": conversation_id,
        "userId": body.user_id or "",
        "irPath": ir_path,
        "params": params,
        "query": body.query or body.inputs.get("query", ""),
        "responseMode": "streaming",
        "dialogueCount": dialogue_count,
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


async def _encapsulate_response(
    response,
    handler_type: str,
    request: Request,
    ir_path: str,
    stream: bool = True,
):
    """对 ir_execute 返回的 StreamingResponse 进行事件封装.

    仅处理 StreamingResponse，JSONResponse 直接透传。
    """
    if not isinstance(response, StreamingResponse):
        return response

    if stream:
        return await EventHandler.encapsulate_stream_response(
            response=response,
            handler_type=handler_type,
            request=request,
            ir_path=ir_path,
        )
    else:
        return await EventHandler.encapsulate_non_stream_response(
            response=response,
            handler_type=handler_type,
            request=request,
            ir_path=ir_path,
        )


async def _execute_workflow_run(
    ctx: WorkflowRunContext,
    body: WorkflowAppRunRequest,
    request: Request,
):
    """工作流试运行核心逻辑."""
    workflow_logger.info(
        f"Workflow app run request: project={ctx.project_id}, workflow={ctx.workflow_id}, "
        f"conversation={ctx.conversation_id}, version={ctx.version}"
    )

    ir_path = build_workflow_ir_path(ctx.workflow_id, ctx.version)
    workflow_logger.debug(f"Built IR path: {ir_path}")

    # 从Redis加载会话历史和对话轮次
    instance_id = ctx.workflow_id
    user_id = body.user_id or "anonymous"
    version_id = ctx.version or ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    conversation_history = await _load_conversation_history(
        ctx.conversation_id, instance_id, user_id, version_id
    )
    dialogue_count = await _load_dialogue_count(
        ctx.conversation_id, instance_id, user_id, version_id
    )

    # 从请求头读取stream参数，默认为True
    stream = request.headers.get("stream", "true").lower() == "true"

    req_json = build_req_json_from_workflow(
        body, ctx.conversation_id, ir_path, conversation_history, dialogue_count
    )

    response = await ir_execute(req_json, request)

    # 工作流固定使用 workflow handler_type
    return await _encapsulate_response(
        response, IRType.Workflow.value, request, ir_path, stream
    )


@app_run_app.post(
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}"
)
async def run_workflow_app(
    body: WorkflowAppRunRequest,
    request: Request,
    version: Optional[str] = None,
):
    """工作流试运行接口"""
    # 从路径参数提取上下文
    path_params = request.path_params
    ctx = WorkflowRunContext(
        project_id=path_params["project_id"],
        workflow_id=path_params["workflow_id"],
        conversation_id=path_params["conversation_id"],
        version=version,
    )
    return await _execute_workflow_run(ctx, body, request)


async def _execute_agent_run(
    ctx: AgentRunContext,
    body: AgentAppRunRequest,
    request: Request,
):
    """智能体试运行核心逻辑."""
    workflow_logger.info(
        f"Agent app run request: project={ctx.project_id}, agent={ctx.agent_id}, "
        f"conversation={ctx.conversation_id}, version={ctx.version}"
    )

    if body.agent_type.lower() == "deepresearch":
        return JSONResponse(
            status_code=400,
            content={"error": "DeepResearch mode is not supported"},
        )

    ir_path = build_agent_ir_path(ctx.agent_id, ctx.version)
    workflow_logger.debug(f"Built IR path: {ir_path}")

    # 从Redis加载会话历史和对话轮次
    instance_id = ctx.agent_id
    user_id = body.user_id or ""
    version_id = ctx.version or ""
    request.state.user_id = user_id
    request.state.version_id = version_id
    conversation_history = await _load_conversation_history(
        ctx.conversation_id, instance_id, user_id, version_id
    )
    dialogue_count = await _load_dialogue_count(
        ctx.conversation_id, instance_id, user_id, version_id
    )

    # 从请求头读取stream参数，默认为True
    stream = request.headers.get("stream", "true").lower() == "true"

    req_json = build_req_json_from_agent(
        body, ctx.conversation_id, ir_path, conversation_history, dialogue_count
    )

    response = await ir_execute(req_json, request)

    # 从IR中确定handler_type
    try:
        handler_type = await _resolve_handler_type(ir_path)
    except Exception as e:
        workflow_logger.error(f"Failed to resolve handler type from IR: {ir_path}, error: {e}")
        raise

    return await _encapsulate_response(
        response, handler_type, request, ir_path, stream
    )


@app_run_app.post(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}"
)
async def run_agent_app(
    body: AgentAppRunRequest,
    request: Request,
    version: Optional[str] = None,
):
    """智能体试运行接口"""
    # 从路径参数提取上下文
    path_params = request.path_params
    ctx = AgentRunContext(
        project_id=path_params["project_id"],
        agent_id=path_params["agent_id"],
        conversation_id=path_params["conversation_id"],
        version=version,
    )
    return await _execute_agent_run(ctx, body, request)
