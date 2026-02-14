from typing import Any, Optional, Dict, AsyncGenerator, Union
from pydantic import ValidationError

from fastapi import APIRouter, HTTPException, Request, status, Depends
from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen.core.common.logging import logger, set_session_id, get_session_id
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse

from openjiuwen_studio.core.executor.agent.agent_runner import agent_mgr, AgentRunner
from openjiuwen_studio.core.executor.component.component_runner import comp_executor
from openjiuwen_studio.core.executor.workflow.pregel_graph_adapter import JiuWenGraphException
from openjiuwen_studio.core.executor.workflow.workflow_runner import flow_mgr, WorkflowRunner
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.utils.exception import log_exception, handle_http_exception, get_safe_error_message
from openjiuwen_studio.schemas import ResponseModel
from openjiuwen_studio.core.executor.plugin.plugin_mgr import plugin_mgr
from openjiuwen_studio.routers.common import handle_response, validate_request
from openjiuwen_studio.core.manager.repositories.trace_summary_repository import trace_summary_repository
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.schemas.trace_summary import (TraceSummaryListRequest, TraceSummaryByTraceIdRequest,
                                       TraceSummaryLatestRequest, TraceSummaryBrief)
from openjiuwen_studio.schemas.execution_log import ExecutionLogSummary
from openjiuwen_studio.schemas.memory import DeleteLongtermMem, DeleteVariable, UpdateLongtermMem, UpdateVariable, \
    GetUserVar, \
    SearchLongtermMem, DeleteScopeLongtermMem
from openjiuwen_studio.core.manager.memory import delete_user_variable, delete_longterm_mem, update_user_variable, \
    update_longterm_mem, get_longterm_mem, get_user_variable, delete_longterm_mem_by_scope_id

from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException, WorkflowFailedResponse, WorkflowErrorData, ErrorNodeInfo
from openjiuwen_studio.core.common.exceptions import JiuWenComponentException
from openjiuwen_studio.core.common.message import ExecuteResponseType
from openjiuwen_studio.core.executor.workflow.workflow_execution_manager import workflow_execution_manager
from openjiuwen_studio.core.executor.component.component_execution_manager import component_execution_manager
from openjiuwen_studio.core.common.language_thread_context import get_language
from openjiuwen.core.common.exception.codes import StatusCode

execution_router = APIRouter()


def _normalize_language(language: Optional[str]) -> str:
    if not language:
        return "zh"
    language = language.strip().lower()
    if language in {"cn", "zh", "zh-cn", "zh-hans", "zh-hans-cn"} or language.startswith("zh"):
        return "zh"
    return "en"


def _resolve_language(current_user: Optional[dict]) -> str:
    """
    解析当前语言。
    策略：倾向于英文 (Sticky English)。
    1. 如果 HTTP Header 指定了英文，返回英文。
    2. 如果用户配置 (Profile) 指定了英文，返回英文。
    3. 否则返回中文。
    """
    # 1. 检查 Header
    language = get_language()
    header_lang = None
    if language and language.strip().lower() not in {"cn"}:
        header_lang = _normalize_language(language)
        if header_lang == "en":
            return "en"

    # 2. 检查用户配置
    if current_user:
        locale = (current_user.get("data") or {}).get("locale")
        if locale:
            user_lang = _normalize_language(locale)
            if user_lang == "en":
                return "en"

    # 3. 默认中文
    return "zh"


class BaseParas(BaseModel):
    space_id: Optional[str] = Field("")
    id: str = Field(default="", description="Unique agent ID")
    version: str = Field(default="", description="Version of the agent")
    conversation_id: str = Field(default="", description="Conversation ID")


class ExecuteParas(BaseParas):
    inputs: Dict[str, Any] = Field(default={}, description="Input parameters")


class DeepSearchParas(BaseModel):
    search_type: str = Field(default="", description="Search type: search or research")
    query: str = Field(description="Query content")


class CompExecuteParas(ExecuteParas):
    component_id: str = Field(default="", description="Component ID")
    loop_id: str = Field(default="", description="Loop component ID")


class UserInput(BaseModel):
    node_id: str = Field(default="", description="Node ID")
    input_value: Any = Field(default="", description="Input value")


class PluginExecuteParas(ExecuteParas):
    plugin_id: str = Field(default="", description="Plugin id")
    tool_id: str = Field(default="", description="Tool id")


class UserInputParas(BaseParas):
    inputs: UserInput = Field(default={}, description="Input parameters")


def get_error_info_in_wf_trace(mgr, chunk):
    code = status.HTTP_200_OK
    message = "Executed successfully"

    if isinstance(mgr, WorkflowRunner) and chunk.get("type") == ExecuteResponseType.Trace.value:
        error_info = chunk.get("payload", {}).get("error")
        if isinstance(error_info, dict) and error_info:
            error_code = error_info.get("error_code")
            if error_code:
                code = error_code
                message = error_info.get("message")

    return code, message


async def handler(
    request_body: Union[ExecuteParas, UserInputParas],
    request: Request,
    mgr: Union[AgentRunner, WorkflowRunner],
    current_user: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    try:
        logger.info(f"in execute: {request_body}, {current_user}")
        if isinstance(request_body.inputs, UserInput):
            inputs = InteractiveInput()
            inputs.update(request_body.inputs.node_id, request_body.inputs.input_value)
        else:
            inputs = request_body.inputs

        session_id = " ".join(
            [
                id_val.strip()
                for id_val in [request_body.space_id, request_body.conversation_id, get_session_id()]
                if id_val and id_val.strip()
            ]
        )
        if session_id:
            set_session_id(session_id)

        async for chunk in mgr.run(request_body.id, request_body.version, inputs,
                                   request_body.conversation_id, request_body.space_id, current_user):
            if await request.is_disconnected():
                raise HTTPException(status_code=404, detail="Disconnected")
            logger.debug(f"Received chunk: {chunk}")
            code, message = get_error_info_in_wf_trace(mgr, chunk)
            yield ResponseModel(
                code=code,
                message=message,
                data=chunk
            ).model_dump_json()
    except JiuWenExecuteException as e:
        log_exception(e)
        error_node_info = ErrorNodeInfo(error_code=e.code, error_message=e.message,
                                        node_id=e.node_id, connection=e.connection)
        data = WorkflowErrorData(workflow_id=e.workflow_id, error_nodes_info=[error_node_info])
        yield WorkflowFailedResponse(data=data, code=e.code, message=e.message).model_dump_json()
    except JiuWenGraphException as e:
        log_exception(e)
        yield ResponseModel(
            code=e.code,
            message=e.message,
            data=None
        ).model_dump_json()
    except JiuWenComponentException as e:
        log_exception(e)
        yield ResponseModel(
            code=e.code,
            message=e.message,
            data={
                "component_id": e.component_id,
                "component_type": e.component_type,
                "error_stage": e.error_stage
            }
        ).model_dump_json()
    except BaseError as e:
        log_exception(e)
        message = e.message
        if e.code == StatusCode.AGENT_TOOL_NOT_FOUND.code:
            lang = _resolve_language(current_user)
            if lang == "zh":
                error_msg = e.params.get("error_msg", "") if e.params else ""
                if not error_msg and "reason: " in message:
                    try:
                        error_msg = message.split("reason: ", 1)[1]
                    except IndexError:
                        pass
                message = f"智能体工具未找到，原因: {error_msg}"

        yield ResponseModel(
            code=e.code,
            message=message,
            data=None
        ).model_dump_json()
    except Exception as e:
        log_exception(e)
        safe_message = get_safe_error_message(e)
        yield ResponseModel(
            code=-1,
            message=safe_message,
            data=None
        ).model_dump_json()


@execution_router.post("/agent", response_model=ResponseModel[dict])
async def execute_agent(
    request_body: ExecuteParas,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EventSourceResponse:
    """Run an agent"""
    try:
        return EventSourceResponse(handler(request_body, request, agent_mgr, current_user))
    except HTTPException:
        raise
    except Exception as e:
        raise handle_http_exception(e, "Agent execution failed") from e


@execution_router.post("/workflow", response_model=ResponseModel[dict])
async def execute_workflow(
    request_body: ExecuteParas,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EventSourceResponse:
    """Run a workflow"""
    try:
        return EventSourceResponse(handler(request_body, request, flow_mgr, current_user))
    except HTTPException:
        raise
    except Exception as e:
        raise handle_http_exception(e, "Workflow execution failed") from e


@execution_router.post("/userInput", response_model=ResponseModel[dict])
async def handle_workflow_user_input(
    request_body: UserInputParas,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EventSourceResponse:
    """handle workflow user input"""
    try:
        return EventSourceResponse(handler(request_body, request, flow_mgr, current_user))
    except HTTPException:
        raise
    except Exception as e:
        raise handle_http_exception(e, "Failed to process workflow user input") from e


@execution_router.post("/agent/userInput", response_model=ResponseModel[dict])
async def handle_agent_user_input(
    request_body: UserInputParas,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EventSourceResponse:
    """handle agent user input"""
    try:
        return EventSourceResponse(handler(request_body, request, agent_mgr, current_user))
    except HTTPException:
        raise
    except Exception as e:
        raise handle_http_exception(e, "Failed to process agent user input") from e


@execution_router.post("/component", response_model=ResponseModel[dict])
async def execute_component(
    request_body: CompExecuteParas,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    """Run a single component"""
    try:
        if isinstance(request_body.inputs, UserInput):
            inputs = InteractiveInput()
            inputs.update(request_body.inputs.node_id, request_body.inputs.input_value)
        else:
            inputs = request_body.inputs
        logger.info(f"request_body: {request_body}")

        result = await comp_executor.run(request_body.id, request_body.version, inputs, request_body.component_id,
                                         request_body.space_id, current_user, request_body.loop_id,
                                         request_body.conversation_id)
        logger.info(f"Received result: {result}")
        return ResponseModel(
            code=status.HTTP_200_OK, message="Component Executed successfully", data=result
        )
    except JiuWenComponentException as e:
        log_exception(e)
        return ResponseModel(
            code=e.code, message=e.message,
            data={"type": "node", "payload": {"output": {"result": e.message, "is_success": False}}}
        )
    except JiuWenGraphException as e:
        log_exception(e)
        return ResponseModel(
            code=e.code, message=e.message,
            data={"type": "node", "payload": {"output": {"result": e.message, "is_success": False}}}
        )
    except BaseError as e:
        log_exception(e)
        return ResponseModel(
            code=e.code, message=e.message,
            data={"type": "node", "payload": {"output": {"result": e.message, "is_success": False}}}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_http_exception(e, "Component execution failed") from e


@execution_router.post("/workflow/validate", response_model=ResponseModel[dict])
async def validate_workflow(
    request_body: ExecuteParas,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResponseModel[dict]:
    """validate workflow graph"""
    try:
        await flow_mgr.validate(request_body.id, request_body.version, request_body.space_id, current_user)
        return ResponseModel(code=status.HTTP_200_OK, message="Workflow validate success", data={})
    except HTTPException:
        raise
    except JiuWenGraphException as e:
        logger.info(f"JiuWenGraphException: {repr(e)}")
        return ResponseModel(
            code=e.code,
            message=e.message,
            data={}
        )
    except JiuWenComponentException as e:
        logger.info(f"JiuWenComponentException: {repr(e)}")
        return ResponseModel(
            code=e.code,
            message=e.message,
            data={
                "component_id": e.component_id,
                "component_type": e.component_type,
                "error_stage": e.error_stage
            }
        )
    except Exception as e:
        raise handle_http_exception(e, "Workflow validation failed") from e


@execution_router.post("/plugin", response_model=ResponseModel[dict])
async def execute_plugin(
    request_body: PluginExecuteParas,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    """Run a plugin"""

    try:
        logger.info(f"in execute: {request_body}")
        if isinstance(request_body.inputs, UserInput):
            inputs = InteractiveInput()
            inputs.update(request_body.inputs.node_id, request_body.inputs.input_value)
        else:
            inputs = request_body.inputs
        version = "draft"
        chunk = await plugin_mgr.run(request_body.plugin_id, request_body.tool_id, inputs, request_body.space_id,
                                     version, current_user)
        logger.warning(f"Received chunk: {chunk}, type: {type(chunk)}")
        return ResponseModel(code=status.HTTP_200_OK, message="Executed successfully", data=chunk)
    except JiuWenComponentException as e:
        log_exception(e)
        return ResponseModel(
            code=e.code, message=e.message,
            data={"type": "node", "payload": {"output": {"result": e.message, "is_success": False}}}
        )
    except JiuWenGraphException as e:
        log_exception(e)
        return ResponseModel(
            code=e.code, message=e.message,
            data={"type": "node", "payload": {"output": {"result": e.message, "is_success": False}}}
        )
    except BaseError as e:
        log_exception(e)
        return ResponseModel(
            code=e.code, message=e.message,
            data={"type": "node", "payload": {"output": {"result": e.message, "is_success": False}}}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_http_exception(e, "Plugin execution failed") from e


@execution_router.post("/get_trace_summary_list", response_model=ResponseModel[list[TraceSummaryBrief]],
                       response_model_by_alias=False)
async def get_trace_summary_list(
        request: Dict,
        current_user: dict = Depends(get_current_user)
):
    try:
        req = validate_request(request, TraceSummaryListRequest)
        _ = check_user_space(req.space_id, current_user)
        res = trace_summary_repository.get_trace_summary_list(req.business_id, req.business_type)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"Trace summary list retrieval failed, error: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@execution_router.post("/get_trace_summary_by_trace_id", response_model=ResponseModel[ExecutionLogSummary],
                       response_model_by_alias=False)
async def get_trace_summary_by_trace_id(
        request: Dict,
        current_user: dict = Depends(get_current_user)
):
    try:
        req = validate_request(request, TraceSummaryByTraceIdRequest)
        _ = check_user_space(req.space_id, current_user)
        res = trace_summary_repository.get_trace_summary_by_trace_id(req.trace_id)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"Trace summary retrieval failed for trace ID, error: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@execution_router.post("/get_latest_trace_summary", response_model=ResponseModel[ExecutionLogSummary],
                       response_model_by_alias=False)
async def get_latest_trace_summary(
        request: Dict,
        current_user: dict = Depends(get_current_user)
):
    try:
        req = validate_request(request, TraceSummaryLatestRequest)
        _ = check_user_space(req.space_id, current_user)
        res = trace_summary_repository.get_latest_trace_summary(req.business_id, req.business_type)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"Get latest trace summary failed, error: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@execution_router.post("/memory/get_user_variable", response_model=ResponseModel[dict])
async def search_variable_memory(
        request: dict, current_user: dict = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    req = GetUserVar(**request)
    _ = check_user_space(req.user_id, current_user)
    try:
        data = await get_user_variable(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get user variable success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"get user variable failed: {str(e)}",
            data=None
        )


@execution_router.post("/memory/get_longterm_mem", response_model=ResponseModel[dict])
async def search_longterm_memory(
        request: dict, current_user: dict = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    req = SearchLongtermMem(**request)
    _ = check_user_space(req.user_id, current_user)
    try:
        data = await get_longterm_mem(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get long term mem success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve long-term memory: {str(e)}",
            data=None
        )


@execution_router.post("/memory/delete_user_variable", response_model=ResponseModel[dict])
async def delete_variable_memory(
    request: dict, current_user: dict = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    req = DeleteVariable(**request)
    _ = check_user_space(req.user_id, current_user)
    try:
        data = await delete_user_variable(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="delete user variable success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"delete user variable failed: {str(e)}",
            data=None
        )


@execution_router.post("/memory/delete_longterm_mem", response_model=ResponseModel[dict])
async def delete_longterm_memory(
    request: dict, current_user: dict = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    req = DeleteLongtermMem(**request)
    _ = check_user_space(req.user_id, current_user)
    try:
        data = await delete_longterm_mem(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="delete long term memory success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to delete long-term memory: {str(e)}",
            data=None
        )


@execution_router.post("/memory/delete_longterm_mem_by_scope", response_model=ResponseModel[dict])
async def delete_longterm_mem_by_scope(
    request: dict,
) -> ResponseModel[Dict[str, Any]]:
    req = DeleteScopeLongtermMem(**request)
    try:
        data = await delete_longterm_mem_by_scope_id(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="delete long term memory success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to delete long-term memory: {str(e)}",
            data=None
        )


@execution_router.post("/memory/update_user_variable", response_model=ResponseModel[dict])
async def update_variable_memory(
    request: dict, current_user: dict = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    req = UpdateVariable(**request)
    _ = check_user_space(req.user_id, current_user)
    try:
        data = await update_user_variable(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="update user variable success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"update user variable failed: {str(e)}",
            data=None
        )


@execution_router.post("/memory/update_longterm_mem", response_model=ResponseModel[dict])
async def update_longterm_memory(
    request: dict, current_user: dict = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    req = UpdateLongtermMem(**request)
    _ = check_user_space(req.user_id, current_user)
    try:
        data = await update_longterm_mem(req)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="update long term memory success",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"update long term memory failed: {str(e)}",
            data=None
        )


@execution_router.post("/agent/reset", response_model=ResponseModel[dict])
async def reset_agent_instance(
    request_body: ExecuteParas,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    """
    Reset agent instance, clear cache and rebuild

    Args:
        request_body: Request parameters containing agent_id, version, conversation_id, etc.
        current_user: Current user information

    Returns:
        ResponseModel: Reset operation result
    """
    try:
        _ = check_user_space(request_body.space_id, current_user)
        # Use common method to reset agent instance cache
        success = await agent_mgr.reset_agent_instance_cache(
            conversation_id=request_body.conversation_id,
            agent_id=request_body.id,
            agent_version=request_body.version
        )
        result = "success" if success else "fail"
        return ResponseModel(
            code=status.HTTP_200_OK,
            message=f"Agent instance reset {result}.",
            data={}
        )
    except Exception as e:
        log_exception(e)
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Reset agent instance failed: {str(e)}",
            data=None
        )


@execution_router.post("/workflow/cancel", response_model=ResponseModel[dict])
async def cancel_workflow_execution(
        request_body: BaseParas,
        current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    """
    取消正在执行的工作流

    Args:
        request_body: 包含 conversation_id
        current_user: 当前用户信息

    Returns:
        ResponseModel: 取消操作的结果
    """
    try:
        logger.info(f"Start to cancel workflow execution")
        _ = check_user_space(request_body.space_id, current_user)
        # 获取执行信息以验证权限
        execution_info = workflow_execution_manager.get_execution(request_body.conversation_id)
        if not execution_info:
            return ResponseModel(
                code=status.HTTP_404_NOT_FOUND,
                message=f"Execution not found for conversation_id: {request_body.conversation_id}",
                data=None
            )

        # 执行取消操作
        success = await workflow_execution_manager.cancel_execution(
            conversation_id=request_body.conversation_id
        )

        if success:
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Workflow execution cancelled successfully",
                data={
                    "conversation_id": request_body.conversation_id,
                    "cancelled": True
                }
            )
        else:
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to cancel workflow execution",
                data=None
            )
    except Exception as e:
        log_exception(e)
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Cancel workflow execution failed: {str(e)}",
            data=None
        )


# 新增取消单节点接口
@execution_router.post("/component/cancel", response_model=ResponseModel[dict])
async def cancel_component_execution(
        request_body: CompExecuteParas,
        current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResponseModel[Dict[str, Any]]:
    """
    取消正在执行的单节点
    """
    try:
        _ = check_user_space(request_body.space_id, current_user)
        execution_id = f"{request_body.id}:{request_body.component_id}:{request_body.conversation_id}"
        exec_info = component_execution_manager.get_execution(execution_id)
        if not exec_info:
            return ResponseModel(
                code=status.HTTP_404_NOT_FOUND,
                message=f"Component execution not found for {execution_id}",
                data=None
            )

        success = await component_execution_manager.cancel_execution(execution_id=execution_id)
        if success:
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Component execution cancelled successfully",
                data={
                    "workflow_id": request_body.id,
                    "component_id": request_body.component_id,
                    "conversation_id": request_body.conversation_id,
                    "cancelled": True,
                    "warning": "component execution cancel by user"
                }
            )
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to cancel component execution",
            data=None
        )
    except Exception as e:
        log_exception(e)
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Cancel component execution failed: {str(e)}",
            data=None
        )