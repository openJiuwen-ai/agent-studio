#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""WorkflowWrapper: 封装 agent-core Workflow，适配旧 WorkflowHandler 的调用模式。"""

import datetime
from typing import AsyncGenerator, Union, Any

from openjiuwen.core.common.logging import workflow_logger

from jiuwen.context.history import ConversationMessage, ConversationHistory
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.extension.workflow_node.utils import (
    WorkflowAbortException,
    JiuWenBaseException,
)
from jiuwen.orchestration.flow.constant import (
    REQUEST_VARIABLES,
    WORKFLOW_EXECUTE_PROJECT_ID,
    WORKFLOW_EXECUTE_USER_ID,
    WORKFLOW_API_CONFIGS,
    ENVIRONMENT_VARIABLES,
    MEMORY_VARIABLES,
    WORKFLOW_GLOBAL_INTENTS,
    MEM_MAP,
    ENABLE_MEMORY_RETRIEVE,
)
from jiuwen.orchestration.flow.enum import ChatHistoryRole
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from jiuwen.orchestration.flow.workflow import CONTROLLER_MODE_SWITCH
from openjiuwen.core.common.constants.constant import INTERACTION
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.session.stream.base import (
    OutputSchema,
    CustomSchema,
    TraceSchema,
    BaseStreamMode,
)
from openjiuwen.core.session.workflow import create_workflow_session

# 映射：调试事件返回 → service
_DEBUG_EVENT_RETURN_TO_SERVICE: dict[str, str] = {
    "FlowQA": "EI.qa",
    "LLMChain": "LLM",
    "SubWorkflow": "jiuwen.workflowComposite",
    "BranchComponent": "Branch",
    "_RoutedIntentDetection": "IntentDetection",
    "LoopComponent": "jiuwen.loop",
    "FlowApi": "Api",
    "FlowInput": "jiuwen.input",
    "ExceptionInfo": "jiuwen.exception",
    "LoopSetVariable": "jiuwen.setVariable",
    "Aggregate": "jiuwen.aggregation",
    "FlowCode": "Code",
    "EI.ComplexIntentDetection": "EI.ComplexIntentDetection",
    "jiuwen.paramExtraction": "jiuwen.paramExtraction",
    "FlowMcp": "jiuwen.mcp",
}

# 控制流节点componentId关键字，命中则跳过调试事件
_SKIP_COMPONENT_KEY: list[str] = [
    "_break_branch_",
    "_break_",
    "_loop_end_",
    "_input",
    "_output",
    "_parallel_done",
]


class WorkflowWrapper:
    """适配旧 WorkflowHandler 调用模式到新 openJiuwen Workflow。

    WorkflowWrapper 平替旧 SpiffWorkflowControllerWorkflow，使 WorkflowHandler
    从调用旧 workflow 切换到调用 WorkflowWrapper，行为等价。

    核心原则：WorkflowWrapper.astream() 返回的 StreamData 与旧 workflow.astream()
    完全一致，因此 WorkflowHandler 中所有基于 StreamData 的处理逻辑不需要修改。
    """

    # 内部保留 type，用于 trigger 通知 wrapper start trace 已解析完成
    _START_TRACE_RESOLVED_TYPE = "__start_trace_resolved__"

    def __init__(self, node_name_type_map: dict[str, dict] = None):
        self._runtime_context: dict = {}
        self._chat_history: ConversationHistory = ConversationHistory()
        # 缓冲 start trace，等待 trigger 解析全局变量后再发送
        # key: componentId, value: 已转换的 StreamData
        self._trace_buffer: dict[str, StreamData] = {}
        # IR 组件映射 {component_id: {name, type}}，用于覆盖 TraceSchema 中的 componentName/componentType
        self._node_name_type_map: dict[str, dict] = node_name_type_map or {}
        self._current_workflow_query: str = ""

    async def astream(
        self,
        query: Union[str, InteractiveInput],
        params: dict = None,
        workflow_id: str = None,
        agent_id: str = None,
        session_id: str = None,
        context=None,
        workflow_name: str = "",
    ) -> AsyncGenerator[Union[Message, StreamData], None]:
        """流式执行工作流，等价于旧 ControllerWorkflow.astream(inputs, params)。

        Args:
            query: 用户查询字符串 或 InteractiveInput（中断恢复时由 Handler 构建）
            params: 工作流参数（对应旧框架的 workflow_input["params"] 或 kwargs）
            workflow_id: 工作流 ID
            agent_id: 智能体 ID
            session_id: 会话 ID
            context: ModelContext（agent-core 上下文）
            workflow_name: 工作流名称，用于 WORKFLOW_START 等事件

        Yields:
            StreamData 对象（Questioner 中断时不 yield Message，由 Handler 检测 should_interrupt 生成）；
            仅 Plugin 参数确认中断（CONTROLLER_INTERRUPT_ERROR）时 yield Message(WORKFLOW_INTERRUPT)
        """
        from openjiuwen.core.runner import Runner

        is_resuming = isinstance(query, InteractiveInput)
        params = params or {}

        envs = self._build_envs(params)
        if agent_id:
            envs["_AGENT_ID"] = agent_id
        session = create_workflow_session(session_id=session_id, envs=envs)
        self._prepare_runtime_context(params)

        # 构建对话历史（每次调用都从 params 重建，因为 _chat_history 是本地字段，不存储在 checkpointer 中）
        # 等价于旧 workflow.py._update_runtime_context() 的 chat_history 初始化逻辑
        global_variables = params.get("global_variables", {})
        sys_args = global_variables.get("sys", {})
        conversation_history = params.get("conversation_history", [])
        sys_conversation_history = sys_args.get("conversationHistory", [])
        origin_chat_history = list(
            sys_conversation_history
            if not conversation_history
            else conversation_history
        )
        origin_chat_history = [
            msg
            for msg in origin_chat_history
            if not (
                isinstance(msg, dict)
                and msg.get("role") == "tool"
                and not msg.get("intent")
            )
        ]
        # Controller 模式下，Handler 从 context_manager 传入带 intent 的完整对话历史，不需要再追加用户查询；
        # 非 Controller 模式下（如 Plan/React 调用），需要手动追加用户查询
        if not params.get(CONTROLLER_MODE_SWITCH, False):
            if not is_resuming:
                origin_chat_history.append(
                    dict(role=ChatHistoryRole.USER.value, content=query)
                )
            else:
                # 恢复模式：追加用户最新回复，确保 LLM 上下文完整
                resume_content = self._extract_resume_query(query)
                if resume_content:
                    # 检查是否已存在（避免 Handler 层已追加导致重复）
                    if not origin_chat_history or origin_chat_history[-1].get("content") != resume_content:
                        origin_chat_history.append(
                            dict(role=ChatHistoryRole.USER.value, content=resume_content)
                        )
        self._chat_history = ConversationHistory(origin_chat_history)

        # 保存当前工作流级别的 query，供 _create_intermediate_messages 在子工作流中断场景下
        # 作为 sub_workflow_query 的 fallback（中断时 MESSAGE_END 来自子 Questioner，不含 sub_workflow_query）
        if is_resuming:
            if query.raw_inputs is not None:
                self._current_workflow_query = str(query.raw_inputs)
            elif query.user_inputs:
                self._current_workflow_query = str(list(query.user_inputs.values())[-1])
            else:
                self._current_workflow_query = ""
        else:
            self._current_workflow_query = str(query)

        workflow = await Runner.resource_mgr.get_workflow(
            workflow_id=workflow_id, tag=agent_id
        )
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if is_resuming:
            inputs = query
        else:
            # 首次执行：将 params 合入 inputs，commit_user_inputs() 会将其写入 global_state
            # 中断恢复：inputs 为 InteractiveInput，commit_user_inputs() 被跳过，
            #          checkpoint 恢复的 global_state 保留中断前的最新值
            inputs = {"query": query, **WorkflowWrapper._build_global_state_params(params, workflow_id)}

        workflow_started = False
        # 跟踪最后执行的节点信息，用于生成工作流级 FINISH StreamData
        # 等价于旧框架 BpmnWorkflow._arun() 中 self._cur_node 的行为
        last_node = {"node_id": "", "node_type": "", "node_name": ""}
        # 跟踪流中是否已产生 FINISH（如 End 节点的 WORKFLOW_FINAL CustomSchema）
        # 旧框架 _process_streaming_output 在第一个 FINISH 处 yield + break，最多只输出一帧 FINISH
        has_finish = False
        # 每次 astream 调用清空缓冲
        self._trace_buffer.clear()
        enable_debug = WorkflowWrapper._is_debug_mode(params)
        try:
            async for chunk in workflow.stream(
                inputs=inputs,
                session=session,
                context=context,
                stream_modes=self._build_stream_modes(params),
            ):
                if not workflow_started and not is_resuming:
                    yield StreamData(
                        code=StreamCode.WORKFLOW_START.value,
                        msg=StreamDataMsg.SUCCESS.value,
                        data={"workflow_id": workflow_id, "workflow_name": workflow_name},
                        execution_id=session_id or "",
                    )
                    workflow_started = True
                if self._is_skip_component(chunk):
                    continue
                if isinstance(chunk, OutputSchema) and chunk.type == INTERACTION:
                    # Questioner 中断：不 yield Message，Handler 从 StreamData 的 should_interrupt 检测并自行生成中断消息
                    # 用 continue 而非 return，确保 async generator 自然完成，session checkpoint 正常保存
                    continue

                elif isinstance(chunk, OutputSchema):
                    stream_data = self._convert_output_schema_to_stream_data(
                        chunk, session_id or ""
                    )
                    if stream_data:
                        interrupt_msg = self._try_convert_plugin_interrupt(stream_data)
                        if interrupt_msg:
                            yield interrupt_msg
                            continue
                        # 恢复模式下跳过 questioner 的重复提问输出（PARTIAL_CONTENT + MESSAGE_END）
                        if (
                            is_resuming
                            and stream_data.data.get("should_interrupt")
                            and stream_data.code
                            in (
                                StreamCode.PARTIAL_CONTENT.value,
                                StreamCode.MESSAGE_END.value,
                            )
                        ):
                            continue
                        if stream_data.code == StreamCode.FINISH.value:
                            has_finish = True
                        if isinstance(stream_data.data, dict) and stream_data.data.get(
                            "node_id"
                        ):
                            last_node["node_id"] = stream_data.data["node_id"]
                            last_node["node_type"] = stream_data.data.get(
                                "node_type", ""
                            )
                            last_node["node_name"] = stream_data.data.get(
                                "node_name", ""
                            )
                            last_node["parent_node_id"] = stream_data.data.get(
                                "parentNodeId", ""
                            )
                            last_node["user_fields"] = stream_data.data.get(
                                "outputs", {}
                            ).get("user_fields", {})
                            if stream_data.data.get(
                                "should_interrupt"
                            ) and stream_data.data.get("outputs", {}):
                                stream_data.data.pop("outputs")
                        yield stream_data
                        if stream_data.code == StreamCode.MESSAGE_END.value:
                            for _im in self._create_intermediate_messages(
                                stream_data, session_id or "", is_resuming
                            ):
                                yield _im

                elif isinstance(chunk, CustomSchema):
                    # 内部通知：trigger 已解析全局变量，start trace 可发送
                    if getattr(chunk, "type", None) == self._START_TRACE_RESOLVED_TYPE:
                        component_id = getattr(chunk, "componentId", "")
                        buffered = self._trace_buffer.pop(component_id, None)
                        if buffered:
                            yield buffered
                        continue

                    if getattr(chunk, "type", None) == INTERACTION:
                        # Questioner 中断：同上，用 continue 保证 checkpoint 保存
                        continue
                    stream_data = self._convert_custom_schema_to_stream_data(
                        chunk, session_id or ""
                    )
                    interrupt_msg = self._try_convert_plugin_interrupt(stream_data)
                    if interrupt_msg:
                        yield interrupt_msg
                        continue
                    # 子工作流恢复模式下跳过 questioner 的重复提问输出（PARTIAL_CONTENT + MESSAGE_END）
                    if (
                        is_resuming
                        and chunk.data.get("parentNodeId")
                        and stream_data.data.get("should_interrupt")
                        and stream_data.code
                        in (
                            StreamCode.PARTIAL_CONTENT.value,
                            StreamCode.MESSAGE_END.value,
                        )
                    ):
                        continue
                    if stream_data.code == StreamCode.FINISH.value:
                        has_finish = True
                    if isinstance(stream_data.data, dict) and stream_data.data.get(
                        "node_id"
                    ):
                        last_node["node_id"] = stream_data.data["node_id"]
                        last_node["node_type"] = stream_data.data.get("node_type", "")
                        last_node["node_name"] = stream_data.data.get("node_name", "")
                        last_node["parent_node_id"] = stream_data.data.get(
                            "parentNodeId", ""
                        )
                        last_node["user_fields"] = stream_data.data.get(
                            "outputs", {}
                        ).get("user_fields", {})
                        if stream_data.data.get(
                            "should_interrupt"
                        ) and stream_data.data.get("outputs", {}):
                            stream_data.data.pop("outputs")
                    # 组件自身的 CustomSchema 工作流节点消息仅在调试模式下输出，
                    # 与 TraceSchema 来源的调试 trace 保持一致。
                    if (
                        not enable_debug
                        and stream_data.code == StreamCode.WORKFLOW_NODE_MESSAGE.value
                        and not chunk.data.get("is_sub")
                    ):
                        pass  # 跳过，但仍更新 last_node 以支持 FINISH 生成
                    elif not chunk.data.get("is_sub"):
                        yield stream_data
                    if stream_data.code == StreamCode.MESSAGE_END.value:
                        for _im in self._create_intermediate_messages(
                            stream_data, session_id or "", is_resuming
                        ):
                            yield _im

                elif isinstance(chunk, TraceSchema):
                    payload = chunk.payload if isinstance(chunk.payload, dict) else {}
                    trace_status = self._compute_trace_status(payload)

                    # start trace 缓冲判断
                    if trace_status == "start" and self._should_buffer_start(
                        workflow, payload
                    ):
                        trace_stream_data = self._convert_trace_schema_to_stream_data(
                            chunk, session_id or ""
                        )
                        if trace_stream_data:
                            component_id = payload.get("componentId", "")
                            self._trace_buffer[component_id] = trace_stream_data
                        continue

                    # running trace：SubWorkflow memory 合并到缓冲的 start trace
                    if trace_status == "running":
                        component_id = payload.get("componentId", "")
                        buffered = self._trace_buffer.get(component_id)
                        if buffered:
                            on_invoke_data = payload.get("onInvokeData", [])
                            memory = self._extract_memory_from_on_invoke_data(
                                on_invoke_data
                            )
                            if memory is not None:
                                buffered.data["memory"] = memory
                                yield buffered
                                del self._trace_buffer[component_id]
                                continue  # 丢弃此 running trace（旧框架不存在这一条）

                    trace_stream_data = self._convert_trace_schema_to_stream_data(
                        chunk, session_id or ""
                    )
                    if trace_stream_data:
                        # finish/error 时刷出同组件的残余缓冲
                        # 正常路径：普通组件由 trigger 通知发送，SubWorkflow 由 running trace 合并发送
                        # 异常路径：组件执行异常导致 trigger/running 未到达，此处兜底
                        component_id = payload.get("componentId", "")
                        buffered = self._trace_buffer.pop(component_id, None)
                        if buffered and trace_status in ("finish", "error"):
                            # 用后续 trace 的 inputs 覆盖缓冲的 inputs（trigger 可能已更新）
                            current_inputs = payload.get("inputs")
                            if current_inputs is not None:
                                buffered.data["inputs"] = current_inputs
                            yield buffered
                        yield trace_stream_data
        except Exception as e:
            # WorkflowAbortException（异常结束节点）已通过 CustomSchema 发出 exception 事件，
            # 不再重复发送 ERROR StreamData，避免前端弹窗。
            if not isinstance(e, WorkflowAbortException):
                code = e.code if not isinstance(e, JiuWenBaseException) else e.error_code
                msg = e.message
                yield StreamData(
                    code=StreamCode.ERROR.value,
                    msg=StreamDataMsg.FAIL,
                    data=dict(
                        code=code,
                        message=msg,
                        node_id=last_node.get("parent_node_id") or last_node["node_id"],
                        node_name=last_node.get("node_name", ""),
                        user_fields=last_node.get("user_fields", {}),
                        node_type="jiuwen.workflowComposite"
                        if last_node.get("parent_node_id")
                        else last_node["node_type"],
                    ),
                    execution_id=session_id or "",
                )
            has_finish = True
            if isinstance(e, WorkflowAbortException):
                yield StreamData(
                    code=StreamCode.FINISH.value,
                    msg=StreamDataMsg.FINISH.value,
                    data=dict(
                        node_id=e.node_id if e.node_id is not None else "",
                        node_name=e.node_name if e.node_name is not None else "",
                        node_type=e.node_type if e.node_type is not None else "",
                    ),
                    execution_id=session_id or "",
                )

        # 刷出所有残余缓冲（error / interrupt 导致 trigger 未触发的情况）
        for component_id in list(self._trace_buffer.keys()):
            yield self._trace_buffer.pop(component_id)

        # 工作流级 FINISH StreamData
        # 等价于旧框架 BpmnWorkflow._arun() L645-650 get_streaming_finish_stream_data()
        # 仅在流中未产生 FINISH 时补上（如 Questioner 中断场景）
        # 正常完成时 End 节点已通过 WORKFLOW_FINAL 输出了 FINISH，无需重复
        if not has_finish:
            yield StreamData(
                code=StreamCode.FINISH.value,
                msg=StreamDataMsg.FINISH.value,
                data=dict(
                    answer="",
                    node_id=last_node.get("parent_node_id") or last_node["node_id"],
                    node_name=last_node.get("node_name", ""),
                    user_fields=last_node.get("user_fields", {}),
                    node_type="jiuwen.workflowComposite"
                    if last_node.get("parent_node_id")
                    else last_node["node_type"],
                ),
                execution_id=session_id or "",
            )

    def get_runtime_context(self) -> dict:
        """等价于旧 SpiffWorkflowControllerWorkflow.get_runtime_context()。

        返回运行时上下文字典，包含 REQUEST_VARIABLES、global_variables 等键。
        """
        return self._runtime_context

    def set_runtime_context(self, key: str, value: Any = None) -> None:
        """等价于旧 runtime_context.set(key, value)。

        通用运行时上下文设置方法，支持设置任意键值对。

        Args:
            key: 运行时上下文键
            value: 运行时上下文值
        """
        if not key:
            return
        self._runtime_context[key] = value

    # ==================== 私有方法 ====================

    @staticmethod
    def _build_global_state_params(params: dict, workflow_id: str = "") -> dict:
        """构建需要通过 inputs → commit_user_inputs() 写入 global_state 的参数。

        这些参数同时存在于 envs（由 _build_envs 生成），但 envs 不被 checkpoint 保存。
        通过 commit_user_inputs() 写入 global_state 后，checkpoint 会保存这些值，
        中断恢复时自动恢复，组件通过 get_workflow_param() 读取时拿到的是最新值。
        """
        result = {}

        if "global_variables" in params:
            excluded_keys = {"conversationId", "sys", "conversationHistory"}
            result["_request"] = {
                k: v
                for k, v in params["global_variables"].items()
                if k not in excluded_keys
            }
            result["global_variables"] = params["global_variables"]

        runtime_keys = [
            "memory_variables",
            "CONTROLLER_MODE_JUMP",
            "CONTROLLER_MODE_SWITCH",
            "plugin_configs",
            "llm_extra_configs",
            "app_id",
            "global_intents",
            "environment_variables",
            "mem_map",
            "enable_memory_retrieve",
            "memory_repo_id",
        ]
        for key in runtime_keys:
            if key in params:
                if key == "environment_variables":
                    result["_env"] = params[key]
                result[key] = params[key]

        return result

    # ---------- TraceSchema 转换（调试信息） ----------

    @staticmethod
    def _is_debug_mode(params: dict) -> bool:
        """检查当前是否为调试模式。从 params 读取显式传递的 is_debug 标志。"""
        if params and params.get("is_debug"):
            return True
        return False

    @staticmethod
    def _build_stream_modes(params: dict) -> list:
        """构建 stream_modes 列表，调试模式下追加 TRACE。"""
        modes = [BaseStreamMode.OUTPUT, BaseStreamMode.CUSTOM]
        if WorkflowWrapper._is_debug_mode(params):
            modes.append(BaseStreamMode.TRACE)
        return modes

    @staticmethod
    def _is_skip_component(chunk: Any) -> bool:
        """检查 chunk 是否来自内部控制流节点（_parallel_done 等），命中则跳过。"""
        comp_id = ""
        if isinstance(chunk, TraceSchema):
            payload = chunk.payload if isinstance(chunk.payload, dict) else {}
            comp_id = payload.get("componentId", "")
        elif isinstance(chunk, CustomSchema):
            comp_id = getattr(chunk, "componentId", "") or ""
            if not comp_id and isinstance(getattr(chunk, "data", None), dict):
                comp_id = chunk.data.get("componentId", "")
        elif isinstance(chunk, OutputSchema):
            payload = chunk.payload if isinstance(chunk.payload, dict) else {}
            comp_id = payload.get("componentId", "")
        if not comp_id:
            return False
        return any(key in comp_id for key in _SKIP_COMPONENT_KEY)

    # ---------- start trace 缓冲逻辑 ----------

    @staticmethod
    def _compute_trace_status(payload: dict) -> str:
        """从 TraceSchema payload 中获取 status。

        on_pre_invoke 发送时 status 一定为 "start"（由 tracer _get_node_status 计算），
        后续 on_invoke/on_call_done 发送时 status 为 "running"/"finish"/"error"/"interrupted"。
        """
        return payload.get("status", "start")

    def _should_buffer_start(self, workflow, payload: dict) -> bool:
        """判断 start trace 是否需要缓冲等待 trigger 解析。

        缓冲条件：input_schema 含 ${global.xxx} 引用。
        SubWorkflow 有 global ref 时也需要缓冲（等待 running trace 携带 memory 合并）。
        无 global ref 的 SubWorkflow 不缓冲（没有 memory 需要合并，也不需要等待 trigger 解析）。
        """
        component_id = payload.get("componentId", "")
        if not component_id:
            return False
        try:
            # workflow 可能被 _TraceProxy 包装，也可能直接是 Workflow 实例
            internal = getattr(workflow, "_internal", workflow)
            internal = getattr(internal, "_wrapped", internal)  # _TraceProxy
            internal = getattr(
                internal, "_internal", internal
            )  # Workflow → BaseWorkflow
            workflow_config = internal.config()
            comp_configs = workflow_config.spec.comp_configs
            node_spec = comp_configs.get(component_id)
            if (
                node_spec
                and node_spec.io_configs
                and node_spec.io_configs.inputs_schema
            ):
                return self._has_global_ref_in_schema(
                    node_spec.io_configs.inputs_schema
                )
        except Exception:
            workflow_logger.debug("Failed to check global ref in schema", exc_info=True)
        return False

    @staticmethod
    def _has_global_ref_in_schema(inputs_schema: dict) -> bool:
        """递归检查 input_schema 中是否包含 ${global.xxx} 引用。"""
        if not isinstance(inputs_schema, dict):
            return False
        from openjiuwen.core.session.utils import is_ref_path, extract_origin_key

        for value in inputs_schema.values():
            if isinstance(value, str) and is_ref_path(value):
                origin_key = extract_origin_key(value)
                if origin_key.startswith("global."):
                    return True
            if isinstance(value, dict):
                if WorkflowWrapper._has_global_ref_in_schema(value):
                    return True
        return False

    @staticmethod
    def _extract_memory_from_on_invoke_data(on_invoke_data: list) -> dict | None:
        """从 on_invoke_data 中提取 memory 字段。"""
        if not on_invoke_data:
            return None
        last_item = on_invoke_data[-1]
        if isinstance(last_item, dict):
            return last_item.get("memory")
        return None

    @staticmethod
    def _serialize_datetime(value: Any) -> Any:
        """将 datetime 对象转换为 ISO 格式字符串，其他值原样返回"""
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                # 补上本地时区偏移
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                local_tz = now_utc.astimezone().tzinfo
                value = value.replace(tzinfo=local_tz)
            return value.isoformat()
        return value

    def _convert_trace_schema_to_stream_data(
        self, chunk: TraceSchema, session_id: str
    ) -> StreamData | None:
        """将 TraceSchema 转换为 WORKFLOW_NODE_MESSAGE StreamData。

        以 status 字段优先分派：
        1. error → 组件异常，on_invoke_data 整包赋值
        2. interrupted → 视为 error（jiuwen 无此状态）
        3. finish → 从 outputs/streamOutputs 提取数据 + memory
        4. running → 检查 on_invoke_data 是否有 inner_error
        5. 其他 → pre_invoke

        Args:
            chunk: TraceSchema 实例
            session_id: 会话 ID（对应旧框架的 conversation_id）

        Returns:
            StreamData(WORKFLOW_NODE_MESSAGE)，或 None
        """
        payload = chunk.payload if isinstance(chunk.payload, dict) else {}
        if not payload or not payload.get("componentId", ""):
            return None

        trace_status = payload.get("status", "")
        outputs = payload.get("outputs")
        stream_outputs = payload.get("streamOutputs")
        on_invoke_data = payload.get("onInvokeData", [])

        # ---- 字段提取 ----
        memory = None
        inner_error = None
        effective_outputs = outputs
        computed_status = None

        if trace_status == "error":
            # 1. 组件抛异常，该组件调试信息到此为止
            # on_invoke_data 直接整包赋值，不取最后一个 dict
            computed_status = "error"

        elif trace_status == "interrupted":
            # 2. 组件被打断，jiuwen 无此状态，视为 ERROR
            computed_status = "running"

        elif trace_status == "finish":
            # 3. 组件正常执行完成
            if outputs is not None:
                # invoke 路径：从 outputs 中取出 memory 并 pop
                if isinstance(outputs, dict):
                    memory = outputs.pop("memory", None)
                effective_outputs = outputs

            elif (
                stream_outputs
                and isinstance(stream_outputs, list)
                and len(stream_outputs) > 0
            ):
                # stream 路径：最后一帧即为完整结果（含可能的 memory 字段）
                last_frame = stream_outputs[-1]
                effective_outputs = last_frame
                if isinstance(last_frame, dict):
                    memory = last_frame.pop("memory", None)

            computed_status = "finish"

        elif trace_status == "running":
            # 4. 组件运行中，中间过程数据
            if on_invoke_data:
                last_item = on_invoke_data[-1]
                if isinstance(last_item, dict) and "inner_error" in last_item:
                    # 最后一个 dict 是 inner_error → 单独发送，status 强制改为 error
                    inner_error = last_item["inner_error"]
                    computed_status = "error"
                else:
                    # 不是 inner_error → 记录整个 on_invoke_data
                    if isinstance(last_item, dict):
                        memory = last_item.get("memory")
                    computed_status = "running"

        else:
            # 5. pre_invoke 或其他
            computed_status = "start"

        # ---- inner_error 时从 on_invoke_data 取 current_time 设置 endTime ----
        end_time_override = None
        if inner_error is not None:
            for item in reversed(on_invoke_data):
                if isinstance(item, dict) and "current_time" in item:
                    end_time_override = item["current_time"]
                    break

        # ---- IR 映射覆盖 componentName / componentType ----
        comp_id = payload.get("componentId", "")
        ir_metadata = self._node_name_type_map.get(comp_id)
        effective_component_name = payload.get("componentName", "")
        effective_component_type = payload.get("componentType", "")
        if ir_metadata:
            ir_name = ir_metadata.get("name", "")
            ir_type = ir_metadata.get("type", "")
            if ir_name:
                effective_component_name = ir_name
            if ir_type:
                effective_component_type = ir_type

        # ---- 构建数据 ----
        data = {
            "executionId": payload.get("executionId", ""),
            "conversationId": session_id,
            "startTime": self._serialize_datetime(payload.get("startTime")),
            "endTime": self._serialize_datetime(
                end_time_override if end_time_override else payload.get("endTime")
            ),
            "onInvokeData": on_invoke_data,
            "agentId": payload.get("workflowId", ""),
            "componentId": comp_id,
            "componentName": effective_component_name,
            "componentType": _DEBUG_EVENT_RETURN_TO_SERVICE.get(
                payload.get("componentType", "unknown"),
                payload.get("componentType", ""),
            ),
            "agentParentInvokeId": "",
            "inputs": payload.get("inputs"),
            "outputs": effective_outputs,
            "error": payload.get("error"),
            "metaData": None,
            "invokeId": payload.get("invokeId"),
            "parentInvokeId": payload.get("parentInvokeId"),
            "traceId": payload.get("traceId", ""),
            "loopNodeId": payload.get("loopNodeId"),
            "loopIndex": payload.get("loopIndex"),
            "innerError": inner_error,
            "memory": memory,
            "parentNodeId": payload.get("parentNodeId", ""),
        }

        # Insight4CallbackHandler: outputs 为空字符串时设为 None
        if data["outputs"] == "":
            data["outputs"] = None

        # 设置 status
        data["status"] = computed_status

        return StreamData(
            code=StreamCode.WORKFLOW_NODE_MESSAGE.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=data,
            execution_id=session_id,
        )

    def _build_envs(self, params: dict) -> dict:
        """将工作流参数构建为 Session 环境变量。

        Args:
            params: 工作流参数字典

        Returns:
            环境变量字典
        """
        envs = {}
        if not params:
            return envs

        if "global_variables" in params:
            envs["global_variables"] = params["global_variables"]
            excluded_keys = {"conversationId", "sys", "conversationHistory"}
            envs["_request"] = {
                k: v
                for k, v in params["global_variables"].items()
                if k not in excluded_keys
            }

        runtime_keys = [
            "memory_variables",
            "CONTROLLER_MODE_JUMP",
            "CONTROLLER_MODE_SWITCH",
            "plugin_configs",
            "llm_extra_configs",
            "app_id",
            "global_intents",
            "environment_variables",
            "mem_map",
            "enable_memory_retrieve",
            "_end_comp_template_render_position_timeout",
        ]
        for key in runtime_keys:
            if key in params:
                envs[key] = params[key]

        return envs

    def _prepare_runtime_context(self, params: dict) -> None:
        """从参数准备运行时上下文。

        Args:
            params: 工作流参数字典
        """
        self._runtime_context = {}
        if not params:
            return

        if "global_variables" in params:
            excluded_keys = {"conversationId", "sys", "conversationHistory"}
            self._runtime_context[REQUEST_VARIABLES] = {
                k: v
                for k, v in params["global_variables"].items()
                if k not in excluded_keys
            }
            self._runtime_context["global_variables"] = params["global_variables"]

        env_mapping = {
            "project_id": WORKFLOW_EXECUTE_PROJECT_ID,
            "plugin_configs": WORKFLOW_API_CONFIGS,
            "environment_variables": ENVIRONMENT_VARIABLES,
            "memory_variables": MEMORY_VARIABLES,
            "global_intents": WORKFLOW_GLOBAL_INTENTS,
            "mem_map": MEM_MAP,
            "enable_memory_retrieve": ENABLE_MEMORY_RETRIEVE,
        }
        for param_key, context_key in env_mapping.items():
            if param_key in params:
                self._runtime_context[context_key] = params[param_key]

        # WORKFLOW_USER_ID 从 global_variables 中提取
        global_vars = params.get("global_variables", {})
        if isinstance(global_vars, dict) and "userId" in global_vars:
            self._runtime_context[WORKFLOW_EXECUTE_USER_ID] = global_vars["userId"]

    def _try_convert_plugin_interrupt(self, stream_data: StreamData) -> Message | None:
        """检查 StreamData 是否为 Plugin 中断（CONTROLLER_INTERRUPT_ERROR），若是则转换为 Message。

        等价于旧 spiffworkflow_graph_engine._process_streaming_output_async() 中的 is_interrupt() 检查。
        Plugin 组件通过 InterruptException（error_code=103102）触发参数确认中断。

        Args:
            stream_data: 待检查的 StreamData

        Returns:
            Message(WORKFLOW_INTERRUPT) 若为 plugin 中断，否则 None
        """
        if stream_data is None or not stream_data.data:
            return None
        code = stream_data.data.get("code")
        if code != 103102:  # StatusCode.CONTROLLER_INTERRUPT_ERROR.code
            return None

        import json
        from jiuwen.controller.common.enum import MessageSubType

        message_str = stream_data.data.get("message", "")
        try:
            message = (
                json.loads(message_str) if isinstance(message_str, str) else message_str
            )
        except (json.JSONDecodeError, TypeError):
            message = {"type": "", "content": str(message_str)}

        message_type = message.get("type", "")
        valid_sub_types = {
            MessageSubType.PLUGIN_PARAM_ERROR.value,
            MessageSubType.PLUGIN_PARAM_MISS.value,
            MessageSubType.PLUGIN_CALL_CONFIRM.value,
            MessageSubType.GLOBAL_INTENT.value,
        }
        if message_type not in valid_sub_types:
            return None

        return Message(
            message_type=MessageType.WORKFLOW_INTERRUPT,
            sub_type=MessageSubType.from_string(message_type),
            content=message_str
            if isinstance(message_str, str)
            else json.dumps(message_str, ensure_ascii=False),
        )

    def _convert_output_schema_to_stream_data(
        self, chunk: OutputSchema, execution_id: str
    ) -> StreamData | None:
        """将 OutputSchema 转换为 StreamData。

        根据 chunk.type 分派到具体的转换方法。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            StreamData 实例，或 None（如果类型不需要转换）
        """
        type_converters = {
            "workflow_final": self._convert_workflow_final,
            "end node stream": self._convert_end_node_stream,
            "message_end": self._convert_message_end,
            "workflow_end": self._convert_workflow_end,
            "workflow_start": self._convert_workflow_start,
            "workflow_exception": self._convert_workflow_exception,
            "component_execute_error": self._convert_error,
        }
        converter = type_converters.get(chunk.type)
        if converter:
            return converter(chunk, execution_id)
        # 未知类型，按 PARTIAL_CONTENT 处理
        payload = chunk.payload
        return StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=chunk.type,
            data=payload if isinstance(payload, dict) else {"answer": str(payload)},
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_end_node_stream(
        self, chunk: OutputSchema, execution_id: str
    ) -> StreamData:
        """转换 end node stream → PARTIAL_CONTENT。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            PARTIAL_CONTENT 类型的 StreamData
        """
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"answer": payload}
        data = {
            "answer": payload.get("answer", ""),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        for key in ("think", "output_mode"):
            if key in payload:
                data[key] = payload[key]

        return StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=data,
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_message_end(
        self, chunk: OutputSchema, execution_id: str
    ) -> StreamData:
        """转换 message_end → MESSAGE_END。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            MESSAGE_END 类型的 StreamData
        """
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"answer": str(payload)}

        data = {
            "answer": payload.get("answer", ""),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        user_fields = payload.get("userFields")
        data.setdefault("enable_history", payload.get("enable_history", True))
        if user_fields and not payload.get("should_interrupt", False):
            data["outputs"] = {"user_fields": user_fields}
        for key in ("origin_answer", "think", "output_mode", "parentNodeId"):
            if key in payload:
                data[key] = payload[key]

        return StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg=StreamDataMsg.MESSAGE_END.value,
            data=data,
            execution_id=execution_id,
            index=chunk.index,
        )

    @staticmethod
    def _convert_workflow_end(chunk: OutputSchema, execution_id: str) -> StreamData:
        """转换 workflow_end → WORKFLOW_END。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            WORKFLOW_END 类型的 StreamData
        """
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"answer": str(payload)}
        data = {
            "answer": payload.get("answer", ""),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        user_fields = payload.get("userFields")
        if user_fields and not payload.get("should_interrupt", False):
            data["outputs"] = {"user_fields": user_fields}
        for key in ("output_mode",):
            if key in payload:
                data[key] = payload[key]

        return StreamData(
            code=StreamCode.WORKFLOW_END.value,
            msg=StreamDataMsg.FINISH.value,
            data=data,
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_workflow_final(
        self, chunk: OutputSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_final → FINISH。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            FINISH 类型的 StreamData
        """
        payload = chunk.payload
        if isinstance(payload, dict):
            data = dict(payload)
            if "userFields" in data and "user_fields" not in data:
                data["user_fields"] = data.pop("userFields")
        else:
            data = {"answer": str(payload)}

        return StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            data=data,
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_workflow_start(
        self, chunk: OutputSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_start → WORKFLOW_START。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            WORKFLOW_START 类型的 StreamData
        """
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"workflow_id": str(payload)}

        return StreamData(
            code=StreamCode.WORKFLOW_START.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=payload,
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_workflow_exception(
        self, chunk: OutputSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_exception → WORKFLOW_EXCEPTION。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            WORKFLOW_EXCEPTION 类型的 StreamData
        """
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"error_code": -1, "message": str(payload)}

        return StreamData(
            code=StreamCode.WORKFLOW_EXCEPTION.value,
            msg=StreamDataMsg.FAIL.value,
            data=payload,
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_error(self, chunk: OutputSchema, execution_id: str) -> StreamData:
        """转换 component_execute_error → ERROR。

        Args:
            chunk: OutputSchema 实例
            execution_id: 执行 ID

        Returns:
            ERROR 类型的 StreamData
        """
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"message": str(payload)}

        return StreamData(
            code=StreamCode.ERROR.value,
            msg=StreamDataMsg.FAIL.value,
            data=payload,
            execution_id=execution_id,
            index=chunk.index,
        )

    def _convert_custom_schema_to_stream_data(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 CustomSchema → StreamData。

        Args:
            chunk: CustomSchema 实例
            execution_id: 执行 ID

        Returns:
            StreamData 实例
        """
        # 直接像处理 OutputSchema 一样处理 CustomSchema
        type_converters = {
            "workflow_final": self._convert_workflow_final_from_custom,
            "end node stream": self._convert_end_node_stream_from_custom,
            "message_end": self._convert_message_end_from_custom,
            "partial_content": self._convert_partial_content_from_custom,
            "message node stream": self._convert_partial_content_from_custom,  # 向后兼容
            "workflow_node_message": self._convert_workflow_node_message_from_custom,
            "workflow_end": self._convert_workflow_end_from_custom,
            "workflow_start": self._convert_workflow_start_from_custom,
            "workflow_exception": self._convert_workflow_exception_from_custom,
            "component_execute_error": self._convert_error_from_custom,
        }

        chunk_type = getattr(chunk, "type", None)
        converter = type_converters.get(chunk_type)
        if converter:
            return converter(chunk, execution_id)

        # 未知类型，按 PARTIAL_CONTENT 处理
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        return StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=chunk_type or "custom_stream",
            data=data if isinstance(data, dict) else {"answer": str(data)},
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_partial_content_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 partial_content (CustomSchema) → PARTIAL_CONTENT。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"result": data}

        result_data = {
            "answer": data.get("answer", data.get("result", "")),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        for key in ("think", "output_mode", "parentNodeId", "workflow_id"):
            if key in data:
                result_data[key] = data[key]

        return StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=result_data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_workflow_node_message_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_node_message (CustomSchema) → WORKFLOW_NODE_MESSAGE"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"response": data}

        result_data = {
            "answer": data.get("response", ""),
            "conversationId": execution_id,
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        for key in (
            "think",
            "output_mode",
            "parentNodeId",
            "workflow_id",
            "componentType",
            "rawOutput",
            "onInvokeData",
            "model_stats",
            "status",
        ):
            if key in data:
                if key == "userFields" or key == "model_stats":
                    if "outputs" not in result_data:
                        result_data["outputs"] = {}
                    result_data["outputs"][key] = data[key]
                    continue
                result_data[key] = data[key]

        return StreamData(
            code=StreamCode.WORKFLOW_NODE_MESSAGE.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=result_data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_end_node_stream_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 end node stream (CustomSchema) → PARTIAL_CONTENT。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"response": data}

        result_data = {
            "answer": data.get("response", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        for key in ("think", "output_mode", "parentNodeId", "workflow_id"):
            if key in data:
                result_data[key] = data[key]

        return StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=result_data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_message_end_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 message_end (CustomSchema) → MESSAGE_END。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"answer": str(data)}

        result_data = {
            "answer": data.get("answer", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        result_data.setdefault("enable_history", data.get("enable_history", True))
        for key in (
            "origin_answer",
            "think",
            "output_mode",
            "model_stats",
            "parentNodeId",
            "userFields",
            "sub_workflow_query",
        ):
            if key in data:
                if key == "userFields" or key == "model_stats":
                    if "outputs" not in result_data:
                        result_data["outputs"] = {}
                    output_key = "user_fields" if key == "userFields" else key
                    result_data["outputs"][output_key] = data[key]
                    continue
                result_data[key] = data[key]

        return StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg=StreamDataMsg.MESSAGE_END.value,
            data=result_data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_workflow_end_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_end (CustomSchema) → WORKFLOW_END。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"answer": str(data)}

        result_data = {
            "answer": data.get("answer", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
            "outputs": {"user_fields": data.get("userFields", {})},
        }
        for key in "output_mode":
            if key in data:
                result_data[key] = data[key]

        return StreamData(
            code=StreamCode.WORKFLOW_END.value,
            msg=StreamDataMsg.FINISH.value,
            data=result_data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_workflow_final_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_final (CustomSchema) → FINISH。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"answer": str(data)}
        else:
            data = dict(data)
            if "userFields" in data and "user_fields" not in data:
                data["user_fields"] = data.pop("userFields")

        return StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            data=data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_workflow_start_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_start (CustomSchema) → WORKFLOW_START。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"workflow_id": str(data)}

        return StreamData(
            code=StreamCode.WORKFLOW_START.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_workflow_exception_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 workflow_exception (CustomSchema) → WORKFLOW_EXCEPTION。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"error_code": -1, "message": str(data)}

        return StreamData(
            code=StreamCode.WORKFLOW_EXCEPTION.value,
            msg=StreamDataMsg.FAIL.value,
            data=data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _convert_error_from_custom(
        self, chunk: CustomSchema, execution_id: str
    ) -> StreamData:
        """转换 component_execute_error (CustomSchema) → ERROR。"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"message": str(data)}

        return StreamData(
            code=StreamCode.ERROR.value,
            msg=StreamDataMsg.FAIL.value,
            data=data,
            execution_id=execution_id,
            index=getattr(chunk, "index", 0),
        )

    def _create_intermediate_messages(
        self,
        message_end_stream_data: StreamData,
        execution_id: str,
        is_resuming: bool = False,
    ) -> list:
        """创建 CONTROLLER_INTERMEDIATE_MESSAGE 类型的 StreamData 列表。

        类似旧框架在 MESSAGE_END 后添加 CONTROLLER_INTERMEDIATE_MESSAGE 的行为。
        从本地维护的 ConversationHistory 中获取历史消息，并在添加新消息后返回。

        当 MESSAGE_END 含有 parentNodeId（来自子工作流）时，生成两个 intermediate message：
          1. 不带 parentNodeId 的（对应旧框架父工作流层 _process_streaming_output 的输出）
          2. 带 parentNodeId 的（对应旧框架子工作流层 _process_streaming_output 的输出）

        关键区别：子工作流层（含 parentNodeId）使用快照，不修改 _chat_history，
        避免与顶层 MESSAGE_END 重复追加 assistant 消息。

        Args:
            message_end_stream_data: 刚刚转换的 MESSAGE_END 类型的 StreamData
            execution_id: 执行 ID

        Returns:
            list[StreamData]: CONTROLLER_INTERMEDIATE_MESSAGE 类型的 StreamData 列表
        """
        content = (
            message_end_stream_data.data.get("origin_answer")
            if message_end_stream_data.data.get("origin_answer", "")
            else message_end_stream_data.data.get("answer", "")
        )
        enable_history = message_end_stream_data.data.get("enable_history", True)
        parent_node_id = message_end_stream_data.data.get("parentNodeId")

        if parent_node_id:
            # 子工作流层：使用快照构建 answer，不修改 _chat_history（避免与顶层重复）
            base_answer = list(self._chat_history.get_all_messages())
            # 追加子工作流的 query 作为 user 消息（等价于旧框架 SubWorkflow.ainvoke 中
            # message=query 传入子工作流后，由 ChatManager 写入对话历史的行为）
            sub_query = message_end_stream_data.data.get("sub_workflow_query", "")
            # 中断场景：MESSAGE_END 来自子 Questioner，SubWorkflow 的 MESSAGE_NODE_END 未执行，
            # sub_workflow_query 为空，使用 WorkflowWrapper 保存的工作流级 query 作为 fallback
            # 恢复场景：SubWorkflow 的 _current_query 未更新，sub_workflow_query 为旧值，
            # 使用 WorkflowWrapper 保存的工作流级 query（从 InteractiveInput 更新）作为 fallback
            if not sub_query:
                sub_query = getattr(self, "_current_workflow_query", "")
            # 顶层 7000（不带 parentNodeId）：不含 sub_query，仅含 content
            answer_for_top = list(base_answer)
            if content and enable_history:
                answer_for_top.append(
                    ConversationMessage(
                        role=ChatHistoryRole.ASSISTANT.value,
                        content=str(content),
                    )
                )
            # 子工作流层 7000（带 parentNodeId）：含 sub_query + content
            answer_for_sub = list(base_answer)
            if sub_query:
                answer_for_sub.append(
                    ConversationMessage(
                        role=ChatHistoryRole.USER.value,
                        content=str(sub_query),
                    )
                )
            if content and enable_history:
                answer_for_sub.append(
                    ConversationMessage(
                        role=ChatHistoryRole.ASSISTANT.value,
                        content=str(content),
                    )
                )
        else:
            # 顶层：正常追加 assistant 到 _chat_history
            if content and enable_history:
                self._chat_history.add(
                    ConversationMessage(
                        role=ChatHistoryRole.ASSISTANT.value, content=str(content)
                    )
                )
            answer_for_top = self._chat_history.get_all_messages()
            answer_for_sub = answer_for_top

        result = []

        # 顶层 intermediate message（不带 parentNodeId）
        if (
            parent_node_id
            and not is_resuming
            and message_end_stream_data.data.get("should_interrupt", False)
        ):
            result.append(
                StreamData(
                    code=StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value,
                    msg="intermediate message",
                    data=dict(answer=answer_for_top),
                    execution_id=execution_id,
                )
            )

        # 子工作流层 intermediate message（带 parentNodeId）
        data = dict(answer=answer_for_sub)
        if parent_node_id:
            data["parentNodeId"] = parent_node_id
        result.append(
            StreamData(
                code=StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value,
                msg="intermediate message",
                data=data,
                execution_id=execution_id,
            )
        )
        return result

    def _extract_resume_query(self, query) -> str:
        """从 InteractiveInput 中提取恢复时的用户回复文本。

        Args:
            query: InteractiveInput 实例或其他类型的 query

        Returns:
            str: 用户回复文本，未找到则返回空字符串
        """
        if isinstance(query, InteractiveInput):
            if query.raw_inputs:
                return str(query.raw_inputs)
            if query.user_inputs:
                return str(list(query.user_inputs.values())[-1])
        return str(query) if query else ""
