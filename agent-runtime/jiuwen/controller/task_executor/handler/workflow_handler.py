#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import copy
import json
import os
import time
from typing import Dict, Any, Generator, Optional, AsyncGenerator, List

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import (
    StatusCode as JiuWenBaseExceptionStatusCode,
)
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.common.status import StatusCode
from jiuwen.context.history import ConversationHistory
from jiuwen.controller.atomic_skills.extract_params import ExtractParams
from jiuwen.controller.common.constants import WorkflowConstants, FUNCTION_ROLE
from jiuwen.controller.common.enum import ActionAfterCompletionType
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType, TaskSubType
from jiuwen.controller.context_manager.context_manager import ContextManager
from jiuwen.controller.context_manager.workflow_context import (
    WorkflowContext,
    WorkflowStatus,
    NodeExecutionInfo,
)
from jiuwen.controller.task_executor.constants import (
    ANSWER,
    RESULT,
    NON_EXIST_FUNC,
    ORIGIN_ANSWER,
)
from jiuwen.controller.task_executor.handler.base_handler import BaseHandler
from jiuwen.controller.utils.utils import MessageConverter
from jiuwen.controller.workflow.workflow import SpiffWorkflowControllerWorkflow
from jiuwen.extension.wrapper.workflow_instance_layer import (
    OpenJiuWenWorkflowInstanceLayer,
)
from jiuwen.extension.wrapper.workflow_loader import (
    ensure_openjiuwen_workflow_registered,
)
from jiuwen.insight.handlers.data import NAME
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_STATE,
    WORKFLOW_STATE_ERROR,
    WORKFLOW_STATE_END,
    WORKFLOW_STATE_RUN,
    REQUEST_VARIABLES,
)
from jiuwen.orchestration.flow.enum import NodeType, ExecutionStatus, StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.orchestration.flow.workflow import (
    _WORKFLOW_CHAT_HISTORY_KEY,
    CONTROLLER_MODE_SWITCH,
    build_workflow,
    CONTROLLER_MODE_JUMP,
)
from jiuwen.planner.common.exception import PanelWorkflowRunException
from jiuwen.planner.common.plan_constants import TimerInfo
from jiuwen.planner.common.stream_post_utils import LATENCY
from jiuwen.plugin.models.tool import WORKFLOW_ANSWER, WORKFLOW_END_TYPE
from jiuwen.serve.common.context import request, g, request_json
from jiuwen.serve.controllers.execution.utils import get_current_time_ms
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class WorkflowHandler(BaseHandler):
    """工作流处理器"""

    def __init__(self, context_manager: ContextManager):
        super().__init__(context_manager)
        self.extract_params = None
        self.llm = None
        self.workflows = None
        self.task_id = context_manager.agent_config.task_id

    def _attach_agent_id_to_workflow_context(
        self, workflow_context: WorkflowContext
    ) -> WorkflowContext:
        metadata = getattr(self.context_manager.agent_config, "metadata", None)
        agent_id = (
            getattr(metadata, "id", None)
            or getattr(self.context_manager.agent_config, "agent_id", None)
            or ""
        )
        if agent_id:
            setattr(workflow_context, "agent_id", agent_id)
        return workflow_context

    @staticmethod
    def process_stream_output(item):
        """后处理流式输出结果"""
        if not isinstance(item, StreamData) or item.code == StreamCode.ERROR.value:
            message = "panel get stream data error"
            if isinstance(item, StreamData) and isinstance(item.data, dict):
                message = item.data.get("message", "")
            raise PanelWorkflowRunException(message=message)
        if isinstance(item.data, dict):
            answer_dict = item.data.get(WORKFLOW_ANSWER)
            if isinstance(answer_dict, dict) and answer_dict:
                item.data.update({WORKFLOW_ANSWER: answer_dict.get(WORKFLOW_ANSWER)})
        result = dict(answer=item.data, code=item.code, msg=item.msg)
        result.update({WORKFLOW_STATE: WORKFLOW_STATE_RUN})
        return result

    @staticmethod
    async def create_workflow_instance(
        workflow_context: WorkflowContext, conversation_id: str, user_id: str
    ) -> SpiffWorkflowControllerWorkflow | OpenJiuWenWorkflowInstanceLayer:
        """创建工作流实例"""
        # 从 request context 提取 headers（旧框架路径和新框架路径共用）
        request_obj = request.get()
        headers = dict(getattr(request_obj, "headers", {}) or {})

        if WorkflowHandler._use_openjiuwen_workflow():
            agent_id = WorkflowHandler._resolve_workflow_agent_id(workflow_context)
            try:
                if workflow_context.workflow_ir:
                    await ensure_openjiuwen_workflow_registered(
                        workflow_context.workflow_ir,
                        workflow_id=workflow_context.workflow_id,
                        workflow_name=workflow_context.workflow_name,
                        description=workflow_context.description,
                        agent_id=agent_id,
                    )

                # 从 headers 提取 is_debug，注入 params 传递到 WorkflowWrapper
                is_debug = headers.get("X-Invoke-Mode", "").lower() == "debug"
                params = dict(workflow_context.workflow_parameters or {})
                params["is_debug"] = is_debug

                # 从 IR 中提取 {component_id: {name, type}} 映射，用于覆盖 TraceSchema 中的 componentName/componentType
                from jiuwen.serve.controllers.execution.ir_converter import IRConverter

                component_name_type_map: dict[str, dict] = {}
                if workflow_context.workflow_ir:
                    # 提取完整节点定义（含 configs），注入到 params → global_state，供 callback 读取
                    node_defs = await IRConverter.extract_node_defs(
                        workflow_context.workflow_ir
                    )
                    if node_defs:
                        component_name_type_map = (
                            IRConverter.node_defs_to_component_name_type_map(
                                node_defs
                            )
                        )
                    if not component_name_type_map:
                        component_name_type_map = (
                            IRConverter.extract_component_name_type_map(
                                workflow_context.workflow_ir
                            )
                        )

                return OpenJiuWenWorkflowInstanceLayer(
                    workflow_id=workflow_context.workflow_id,
                    workflow_name=workflow_context.workflow_name,
                    description=workflow_context.description,
                    params=params,
                    agent_id=agent_id,
                    session_id=conversation_id,
                    node_name_type_map=component_name_type_map,
                )
            except Exception as e:
                logger.warning(
                    "failed to create openjiuwen workflow, fallback to legacy workflow. "
                    f"workflow_id={workflow_context.workflow_id}, agent_id={agent_id}, error={e}"
                )

        # 旧框架路径
        project_id = (g.get() or {}).get("project_id", "")
        state = (
            workflow_context.state
            if workflow_context.state
            else workflow_context.workflow_ir
        )
        graph_instance = await build_workflow(
            state,
            project_id=project_id,
            x_auth_token=headers.get("X-Auth-Token"),
            cust_headers=headers,
            conversation_id=conversation_id,
            is_workflow_mode=True,
            user_id=user_id,
        )

        return SpiffWorkflowControllerWorkflow(
            workflow_id=workflow_context.workflow_id,
            description=workflow_context.description,
            params=workflow_context.workflow_parameters,
            graph_instance=graph_instance,
        )

    @staticmethod
    def _use_openjiuwen_workflow() -> bool:
        value = os.getenv("USE_OPENJIUWEN_WORKFLOW", "true").strip().lower()
        return value not in {"0", "false", "no", "off"}

    @staticmethod
    def _resolve_workflow_agent_id(workflow_context: WorkflowContext) -> str:
        agent_id = (
            getattr(workflow_context, "agent_id", None)
            or os.getenv("OPENJIUWEN_WORKFLOW_TAG", "")
            or workflow_context.config_name
            or ""
        )
        if not agent_id:
            logger.warning(
                "openjiuwen workflow tag is empty, workflow lookup will use workflow_id only. "
                f"workflow_id={workflow_context.workflow_id}"
            )
        return agent_id

    @staticmethod
    def initialize_workflow_status() -> dict:
        """初始化工作流状态跟踪字典"""
        return {
            "workflow_end": False,
            "questioner_interrupted": False,
            "intention_detection_interrupted": False,
        }

    @staticmethod
    def create_workflow_input(task: Any, workflow_req_params: dict) -> dict:
        """创建工作流输入参数"""
        return {"inputs": task.input_data.get("query"), "params": workflow_req_params}

    @staticmethod
    def get_filtered_global_variables(workflow_req_params: dict) -> dict:
        """获取过滤后的全局变量（排除None值）"""
        global_variables = workflow_req_params.get("global_variables", {})
        return {k: v for k, v in global_variables.items() if v is not None}

    @staticmethod
    def create_workflow_jump_debug_data(
        query: str, intent_name: str, current_node: NodeExecutionInfo
    ) -> dict:
        if current_node is None:
            current_node = NodeExecutionInfo(
                node_id="",
                node_name="",
                node_type="",
                execution_id="",
                workflow_id="",
                workflow_name="",
            )
        """记录工作流跳转信息"""
        return {
            "node_id": current_node.node_id,
            "node_name": current_node.node_name,
            "node_type": current_node.node_type,
            "workflow_name": current_node.workflow_name,
            "workflow_id": current_node.workflow_id,
            "query": query,
            "intent_id": intent_name,  # intent_id获取方式待定
            "intent_name": intent_name,
            "time": get_current_time_ms(),
            "execution_id": current_node.execution_id,
        }

    @staticmethod
    def _init_time_dict(time_dict: Dict[str, Any]) -> None:
        """初始化时间字典的默认值"""
        time_dict.setdefault("total_latency", 0.0)
        time_dict.setdefault("model_latency", 0.0)
        time_dict.setdefault("wait_latency", 0.0)

    @staticmethod
    def _filter_workflow_history(messages: list) -> list:
        """过滤工作流对话历史中的 hint 和空消息"""
        if not isinstance(messages, list):
            return []
        filtered = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            content = item.get("content", "")
            if not content:
                continue
            if "<system-hint>" in content:
                continue
            if item.get("function_call", ""):
                # 过滤中断工作流的恢复添加assistant-message 提问器可以通过最后一条message提取到用户传入query
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _check_questioner_interrupt(workflow, func_res: StreamData) -> None:
        """检查并处理问答器中断"""
        if not (isinstance(func_res, StreamData) and isinstance(func_res.data, dict)):
            return
        if (
            func_res.data.get("should_interrupt", False)
            or func_res.data.get("node_type") == NodeType.QUESTIONER.value
        ):
            if workflow is None:
                return
            setattr(workflow, "_questioner_interrupted", True)
            WorkflowHandler._mark_workflow_interrupted(workflow)

    # ========== 以下是公共方法 (public methods) ==========

    @staticmethod
    def _mark_workflow_interrupted(workflow_instance) -> None:
        mark_interrupted = getattr(workflow_instance, "mark_interrupted", None)
        if mark_interrupted:
            mark_interrupted()

    @staticmethod
    async def _cleanup_workflow_instance(workflow_instance) -> None:
        cleanup = getattr(workflow_instance, "cleanup", None) or getattr(
            workflow_instance, "async_clean_up", None
        )
        if cleanup:
            await cleanup()

    @staticmethod
    def _get_workflow_execute_status(workflow_instance):
        get_status = getattr(workflow_instance, "get_workflow_execute_status", None)
        if get_status:
            return get_status()
        return None

    @staticmethod
    def _get_workflow_state(workflow_instance):
        get_state = getattr(workflow_instance, "get_workflow_state", None) or getattr(
            workflow_instance, "get_state", None
        )
        if get_state:
            return get_state()
        graph_engine = getattr(workflow_instance, "graph_engine", None)
        if graph_engine is not None:
            graph_get_state = getattr(
                graph_engine, "get_workflow_state", None
            ) or getattr(graph_engine, "get_state", None)
            if graph_get_state:
                return graph_get_state()
            graph_instance = getattr(graph_engine, "graph_instance", None)
            if graph_instance is not None:
                graph_instance_get_state = getattr(
                    graph_instance, "get_workflow_state", None
                ) or getattr(graph_instance, "get_state", None)
                if graph_instance_get_state:
                    return graph_instance_get_state()
        return None

    @staticmethod
    def _get_workflow_runtime_context(workflow_instance):
        get_runtime_context = getattr(workflow_instance, "get_runtime_context", None)
        if get_runtime_context:
            return get_runtime_context()
        return None

    def handle(self, task: Task, context: Dict[str, Any], **kwargs) -> Message:
        """处理工作流相关任务

        Args:
            task: 任务对象
            context: 当前上下文
            **kwargs: 额外参数，包含workflows

        Returns:
            Message: 处理结果消息
        """
        # 从kwargs中获取workflows
        self.workflows = kwargs.get("workflows", [])

        if task.task_type == TaskType.WORKFLOW_START:
            return self._handle_workflow_start(task)
        if task.task_type == TaskType.WORKFLOW_RESUME:
            return self._handle_workflow_resume(task)
        if task.task_type == TaskType.WORKFLOW_COMPLETION:
            return self._handle_workflow_completion(task)
        raise ValueError(f"不支持的任务类型: {task.task_type}")

    async def astream_handle(self, task: Task, **kwargs) -> AsyncGenerator:
        """流式处理工作流相关任务

        Args:
            task: 任务对象
            **kwargs: 额外参数，包含plugins

        Yields:
            流式处理结果，可以是字典、字符串或消息对象
        """
        # 从kwargs中获取plugins
        self.workflows = kwargs.get("workflows", [])
        self.llm = kwargs.get("llm")
        if task.task_type == TaskType.WORKFLOW_START:
            if task.sub_task_type == TaskSubType.STARTED_FROM_REACT:
                async for react_res in self.stream_handle_workflow_start_from_react(
                    task
                ):
                    yield react_res
            if task.sub_task_type == TaskSubType.STARTED_FROM_CONTROLLER:
                async for (
                    controller_res
                ) in self.stream_handle_workflow_start_from_controller(task):
                    yield controller_res
            if task.sub_task_type == TaskSubType.STARTED_FROM_PLAN_EXECUTE:
                async for pe_res in self.stream_handle_workflow_from_plan_execute(task):
                    yield pe_res
        elif task.task_type == TaskType.WORKFLOW_MESSAGE:
            for wf_msg in self._handle_workflow_message(task):
                yield wf_msg
        elif task.task_type == TaskType.WORKFLOW_RESUME:
            pass
        else:
            error_msg = f"不支持的任务类型: {task.task_type}"
            yield {"type": "error", "content": error_msg}
            yield Message(
                message_type=MessageType.ERROR,
                content=error_msg,
                runtime_data={"task_id": task.id, "error": error_msg},
            )

    async def execute_workflow_from_function_call(
        self, workflow, function_call, **kwargs
    ):
        """执行工作流工具调用"""
        arguments = function_call.get("arguments")
        start_time = time.time()
        function_exec_res = self._exec_workflow(workflow, arguments, **kwargs)
        exec_latency = round(time.time() - start_time, 2)
        return function_exec_res, exec_latency

    async def stream_wrap_result(
        self,
        workflow_name,
        function_call,
        exec_result,
        exec_latency,
        time_dict,
        **kwargs,
    ):
        """执行工作流流式输出"""
        async for output in self._post_process_stream_workflow(
            workflow_name, function_call, exec_result, time_dict
        ):
            if not isinstance(output, tuple):
                yield output
                continue

            total_result, answer = output
            if total_result:
                time_dict["total_latency"] += total_result.get(LATENCY, 0.0)
                yield {
                    "function_call": function_call,
                    "time_consumption": TimerInfo(**time_dict),
                    "is_workflow": True,
                }
                yield {
                    "plugin_name": workflow_name,
                    "function_name": function_call.get(NAME),
                    "result": total_result.get("result"),
                    "latency": total_result.get("latency"),
                }
            self.context_manager.set_result_message(answer)
            self.context_manager.add_function_message(
                workflow_name,
                workflow_name,
                answer,
                role=FUNCTION_ROLE,
                tool_call_id=function_call.get("tool_call_id", ""),
            )

    async def stream_handle_workflow_start_from_controller(
        self, task
    ) -> AsyncGenerator[StreamData | Message | Any, None]:
        """处理来自控制器的工作流启动任务的流式输出"""
        workflow_context: WorkflowContext = task.workflow_context
        workflow_req_params = task.input_data.get(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
        )
        # Fallback: if not in task.input_data, get from context_manager
        # (controller_planner stores it as a global variable).
        if not workflow_req_params:
            workflow_req_params = self.context_manager.get_global_variables(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
            )

        # 处理非顺序执行的工作流
        if not self._has_workflow_sequence():
            gen = self._handle_non_sequential_workflow(
                workflow_context, workflow_req_params
            )
            while True:
                try:
                    yield next(gen)
                except StopIteration as e:
                    interrupted = e.value
                    if interrupted:
                        return
                    break

        # 准备工作流执行参数
        workflow_req_params = self.prepare_workflow_params(
            workflow_req_params, workflow_context
        )
        global_variables = workflow_req_params.get("global_variables")
        logger.info(
            f"task_id: {self.task_id}| Workflow {workflow_context.workflow_name} request params with "
            f"global vars: {global_variables}"
        )

        # 调用流式执行逻辑
        async for exe_res in self._stream_execute_workflow(
            task, workflow_context, workflow_req_params
        ):
            yield exe_res

    async def stream_handle_workflow_start_from_react(
        self, task
    ) -> AsyncGenerator[Any, None]:
        """处理来自知识型Agent的工作流启动任务的流式输出"""
        workflow_context: WorkflowContext = task.workflow_context
        function_call, runtime_data, time_dict = self._extract_react_task_data(
            task.input_data
        )
        async for output in self._stream_handle_workflow_from_function_call(
            workflow_context=workflow_context,
            function_call=function_call,
            runtime_data=runtime_data,
            time_dict=time_dict,
            emit_blocked=False,
            query="",
            conversation_id=task.input_data.get("conversation_id", ""),
        ):
            yield output

    async def stream_handle_workflow_from_plan_execute(
        self, task
    ) -> AsyncGenerator[Any, None]:
        """处理来自 PlanExecute 的工作流启动任务流式输出"""
        workflow_context: WorkflowContext = task.workflow_context
        workflow_name = workflow_context.workflow_name
        workflow_req_params = (
            task.input_data.get(WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY) or {}
        )
        workflow_req_params = self.prepare_workflow_params(
            workflow_req_params, workflow_context, use_all_history=True
        )

        # 把完整的工具参数注入 global_variables
        arguments = task.input_data.get("arguments", {})
        if arguments and isinstance(arguments, dict):
            global_variables = workflow_req_params.get("global_variables", {})
            if not isinstance(global_variables, dict):
                global_variables = {}
            for key, value in arguments.items():
                if key != "query":
                    global_variables[key] = value
            workflow_req_params["global_variables"] = global_variables

        final_answer = None
        async for exe_res in self._stream_execute_workflow(
            task, workflow_context, workflow_req_params, from_pe=True
        ):
            # 拦截完成消息，提取 final_answer
            if isinstance(exe_res, Message) and exe_res.is_workflow_completion:
                content = exe_res.content
                if isinstance(content, dict):
                    final_answer = content.get("exec_res", {}).get("answer", "")
            
            # 为 StreamData 类型的事件添加 sub_workflow 标识，便于前端归类显示
            # 子工作流的输出不应该混入父步骤的执行过程中
            if isinstance(exe_res, StreamData):
                if exe_res.data and isinstance(exe_res.data, dict):
                    # 添加子工作流标识，前端可据此判断是否为嵌套的工作流输出
                    exe_res.data["sub_workflow"] = workflow_name
                    exe_res.data["sub_workflow_id"] = workflow_context.workflow_id
            
            yield exe_res

        # 工作流完成后写入 context_manager tool_message（参考 react）
        if final_answer:
            tool_call_id = task.input_data.get("tool_call_id", "")
            self.context_manager.add_function_message(
                workflow_context.workflow_name,
                workflow_context.workflow_name,
                final_answer,
                role=FUNCTION_ROLE,
                tool_call_id=tool_call_id,
            )

    async def stream_execute_workflow_for_intent_detection(
        self,
        workflow_input: dict,
        workflow_context: WorkflowContext,
        conversation_id: str,
    ) -> AsyncGenerator[StreamData | Message | Any, None]:
        """为意图识别专门提供的工作流流式执行方法"""
        try:
            # 创建工作流实例
            user_id = request_json.get().get("userId", "")
            workflow_instance = await self.create_workflow_instance(
                self._attach_agent_id_to_workflow_context(workflow_context),
                conversation_id,
                user_id,
            )

            # 初始化工作流状态（简化版，不需要完整的生命周期管理）
            workflow_status = self.initialize_workflow_status()

            # 流式执行工作流
            async for result in self._stream_handle_workflow_execute(
                workflow_input,
                workflow_context,
                workflow_instance,
                workflow_status,
                is_intent_workflow=True,
            ):
                yield result

            logger.info(
                f"Intent detection workflow {workflow_context.workflow_name} executed successfully"
            )

            self._handle_workflow_interruption(
                workflow_context, workflow_instance, workflow_status
            )

            # 生成最终状态消息 —— 不需要在意图模块流出
            self._generate_final_status_message(
                workflow_context, workflow_instance, workflow_status
            )
        except Exception as e:
            logger.error(
                f"Intent detection workflow {workflow_context.workflow_name} failed, returning empty result for LLM fallback: {e}",
                simple_log="Intent detection workflow failed, returning empty result",
            )
            # 对于意图识别工作流，执行失败时不抛出异常，直接返回（不 yield 任何内容）
            # 上层 _parse_workflow_output 会检测到空结果并触发 LLM fallback
            return
        finally:
            await self._cleanup_workflow_instance(workflow_instance)

    def prepare_workflow_params(
        self,
        workflow_req_params: dict,
        workflow_context: WorkflowContext,
        use_all_history: bool = False,
    ) -> dict:
        """准备工作流执行所需的参数"""
        # 获取并过滤全局变量
        self._prepare_global_variables(workflow_req_params)
        raw_history = self.context_manager.get_message_by_intent(
            workflow_context.workflow_name if not use_all_history else None
        )
        workflow_req_params[_WORKFLOW_CHAT_HISTORY_KEY] = self._filter_workflow_history(
            raw_history
        )
        workflow_req_params[CONTROLLER_MODE_SWITCH] = True

        # 获取上上条user message的intent
        previous_intent = self.context_manager.get_second_latest_user_intent()
        current_intent = workflow_context.workflow_name

        # 判断是否跳转
        is_jumped = False
        if previous_intent is None:
            # 第一条或第二条query，没有跳转
            is_jumped = False
        else:
            is_jumped = current_intent != previous_intent

        workflow_req_params[CONTROLLER_MODE_JUMP] = is_jumped
        return workflow_req_params

    # ========== 以下是保护方法 (protected methods) ==========

    def _check_user_interact(
        self, workflow_instance, questioner_interrupted: bool
    ) -> bool:
        """检查是否为用户交互状态"""
        return (
            (
                self._get_workflow_execute_status(workflow_instance)
                == ExecutionStatus.USER_INTERACT
            )
            or questioner_interrupted
            or getattr(workflow_instance, "_questioner_interrupted", False)
        )

    async def _handle_user_interact_state(
        self,
        workflow_context: WorkflowContext,
        workflow_instance,
        exec_result,
        emit_blocked: bool,
        query: str,
    ) -> AsyncGenerator[Any, None]:
        """处理用户交互中断状态"""
        workflow_id = workflow_context.workflow_id
        current_node = NodeExecutionInfo(
            node_id="",
            node_name="",
            node_type="",
            execution_id="",
            workflow_id=workflow_id,
            workflow_name=workflow_context.workflow_name,
        )
        exec_result_data = exec_result.get("data", {})
        workflow_state = exec_result_data.get("workflow_state", "")
        if workflow_state == "running":
            exec_result_data_answer = exec_result_data.get("answer", {})
            current_node.node_id = exec_result_data_answer.get("node_id", "")
            current_node.node_type = exec_result_data_answer.get("node_type", "")

        self.context_manager.update_workflow_status(
            workflow_id, workflow_context.type, WorkflowStatus.INTERRUPTED, current_node
        )
        self.context_manager.set_workflow_state(
            workflow_id,
            workflow_context.type,
            self._get_workflow_state(workflow_instance),
        )
        yield MessageConverter.create_workflow_interrupt_from_questioner_message(
            workflow_name=workflow_id, exec_res=exec_result
        )
        if emit_blocked:
            current_node = NodeExecutionInfo(
                node_id="",
                node_name="",
                node_type="",
                execution_id=self.task_id,
                workflow_id=workflow_context.workflow_id,
                workflow_name=workflow_context.workflow_name,
            )
            yield StreamData(
                code=StreamCode.WORKFLOW_BLOCKED_MESSAGE.value,
                msg="workflow_blocked_message",
                data=WorkflowHandler.create_workflow_jump_debug_data(
                    query, workflow_context.workflow_name, current_node
                ),
                execution_id=self.task_id,
            )

    async def _stream_handle_workflow_from_function_call(
        self,
        workflow_context: WorkflowContext,
        function_call: Dict[str, Any],
        runtime_data: Dict[str, Any],
        time_dict: Dict[str, Any],
        emit_blocked: bool,
        query: str,
        conversation_id: str = "",
    ) -> AsyncGenerator[Any, None]:
        """复用 function_call 流式执行逻辑"""
        self._init_time_dict(time_dict)
        req_data = request_json.get()
        workflow_instance = await self.create_workflow_instance(
            self._attach_agent_id_to_workflow_context(workflow_context),
            conversation_id,
            req_data.get("userId", ""),
        )
        questioner_interrupted = False
        last_exec_item = None

        function_call_or_interactive_input = (
            self._transform_function_call_to_interactive_input(
                function_call, workflow_context
            )
        )

        async def _tap_exec_result(gen: AsyncGenerator):
            nonlocal questioner_interrupted, last_exec_item
            async for item in gen:
                if isinstance(item, dict):
                    last_exec_item = item
                    answer_data = (
                        item.get("data", {}).get(WORKFLOW_ANSWER)
                        or item.get("data", {}).get("answer")
                        or {}
                    )
                    if isinstance(answer_data, dict) and (
                        answer_data.get("should_interrupt")
                        or answer_data.get("node_type") == NodeType.QUESTIONER.value
                    ):
                        questioner_interrupted = True
                yield item

        try:
            exec_result, exec_latency = await self.execute_workflow_from_function_call(
                workflow_instance, function_call_or_interactive_input, **runtime_data
            )
            async for wrapped_res in self.stream_wrap_result(
                workflow_context.workflow_id,
                function_call,
                _tap_exec_result(exec_result),
                exec_latency,
                time_dict,
                **runtime_data,
            ):
                yield wrapped_res

            exec_res_dict = last_exec_item or {}
            if self._check_user_interact(workflow_instance, questioner_interrupted):
                async for msg in self._handle_user_interact_state(
                    workflow_context,
                    workflow_instance,
                    exec_res_dict,
                    emit_blocked,
                    query,
                ):
                    yield msg
            else:
                self.context_manager.update_workflow_status(
                    workflow_context.workflow_id,
                    workflow_context.type,
                    WorkflowStatus.COMPLETED,
                )
                self.context_manager.set_workflow_state(
                    workflow_context.workflow_id, workflow_context.type, None
                )
                yield MessageConverter.create_workflow_completion_message(
                    workflow_context=workflow_context, exec_res=exec_res_dict
                )
        finally:
            await self._cleanup_workflow_instance(workflow_instance)

    @staticmethod
    def _transform_function_call_to_interactive_input(function_call, workflow_context):
        function_call_or_interactive_input = copy.deepcopy(function_call)

        if workflow_context.status == WorkflowStatus.INTERRUPTED:
            user_feedback_query = function_call.get("arguments", "")
            try:
                user_feedback_dict = json.loads(user_feedback_query)
                if user_feedback_dict:
                    user_feedback = list(user_feedback_dict.values())[0]
                    # 始终使用 raw_inputs 路由，原因同 _stream_execute_workflow：
                    # Loop 内 QA 节点的 executable_id 含前缀，user_inputs 路由的
                    # comp_state key 不匹配，导致恢复时读不到用户回复。
                    interactive_input = InteractiveInput(raw_inputs=user_feedback)
                    function_call_or_interactive_input.update(
                        {"arguments": {"query": interactive_input}}
                    )
            except json.decoder.JSONDecodeError:
                logger.error("Failed to parse user feedback")

        return function_call_or_interactive_input

    def _handle_workflow_start(self, task: Task) -> Message:
        """处理工作流启动

        Args:
            task: 任务对象
            context: 当前上下文

        Returns:
            处理结果消息
        """
        pass

    def _handle_workflow_resume(self, task: Task) -> Message:
        pass

    def _handle_workflow_completion(self, task: Task) -> Message:
        pass

    def _handle_workflow_message(self, task: Task) -> Generator:
        fix_response = task.input_data.get(WorkflowConstants.WORKFLOW_FIXED_RESPONSE)
        terminate = task.input_data.get("termination")
        action = task.input_data.get("action")
        yield MessageConverter.create_end_message_from_controller_message(
            fix_message=fix_response, terminate=terminate, action=action
        )

    def _generate_workflow_resume_message(
        self, query: str, workflow_context: WorkflowContext
    ) -> Generator[StreamData, None, None]:
        """发送工作流恢复流式数据"""
        current_intent = workflow_context.workflow_name
        intent_status = workflow_context.status
        resume_node = workflow_context.current_node_info
        # 发送workflow_resume事件
        intent_in_history = self.context_manager.engine.history.has_intent_in_history(
            current_intent
        )
        if intent_in_history and intent_status == WorkflowStatus.INTERRUPTED:
            workflow_resume_data = WorkflowHandler.create_workflow_jump_debug_data(
                query, current_intent, resume_node
            )
            yield StreamData(
                code=StreamCode.WORKFLOW_RESUME_MESSAGE.value,
                msg="workflow_resume_message",
                data=workflow_resume_data,
                execution_id=self.task_id,
            )

    async def _stream_execute_workflow(
        self,
        task: Task,
        workflow_context: WorkflowContext,
        workflow_req_params: dict,
        from_pe: bool = False,
    ) -> AsyncGenerator[StreamData | Message | Any, None]:
        """流式执行工作流的完整逻辑，包含状态管理和生命周期处理"""
        # 发送恢复消息
        query = task.input_data.get("query", "")
        for resume_chunk in self._generate_workflow_resume_message(
            query, workflow_context
        ):
            yield resume_chunk
        # 执行工作流
        workflow_status = self.initialize_workflow_status()
        workflow_input = self.create_workflow_input(task, workflow_req_params)
        # 注入中断恢复信息：构建 InteractiveInput 替代原始 query
        if workflow_context.status == WorkflowStatus.INTERRUPTED:
            user_query = workflow_input.get("inputs", query)
            # 始终使用 raw_inputs 路由，原因与 SubWorkflow 场景一致：
            # user_inputs 路由依赖 node_id 匹配 executable_id，但当 QA 节点位于
            # Loop 内部时，executable_id 含 Loop 前缀（如 "Loop_xxx.node_id"），
            # 而 current_node_info.node_id 仅为基础 node_id（不含前缀），导致
            # comp_state key 不匹配，QA 节点恢复时读不到用户回复。
            # raw_inputs 写入 workflow_state（全局共享），QA 节点的
            # WorkflowInteraction 通过 get_workflow_state 读取，不依赖
            # executable_id 匹配。工作流一次只有一个节点处于 USER_INTERACT
            # （pregel 引擎保证），因此 raw_inputs 广播不会导致误投递。
            interactive_input = InteractiveInput(raw_inputs=user_query)
            workflow_input["inputs"] = interactive_input
        current_node = NodeExecutionInfo(
            node_id="",
            node_name="",
            node_type="",
            execution_id="",
            workflow_id=workflow_context.workflow_id,
            workflow_name=workflow_context.workflow_name,
        )
        user_id = request_json.get().get("userId", "")
        # 创建工作流实例
        workflow_instance = await self.create_workflow_instance(
            self._attach_agent_id_to_workflow_context(workflow_context),
            task.input_data.get("conversation_id", ""),
            user_id,
        )
        try:
            async for exec_res in self._stream_handle_workflow_execute(
                workflow_input,
                workflow_context,
                workflow_instance,
                workflow_status,
                current_node,
                from_pe=from_pe,
            ):
                yield exec_res

            logger.info(
                f"task_id: {self.task_id}| Stream execute workflow current_node: {current_node}, "
                f"workflow_status: {workflow_status}"
            )

            # 处理中断状态
            self._handle_workflow_interruption(
                workflow_context, workflow_instance, workflow_status, current_node
            )

            # 生成最终状态消息
            async for final_stat_msg in self._generate_final_status_message(
                workflow_context,
                workflow_instance,
                workflow_status,
                query,
                current_node,
            ):
                yield final_stat_msg
        finally:
            # 无论成功、失败还是中断，都同步 _REQUEST 变量
            self._sync_request_variables(workflow_instance)
            await self._cleanup_workflow_instance(workflow_instance)

    def _has_workflow_sequence(self) -> bool:
        """检查是否存在工作流序列"""
        return bool(
            self.context_manager.get_global_variables(
                WorkflowConstants.VALID_WORKFLOW_SEQUENCE_KEY
            )
        )

    def _handle_non_sequential_workflow(
        self, workflow_context: WorkflowContext, workflow_req_params: dict
    ) -> Generator[Message, None, bool]:
        """处理非顺序执行的工作流，返回是否中断"""
        question, extracted_key_fields_dict = self._handle_missing_params(
            workflow_context
        )

        if question:
            self.context_manager.add_assistant_message(
                content=question, intent=workflow_context.workflow_name
            )
            yield MessageConverter.create_workflow_interrupt_from_controller_message(
                workflow_name=workflow_context.workflow_name, question=question
            )
            return True

        # 更新全局变量
        if extracted_key_fields_dict:
            self._update_global_variables(
                workflow_req_params, extracted_key_fields_dict
            )

        return False

    def _update_global_variables(
        self, workflow_req_params: dict, extracted_fields: dict
    ) -> None:
        """更新工作流请求参数中的全局变量"""
        global_variables = workflow_req_params.get("global_variables", {})
        global_variables.update(extracted_fields)
        workflow_req_params["global_variables"] = global_variables
        self.context_manager.set_global_variables(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, workflow_req_params
        )

    def _prepare_global_variables(self, workflow_req_params):
        def _filter_none(d: dict[str, Any] | None) -> dict[str, Any]:
            """过滤字典中的None值"""
            return {k: v for k, v in (d or {}).items() if v is not None}

        # 获取全局变量并过滤掉None值
        global_variables = _filter_none(workflow_req_params.get("global_variables", {}))

        # 获取现有的controller_variables
        raw_controller_vars = (
            self.context_manager.get_global_variables(
                WorkflowConstants.CONTROLLER_GLOBAL_VARIABLES_KEY
            )
            or {}
        )
        controller_variables = _filter_none(raw_controller_vars)

        # 调用工作流前从context_manager获取全局变量 request_variables，传入workflow_req_params
        request_variables = _filter_none(
            self.context_manager.get_global_variables(REQUEST_VARIABLES)
        )

        # 创建合并后的变量字典（取并集）
        # 优先级：request_variables > global_variables > controller_variables
        merged_variables = controller_variables.copy()  # 先复制controller_variables

        # 将global_variables中的非None值合并进去
        for key, value in global_variables.items():
            merged_variables[key] = value

        for key, value in request_variables.items():
            merged_variables[key] = value

        # 只更新controller_global_variables 中已有键的值，避免用整个merged_variables 覆盖导致原始键丢失
        self.context_manager.set_global_variables(
            WorkflowConstants.CONTROLLER_GLOBAL_VARIABLES_KEY,
            {k: merged_variables.get(k, v) for k, v in raw_controller_vars.items()},
        )

        if self.context_manager.memory_enable:
            merged_variables["userId"] = request_json.get().get("userId", "")

        # 更新workflow_req_params中的global_variables为合并后的结果
        workflow_req_params["global_variables"] = merged_variables

    def _handle_workflow_interruption(
        self,
        workflow_context: WorkflowContext,
        workflow_instance: SpiffWorkflowControllerWorkflow,
        workflow_status: dict,
        current_node: Optional[NodeExecutionInfo] = None,
    ) -> None:
        """处理工作流中断状态"""
        if (
            workflow_status["questioner_interrupted"]
            or workflow_status["intention_detection_interrupted"]
        ):
            self.context_manager.update_workflow_status(
                workflow_context.workflow_id,
                workflow_context.type,
                WorkflowStatus.INTERRUPTED,
                current_node,
            )
            self.context_manager.set_workflow_state(
                workflow_context.workflow_id,
                workflow_context.type,
                self._get_workflow_state(workflow_instance),
            )

    def _update_node_execution_info(
        self, output, node_execution_info: NodeExecutionInfo
    ) -> None:
        if output and output.data and node_execution_info:
            node_execution_info.node_id = output.data.get("node_id")
            node_execution_info.node_name = output.data.get("node_name")
            node_execution_info.node_type = output.data.get("node_type")
            node_execution_info.execution_id = output.execution_id

    async def _stream_handle_workflow_execute(
        self,
        workflow_input,
        workflow_context,
        workflow_instance,
        workflow_status,
        current_node: Optional[NodeExecutionInfo] = None,
        is_intent_workflow=False,
        from_pe: bool = False,
    ):
        """处理workflow实例的流式消息

        Args:
            is_intent_workflow:
        """
        # 处理工作流流式输出
        result = await workflow_instance.astream(**workflow_input)
        if isinstance(result, Message):
            logger.info(
                f"task_id: {self.task_id}| Message detected in workflow stream: {result}",
                simple_log="Message detected in workflow stream",
            )
            # 检测意图识别中断
            if result.message_type == MessageType.WORKFLOW_INTERRUPT:
                workflow_status["intention_detection_interrupted"] = True
            yield result
        else:
            async for output in result:
                # 拦截workflow流出的INTERMEDIATE_MESSAGE
                if output.code == StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value:
                    logger.debug(
                        f"drop workflow intermediate_message data: {output}",
                        simple_log="drop workflow intermediate_message data",
                    )
                    continue
                # 检测工作流结束
                if (
                    output.data.get("node_type") == WORKFLOW_END_TYPE
                    and output.code == StreamCode.FINISH.value
                ):
                    workflow_status["workflow_end"] = True
                    # end组件输出更新写入controller global variables全局变量
                    logger.info(
                        f"task_id: {self.task_id}| End Message detected in workflow stream: {output.data}",
                        simple_log="End Message detected in workflow stream",
                    )
                    action_after_completion_val = output.data.get(
                        "user_fields", {}
                    ).get("action_after_completion")
                    # 更新 controller global variables
                    self._update_output_global_variables(
                        output.data.get("user_fields", {})
                    )
                    # 同步global_varibales到runtime_context.request_variables
                    self._update_output_global_variables_for_request(
                        output.data.get("user_fields", {}), workflow_instance
                    )
                    controller_global_variables = (
                        self.context_manager.get_global_variables(
                            "controller_global_variables"
                        )
                    )
                    if not action_after_completion_val and controller_global_variables:
                        action_after_completion_val = controller_global_variables.get(
                            "action_after_completion", ""
                        )
                    action_after_completion = ActionAfterCompletionType.from_string(
                        action_after_completion_val
                    )
                    if (
                        action_after_completion
                        and action_after_completion
                        != workflow_context.action_after_completion
                    ):
                        workflow_context.action_after_completion = (
                            action_after_completion
                        )
                # 检测提问器中断，不会上报中断消息，后续统一逻辑
                elif (
                    output.data.get("should_interrupt", False)
                    or output.data.get("node_type") == NodeType.QUESTIONER.value
                ):
                    workflow_status["questioner_interrupted"] = True
                elif output.data.get("node_type") == NodeType.QA.value:
                    logger.info(
                        f"task_id: {self.task_id}| QA Message detected in workflow stream: {output}",
                        simple_log="QA Message detected in workflow stream",
                    )
                    if output.data.get("need_reply", True):
                        workflow_status["questioner_interrupted"] = True
                if output.msg == StreamDataMsg.MESSAGE_END.value:
                    self.__process_message_end_event(
                        output,
                        is_intent_workflow,
                        workflow_context,
                        current_node,
                        workflow_status,
                        from_pe=from_pe,
                    )
                # 流式输出添加workflow_id和workflow_name字段
                if output.data:
                    output.data["workflow_id"] = workflow_context.workflow_id
                    output.data["workflow_name"] = workflow_context.workflow_name
                # 转发所有输出
                yield output

    def __process_message_end_event(
        self,
        output,
        is_intent_workflow,
        workflow_context,
        current_node,
        workflow_status,
        from_pe: bool = False,
    ):
        """process message end event"""
        # 如果存在结构化消息，需要将原始信息存入上下文
        # PE 模式下end节点不写入 context_manager，直接使用累积的工作流结果
        content = output.data.get(ORIGIN_ANSWER) or output.data.get(ANSWER)
        if not content or is_intent_workflow:
            self._update_node_execution_info(output, current_node)
            return
        enable_history = output.data.get("enable_history", True)
        if not from_pe and enable_history:
            self.context_manager.add_assistant_message(
                content=content, intent=workflow_context.workflow_name
            )
        if workflow_status is not None:
            has_parent = output.data.get("parentNodeId", "")
            is_questioner = (
                output.data.get("node_type", "") == NodeType.QUESTIONER.value
            )
            if not has_parent or is_questioner:
                workflow_status.setdefault("final_answer", []).append(content)
        # 更新节点信息
        self._update_node_execution_info(output, current_node)

    async def _generate_final_status_message(
        self,
        workflow_context,
        workflow_instance,
        workflow_status,
        query: Optional[str] = None,
        current_node: Optional[NodeExecutionInfo] = None,
    ):
        # 根据最终状态生成相应消息
        if workflow_status["workflow_end"]:
            self.context_manager.update_workflow_status(
                workflow_context.workflow_id,
                workflow_context.type,
                WorkflowStatus.COMPLETED,
                current_node,
            )
            self.context_manager.set_workflow_state(
                workflow_context.workflow_id, workflow_context.type, None
            )
            yield MessageConverter.create_workflow_completion_message(
                workflow_context=workflow_context,
                exec_res={"answer": "".join(str(x) for x in workflow_status.get("final_answer", []))},
            )

        if workflow_status["questioner_interrupted"]:
            yield MessageConverter.create_workflow_interrupt_from_questioner_message(
                workflow_name=workflow_context.workflow_name, exec_res={}
            )
            # 发送workflow_blocked事件
            if current_node:
                workflow_blocked_data = WorkflowHandler.create_workflow_jump_debug_data(
                    query, workflow_context.workflow_name, current_node
                )
                yield StreamData(
                    code=StreamCode.WORKFLOW_BLOCKED_MESSAGE.value,
                    msg="workflow_blocked_message",
                    data=workflow_blocked_data,
                    execution_id=self.task_id,
                )

    def _handle_missing_params(self, workflow_context):
        workflow_name = workflow_context.workflow_name
        properties = workflow_context.workflow_parameters.get("parameters", {}).get(
            "properties", {}
        )
        # 初始化missing_parameters，排除query参数
        missing_parameters = {
            key: value.get("description", "")
            for key, value in properties.items()
            if value.get("required", False) and key not in ("query", "sys")
        }
        # 获取workflow_req_params
        workflow_req_params = self.context_manager.get_global_variables(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
        )

        # 获取globalVariables
        global_variables = workflow_req_params.get("global_variables", {})
        if global_variables is None:
            global_variables = {}
        # 更新missing_parameters：移除已在globalVariables中的参数
        missing_parameters = {
            key: value
            for key, value in missing_parameters.items()
            if global_variables.get(key) is None
        }
        logger.info(
            f"task_id: {self.task_id}| missing_params: {missing_parameters}",
            simple_log="missing_params update successfully",
        )
        # 如果没有缺失参数，直接返回
        if not missing_parameters:
            return None, global_variables

        self.extract_params = ExtractParams(
            tools=[], llm=self.llm, context_manager=self.context_manager
        )
        task_id = self.context_manager.agent_config.task_id

        extract_param_context = {
            "conversation_id": task_id,
            "missing_parameters": missing_parameters,
            "workflow_name": workflow_name,
            "prompt_template": None,
        }

        question, extracted_fields = self.extract_params.invoke(
            context=extract_param_context
        )
        return question, extracted_fields

    def _update_output_global_variables(self, end_user_fields):
        controller_global_variables = self.context_manager.get_global_variables(
            "controller_global_variables"
        )
        if controller_global_variables is None or not end_user_fields:
            return
        is_updated = False
        updated_keys = []
        for key, value in end_user_fields.items():
            if key and key in controller_global_variables:
                controller_global_variables.update({key: value})
                is_updated = True
                updated_keys.append(key)
        if is_updated:
            self.context_manager.set_global_variables(
                "controller_global_variables", controller_global_variables
            )
            # 同步更新 workflow_req_params 中的 global_variables 和 context_manager 中的
            # REQUEST_VARIABLES，避免后续子工作流 _prepare_global_variables 合并时被旧值覆盖
            self._sync_end_fields_to_shared_stores(
                controller_global_variables, updated_keys
            )
            logger.info(
                f"task_id: {self.task_id}| controller global variables updated from end output: "
                f"{controller_global_variables}",
                simple_log=f"task_id: {self.task_id}| controller global variables updated from end output: "
                "controller_global_variables",
            )

    def _sync_end_fields_to_shared_stores(
        self, controller_global_variables: dict, updated_keys: list
    ) -> None:
        """end 节点更新 controller_global_variables 后，同步到跨工作流共享的两个存储：
        1. workflow_req_params["global_variables"]：意图流 _prepare_global_variables 时会把
           "意图流入前的 merged 值"冻结到这里，end 节点必须覆盖同名 key，否则子工作流
           prepare 时会用旧 global 覆盖 controller 的新值。
        2. context_manager 的 REQUEST_VARIABLES：意图流 finally 不 sync（只有子工作流
           finally 会 sync），因此 end 节点必须主动同步，否则子工作流 prepare 时
           request_variables（优先级最高）会把 merged 覆盖回旧值。
        """
        if not updated_keys:
            return

        req_params = self.context_manager.get_global_variables(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
        )
        if isinstance(req_params, dict):
            global_variables = req_params.get("global_variables")
            if not isinstance(global_variables, dict):
                global_variables = {}
                req_params["global_variables"] = global_variables
            for key in updated_keys:
                if key in controller_global_variables:
                    global_variables[key] = controller_global_variables[key]
            self.context_manager.set_global_variables(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, req_params
            )

        ctx_request_variables = self.context_manager.get_global_variables(
            REQUEST_VARIABLES
        )
        if not isinstance(ctx_request_variables, dict):
            ctx_request_variables = {}
        for key in updated_keys:
            if key in controller_global_variables:
                ctx_request_variables[key] = controller_global_variables[key]
        self.context_manager.set_global_variables(
            REQUEST_VARIABLES, ctx_request_variables
        )

    def _update_output_global_variables_for_request(
        self, end_user_fields, workflow_instance
    ):
        """更新 global variables 同步到 runtime_context.request_variables

        Args:
            end_user_fields: 需要更新的字段字典
            workflow_instance: 工作流实例，用于访问 runtime_context
        """
        if not end_user_fields:
            return

        runtime_context = self._get_workflow_runtime_context(workflow_instance)

        if not runtime_context:
            return

        request_variables = runtime_context.get(REQUEST_VARIABLES)
        if request_variables is None:
            return

        is_updated = False
        for key, value in end_user_fields.items():
            if key and key in request_variables:
                request_variables.update({key: value})
                is_updated = True
        if is_updated:
            runtime_context.set(REQUEST_VARIABLES, request_variables)
            logger.info(
                f"task_id: {self.task_id}| request global variables updated from end output: "
                f"{request_variables}",
                simple_log=f"task_id: {self.task_id}| request global variables updated from end output",
            )

    def _extract_react_task_data(self, input_data: dict) -> tuple:
        """提取React任务的输入数据，处理函数调用参数"""
        function_call = input_data.get("function_call")
        runtime_data = input_data.get("runtime_data")
        time_dict = input_data.get("time_dict")
        # 处理workflow参数对于记忆变量和输入变量的引用
        function_call = self._merge_workflow_arguments(function_call, runtime_data)

        # 处理函数参数 - 这部分逻辑无法复用，需要保留
        args = function_call.get("arguments", "{}")
        check_result, trans_result = ModelUtil.check_and_trans2json(args)
        if not check_result:
            raise JiuWenBaseException(
                JiuWenBaseExceptionStatusCode.INVOKABLE_JSON_ILLEGAL.code,
                "Invalid arguments format: must be valid JSON",
            )

        function_call["arguments"] = json.dumps(trans_result, ensure_ascii=False)

        return function_call, runtime_data, time_dict

    def _merge_workflow_arguments(
        self, function_call: Dict[str, Any], runtime_data: Dict[str, Any]
    ):
        """
        根据工作流定义（workflow.arguments）和 input_parameters 规则，
        为 function_call['arguments'] 补全缺失的嵌套参数。

        规则：
        1. 解析 function_call['arguments'] 为字典。
        2. 从 runtime_data['workflows'] 中找到与 function_call['name'] 匹配的工作流。
        3. 递归遍历该工作流的 arguments（支持 schema 嵌套），收集所有叶子参数路径（如 "a.b.c"）。
        4. 对每个叶子路径：
            - 若 function_call 已提供有效值（非 None 且非空字符串），则保留；
            - 否则，检查 workflow.input_parameters 是否包含该路径：
                - 若包含，则解析模板（如 "{{inputs.x}}" 或 "{{memory.y}}"），从上下文取值；
                - 若不包含，则使用 arguments 中该叶子的 defaultValue。
        5. 将补齐后的参数重新序列化为 JSON 字符串，写回 function_call。
        """
        # 1. 解析当前 arguments（可能为 JSON 字符串）
        try:
            current_args = json.loads(function_call["arguments"])
            if not isinstance(current_args, dict):
                current_args = {}
        except (json.JSONDecodeError, TypeError) as e:
            raise JiuWenBaseException(
                JiuWenBaseExceptionStatusCode.INVOKABLE_JSON_ILLEGAL.code,
                "Invalid arguments format: must be valid JSON",
            ) from e

        # 2. 查找匹配的工作流（按名称）
        workflow_name = function_call.get("name", None)
        workflows = runtime_data.get("workflows", []) if runtime_data else []
        matched_workflow = None
        for wf in workflows:
            if wf.workflow_ir.get("workflowName") == workflow_name:
                matched_workflow = wf
                break

        if not matched_workflow:
            return function_call

        # 3. 获取工作流的参数定义和输入映射
        workflow_arguments = getattr(matched_workflow, "arguments", []) or []
        input_parameters = getattr(matched_workflow, "input_parameters", {}) or {}

        # 4. 获取全局上下文变量
        agent_inputs = self.context_manager.get_global_variables("agent_inputs") or {}
        memory_variables = (
            self.context_manager.get_global_variables("memory_variables") or {}
        )

        # 5. 递归收集所有叶子参数路径（如 "where_user_is.state.userhome"）
        leaf_nodes = self._collect_workflow_leaves(workflow_arguments)

        # 6. 从 current_args 开始构建最终结果
        result = current_args.copy()

        # 7. 为每个叶子路径补全值
        self._form_merged_arguments(
            agent_inputs, input_parameters, leaf_nodes, memory_variables, result
        )

        # 8. 序列化回 function_call
        function_call["arguments"] = json.dumps(result, ensure_ascii=False)
        return function_call

    def _form_merged_arguments(
        self, agent_inputs, input_parameters, leaf_nodes, memory_variables, result
    ):
        """获取融合后的参数"""
        for full_path, arg_config in leaf_nodes:
            # 检查是否已存在有效值
            existing_val = self._get_nested_value(result, full_path)
            if existing_val is not None and not (
                isinstance(existing_val, str) and existing_val == ""
            ):
                continue

            value = None
            # 仅当 input_parameters 显式声明了该叶子路径时，才从上下文取值
            if full_path in input_parameters:
                template = input_parameters[full_path].strip()
                if template.startswith("{{") and template.endswith("}}"):
                    inner = template[2:-2].strip()
                    if inner.startswith("inputs.") and len(inner) > 7:
                        path_in_inputs = inner[7:]
                        value = self._get_nested_value(agent_inputs, path_in_inputs)
                    elif inner.startswith("memory.") and len(inner) > 7:
                        path_in_memory = inner[7:]
                        value = self._get_nested_value(memory_variables, path_in_memory)

            # 若未从上下文取到值（或未声明），使用agent IR中的default_value
            if value is None:
                if (
                    "default_value" not in arg_config
                    or arg_config["default_value"] is None
                ):
                    continue
                value = arg_config.get("default_value")

            # 写入结果字典的对应路径
            self._set_nested_value(result, full_path, value)

    def _collect_workflow_leaves(
        self, arguments: List[Dict], prefix: str = ""
    ) -> List[tuple]:
        """
        递归遍历 workflow.arguments（每个元素是 dict），收集所有叶子节点的 (完整路径, 配置)。
        - 非叶子节点：type 为 'object' 且有 'schema' 字段（schema 是子 arguments 列表）。
        - 叶子节点：其他类型，或无 schema。
        """
        leaves = []
        for arg in arguments:
            name = arg.get("name", "")
            if not name:
                continue
            full_path = f"{prefix}.{name}" if prefix else name

            # 判断是否为嵌套对象：有 schema 且 schema 是非空列表
            schema = arg.get("schema")
            arg_type = arg.get("type", "")
            if arg_type == "object" and isinstance(schema, list) and len(schema) > 0:
                # 递归处理子字段
                leaves.extend(self._collect_workflow_leaves(schema, full_path))
            else:
                # 叶子节点：保存完整路径和配置（含 defaultValue）
                leaves.append((full_path, arg))
        return leaves

    def _prepare_workflow_kwargs(self, inputs_dict: dict, kwargs) -> None:
        """准备工作流执行的 kwargs 参数"""
        runtime_context = kwargs.get("runtime_context")
        kwargs["conversation_history"] = (
            runtime_context.agent_workflow_context.get(
                "workflow_chat_history", ConversationHistory()
            )
        ).get_all_messages()
        kwargs["plugin_configs"] = {
            "default": runtime_context.api_config.get("headers", {})
        }
        req_data = request_json.get()
        kwargs["global_variables"] = {
            "sys": {
                "conversationHistory": [],
                "conversationId": req_data.get("conversationId", ""),
                "userId": req_data.get("userId", ""),
            },
            "conversationId": req_data.get("conversationId", ""),
            "userId": req_data.get("userId", ""),
        } | inputs_dict

    async def _exec_workflow(self, workflow, inputs, **kwargs):
        """执行工作流"""
        err_func_res = dict(
            errMessage={
                WORKFLOW_ANSWER: WORKFLOW_STATE_ERROR,
                WORKFLOW_STATE: WORKFLOW_STATE_ERROR,
            },
            errCode=StatusCode.INTER_ERROR.code,
        )
        if isinstance(inputs, str):
            try:
                inputs_dict = json.loads(inputs)
            except json.JSONDecodeError:
                inputs_dict = dict()
        elif isinstance(inputs, dict):
            inputs_dict = inputs
        else:
            inputs_dict = {}

        query = inputs_dict.pop("query", "")
        if not query:
            logger.error("workflow inputs do not have any query")
            err_func_res["errMessage"][WORKFLOW_ANSWER] = (
                "workflow inputs do not have any query"
            )

        self._prepare_workflow_kwargs(inputs_dict, kwargs)
        try:
            res_generator = await workflow.astream(query, **kwargs)
            async for func_res in res_generator:
                self._check_questioner_interrupt(workflow, func_res)
                func_res = self.process_stream_output(func_res)
                if (
                    func_res.get(WORKFLOW_ANSWER, {}).get("node_type")
                    == WORKFLOW_END_TYPE
                    and func_res.get("code") == StreamCode.FINISH.value
                ):
                    func_res[WORKFLOW_STATE] = WORKFLOW_STATE_END
                yield dict(
                    data=func_res,
                    errCode=StatusCode.SUCCESS.code,
                    errMessage=StatusCode.SUCCESS.message,
                )
        except Exception as e:
            import traceback

            logger.error(
                f"Panel execute workflow error {traceback.format_exc()}",
                simple_log=f"Panel execute workflow error: {type(e)}",
            )
            err_func_res["errMessage"][WORKFLOW_ANSWER] = (
                str(e)
                if LOG_VERBOSE_MODE
                else f"Panel execute workflow error: {type(e)}"
            )
            yield err_func_res

    async def _post_process_stream_workflow(
        self, workflow_name, function_call, func_res, time_dict
    ):
        """后处理工作流流式结果"""
        report_answer, total_result = "", None
        if not isinstance(func_res, AsyncGenerator):
            yield total_result, report_answer
            return

        last_item = None
        start_time = time.time()
        async for item in func_res:
            item = dict(errCode=-1, errMessage=NON_EXIST_FUNC) if not item else item
            item_res = self._exec_func(function_call, item, None)
            last_item = item_res
            result = item_res.get(RESULT, {})

            if result.get("code") == StreamCode.MESSAGE_END.value:
                report_answer = self._extract_report_answer(result, report_answer)
                continue

            if item_res.get("error_code") != 0:
                for resp in self._build_error_response(
                    workflow_name, function_call, time_dict, item, item_res
                ):
                    yield resp
            elif self._should_yield_stream_message(result):
                yield {
                    "role": "assistant",
                    "content": result.get(ANSWER, {}).get(ANSWER),
                }

        exec_latency = round(time.time() - start_time, 2)
        workflow_state = last_item.get(RESULT, {}).get(WORKFLOW_STATE)
        if item_res.get("error_code") != 0:
            report_answer = last_item.get(RESULT, {}).get(ANSWER, {})
        else:
            total_result = {
                RESULT: {ANSWER: report_answer, WORKFLOW_STATE: workflow_state},
                LATENCY: exec_latency,
            }

        yield total_result, report_answer

    def _should_yield_stream_message(self, result: dict) -> bool:
        """判断是否应该yield流式消息"""
        if result.get("code") != StreamCode.FINISH.value:
            return False
        answer_dict = result.get(ANSWER, {})
        if not isinstance(answer_dict, dict) or not answer_dict.get(ANSWER):
            return False
        return answer_dict.get("node_type", "") != NodeType.END.value

    def _extract_report_answer(self, result: dict, current_answer: str) -> str:
        """提取并累加report_answer"""
        answer_info = result.get(ANSWER, {})
        if (
            answer_info.get("parentNodeId", "")
            and answer_info.get("node_type", "") != NodeType.QUESTIONER.value
        ):
            return current_answer
        return current_answer + (
            answer_info.get(ORIGIN_ANSWER) or answer_info.get(ANSWER, "")
        )

    def _build_error_response(
        self, workflow_name, function_call, time_dict, item, item_res
    ):
        """构建错误响应列表"""
        return [
            {
                "function_call": function_call,
                "time_consumption": TimerInfo(**time_dict),
                "is_workflow": True,
            },
            {
                "plugin_name": workflow_name,
                "function_name": function_call.get(NAME),
                "result": item,
                "latency": item_res.get("latency"),
            },
        ]

    def _create_intermediate_message(self, func_res):
        tool_msg = []
        intent_name = None
        function_call_msg = self.context_manager.get_latest_assistant_message()
        if function_call_msg:
            _function_call_msg = {
                "role": function_call_msg.role,
                "content": function_call_msg.content,
                "function_call": function_call_msg.function_call,
            }
            tool_msg.append(_function_call_msg)
            intent_name = function_call_msg.intent
        func_exec_res = func_res.get("answer", {}).get("answer", None)
        if func_exec_res:
            tool_exec_res = {
                "role": "function",
                "name": intent_name,
                "content": func_exec_res,
            }
            tool_msg.append(tool_exec_res)
        if len(tool_msg) == 2:
            intermediate_message = {"tool_msg": tool_msg}
            yield intermediate_message

    def _exec_func(self, function_call, result, exec_latency):
        """process function result"""
        if isinstance(result, dict):
            error_code = result.get("errCode")
            error_message = result.get("errMessage")
        else:
            error_code = (
                result.err_code
                if result is not None and hasattr(result, "err_code")
                else -1
            )
            error_message = (
                result.err_msg
                if result is not None and hasattr(result, "err_msg")
                else "工具执行异常"
            )

        if error_code != 0:
            output = error_message
            content = "工具执行异常"
            if isinstance(output, dict):
                content = output.get("answer")
            self.context_manager.add_function_message(
                function_call.get("name"),
                function_call.get("name"),
                content,
                role=FUNCTION_ROLE,
                tool_call_id=function_call.get("tool_call_id", ""),
            )
        else:
            output = result.get("data")
        return dict(error_code=error_code, result=output, latency=exec_latency)

    def _sync_request_variables(self, workflow_instance) -> None:
        """中断或工作流结束时同步 _REQUEST 变量从 RuntimeContext 到 ContextManager"""
        runtime_context = self._get_workflow_runtime_context(workflow_instance)

        if runtime_context:
            request_variables = runtime_context.get(REQUEST_VARIABLES)
            controller_global_variables = self.context_manager.get_global_variables(
                "controller_global_variables"
            )
            controller_global_variables = {
                k: request_variables.get(k, v)
                for k, v in (controller_global_variables or {}).items()
            }
            self.context_manager.set_global_variables(
                WorkflowConstants.CONTROLLER_GLOBAL_VARIABLES_KEY,
                controller_global_variables,
            )
            self.context_manager.set_global_variables(
                REQUEST_VARIABLES, request_variables
            )
            logger.info(
                f"task_id: {self.task_id}| REQUEST variables synced to ContextManager: {request_variables}, "
                f"controller_global_variables synced : {controller_global_variables}",
                simple_log="REQUEST variables synced to ContextManager",
            )
