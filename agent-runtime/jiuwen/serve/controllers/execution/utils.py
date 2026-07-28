# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""This module defines several util functions for ir execution."""

import copy
import os
import time
import traceback
from asyncio import Queue, QueueEmpty
from copy import deepcopy
from typing import Iterable, Tuple, Optional, Generator, Union, AsyncGenerator

from fastapi.responses import StreamingResponse
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.intent_detection.config import LLMConfig
from jiuwen.common.log.base import logger, performance_logger
from jiuwen.common.utils.singleton import Singleton
from jiuwen.common.utils.utils import safe_json_loads_raise_exception
from jiuwen.context.base import ContextConfig
from jiuwen.context.history import ConversationHistory
from jiuwen.context.memory_engine.config.memory_ir_config import MemoryIrConfig
from jiuwen.controller.common.config import (
    ReactConfig,
    ControllerConfig,
    IntentConfig,
    WorkflowConfig,
    ToolUseConfig,
    IntentIdentificationConfig,
    MultiLayerIntentDetectionConfig,
    PlanExecuteConfig,
    SceneConfig,
    GuidelineConfig,
    RelationConfig,
    PlanningConfig,
)
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import (
    HandlerType,
    ActionAfterCompletionType,
    IntentIdentificationMethod,
    ControlSignal,
    RetCode,
)
from jiuwen.deep_research.utils import execute_deepresearch
from jiuwen.extension.wrapper.workflow_instance_layer import (
    OpenJiuWenWorkflowInstanceLayer,
)
from jiuwen.insight.async_client import Client
from jiuwen.insight.handlers.async_handler import InsightHandler
from jiuwen.insight.manager import TraceManager
from jiuwen.orchestration.common.perf_log import wf_performance_buffer
from jiuwen.orchestration.flow.constant import WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE
from jiuwen.orchestration.flow.enum import ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowInvokeOutput
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.orchestration.flow.workflow import Workflow
from jiuwen.orchestration.task_model import TaskConfig, TaskModel
from jiuwen.planner.common.enum_class import PlanStrategyType
from jiuwen.planner.common.plan_runtime_context import PlanRuntimeContext
from jiuwen.plugin.common.utils.ir_utils import PluginIRConverter, McpIRConverter
from jiuwen.prompt import TemplateManager, Template
from jiuwen.serve.common.exception.exception_handler import CODE, MESSAGE
from jiuwen.serve.common.message import MessageCollector
from jiuwen.serve.controllers.execution.enum import (
    IRType,
    ResponseMode,
    ConversationEvent,
    MessageRole,
    PlanModeType,
    AsyncExecutionStatus,
)
from jiuwen.serve.controllers.execution.manager import (
    StateManager,
    ExecutionResultManager,
    AsyncStateManager,
    AsyncExecAsyncStateManager,
)
from jiuwen.serve.controllers.execution.open_utils import (
    async_ir_load,
    serialize_object,
)
from jiuwen.serve.controllers.execution.types import (
    StreamingChatResponse,
    CompletionChatResponse,
    ExecutionData,
    AsyncExecutionState,
    WorkflowConfigs,
)
from jiuwen.serve.schemas.orchestration_mgr import (
    ExecutionRequest,
    ComponentExecutionRequest,
)

_ROLE = "role"
_NAME = "name"
_CONTENT = "content"
_EXCEPTION = "exception"
_ERROR_MSG = "error_msg"
_INTERMEDIATE_MESSAGE = "intermediate_message"

_CONSTRAIN = "constrain"
_MAX_ITERATION = 2
_MAX_CHAT_ROUND = 15
_PROPOSE_NEXT = "propose_next"

PLAN_TYPE = {
    "ReAct": PlanStrategyType.ReAct,
    "Controller": PlanStrategyType.Controller,
    "ToolUse": PlanStrategyType.ToolUse,
    "PlanExecute": PlanStrategyType.PlanExecute,
}

DEFAULT_PLAN_CONFIG = {
    _PROPOSE_NEXT: {
        "prompt_template_name": "",
        "is_chat": True,
        "reserved_max_chat_rounds": _MAX_CHAT_ROUND,
    },
    "constrain": {"max_iteration": _MAX_ITERATION},
}

_TIME_CONSUMPTION = "time_consumption"
_OVERALL_LATENCY = "overall_latency"
_PLUGIN_LATENCY = "plugin_latency"
_LATENCY = "latency"
_API_RESULT = "api_result"
_FUNCTION_NAME = "function_name"
_PLUGIN_CONFIGS = "plugin_configs"
_STREAM_OUTPUT_CHAR = "stream_output_char"
_FUNCTION_CALL_GENERATION = "function_call_generation"
_RESULT = "result"
_ANSWER = "answer"
_THINK = "think"
_REFLECTION = "reflection"

_CONTROL_SIGNAL = "control_signal"
_RET_CODE = "ret_code"

_DEFAULT = "default"

_AGENT_ERROR_REPLY = "生成回复失败"
_UTF_8 = "utf-8"
_BASE_AGENT_SWITCH = "BASE_AGENT_SWITCH"

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"

item_code_to_conversation_event_type = {
    StreamCode.PARTIAL_CONTENT.value: ConversationEvent.MESSAGE,
    StreamCode.ERROR.value: ConversationEvent.ERROR,
    StreamCode.WORKFLOW_EXCEPTION.value: ConversationEvent.EXCEPTION,
    StreamCode.FINISH.value: ConversationEvent.DONE,
    StreamCode.MESSAGE_END.value: ConversationEvent.MESSAGE_END,
    StreamCode.WORKFLOW_START.value: ConversationEvent.WORKFLOW_START,
    StreamCode.WORKFLOW_END.value: ConversationEvent.WORKFLOW_END,
    StreamCode.WORKFLOW_NODE_MESSAGE.value: ConversationEvent.WORKFLOW_NODE_MESSAGE,
    StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value: ConversationEvent.INTERMEDIATE_MESSAGE,
    StreamCode.CONTROLLER_START_MESSAGE.value: ConversationEvent.TASK_START,
    StreamCode.CONTROLLER_FINISH_MESSAGE.value: ConversationEvent.TASK_END,
    StreamCode.WORKFLOW_BLOCKED_MESSAGE.value: ConversationEvent.WORKFLOW_BLOCKED,
    StreamCode.WORKFLOW_RESUME_MESSAGE.value: ConversationEvent.WORKFLOW_RESUME,
    StreamCode.TASK_TERMINATED_MESSAGE.value: ConversationEvent.TASK_TERMINATED,
    StreamCode.CONTROLLER_AGENT_INTERRUPT_MESSAGE.value: ConversationEvent.AGENT_INTERRUPTED,
    # PlanExecute 专属事件映射
    StreamCode.PE_SCENE_MATCH.value: ConversationEvent.SCENE_MATCH,
    StreamCode.PE_PLAN_END.value: ConversationEvent.PLAN_END,
    StreamCode.PE_STEP_START.value: ConversationEvent.STEP_START,
    StreamCode.PE_STEP_END.value: ConversationEvent.STEP_END,
    StreamCode.PE_TASK_COMPLETE.value: ConversationEvent.TASK_COMPLETE,
    StreamCode.PE_FUNCTION_CALL.value: ConversationEvent.FUNCTION_CALL,
    StreamCode.PE_API_EXEC_DATA.value: ConversationEvent.API_EXEC_DATA,
    StreamCode.PE_FUNCTION_CALL_END.value: ConversationEvent.FUNCTION_CALL_END,
    # PlanExecute 统计和汇总事件映射
    StreamCode.STATISTIC_DATA.value: ConversationEvent.STATISTIC_DATA,
    StreamCode.SUMMARY_RESPONSE.value: ConversationEvent.SUMMARY_RESPONSE,
}


async def distribute_execution_request(
    req: ExecutionRequest, execution_data: ExecutionData
):
    """
    The general entry for IR execution. Distributing requests to each handler for processing.
    """
    if execution_data.instance_type == IRType.Agent:
        try:
            return await _execute_agent(req, execution_data)
        except Exception:
            template_delete(task_id=execution_data.instance.task_id)
            await AsyncStateManager().delete_state(req.conversation_id)
            raise
    if execution_data.instance_type == IRType.MultiAgents:
        try:
            return await _execute_agent_group(req, execution_data)
        except Exception as e:
            await AsyncStateManager().delete_state(req.conversation_id)
            logger.error(f"execute_agent_group error: {type(e)}")
            raise
    if execution_data.instance_type == IRType.Workflow:
        try:
            return await _execute_workflow(req, execution_data)
        except Exception as e:
            wf_performance_buffer.record(req.conversation_id)
            await AsyncStateManager().delete_state(req.conversation_id)
            await execution_data.instance.async_clean_up()
            logger.error(f"execute_workflow error: {type(e)}")
            raise
    if execution_data.instance_type == IRType.DeepResearch:
        try:
            return await execute_deepresearch(req, execution_data)
        except Exception as e:
            logger.error(f"execute_deepresearch error: {type(e)}")
            raise
    raise JiuWenBaseException(
        error_code=StatusCode.IR_DATA_VALIDATION_ERROR.code,
        message=StatusCode.IR_DATA_VALIDATION_ERROR.errmsg,
    )


async def _execute_agent_group(req, execution_data):
    """
    Agent group execution request handler.
    """
    agent_group = execution_data.instance
    insight_client, runtime_context, tracer = await build_agent_input(req)
    is_debug = req.headers.get("X-Invoke-Mode", "").lower() == "debug"
    if req.response_mode == ResponseMode.STREAMING:
        streaming_output = agent_group.astream(
            req.query,
            stream=True,
            runtime_context=runtime_context,
            tool_switch_dict=req.params.tool_switch_dict,
            trace_handlers=tracer,
        )
        resp = post_process_agent_group_streaming_output(
            conversation_id=req.conversation_id,
            origin_output=streaming_output,
            execution_data=execution_data,
            insight_queue=insight_client.data_queue,
            is_debug=is_debug,
        )
        return StreamingResponse(resp, media_type="text/event-stream")
    # 非流式调用
    raise JiuWenBaseException(
        error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
        message="responseMode Blocking is not supported yet.",
    )


async def _execute_agent(req: ExecutionRequest, execution_data: ExecutionData):
    """
    Agent execution request handler.
    """
    agent = execution_data.instance

    insight_client, runtime_context, tracer = await build_agent_input(req)
    is_debug = req.headers.get("X-Invoke-Mode", "").lower() == "debug"
    # 流式调用
    if req.response_mode == ResponseMode.STREAMING:
        if _is_base_agent_switch_enabled():
            runner_inputs = _build_runner_agent_inputs(
                req=req,
                runtime_context=runtime_context,
                tracer=tracer,
            )
            runner_agent = _build_runner_agent(agent)
            streaming_output = _run_agent_streaming_via_runner(
                runner_agent=runner_agent, runner_inputs=runner_inputs
            )
        else:
            streaming_output = agent.astream(
                req.query,
                stream=True,
                runtime_context=runtime_context,
                tool_switch_dict=req.params.tool_switch_dict,
                trace_handlers=tracer,
            )
        if agent.get_control_mode() in ["ReAct", "ToolUse"]:
            resp = _format_agent_streaming_output(
                origin_output=streaming_output,
                insight_queue=insight_client.data_queue,
                task_id=agent.task_id,
                conversation_id=req.conversation_id,
                execution_data=execution_data,
                is_debug=is_debug,
            )
        else:
            resp = post_process_agent_workflow_streaming_output(
                conversation_id=req.conversation_id,
                origin_output=streaming_output,
                execution_data=execution_data,
                insight_queue=insight_client.data_queue,
                is_debug=is_debug,
            )
        return StreamingResponse(resp, media_type="text/event-stream")

    # 非流式调用
    raise JiuWenBaseException(
        error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
        message="responseMode Blocking is not supported yet.",
    )


def _build_runner_agent_inputs(req: ExecutionRequest, runtime_context, tracer) -> dict:
    """Build dict-like inputs for Runner.run_agent_streaming."""
    return {
        "query": req.query,
        "conversation_id": req.conversation_id,
        "_jiuwen_runtime_kwargs": {
            "stream": True,
            "runtime_context": runtime_context,
            "tool_switch_dict": req.params.tool_switch_dict,
            "trace_handlers": tracer,
        },
    }


def _is_base_agent_switch_enabled() -> bool:
    """Return whether the BaseAgent bridge path is explicitly enabled."""
    return os.getenv(_BASE_AGENT_SWITCH, "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_runner_agent(agent):
    """Create the Runner-facing agent, preserving facade instances when provided."""
    from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade

    if isinstance(agent, OpenJiuwenAgentFacade):
        return agent
    return OpenJiuwenAgentFacade(agent)


def _run_agent_streaming_via_runner(runner_agent, runner_inputs):
    """Invoke the openJiuwen Runner streaming path lazily when the switch is enabled."""
    from openjiuwen.core.runner import Runner

    return Runner.run_agent_streaming(agent=runner_agent, inputs=runner_inputs)


async def build_agent_input(req):
    """
    构建agent入参
    Args:
        req:

    Returns:

    """
    # 插件所需headers透传
    runtime_context = PlanRuntimeContext()
    runtime_context.api_config = {"headers": req.headers}
    workflow_chat_history = ConversationHistory(
        [chat.model_dump(exclude_none=True) for chat in req.params.conversation_history]
    )
    runtime_context.agent_workflow_context["workflow_chat_history"] = (
        workflow_chat_history
    )
    runtime_context.agent_workflow_context[
        WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
    ] = req.params.model_dump()
    runtime_context.conversation_id = req.conversation_id

    # 从请求参数中提取 sys_operation_card，写入 runtime_context
    sys_op_card_data = req.params.sys_operation_card
    if sys_op_card_data is not None:
        from openjiuwen.core.sys_operation import SysOperationCard
        from jiuwen.common.utils.utils import convert_camel_to_snake

        sys_op_card_data = convert_camel_to_snake(sys_op_card_data)
        # 旧字段 workDir(单个字符串) -> sandbox_root(List[str])；shell_allowlist 保持不变
        # 同时强制开启 restrict_to_sandbox，限制 shell/code 执行只能在 sandbox_root 内
        work_config = sys_op_card_data.get("work_config")
        if isinstance(work_config, dict):
            if "work_dir" in work_config:
                work_dir_value = work_config.pop("work_dir")
                if isinstance(work_dir_value, list):
                    work_config["sandbox_root"] = work_dir_value
                elif work_dir_value:
                    work_config["sandbox_root"] = [work_dir_value]
                else:
                    work_config["sandbox_root"] = []
            # 若前端直接传的是 sandbox_root 但类型为 str，也兼容包成 list
            if isinstance(work_config.get("sandbox_root"), str):
                work_config["sandbox_root"] = [work_config["sandbox_root"]]
            work_config["restrict_to_sandbox"] = True
        runtime_context.sys_operation_card = SysOperationCard(**sys_op_card_data)

    insight_client = Client(insight_project_id="agent_debug_info")
    if req.headers.get("x-invoke-mode", "").lower() == "debug":
        tracer = TraceManager(trace_handlers=[InsightHandler(client=insight_client)])
    else:
        logger.debug(
            "_execute_agent, X-Invoke-Mode is not debug, no insight info return"
        )
        tracer = TraceManager(trace_handlers=[])
    return insight_client, runtime_context, tracer


async def _execute_workflow(req: ExecutionRequest, execution_data: ExecutionData):
    """
    Workflow execution request handler.
    """
    wf = execution_data.instance
    start_time = time.perf_counter()

    # 从 IR 中提取 {component_id: {name, type}} 映射，用于覆盖 TraceSchema 中的 componentName/componentType
    component_name_type_map: dict[str, dict] = {}
    node_defs: dict[str, dict[str, dict]] = {}
    if req.ir_path:
        try:
            ir_data = await async_ir_load(req.ir_path)
            from jiuwen.serve.controllers.execution.ir_converter import IRConverter

            node_defs = await IRConverter.extract_node_defs(ir_data)
            if node_defs:
                component_name_type_map = (
                    IRConverter.node_defs_to_component_name_type_map(node_defs)
                )
            if not component_name_type_map:
                component_name_type_map = IRConverter.extract_component_name_type_map(
                    ir_data
                )
        except Exception:
            logger.debug(
                "Failed to extract component name/type map from IR for workflow execution"
            )

    # 流式调用
    if req.response_mode == ResponseMode.STREAMING:
        card = wf.card
        params = req.params.model_dump()
        params["is_debug"] = req.headers.get("X-Invoke-Mode", "").lower() == "debug"

        wf_wrapper = OpenJiuWenWorkflowInstanceLayer(
            workflow_id=card.id,
            workflow_name=card.name,
            description=card.description,
            params=params,
            agent_id=card.id,
            session_id=req.conversation_id,
            node_name_type_map=component_name_type_map,
        )

        try:
            streaming_output = await wf_wrapper.astream(
                query=req.query, workflow_id=card.id, params=params
            )
        except Exception as e:
            logger.error(f"_execute_workflow exception: {e}")

        end_time = time.perf_counter()
        duration = round((end_time - start_time) * 1000)
        wf_performance_buffer.info("workflow_execution", duration)
        performance_logger.info(f"stream_execute_workflow|{duration}")
        resp = post_process_workflow_streaming_output(
            conversation_id=req.conversation_id,
            origin_output=streaming_output,
            workflow_instance=wf_wrapper,
            collector=execution_data.collector,
        )
        return StreamingResponse(resp, media_type="text/event-stream")

    # 非流式调用
    blocking_params = req.params.model_dump()
    blocking_params["is_debug"] = (
        req.headers.get("X-Invoke-Mode", "").lower() == "debug"
    )
    blocking_output = await wf.ainvoke(query=req.query, params=blocking_params)
    resp = await _post_process_workflow_blocking_output(
        conversation_id=req.conversation_id,
        origin_output=blocking_output,
        execution_data=execution_data,
    )
    end_time = time.perf_counter()
    duration = round((end_time - start_time) * 1000)
    performance_logger.info(f"block_execute_invokable|{duration}")
    wf_performance_buffer.info("workflow_execution", duration)
    wf_performance_buffer.record(req.conversation_id)
    return resp


def update_state_of_workflow(
    conversation_id: str, workflow_instance: Workflow, error_flag: bool = False
):
    """更新workflow的状态"""
    state_manager = StateManager()
    if error_flag:
        # 发生错误
        state_manager.delete_state(conversation_id)
    elif (
        workflow_instance.get_workflow_execute_status() == ExecutionStatus.USER_INTERACT
    ):
        # 正常执行，且未执行完毕，导出workflow的状态，并保存进存储介质
        state = workflow_instance.get_state()
        state_manager.save_state(conversation_id, serialize_object(state))
    else:
        # 正常执行完毕
        state_manager.delete_state(conversation_id)


async def async_update_state_of_workflow(
    conversation_id: str,
    workflow_instance: OpenJiuWenWorkflowInstanceLayer,
    error_flag: bool = False,
):
    """更新workflow的状态"""
    state_manager = AsyncStateManager()
    if error_flag:
        # 发生错误
        await state_manager.delete_state(conversation_id)
    elif (
        workflow_instance.graph_engine.graph_instance.get_workflow_execute_status()
        == ExecutionStatus.USER_INTERACT
    ):
        # 正常执行，且未执行完毕，导出workflow的状态，并保存进存储介质
        state = workflow_instance.graph_engine.get_state()
        await state_manager.save_state(conversation_id, serialize_object(state))
    else:
        # 正常执行完毕
        await state_manager.delete_state(conversation_id)


async def execute_single_component(
    req: ComponentExecutionRequest, execution_data: ExecutionData
):
    """
    执行单个组件的请求处理器。

    通过 SingleComponentDebugWrapper 绕过旧框架 Workflow，直接在新框架组件上执行。

    Args:
        req (ComponentExecutionRequest): 组件执行请求对象，包含执行所需的输入和参数。
        execution_data (ExecutionData): 执行数据对象，其 instance 应为 SingleComponentInfo。

    Returns:
        StreamingResponse: 返回一个流式响应对象，媒体类型为'text/event-stream'，用于实时传输执行结果。
    """
    from jiuwen.extension.wrapper.single_component_debug_wrapper import (
        SingleComponentDebugWrapper,
        SingleComponentInfo,
    )

    component_info: SingleComponentInfo = execution_data.instance
    execution_id = req.conversation_id

    wrapper = SingleComponentDebugWrapper(
        component_info=component_info,
        execution_id=execution_id,
    )

    # 将 execution_data.instance 替换为 wrapper，
    # 以便 _format_component_output 内部调用 async_update_state_of_workflow 时 duck-type 兼容
    execution_data.instance = wrapper

    output = wrapper.astream(inputs=req.inputs, execution_id=execution_id)

    # _format_component_output 无需改动，wrapper 通过 duck-type 兼容其尾部清理逻辑
    resp = _format_component_output(
        conversation_id=req.conversation_id,
        origin_output=output,
        execution_data=execution_data,
        workflow_instance=wrapper,
    )
    return StreamingResponse(resp, media_type="text/event-stream")


def _consume_insight_queue(insight_queue: Queue, task_id: str) -> Generator:
    while True:
        try:
            data_pop = insight_queue.get_nowait()
            # 支持自定义事件类型，默认使用 AGENT_NODE_MSG
            event_type = data_pop.get("event", ConversationEvent.AGENT_NODE_MSG)
            if isinstance(event_type, str):
                event_type = ConversationEvent(event_type)
            structure = StreamingChatResponse(
                event=event_type,
                data=data_pop.get("data"),
                createdTime=get_current_time_ms(),
                executionId=task_id,
            )
            insight_queue.task_done()
            yield f"data: {structure.model_dump_json(by_alias=True, exclude_none=True)}\n\n".encode(
                _UTF_8
            )
        except QueueEmpty:
            break


async def _yield_streaming_response(
    structure: StreamingChatResponse,
    collector: Optional[MessageCollector],
) -> bytes:
    """
    Collect and format streaming response as bytes.

    Args:
        structure: The StreamingChatResponse to format
        collector: Optional message collector

    Returns:
        bytes: Formatted response data
    """
    if collector:
        await collector.collect(structure)
    return f"data: {structure.model_dump_json(by_alias=True, exclude_none=True)}\n\n".encode(
        _UTF_8
    )


async def _handle_summary_response(
    data: dict,
    start_time: float,
    collector: Optional[MessageCollector],
) -> bytes:
    """
    Handle SUMMARY_RESPONSE event by creating STATISTIC_DATA response.

    Args:
        data: Response data containing time consumption info
        start_time: Start time for calculating overall latency
        collector: Optional message collector

    Returns:
        bytes: Formatted STATISTIC_DATA response
    """
    time_consumption = data.get(_ANSWER).pop(_TIME_CONSUMPTION)
    time_consumption[_OVERALL_LATENCY] = round(time.time() - start_time, 2)
    static_data_structure = StreamingChatResponse(
        event=ConversationEvent.STATISTIC_DATA,
        data=dict(answer=time_consumption),
        createdTime=get_current_time_ms(),
    )
    return await _yield_streaming_response(static_data_structure, collector)


async def _format_agent_streaming_output(
    origin_output: Iterable,
    insight_queue: Queue,
    task_id: str,
    conversation_id: str,
    execution_data: Optional[ExecutionData],
    is_debug: bool = False,
) -> Generator:
    """
    Used for agent streaming output formatting.
    Call the formatting tool class of Task - TaskOutputFormatter.
    Convert the item in the origin_output Iterable to StreamingChatResponse, and dump it to a json string.
    """
    start_time = time.time()
    collector = execution_data.collector if execution_data else None
    async for item in origin_output:
        # For each item yielded by the agent (or more accurately, Task),
        # call the corresponding method of TaskOutputFormatter for structured processing.
        if isinstance(item, dict):
            event, data = TaskOutputFormatter.handle_dict_item(start_time, item)
        elif isinstance(item, str):
            event, data = TaskOutputFormatter.handle_str_item(item)
        elif isinstance(item, JiuWenBaseException):
            yield await _handle_error_response(item)
            return
        else:
            event, data = TaskOutputFormatter.handle_unknown_item()

        # summary_response event will be formatted into [two] StreamingChatResponse structure:
        # STATISTIC_DATA and SUMMARY_RESPONSE
        if event == ConversationEvent.SUMMARY_RESPONSE:
            yield await _handle_summary_response(data, start_time, collector)

        structure = StreamingChatResponse(
            event=event,
            data=data,
            createdTime=get_current_time_ms(),
            executionId=task_id,
        )
        yield await _yield_streaming_response(structure, collector)

        if is_debug and insight_queue is not None:
            for msg in _handle_insight(insight_queue, task_id):
                yield msg
    if collector:
        await collector.done()
    if is_debug and insight_queue is not None:
        for item in _consume_insight_queue(insight_queue, task_id):
            yield item
    template_delete(task_id=task_id)
    await execution_data.instance.save_state(conversation_id)


async def _handle_error_response(item: JiuWenBaseException) -> bytes:
    error_response_str = StreamingChatResponse(
        **{
            "event": "error",
            "data": {
                MESSAGE: WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(
                    item.error_code,
                    item.message if LOG_VERBOSE_MODE else "test error message",
                ),
                CODE: item.error_code,
            },
            "createdTime": get_current_time_ms(),
        }
    ).model_dump_json(by_alias=True, exclude_none=True)
    logger.error(item.message)
    err_resp = f"data: {error_response_str}\n\n".encode(_UTF_8)
    return err_resp


def _handle_insight(insight_queue: Queue, task_id: str):
    while not insight_queue.empty():
        data_pop = insight_queue.get_nowait()
        structure = StreamingChatResponse(
            event=get_event_type(data_pop),
            data=data_pop.get("data"),
            createdTime=get_current_time_ms(),
            executionId=task_id,
        )
        insight_queue.task_done()
        yield f"data: {structure.model_dump_json(by_alias=True, exclude_none=True)}\n\n".encode(
            _UTF_8
        )


def get_event_type(data_pop):
    """获取事件类型"""
    # 支持自定义事件类型，默认使用 AGENT_NODE_MSG
    event_type = data_pop.get("event", ConversationEvent.AGENT_NODE_MSG)
    if isinstance(event_type, str):
        event_type = ConversationEvent(event_type)
    return event_type


class TaskOutputFormatter(metaclass=Singleton):
    """
    Tool class for formatting task streaming output.

    3 main methods to handle different streaming output structures:
    - handle_dict_item(start_time: float, item: dict)
    - handle_str_item(item: str)
    - handle_unknown_item()

    3 control signal handlers:
    - _handle_control_stream_start()
    - _handle_control_content_gen_end()
    - _handle_control_function_call_end()

    5 return code handlers:
    - _handle_code_func_call_gen(start_time: float, item: dict)
    - _handle_code_api_exec_result(start_time: float, item: dict)
    - _handle_code_api_exception(start_time: float, item: dict)
    - _handle_code_stream_output_llm(_: float, item: dict)
    - _handle_code_stream_reflection(_: float, item: dict)

    1 utilization method for string parsing:
    - _split_util(content_string: str)
    """

    _TASK_OUTPUT_SPLITTER = "#*#*#"

    @staticmethod
    def handle_dict_item(
        start_time: float, item: dict
    ) -> Tuple[ConversationEvent, Optional[dict]]:
        """
        Handle dict-like structure.
        """
        control_signal = item.get(_CONTROL_SIGNAL, "")
        ret_code = item.get(_RET_CODE, "")

        control_signal_handlers = {
            ControlSignal.STREAM_START: TaskOutputFormatter._handle_control_stream_start,
            ControlSignal.CONTENT_GEN_END: TaskOutputFormatter._handle_control_content_gen_end,
            ControlSignal.FUNCTION_CALL_END: TaskOutputFormatter._handle_control_function_call_end,
        }

        ret_code_handlers = {
            RetCode.FUNC_CALL_GEN: TaskOutputFormatter._handle_code_func_call_gen,
            RetCode.API_EXEC_RESULT: TaskOutputFormatter._handle_code_api_exec_result,
            RetCode.API_EXCEPTION: TaskOutputFormatter._handle_code_api_exception,
            RetCode.STREAM_OUTPUT_LLM: TaskOutputFormatter._handle_code_stream_output_llm,
            RetCode.STREAM_THINK_LLM: TaskOutputFormatter._handle_code_stream_think_llm,
            RetCode.STREAM_REFLECTION: TaskOutputFormatter._handle_code_stream_reflection,
            RetCode.INTERMEDIATE_MESSAGE: TaskOutputFormatter._handle_code_intermediate_message,
        }

        if control_signal in control_signal_handlers:
            return control_signal_handlers[control_signal]()
        if ret_code in ret_code_handlers:
            return ret_code_handlers[ret_code](start_time, item)

        return TaskOutputFormatter.handle_unknown_item()

    @staticmethod
    def handle_str_item(item: str) -> Tuple[ConversationEvent, dict]:
        """
        Handle str-like structure.
        """
        ans_message = TaskOutputFormatter._split_util(item)
        return ConversationEvent.SUMMARY_RESPONSE, {_ANSWER: ans_message}

    @staticmethod
    def handle_unknown_item() -> Tuple[ConversationEvent, dict]:
        """
        Handle unknown structure.
        """
        return ConversationEvent.MESSAGE, {_ANSWER: _AGENT_ERROR_REPLY}

    @staticmethod
    def _handle_control_stream_start() -> Tuple[ConversationEvent, dict]:
        """
        Handle ControlSignal.STREAM_START
        """
        return ConversationEvent.START, {}

    @staticmethod
    def _handle_control_content_gen_end() -> Tuple[ConversationEvent, dict]:
        """
        Handle ControlSignal.CONTENT_GEN_END
        """
        return ConversationEvent.DONE, {}

    @staticmethod
    def _handle_control_function_call_end() -> Tuple[ConversationEvent, dict]:
        """
        Handle ControlSignal.FUNCTION_CALL_END
        """
        return ConversationEvent.FUNCTION_CALL_END, {}

    @staticmethod
    def _handle_code_func_call_gen(
        start_time: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.FUNC_CALL_GEN
        """
        ans_message = item[_FUNCTION_CALL_GENERATION]
        end_time = time.time()
        ans_message[_TIME_CONSUMPTION][_OVERALL_LATENCY] = round(
            end_time - start_time, 2
        )
        return ConversationEvent.FUNCTION_CALL, {_ANSWER: ans_message}

    @staticmethod
    def _handle_code_api_exec_result(
        start_time: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.API_EXEC_RESULT
        """
        ans_message = {
            _ROLE: MessageRole.FUNCTION.value,
            _NAME: item.get(_API_RESULT, dict()).get(_FUNCTION_NAME, ""),
            _CONTENT: item[_API_RESULT][_RESULT],
            _TIME_CONSUMPTION: {
                _PLUGIN_LATENCY: item.get(_API_RESULT, dict()).get(_LATENCY, 0.0)
            },
        }
        end_time = time.time()
        ans_message[_TIME_CONSUMPTION][_OVERALL_LATENCY] = round(
            end_time - start_time, 2
        )
        return ConversationEvent.API_EXEC_DATA, {_ANSWER: ans_message}

    @staticmethod
    def _handle_code_api_exception(
        start_time: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.API_EXCEPTION
        """
        ans_message = {
            _ROLE: MessageRole.FUNCTION.value,
            _NAME: item[_EXCEPTION][_FUNCTION_NAME],
            _CONTENT: item[_EXCEPTION][_ERROR_MSG],
            _TIME_CONSUMPTION: {_PLUGIN_LATENCY: item[_EXCEPTION][_LATENCY]},
        }
        end_time = time.time()
        ans_message[_TIME_CONSUMPTION][_OVERALL_LATENCY] = round(
            end_time - start_time, 2
        )
        return ConversationEvent.FUNCTION_CALL, {_ANSWER: ans_message}

    @staticmethod
    def _handle_code_stream_output_llm(
        _: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.STREAM_OUTPUT_LLM
        """
        return ConversationEvent.MESSAGE, {_ANSWER: item[_STREAM_OUTPUT_CHAR]}

    @staticmethod
    def _handle_code_stream_think_llm(
        _: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.STREAM_THINK_LLM
        """
        return ConversationEvent.MESSAGE, {_THINK: item[_STREAM_OUTPUT_CHAR]}

    @staticmethod
    def _handle_code_stream_reflection(
        _: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.STREAM_REFLECTION
        """
        raw = item.get(_REFLECTION)
        ans_message = TaskOutputFormatter._split_util(raw)
        return ConversationEvent.SUMMARY_RESPONSE, {_ANSWER: ans_message}

    @staticmethod
    def _handle_code_intermediate_message(
        _: float, item: dict
    ) -> Tuple[ConversationEvent, dict]:
        """
        Handle RetCode.STREAM_REFLECTION
        """
        raw = item.get(_INTERMEDIATE_MESSAGE)
        return ConversationEvent.INTERMEDIATE_MESSAGE, {_ANSWER: raw}

    @classmethod
    def _split_util(cls, content_string: str):
        """
        Utilization method for string parsing.
        """
        if cls._TASK_OUTPUT_SPLITTER in content_string:
            split_list = content_string.split(cls._TASK_OUTPUT_SPLITTER, 1)
            final_answer = split_list[0]
            time_consumption_str = split_list[1]
            time_consumption = safe_json_loads_raise_exception(time_consumption_str)

            ans_message = dict(
                role=MessageRole.ASSISTANT.value,
                content=final_answer,
                time_consumption=time_consumption,
            )
        else:
            ans_message = dict(
                role=MessageRole.ASSISTANT.value,
                content=content_string,
                time_consumption={},
            )
        return ans_message


async def _post_process_workflow_blocking_output(
    conversation_id: str,
    origin_output: WorkflowInvokeOutput,
    execution_data: ExecutionData,
) -> CompletionChatResponse:
    """
    Processes the original workflow blocking output result in a structured manner.
    """
    start_time = time.perf_counter()
    error_flag = False
    if "error_code" in origin_output.data and "error_message" in origin_output.data:
        # 非流式执行报错
        error_flag = True
    await async_update_state_of_workflow(
        conversation_id=conversation_id,
        workflow_instance=execution_data.instance,
        error_flag=error_flag,
    )
    # 非流式执行结束后，清理workflow对象
    await execution_data.instance.async_clean_up()
    response = CompletionChatResponse(
        executionId=origin_output.execution_id,
        data=origin_output.data,
        messageList=origin_output.message_list,
        cardList=origin_output.card_list,
        createdTime=get_current_time_ms(),
    )
    end_time = time.perf_counter()
    duration = round((end_time - start_time) * 1000)
    performance_logger.info(f"_post_process_workflow_blocking_output|{duration}")
    wf_performance_buffer.info(
        "workflow_execution_output", duration, uid=conversation_id
    )
    return response


async def _format_component_output(
    conversation_id: str,
    origin_output: Iterable,
    execution_data: ExecutionData,
    workflow_instance: Workflow,
) -> Generator:
    """
    Processes the single component output result in a structured manner.
    """
    start_flag = True
    execution_id = ""
    error_flag = False
    async for item in origin_output:
        if not execution_id:
            execution_id = item.execution_id
        if start_flag:
            start_stream_data = StreamingChatResponse(
                event=ConversationEvent.START,
                index=0,
                executionId=item.execution_id,
                data={},
                createdTime=get_current_time_ms(),
                isStructMessage=item.is_struct_message,
            ).model_dump_json(by_alias=True, exclude_none=True)
            start_flag = False
            yield f"data: {start_stream_data}\n\n".encode(_UTF_8)
        if item.code == StreamCode.ERROR.value:
            code_of_data = item.data.get("code") or ""
            item.data.update(
                dict(
                    message=WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(
                        code_of_data, item.data.get("message")
                    )
                )
            )
            error_flag = True
        event = item_code_to_conversation_event_type.get(item.code)
        static_data_res = StreamingChatResponse(
            event=event,
            data=item.data,
            index=item.index,
            executionId=item.execution_id,
            createdTime=get_current_time_ms(),
            isStructMessage=item.is_struct_message,
        ).model_dump_json(by_alias=True, exclude_none=True)
        yield f"data: {static_data_res}\n\n".encode(_UTF_8)
    await async_update_state_of_workflow(
        conversation_id=conversation_id,
        workflow_instance=execution_data.instance,
        error_flag=error_flag,
    )
    await workflow_instance.async_clean_up()


async def _process_streaming_output(
    origin_output: Iterable,
    insight_queue: Optional[Queue] = None,
    task_id: Optional[str] = None,
    is_debug: bool = False,
    collector: Optional[MessageCollector] = None,
) -> AsyncGenerator:
    """
    处理流式输出，生成格式化的响应数据
    """
    # 每次对话都需要先生成一个start标识
    start_flag = True

    async for item in origin_output:
        # 生成开始标识
        if start_flag:
            start_stream_data = StreamingChatResponse(
                event=ConversationEvent.START,
                index=0,
                executionId=item.execution_id,
                data={},
                createdTime=get_current_time_ms(),
                isStructMessage=item.is_struct_message,
            ).model_dump_json(by_alias=True, exclude_none=True)
            start_flag = False
            yield f"data: {start_stream_data}\n\n".encode(_UTF_8)

        # 处理错误信息
        if item.code == StreamCode.ERROR.value:
            code_of_data = item.data.get("code") or item.code
            item.data.update(
                dict(
                    message=WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(
                        code_of_data,
                        item.data.get("message")
                        if LOG_VERBOSE_MODE
                        else "test error message",
                    )
                )
            )

        # 生成响应数据
        response = await _build_streaming_response(item, collector)
        yield response

        if is_debug and insight_queue is not None:
            for res in _handle_insight(insight_queue, task_id):
                yield res

    if collector:
        await collector.done()
    if is_debug and insight_queue is not None:
        for item in _consume_insight_queue(insight_queue, task_id):
            yield item


async def _build_streaming_response(item, collector: MessageCollector | None) -> bytes:
    response = StreamingChatResponse(
        event=item_code_to_conversation_event_type.get(item.code),
        data=item.data,
        index=item.index,
        executionId=item.execution_id,
        createdTime=get_current_time_ms(),
        isStructMessage=item.is_struct_message,
    )
    if collector:
        await collector.collect(response)

    json_str = response.model_dump_json(by_alias=True, exclude_none=True)
    return f"data: {json_str}\n\n".encode(_UTF_8)


async def post_process_agent_group_streaming_output(
    conversation_id: str,
    origin_output: Iterable,
    execution_data: ExecutionData,
    insight_queue: Optional[Queue] = None,
    is_debug: bool = False,
) -> AsyncGenerator:
    """
    Processes the original workflow streaming output result in a structured manner.
    Processing may be accompanied by state update operations.
    """
    # 每次对话都需要先生成一个start标识
    execution_id = ""
    try:
        async for output_data in _process_streaming_output(
            origin_output,
            insight_queue=insight_queue,
            task_id=conversation_id,
            is_debug=is_debug,
            collector=execution_data.collector,
        ):
            if not execution_id and hasattr(output_data, "execution_id"):
                execution_id = output_data.execution_id
            yield output_data
    except Exception:
        error_msg = traceback.format_exc()
        logger.error(error_msg, simple_log="Streaming output processing failed")
        await AsyncStateManager().delete_state(conversation_id)
    # 更新或者删除存储介质中的workflow state
    try:
        if execution_data.instance.get_task_end():
            await AsyncStateManager().delete_state(conversation_id)
            logger.info(
                f"conversation {conversation_id} has deleted execution state for agent group"
            )
        else:
            agent_group_state = await execution_data.instance.get_state()
            serialized_agent_state = serialize_object(agent_group_state)
            await AsyncStateManager().save_state(
                conversation_id, serialized_agent_state
            )
            logger.info(
                f"conversation {conversation_id} has saved execution state for agent group"
            )
        execution_data.instance.clear_state()
        # 根据task_id删除template
        task_ids = execution_data.instance.task_ids
        for _, task_id in task_ids.items():
            template_delete(task_id=task_id)
    except Exception as e:
        logger.error(f"Error in updating or deleting state: {type(e)}")
        raise JiuWenBaseException(
            StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.code,
            StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.errmsg.format(
                reason=f"Error in updating or deleting state: {type(e)}"
            ),
        ) from e
    performance_logger.info(
        f"conversation {conversation_id} has ended agent group execution for task "
    )


async def post_process_agent_workflow_streaming_output(
    conversation_id: str,
    origin_output: Iterable,
    execution_data: ExecutionData,
    insight_queue: Optional[Queue] = None,
    is_debug: bool = False,
) -> Generator:
    """
    Processes the original workflow streaming output result in a structured manner.
    Processing may be accompanied by state update operations.
    """
    execution_id = ""
    try:
        async for output_data in _process_streaming_output(
            origin_output,
            insight_queue=insight_queue,
            task_id=execution_data.instance.task_id,
            is_debug=is_debug,
            collector=execution_data.collector,
        ):
            if not execution_id and hasattr(output_data, "execution_id"):
                execution_id = output_data.execution_id
            yield output_data
    except Exception:
        error_msg = traceback.format_exc()
        logger.error(error_msg, simple_log="Streaming output processing failed")
        await AsyncStateManager().delete_state(conversation_id)
    # 更新或者删除存储介质中的workflow state
    if execution_data.instance.get_task_end():
        await AsyncStateManager().delete_state(conversation_id)
        logger.info(f"conversation {conversation_id} has deleted execution state")
    else:
        await execution_data.instance.save_state(conversation_id)
        logger.info(f"conversation {conversation_id} has saved execution state")
    execution_data.instance.clear_state()
    task_id = execution_data.instance.task_id
    template_delete(task_id=task_id)
    performance_logger.info(
        f"conversation {conversation_id} has ended execution for task {task_id}"
    )


async def post_process_workflow_streaming_output(
    conversation_id: str,
    origin_output: Iterable,
    workflow_instance: OpenJiuWenWorkflowInstanceLayer,
    collector: Optional[MessageCollector] = None,
) -> AsyncGenerator:
    """
    Processes the original workflow streaming output result in a structured manner.
    Processing may be accompanied by state update operations.
    """
    # 每次对话都需要先生成一个start标识
    start_flag = True
    execution_id = ""
    error_flag = False
    start_time = time.perf_counter()
    workflow_id = workflow_instance.workflow_id
    async for item in origin_output:
        if not execution_id:
            execution_id = item.execution_id
        if start_flag:
            start_stream_data = StreamingChatResponse(
                event=ConversationEvent.START,
                index=0,
                executionId=item.execution_id,
                data={},
                createdTime=get_current_time_ms(),
                isStructMessage=item.is_struct_message,
            ).model_dump_json(by_alias=True, exclude_none=True)
            start_flag = False
            yield f"data: {start_stream_data}\n\n".encode(_UTF_8)
        if item.code == StreamCode.ERROR.value:
            code_of_data = item.data.get("code") or ""
            item.data.update(
                dict(
                    message=WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(
                        code_of_data, item.data.get("message")
                    )
                )
            )
            error_flag = True
        elif item.code == StreamCode.WORKFLOW_EXCEPTION.value:
            error_flag = True
        if item.code in [StreamCode.PARTIAL_CONTENT.value, StreamCode.ERROR.value]:
            if "workflow_id" not in item.data:
                item.data.update(dict(workflow_id=workflow_id))
        if item.code == StreamCode.FINISH.value:
            # 更新或者删除存储介质中的workflow state
            await async_update_state_of_workflow(
                conversation_id=conversation_id,
                workflow_instance=workflow_instance,
                error_flag=error_flag,
            )

        response = await _build_streaming_response(item, collector)
        yield response
    if collector:
        await collector.done()
    # 流式执行结束，清理workflow对象
    await workflow_instance.graph_engine.graph_instance.async_clean_up()
    end_time = time.perf_counter()
    duration = round((end_time - start_time) * 1000)
    performance_logger.info(f"post_process_workflow_streaming_output|{duration}")
    wf_performance_buffer.info(
        "workflow_execution_output", duration, uid=conversation_id
    )
    wf_performance_buffer.record(conversation_id)


async def post_process_workflow_streaming_output_async(
    conversation_id: str, origin_output: Iterable, workflow_instance: Workflow
) -> AsyncExecutionStatus:
    """
    Processes the original workflow streaming output result in a structured manner.
    Processing may be accompanied by state update operations.
    """
    # 每次对话都需要先生成一个start标识
    start_flag = True
    execution_id = ""
    error_flag = False
    for item in origin_output:
        if not execution_id:
            execution_id = item.execution_id
        if start_flag:
            start_stream_data = StreamingChatResponse(
                event=ConversationEvent.START,
                index=0,
                executionId=item.execution_id,
                data={},
                createdTime=get_current_time_ms(),
                isStructMessage=item.is_struct_message,
            )
            start_flag = False
            ExecutionResultManager().append_message(execution_id, start_stream_data)

        if item.code == StreamCode.ERROR.value:
            code_of_data = item.data.get("code") or ""
            item.data.update(
                dict(
                    message=WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(
                        code_of_data, item.data.get("message")
                    )
                )
            )
            error_flag = True
        static_data_res = StreamingChatResponse(
            event=item_code_to_conversation_event_type.get(item.code),
            data=item.data,
            index=item.index,
            executionId=item.execution_id,
            createdTime=get_current_time_ms(),
            isStructMessage=item.is_struct_message,
        )
        ExecutionResultManager().append_message(execution_id, static_data_res)

    execution_status: ExecutionStatus = workflow_instance.get_workflow_execute_status()

    # 修改AsyncExecutionState
    async_exec_status: AsyncExecutionStatus = _get_conv_status_by_exec_status(
        execution_status
    )
    async_exec_state = AsyncExecutionState(
        status=async_exec_status, exec_id=execution_id
    )

    await AsyncExecAsyncStateManager().set_state_structure(
        conversation_id, async_exec_state
    )

    # 更新或者删除存储介质中的workflow state
    await async_update_state_of_workflow(
        conversation_id=conversation_id,
        workflow_instance=workflow_instance,
        error_flag=error_flag,
    )
    # 流式执行结束，清理workflow对象
    await workflow_instance.clean_up()
    return async_exec_status


def prepare_params(req: Union[ExecutionRequest, ComponentExecutionRequest]):
    """
    格式化请求参数并将请求头中的信息添加到参数中。

    此函数用于处理请求参数，特别是插件配置部分。它将请求头中的信息合并到插件配置中，并返回处理后的参数。

    Args:
        req (Union[ExecutionRequest, ComponentExecutionRequest]): 执行请求或组件执行请求对象，包含请求参数和请求头。

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


def _create_react_config(base_config, history_size, max_iteration, task_id):
    # 默认使用react模式的配置（包括其他所有非controller的模式）
    # 提取输入变量
    input_variables = base_config.pop("input_variables", [])
    react_config = {
        **base_config,
        "propose_next": {
            "prompt_template_name": task_id,
            "is_chat": True,
            "reserved_max_chat_rounds": history_size if history_size else 10,
        },
        _CONSTRAIN: {"max_iteration": max_iteration},
    }
    config = ReactConfig.from_config_dict(react_config)
    config.input_variables = input_variables  # 设置输入变量
    return config


def _create_tool_use_config(base_config, max_iterations):
    base_config = {
        **base_config,
        "max_iterations": max_iterations,
        "propose_next": {
            "prompt_template_name": base_config.get("task_id", ""),
            "is_chat": True,
            "reserved_max_chat_rounds": 10,
        },
        _CONSTRAIN: {"max_iteration": max_iterations},
    }
    return ToolUseConfig.from_config_dict(base_config)


class AgentIrUtils:
    @staticmethod
    def update_prompt_plugin(
        task_id, agent, task_model: TaskModel, ir_data: dict, **kwargs
    ):
        """注册prompt"""
        AgentIrUtils.build_prompt(task_id, task_model)
        # 设置插件
        conversation_id = kwargs.pop("conversation_id", "")
        AgentIrUtils.update_plugins_from_ir(
            agent, ir_data, conversation_id=conversation_id
        )
        # 设置MCP
        AgentIrUtils.update_mcps_from_ir(agent, ir_data, **kwargs)
        return agent

    @staticmethod
    def build_prompt(task_id, task_model: TaskModel):
        """注册prompt"""
        prompt = task_model.configs.sys_prompt_template
        if prompt is None:
            prompt = f"你是{task_model.agent_name}，你是能力是[{str(task_model.description)}]"
        # 临时方案设置prompt markdown格式
        model_config = task_model.configs.model_config
        if model_config.get("outputFormat"):
            output_format = model_config.get("outputFormat")
            if output_format == "markdown":
                prompt = f"{prompt}\n\n请以Markdown格式输出。"
        TemplateManager().register(
            Template(name=task_id, content=[{_ROLE: "system", _CONTENT: prompt}]),
            force=True,
        )

    @staticmethod
    def register_system_prompt(task_id, prompt, system_prompt=None):
        """注册prompt"""
        prompt = TemplateManager().get(prompt, filters={"tag": "default"}).content
        if system_prompt:
            prompt = prompt.replace("{{constrains}}", system_prompt)
        TemplateManager().register(
            Template(name=task_id, content=[{_ROLE: "system", _CONTENT: prompt}]),
            force=True,
        )

    @staticmethod
    def update_plugins_from_ir(agent, ir_data, conversation_id=""):
        """从IR中更新插件信息"""
        plugin_irs = ir_data.get("configs", {}).get("plugins")
        if plugin_irs:
            agent_id = ir_data.get("agentId", "")
            current_plugins = [
                PluginIRConverter.ir_to_plugin(
                    p, agent_id=agent_id, conversation_id=conversation_id
                )
                for p in plugin_irs
            ]
        else:
            current_plugins = []
        agent.update_plugins(current_plugins)

    @staticmethod
    def update_mcps_from_ir(agent, ir_data, **kwargs):
        """从IR中更新mcp信息"""
        mcp_irs = ir_data.get("configs", {}).get("mcps")
        current_mcps = (
            [McpIRConverter.ir_to_mcp(mcp_ir, **kwargs) for mcp_ir in mcp_irs]
            if mcp_irs
            else []
        )
        agent.update_mcps(current_mcps)

    @staticmethod
    def create_plan_config(prompt_name) -> dict:
        """create planner config dict"""
        config_dict = copy.deepcopy(DEFAULT_PLAN_CONFIG)
        if _PROPOSE_NEXT in config_dict and isinstance(
            config_dict.get(_PROPOSE_NEXT), dict
        ):
            config_dict[_PROPOSE_NEXT].update(prompt_template_name=prompt_name)
        return config_dict

    @staticmethod
    def get_intent_identification_configs(
        ir_data: dict,
    ) -> Optional[IntentIdentificationConfig]:
        """
        从ir_data中提取意图识别配置信息

        Args:
            ir_data (dict): 包含agent配置信息的字典

        Returns:
            IntentIdentificationConfig: 意图识别配置对象，如果不存在则返回None
        """
        configs = ir_data.get("configs", {})
        intent_identification_data = configs.get("intent_identification")

        if not intent_identification_data:
            return None

        method = IntentIdentificationMethod.from_string(
            intent_identification_data.get("type", "")
        )
        config = IntentIdentificationConfig(method=method)
        config.id = intent_identification_data.get("id")
        config.enable_multi_layer_detection = intent_identification_data.get(
            "enable_multi_layer_detection", False
        )
        if config.enable_multi_layer_detection:
            multi_layer_id_cfg_data = intent_identification_data.get(
                "multi_layer_id_cfg", {}
            )
            llm_cfg_data = multi_layer_id_cfg_data.get("llm_matcher_config", {}).get(
                "llm_config", {}
            )
            llm_cfg = LLMConfig(
                model_type=llm_cfg_data.get("modelType")
                or llm_cfg_data.get("model_type", ""),
                model_name=llm_cfg_data.get("modelName")
                or llm_cfg_data.get("model_name", ""),
                hyper_parameters=llm_cfg_data.get("hyperParameters")
                or llm_cfg_data.get("hyper_parameters", ""),
                extension=llm_cfg_data.get("extension", {}),
            )
            llm_cfg = llm_cfg.dict()
            multi_layer_id_cfg_data["llm_matcher_config"].update(llm_config=llm_cfg)
            multi_layer_id_cfg = MultiLayerIntentDetectionConfig.from_dict(
                multi_layer_id_cfg_data
            )
            config.multi_layer_id_cfg = multi_layer_id_cfg
        return config

    @staticmethod
    async def get_controller_workflow_configs(ir_data: dict) -> WorkflowConfigs:
        """Get controller workflow instances including workflows, start/end workflow, and global intent workflows

        Args:
            ir_data: Agent IR data containing workflow configurations

        Returns:
            WorkflowConfigs: Container with all workflow configurations
        """
        # 处理常规工作流、开始工作流和结束工作流
        workflow_configs = await AgentIrUtils.process_workflows(ir_data)

        # 处理全局意图工作流
        global_workflow_configs = await AgentIrUtils.process_global_intents(ir_data)

        return WorkflowConfigs(
            normal=workflow_configs["normal"],
            start=workflow_configs["start"],
            end=workflow_configs["end"],
            default=workflow_configs["default"],
            global_workflows=global_workflow_configs,
            intent=workflow_configs["intent"],
        )

    @staticmethod
    async def process_workflows(ir_data: dict) -> dict:
        """Process all workflow configurations and categorize them by type"""
        configs = {
            "normal": [],
            "start": None,
            "end": None,
            "default": None,
            "intent": [],
        }

        for workflow_info in ir_data.get("configs", {}).get("workflows", []):
            workflow_ir = await async_ir_load(workflow_info.get("ir_path"))
            action_after_completion = ActionAfterCompletionType.from_string(
                workflow_info.get("action_after_completion", "Continue")
            )
            config = WorkflowConfig(
                workflow_ir=workflow_ir,
                action_after_completion=action_after_completion,
                config_description=workflow_info.get("description"),
                config_name=workflow_info.get("name"),
                intent_name=workflow_info.get("intent", {}).get("name", ""),
                intent_description=workflow_info.get("intent", {}).get(
                    "description", ""
                ),
                arguments=workflow_info.get("arguments", []),
                input_parameters=workflow_info.get("inputParameters", {}),
            )

            workflow_type = workflow_info.get("workflow_type", "Normal")
            if workflow_type == "Start":
                configs["start"] = config
            elif workflow_type == "End":
                configs["end"] = config
            elif workflow_type == "Default":
                configs["default"] = config
            elif workflow_type == "IntentIdentification":
                config.config_name = workflow_info.get("id")
                configs["intent"].append(config)
            else:
                configs["normal"].append(config)

        return configs

    @staticmethod
    async def process_global_intents(ir_data: dict) -> list:
        """Process global intent workflows"""
        global_workflow_configs = []

        for intent in ir_data.get("configs", {}).get("global_intents", []):
            action = ActionAfterCompletionType.from_string(
                intent.get(
                    "action_after_completion",
                    ActionAfterCompletionType.WAITING_USER_INPUT.value,
                )
            )
            handler_type = intent.get("handler_type", "Workflow")

            if handler_type == HandlerType.WORKFLOW.value and intent.get("handler"):
                handler = intent["handler"]
                workflow_ir = await async_ir_load(handler.get("ir_path"))
                if workflow_ir:
                    global_workflow_configs.append(
                        WorkflowConfig(
                            workflow_ir=workflow_ir,
                            action_after_completion=action,
                            config_name=handler.get("name"),
                        )
                    )

        return global_workflow_configs

    @staticmethod
    def parse_global_intents_from_ir(ir_configs):
        """
        Parse global intents from IR configuration

        :param ir_configs: Configuration dictionary from IR data
        :return: List of IntentConfig objects
        """
        global_intents = []
        termination = False
        for intent in ir_configs.get("global_intents", []):
            handler = None
            handler_type = intent.get("handler_type")

            # 根据handler_type处理不同的handler
            if handler_type == HandlerType.WORKFLOW.value:
                handler = {
                    "id": intent.get("handler", {}).get("id"),
                    "ir_path": intent.get("handler", {}).get("ir_path"),
                    "name": intent.get("handler", {}).get("name"),
                }
            else:  # TEXT或其他类型
                handler = intent.get("handler")
                termination = (
                    intent.get("action_after_completion")
                    == ActionAfterCompletionType.TERMINATE.value
                )

            action_after_completion = ActionAfterCompletionType.from_string(
                intent.get(
                    "action_after_completion",
                    ActionAfterCompletionType.WAITING_USER_INPUT.value,
                )
            )
            intent_config = IntentConfig(
                name=intent.get("name"),
                intent_id=intent.get("intent_id"),
                description=intent.get("description"),
                handler_type=handler_type,
                handler=handler,
                termination=termination,
                action_after_completion=action_after_completion,
            )

            global_intents.append(intent_config)

        return global_intents

    @staticmethod
    def parse_input_variables_from_ir(input_variables):
        """
        Parse input variables from IR and preserve nested object structure.

        :param input_variables: Configuration list from IR data
        :return: List of input variables in tree form.
                 Each variable has 'name', 'type', 'default', and optionally 'fields' (for object type).
        """

        def parse_variable(var):
            """Recursively parse a variable, preserving object nesting."""
            name = var.get("name")
            var_type = var.get("type", "")
            default = var.get("default")

            result = {"name": name, "type": var_type, "default": default}

            # 如果是 object 类型且包含 schema，则递归解析内部字段
            if (
                var_type.lower() == "object"
                and "schema" in var
                and isinstance(var["schema"], list)
            ):
                result["fields"] = [parse_variable(child) for child in var["schema"]]

            return result

        return [parse_variable(variable) for variable in input_variables]

    @staticmethod
    def parse_global_variables_from_ir(ir_configs):
        """
        Parse global variables from IR configuration

        :param ir_configs: Configuration dictionary from IR data
        :return: List of global variables
        """
        global_variables = []

        for variable in ir_configs.get("global_variables", []):
            var_dict = {
                "name": variable.get("name"),
                "type": variable.get("type"),
                "default": variable.get("default"),
            }
            global_variables.append(var_dict)

        return global_variables

    @staticmethod
    def _create_plan_execute_config(ir_configs, base_config):
        """
        Create PlanExecute configuration from IR data

        解析 IR 中的 scenes 配置，包括:
        - scenes[].id/name/description
        - scenes[].tools
        - scenes[].guidelines[].id/condition/action/tools
        - scenes[].relations[].type/src/tgt

        :param ir_configs: Configuration dictionary from IR data
        :param base_config: Base configuration dictionary
        :return: PlanExecuteConfig instance
        """
        scenes_data = ir_configs.get("scenes", [])
        scenes = []

        for scene_data in scenes_data:
            # 解析 guidelines
            guidelines = []
            for g in scene_data.get("guidelines", []):
                guidelines.append(
                    GuidelineConfig(
                        id=g.get("id"),
                        condition=g.get("condition", ""),
                        action=g.get("action", ""),
                        tools=g.get("tools", []),
                    )
                )

            # 解析 relations
            relations = []
            for r in scene_data.get("relations", []):
                relations.append(
                    RelationConfig(
                        type=r.get("type", "dependency"),
                        src=r.get("src"),
                        tgt=r.get("tgt"),
                    )
                )

            # 获取场景工具列表
            scene_tools = scene_data.get("tools", [])
            if isinstance(scene_tools, list) and scene_tools:
                if isinstance(scene_tools[0], dict):
                    scene_tools = [t.get("name", "") for t in scene_tools]

            scenes.append(
                SceneConfig(
                    id=scene_data.get("id"),
                    name=scene_data.get("name"),
                    description=scene_data.get("description", ""),
                    tools=scene_tools,
                    guidelines=guidelines,
                    relations=relations,
                )
            )

        # 解析 planning 配置
        planning_data = ir_configs.get("planning", {})
        planning = PlanningConfig(
            max_steps=planning_data.get("max_steps", 10),
            allow_replanning=planning_data.get("allow_replanning", False),
        )

        return PlanExecuteConfig(
            task_id=base_config.get("task_id"),
            plan_mode=base_config.get("plan_mode"),
            scenes=scenes,
            planning=planning,
            sys_prompt_template=ir_configs.get("sysPromptTemplate"),
        )

    def get_task_model(self, ir_data, task_id):
        """
        Build task model based on IR data configurations

        :param ir_data: Dictionary parsed from JSON IR file
        :param task_id: Unique identifier for the task
        :return: Tuple of (TaskModel, model_configs)
        """
        ir_configs = ir_data.get("configs", {})
        model_configs = ir_configs.get("modelConfig", {})
        mode = ir_configs.get("mode")

        # 根据不同mode创建不同的plan_config，所有配置都在这个方法内处理
        plan_config = self._create_plan_config_by_mode(
            task_id, mode, ir_data, ir_configs, model_configs
        )

        # 创建TaskConfig和TaskModel
        max_iteration = ir_configs.get("maxIteration", _MAX_ITERATION)

        # construct context engine config
        context = ContextConfig.from_config_dict(ir_configs.get("context", {}))
        memory_config = MemoryIrConfig.from_config_dict(ir_configs.get("memory", {}))
        task_config = TaskConfig(
            sys_prompt_template=ir_configs.get("sysPromptTemplate"),
            mode=PLAN_TYPE.get(mode),
            max_iteration=max_iteration,
            plan_config=plan_config,
            context=context,
            memory_config=memory_config,
        )

        task_model = TaskModel(
            agent_id=ir_data.get("agentName"),
            agent_version=ir_data.get("agentVersion"),
            description=ir_data.get("description"),
            agent_name=ir_data.get("agentName"),
            configs=task_config,
        )

        return task_model, model_configs

    def _create_plan_config_by_mode(
        self, task_id, mode, ir_data, ir_configs, model_configs
    ):
        """
        Create plan configuration based on the specified mode

        :param task_id: Unique identifier for the task
        :param mode: Planning mode from IR configuration
        :param ir_data: Full IR data dictionary
        :param ir_configs: Configuration dictionary from IR data
        :param model_configs: Model configuration from IR data
        :return: Plan configuration dictionary
        """
        # 获取历史上下文轮数和最大迭代次数
        history_size = model_configs.get("historySize")
        max_iteration = ir_configs.get("maxIteration", _MAX_ITERATION)

        input_variables = self.parse_input_variables_from_ir(ir_data.get("inputs", []))
        # 默认基础配置
        base_config = {
            "task_id": task_id,
            "plan_mode": mode,
            "input_variables": input_variables,
        }

        # 根据模式创建特定配置
        if mode == PlanModeType.Controller:
            # 为控制器模式创建特定的配置结构
            return self._create_controller_config(ir_data, ir_configs, base_config)
        if mode == PlanModeType.ToolUse:
            return _create_tool_use_config(base_config, max_iteration)
        if mode == PlanModeType.PlanExecute:
            return self._create_plan_execute_config(ir_configs, base_config)
        return _create_react_config(base_config, history_size, max_iteration, task_id)

    def _create_controller_config(self, ir_data, ir_configs, base_config):
        """
        Create controller configuration for controller mode

        :param ir_data: Full IR data dictionary
        :param ir_configs: Configuration dictionary from IR data
        :return: ControllerConfig as dictionary
        """

        # 解析全局意图和变量
        global_intents = self.parse_global_intents_from_ir(ir_data.get("configs"))
        global_variables = self.parse_global_variables_from_ir(ir_data.get("configs"))
        input_variables = self.parse_input_variables_from_ir(ir_data.get("inputs", []))
        chat_history_max_turn = ir_configs.get("chatHistoryMaxTurn", _MAX_CHAT_ROUND)
        # 构建ControllerConfig结构
        controller_config = {
            **base_config,
            "max_iterations": ir_configs.get("maxIteration", 20),
            "chat_history_max_turn": chat_history_max_turn,
            "global_intents": global_intents,
            "global_variables": global_variables,
            "input_variables": input_variables,
            "specify_workflow_order": ir_configs.get("specify_workflow_order", False),
        }

        return ControllerConfig(**controller_config)


def get_current_time_ms() -> int:
    """
    获取当前时间的毫秒数。

    此函数用于获取当前时间的时间戳，并将其转换为毫秒形式。

    Args:
        无参数。

    Returns:
        int: 当前时间的时间戳，单位为毫秒。

    Raises:
        无特定异常抛出。

    Notes:
        - 函数使用`time.time()`获取当前时间的时间戳。
        - 通过乘以1000并将结果四舍五入为整数，将时间戳转换为毫秒。
    """
    current_timestamp = time.time()
    current_timestamp_ms = int(round((current_timestamp * 1000)))
    return current_timestamp_ms


def _get_conv_status_by_exec_status(
    execution_status: ExecutionStatus,
) -> AsyncExecutionStatus:
    if execution_status == ExecutionStatus.USER_INTERACT:
        return AsyncExecutionStatus.INTERACTING
    if execution_status == ExecutionStatus.END:
        return AsyncExecutionStatus.SUCCESS

    return AsyncExecutionStatus.FAILED


def template_delete(task_id: str):
    """template delete"""
    if task_id:
        try:
            TemplateManager().delete(task_id)
        except Exception as e:
            logger.error(
                f"Fail delete {task_id} template due to {str(e)}",
                simple_log=f"Fail delete {task_id} template due to {type(e)}",
            )
