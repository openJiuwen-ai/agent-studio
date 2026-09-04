#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
from typing import Optional, Dict, List, Any, Union

from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.messages import HumanMessage
from jiuwen.common.log.base import logger
from jiuwen.context.base import VARIABLE_NAME_KEY, VARIABLE_DEFAULT_KEY
from jiuwen.context.engine import ContextEngine
from jiuwen.context.history import ConversationMessage
from jiuwen.context.memory_engine.config.memory_ir_config import MemoryIrConfig
from jiuwen.controller.common.constants import WorkflowConstants, FUNCTION_ROLE
from jiuwen.controller.common.enum import WorkflowType, ActionAfterCompletionType
from jiuwen.controller.context_manager.controller_context import ControllerContext
from jiuwen.controller.context_manager.workflow_context import (
    WorkflowContext,
    WorkflowStatus,
    NodeExecutionInfo,
)
from jiuwen.controller.task_planner.planners.controller_planner import ControllerState
from jiuwen.controller.utils.utils import WorkspaceUtils
from jiuwen.extension.memory.client.memory_proxy import MemoryProxy
from jiuwen.serve.common.context import request_json

_GLOBAL_VARIABLES = "globalVariables"


class ContextManager:
    def __init__(self, agent_config):
        context_config = agent_config.context if agent_config else None
        self.engine: ContextEngine = ContextEngine(
            context_config=context_config, model=agent_config.model
        )
        self.workflow_contexts: Dict[str, WorkflowContext] = {}
        self.agent_config = agent_config
        self.controller_context: ControllerContext = ControllerContext()
        self.memory_app_id: str = ""
        self._memory_message = None
        self._memory_proxy = None
        memory_config = agent_config.memory_config
        self.memory_enable: bool = (
            isinstance(memory_config, MemoryIrConfig) and memory_config.enable_memory
        )
        if self.memory_enable or (context_config and context_config.enable_memory):
            self._memory_proxy = MemoryProxy(memory_config)

        # 初始化时创建所有工作流上下文
        self._initialize_workflow_contexts()

    @classmethod
    def generate_unique_key(cls, workflow_id: str, workflow_type: WorkflowType) -> str:
        """生成唯一键，避免不同类型工作流ID冲突"""
        return f"{workflow_type.name.lower()}_{workflow_id}"

    def get_workflow_context_by_name_and_type(
        self, workflow_name: str, workflow_type=WorkflowType.GENERAL
    ) -> Optional[WorkflowContext]:
        """通过名称获取工作流上下文

        Args:
            workflow_name:
            workflow_type:
        """
        for context in self.workflow_contexts.values():
            if context.workflow_name == workflow_name and context.type == workflow_type:
                return context
        return None

    def get_workflow_context_by_config_name(
        self, config_name: str
    ) -> Optional[WorkflowContext]:
        """通过配置项名称获取工作流上下文"""
        for context in self.workflow_contexts.values():
            if context.config_name == config_name:
                return context
        return None

    def get_workflow_context_by_id(
        self, workflow_id: str, workflow_type: WorkflowType
    ) -> Optional[WorkflowContext]:
        """通过ID和工作流类型获取工作流上下文"""
        # 如果指定了类型，使用唯一键查找
        unique_key = self.generate_unique_key(workflow_id, workflow_type)
        return self.workflow_contexts.get(unique_key)

    def get_start_workflow_contexts(self) -> Union[WorkflowContext | None]:
        """获取开始工作流上下文"""
        for ctx in self.workflow_contexts.values():
            if ctx.type == WorkflowType.START:
                return ctx
        return None

    def get_default_workflow_contexts(self) -> Union[WorkflowContext | None]:
        """获取开始工作流上下文"""
        for ctx in self.workflow_contexts.values():
            if ctx.type == WorkflowType.DEFAULT:
                return ctx
        return None

    def get_normal_workflow_contexts(self) -> list:
        """获取所有业务工作流上下文"""
        normal_workflow_contexts = []
        for ctx in self.workflow_contexts.values():
            if ctx.type == WorkflowType.GENERAL:
                normal_workflow_contexts.append(ctx)
        return normal_workflow_contexts

    def get_end_workflow_contexts(self) -> Union[WorkflowContext | None]:
        """获取结束工作流上下文"""
        for ctx in self.workflow_contexts.values():
            if ctx.type == WorkflowType.END:
                return ctx
        return None

    def get_workflow_status(self, workflow_id: str, workflow_type) -> WorkflowStatus:
        """获取工作流状态

        Args:
            workflow_type:
        """
        unique_key = self.generate_unique_key(workflow_id, workflow_type)
        return self.workflow_contexts[unique_key].status

    def update_workflow_status(
        self,
        workflow_id: str,
        workflow_type: WorkflowType,
        status: WorkflowStatus,
        current_node_info: Optional[NodeExecutionInfo] = None,
    ) -> None:
        """更新工作流状态"""
        unique_key = self.generate_unique_key(workflow_id, workflow_type)
        context = self.workflow_contexts.get(unique_key)
        if context is not None:
            context.status = status
            if current_node_info is not None:
                context.current_node_info = current_node_info
        if status is not WorkflowStatus.INTERRUPTED:
            self.set_workflow_state(workflow_id, workflow_type, None)

    def set_workflow_state(
        self, workflow_id: str, workflow_type: WorkflowType, workflow_state: Any
    ) -> None:
        """设置工作流状态"""
        unique_key = self.generate_unique_key(workflow_id, workflow_type)
        if unique_key in self.workflow_contexts:
            self.workflow_contexts[unique_key].state = workflow_state

    def get_interrupted_workflow_states(self) -> Dict[str, Any]:
        """返回所有状态为interrupted的工作流状态映射

        Returns:
            Dict[str, Any]: 以工作流ID为键，包含工作流状态和类型的字典
        """
        interrupted_states = {}
        for unique_key, context in self.workflow_contexts.items():
            if context.status == WorkflowStatus.INTERRUPTED:
                # 保存工作流状态和类型，以便在恢复时也能恢复类型
                interrupted_states[unique_key] = {
                    "state": context.state,
                    "type": context.type.value,  # 使用枚举值（整数）
                    "description": context.description,
                    "status": context.status.value,
                    "parameters": context.workflow_parameters,
                    "action_after_completion": context.action_after_completion.value
                    if context.action_after_completion
                    else None,
                    "workflow_name": context.workflow_name,
                    "config_name": context.config_name,
                    "workflow_id": context.workflow_id,
                    "current_node_info": context.current_node_info
                    if context.current_node_info
                    else None,
                }
        return interrupted_states

    def load_state(self, agent_state) -> None:
        """从AgentState恢复工作流上下文
        Args:
            agent_state: 包含工作流状态的Agent状态对象
        """
        self.load_workflow_contexts(agent_state.workflow_states)
        self.load_controller_context(agent_state.controller_state)
        logger.debug(
            "start workflow restore_from_agent_state: %s",
            agent_state.controller_state,
            simple_log="start workflow restore_from_agent_state",
        )
        # controller模式下更新全局变量
        if self.agent_config.plan_config.plan_mode == "Controller":
            self.load_controller_global_variables(agent_state)

    def load_workflow_contexts(self, workflow_states):
        """从保存的状态加载工作流上下文"""
        if not workflow_states:
            return

        # 现在workflow_states是一个字典，键是工作流ID，值是包含状态和类型的字典
        for unique_key, workflow_data in workflow_states.items():
            # 获取工作流状态和类型
            workflow_id = workflow_data["workflow_id"]
            workflow_state = workflow_data.get("state")
            workflow_type_value = workflow_data.get("type")
            description = workflow_data.get("description", "")
            parameters = workflow_data.get("parameters", {})
            workflow_name = workflow_data.get("workflow_name")
            action_after_completion = workflow_data.get("action_after_completion")
            config_name = workflow_data.get("config_name")
            # 将类型值转换为枚举
            workflow_type = WorkflowType.GENERAL
            try:
                # 尝试通过值找到对应的枚举
                for type_enum in WorkflowType:
                    if type_enum.value == workflow_type_value:
                        workflow_type = type_enum
                        break
            except (ValueError, TypeError):
                pass  # 使用默认值 WorkflowType.GENERAL

            # 查找或创建工作流上下文
            context = self.get_workflow_context_by_id(workflow_id, workflow_type)
            if not context:
                # 如果上下文不存在，创建一个新的
                context = WorkflowContext(
                    workflow_id=workflow_id,
                    workflow_name=workflow_name,
                    description=description,
                    workflow_parameters=parameters,
                    action_after_completion=ActionAfterCompletionType.from_string(
                        action_after_completion
                    ),
                    workflow_ir=None,
                    type=workflow_type,
                    config_name=config_name,
                )
                self.workflow_contexts[unique_key] = context

            # 设置工作流状态
            context.state = workflow_state
            context.type = workflow_type
            context.current_node_info = workflow_data.get("current_node_info")
            # 设置工作流为中断状态，因为这些状态是从中断的工作流中保存的
            context.status = WorkflowStatus.INTERRUPTED

    def add_user_message(
        self,
        content: str,
        intent: Optional[str] = None,
        files: Optional[List[Dict[str, Any]]] = None,
        enable_history: Optional[bool] = True,
    ) -> None:
        """添加用户消息"""
        self.engine.add_user_message(
            content=content,
            intent=intent,
            files=files,
            enable_history=enable_history,
            agent_id=self.agent_config.metadata.id if self.agent_config else "",
        )

    def add_assistant_message(
        self,
        content: str,
        intent: Optional[str] = None,
        function_call: Optional[Dict[str, Any]] = None,
    ) -> None:
        """添加助手消息"""
        self.engine.add_assistant_message(
            content,
            intent,
            function_call,
            agent_id=self.agent_config.metadata.id if self.agent_config else "",
        )

    def add_assistant_message_with_multi_function_call(
        self,
        content: str,
        intent_list: Optional[List[str]] = None,
        function_call_list: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """添加助手消息"""
        self.engine.add_message(
            ConversationMessage(
                content=content,
                role="assistant",
                function_call=function_call_list,
                agent_id=self.agent_config.metadata.id if self.agent_config else "",
            )
        )
        if intent_list:
            self.set_latest_intent_list(intent_list)

    def add_function_message(
        self, name: str, intent: str, content: str, role=FUNCTION_ROLE, tool_call_id=""
    ) -> None:
        """添加函数调用结果消息"""
        self.engine.add_message(
            ConversationMessage(
                content=content,
                role=role,
                name=name,
                tool_call_id=tool_call_id,
                agent_id=self.agent_config.metadata.id if self.agent_config else "",
            )
        )
        if intent:
            self.set_latest_intent(intent)

    def get_message_by_intent(self, intent: str):
        """根据意图过滤出会话中的所有相关消息，并按API格式返回"""
        filtered_messages = self.engine.get_messages(filters={"intent": intent})
        formatted_messages = []
        for msg in filtered_messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content,
                "intent": msg.intent,
                "enable_history": msg.enable_history,
            }
            # 如果有函数调用信息，添加到消息中
            if msg.function_call:
                message_dict["function_call"] = msg.function_call
            # 如果是function角色且有name，添加name字段
            if msg.role == "function" and msg.name:
                message_dict["name"] = msg.name
            formatted_messages.append(message_dict)
        return formatted_messages

    def set_latest_intent(self, intent: str):
        """设置最新一条消息的意图"""
        self.engine.history.set_latest_intent(intent)

    def set_latest_intent_list(self, intent_list: List):
        """设置最新一条消息的意图"""
        self.engine.history.set_latest_intent_list(intent_list)

    def add_global_intent(self, global_intent):
        """为上下文添加全局意图"""
        self.engine.history.add_global_intent(global_intent)

    def get_function_and_assistant_messages(self):
        """返回所有工具调用结果和工具调用命令的消息对"""
        msgs = self.engine.get_messages()
        pairs = []

        # 从后往前遍历查找所有function消息
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i].role == FUNCTION_ROLE:
                function_msg = msgs[i]

                # 在当前function消息之前找对应的assistant消息
                assistant_msg = None
                for j in range(i - 1, -1, -1):
                    if (
                        msgs[j].role == "assistant"
                        and getattr(msgs[j], "function_call", None) is not None
                    ):
                        assistant_msg = msgs[j]
                        break

                # 如果找到了配对的assistant消息，添加到结果中
                if assistant_msg:
                    pairs.append((function_msg, assistant_msg))

        # 反转列表，使其按时间顺序排列（早的在前）
        pairs.reverse()

        return pairs

    def get_all_assistant_msg_and_tool_msg(self):
        """返回带function call的 assistant messages和所有的 tool messages"""
        result = list()
        # 先找到最近一次user的位置
        count = 0
        msgs = self.engine.get_messages()
        for item in reversed(msgs):
            count += 1
            if item.role == "user":
                break

        for item in msgs[-count:]:
            if (
                item.role == "assistant"
                and getattr(item, "function_call", None) is not None
            ):
                result.append(item)
            if item.role == FUNCTION_ROLE:
                result.append(item)
        return result

    def add_intent_to_latest_user_message(self, intent):
        """为最新的用户消息添加意图"""
        latest_user_msg = self.get_latest_user_message()
        if latest_user_msg:
            if latest_user_msg.intent:
                # 只有当intent不在列表中时才添加
                if intent not in latest_user_msg.intent:
                    latest_user_msg.intent.append(intent)
            else:
                latest_user_msg.intent = [intent]

    def get_latest_k_chat_history(self, k: int) -> List[Dict[str, Any]]:
        """获取最近k条消息，按标准格式返回"""
        return self.engine.get_latest_k_chat_history_dict(k)

    def get_latest_intent(self) -> Optional[str]:
        """获取会话的最新意图（列表中的最后一个元素）

        Returns:
            str 或 None: 如果意图列表非空，返回最后一个意图；如果列表为空，返回None
        """
        intent_list = self.engine.history.get_latest_intent()
        # 确保intent_list是列表
        intent_list = intent_list if isinstance(intent_list, list) else []

        # 返回列表中的最后一个元素，如果列表为空则返回None
        return intent_list[-1] if intent_list else None

    def get_second_latest_user_intent(self) -> Optional[str]:
        """获取第二个user intent"""
        return self.engine.history.get_second_latest_user_intent()

    def clear_all(self):
        """清理所有上下文内容和状态，包括完全清空工作流上下文"""
        # 清理上下文引擎，包含消息上下文和内存上下文
        self.engine = None
        # 完全清空工作流上下文
        self.workflow_contexts.clear()
        # 重置控制器上下文
        self.controller_context = None
        self.agent_config = None

    def set_result_message(self, content: str):
        """设置结果消息"""
        self.engine.history.set_result_msg(content)

    def get_result_message(self):
        """获取结果消息"""
        return self.engine.history.result_message

    def get_latest_assistant_message(self) -> Optional[ConversationMessage]:
        """获取最新的assistant消息"""
        for msg in reversed(self.engine.get_messages()):
            if msg.role == "assistant":
                return msg
        return None

    def get_latest_function_message(self) -> Optional[ConversationMessage]:
        """获取最新的function消息"""
        for msg in reversed(self.engine.get_messages()):
            if msg.role == "function":
                return msg
        return None

    def get_latest_user_message(self) -> Optional[ConversationMessage]:
        """获取最新的user消息"""
        enable_intent = os.getenv("ENABLE_INTENT_WORKFLOW", "false").lower() == "true"

        for msg in reversed(self.engine.get_messages()):
            if msg.role == "user":
                if enable_intent or msg.enable_history:
                    return msg

        return None

    def is_first_user_message(self) -> bool:
        """获取判断是否对话里面只包含当前一次用户query"""
        return sum(1 for msg in self.engine.get_messages() if msg.role == "user") == 1

    def get_latest_assistant_content(self) -> Optional[str]:
        """获取最新的assistant消息的content"""
        latest_msg = self.get_latest_assistant_message()
        return latest_msg.content if latest_msg else None

    def get_latest_assistant_function_call(self) -> Optional[Dict[str, Any]]:
        """获取最新的assistant消息中的function_call"""
        result = None
        latest_msg = self.get_latest_assistant_message()
        if latest_msg:
            function_call = latest_msg.function_call
            if isinstance(function_call, Dict):
                result = function_call
        return result

    def get_latest_assistant_function_call_list(self) -> Optional[List[Dict[str, Any]]]:
        """获取最新的assistant消息中的多function_call列表"""
        result = None
        latest_msg = self.get_latest_assistant_message()
        if latest_msg:
            function_call = latest_msg.function_call
            if isinstance(function_call, List):
                result = function_call
        return result

    def get_latest_user_content(self) -> Optional[str]:
        """获取最新的assistant消息中的function_call"""
        latest_msg = self.get_latest_user_message()
        if not latest_msg:
            err_msg = "No valid query for this conversation"
            logger.error(err_msg)
            raise JiuWenBaseException(
                error_code=StatusCode.CONTROLLER_INTENT_DETECTION_ERROR.code,
                message=err_msg,
            )
        return latest_msg.content

    def get_param_extraction_context(self, task_id, workflow_name):
        """获取提问器上下文"""
        key = f"{task_id}_{workflow_name}"
        return self.engine.get_param_extraction_context(key)

    def set_param_extraction_context(self, task_id, workflow_name, task_state):
        """设置提问器上下文"""
        key = f"{task_id}_{workflow_name}"
        state_key = "extract_params"
        self.engine.add_short_term_memory(key, state_key, task_state)

    def get_tool_results(self, task_id, workflow_name):
        """获取工具调用结果"""
        key = f"{task_id}_{workflow_name}"
        return self.engine.get_tool_results(key)

    def add_tool_results(self, task_id, workflow_name, task_state):
        """添加工具调用结果"""
        key = f"{task_id}_{workflow_name}"
        state_key = "tool"
        self.engine.add_short_term_memory(key, state_key, task_state)

    def set_global_variables(self, key, variable):
        """添加全局变量"""
        self.engine.add_short_term_memory(_GLOBAL_VARIABLES, key, variable)

    def get_global_variables(self, key, default=None):
        """获取全局变量"""
        try:
            global_variables_obj = self.engine.get_short_term_memory(_GLOBAL_VARIABLES)
            return (
                global_variables_obj.get(key)
                if global_variables_obj and isinstance(global_variables_obj, dict)
                else default
            )
        except KeyError:
            return default

    def load_controller_context(self, state: Optional[ControllerState] = None):
        """初始化或恢复控制器上下文

        Args:
            state: 可选的控制器状态，如果提供则使用它初始化，否则重置为默认值
        """
        # 使用提供的状态初始化
        if state:
            self.controller_context.current_workflow_index = (
                state.current_workflow_index
            )
            self.controller_context.start_workflow_executed = (
                state.start_workflow_executed
            )
            self.controller_context.start_workflow_completed = (
                state.start_workflow_completed
            )
            self.controller_context.end_workflow_executed = state.end_workflow_executed
            self.controller_context.end_workflow_completed = (
                state.end_workflow_completed
            )
            self.controller_context.global_iteration_count = (
                state.global_iteration_count
            )
            self.controller_context.processed_workflow_names = (
                state.processed_workflow_names
            )
            self.controller_context.task_end = state.task_end

    def load_controller_global_variables(self, agent_state=None):
        """多实例下恢复全局变量"""
        if agent_state and hasattr(agent_state, "controller_global_variables"):
            self.set_global_variables(
                WorkflowConstants.CONTROLLER_GLOBAL_VARIABLES_KEY,
                agent_state.controller_global_variables,
            )

    def get_controller_state(self, task_id: str) -> ControllerState:
        """获取控制器状态（用于向后兼容）

        Args:
            task_id: 任务ID

        Returns:
            ControllerState: 控制器状态对象
        """
        return ControllerState(
            current_workflow_index=self.controller_context.current_workflow_index,
            start_workflow_executed=self.controller_context.start_workflow_executed,
            start_workflow_completed=self.controller_context.start_workflow_completed,
            end_workflow_executed=self.controller_context.end_workflow_executed,
            end_workflow_completed=self.controller_context.end_workflow_completed,
            global_iteration_count=self.controller_context.global_iteration_count,
            processed_workflow_names=self.controller_context.processed_workflow_names,
            task_end=self.controller_context.task_end,
            task_id=task_id,
        )

    def is_start_workflow_executed(self) -> bool:
        """判断start_workflow是否已执行

        Returns:
            bool: 是否已执行
        """
        return self.controller_context.start_workflow_executed

    def is_end_workflow_executed(self) -> bool:
        """判断end_workflow是否已执行

        Returns:
            bool: 是否已执行
        """
        return self.controller_context.end_workflow_executed

    def is_end_workflow_completed(self) -> bool:
        """判断end_workflow是否已执行

        Returns:
            bool: 是否已执行
        """
        return self.controller_context.end_workflow_completed

    def is_start_workflow_completed(self) -> bool:
        """判断start_workflow是否已完成

        Returns:
            bool: 是否已完成
        """
        return self.controller_context.start_workflow_completed

    def is_task_end(self) -> bool:
        """标记任务结束

        Returns:
            bool: 是否已完成
        """
        return self.controller_context.task_end

    def mark_task_end(self):
        """标记任务结束

        Returns:
            bool: 是否已完成
        """
        self.controller_context.task_end = True

    def mark_all_workflow_completed(self):
        """标记所有除了结束工作流之外的工作流为完成状态

        Returns:
            bool: 是否已完成
        """
        self.controller_context.current_workflow_index = 1000
        self.controller_context.start_workflow_completed = True

    def mark_start_workflow_executed(self):
        """标记start_workflow已执行"""
        self.controller_context.start_workflow_executed = True

    def mark_start_workflow_completed(self):
        """标记start_workflow已完成"""
        self.controller_context.start_workflow_completed = True

    def mark_end_workflow_executed(self):
        """标记end_workflow已执行"""
        self.controller_context.end_workflow_executed = True

    def mark_end_workflow_completed(self):
        """标记start_workflow已完成"""
        self.controller_context.end_workflow_completed = True

    def is_general_workflow_completed(self, workflow_id: str) -> bool:
        """判断指定工作流ID是否已结束

        Args:
            workflow_id: 工作流ID

        Returns:
            bool: 如果该工作流状态为COMPLETED，则返回True；
                  如果工作流状态不是COMPLETED，则返回False；
                  如果未找到该工作流，则返回False并打印警告信息
        """
        # 首先从上下文管理器获取工作流上下文
        workflow_context = self.get_workflow_context_by_id(
            workflow_id, WorkflowType.GENERAL
        )
        if not workflow_context:
            return False

        # 检查工作流状态是否为COMPLETED
        if workflow_context.status == WorkflowStatus.COMPLETED:
            return True
        return False

    def is_general_workflow_running(self, workflow_id: str) -> bool:
        """判断指定工作流ID是否已经开始运行（即不处于PENDING状态）

        Args:
            workflow_id: 工作流ID

        Returns:
            bool: 如果该工作流状态不是PENDING，则返回True；
                  否则返回False
        """
        # 获取工作流上下文
        workflow_context = self.get_workflow_context_by_id(
            workflow_id, WorkflowType.GENERAL
        )
        if not workflow_context:
            return False

        # 检查工作流状态是否不是PENDING
        has_started = workflow_context.status != WorkflowStatus.PENDING
        return has_started

    def get_workflow_index(self) -> int:
        """获取当前工作流索引

        Returns:
            int: 当前工作流索引
        """
        return self.controller_context.current_workflow_index

    def update_workflow_index(self, index: int):
        """更新工作流索引

        Args:
            index: 新的工作流索引
        """
        self.controller_context.current_workflow_index = index

    def reset_controller_context(self):
        """重置控制器上下文"""
        self.controller_context = ControllerContext()

    def set_memory_request_params(
        self, memory_app_id: str, memory_enable_user_profile: bool
    ):
        """set request params of memory"""
        self.memory_app_id = memory_app_id
        self.memory_enable = self.memory_enable and memory_enable_user_profile

    async def get_memory_message(self, query: str) -> HumanMessage | None:
        """get memory message by query"""
        if self._memory_message is not None:
            return self._memory_message
        if not self.memory_enable:
            return None
        user_id = request_json.get().get("userId", "")
        if user_id == "" or self.memory_app_id == "":
            return None
        self._memory_message = await self._memory_proxy.get_related_memory_msg(
            user_id=user_id, scope_id=self.memory_app_id, query=query
        )
        return self._memory_message

    async def get_memory_variables(self):
        """get memory variables"""
        if (
            not hasattr(self.agent_config, "context")
            or not hasattr(self.agent_config.context, "enable_memory")
            or not hasattr(self.agent_config.context, "mem_variables")
        ):
            return ""
        if (
            not self.agent_config.context.enable_memory
            or not self.agent_config.context.mem_variables
        ):
            return ""
        all_vars_dict = await self.get_memory_variables_dict()
        if all_vars_dict is None:
            all_vars_dict = {}
        mem_variables = self.agent_config.context.mem_variables
        long_term_memory_variables = ""
        # 遍历配置中定义的变量，匹配并拼接结果
        for var in mem_variables:
            name = var.get(VARIABLE_NAME_KEY)
            if not name:
                continue

            # 从一次性获取的字典中取值，若无则用默认值
            var_value = all_vars_dict.get(name, "")
            default_value = var.get(VARIABLE_DEFAULT_KEY, "")
            if var_value:
                long_term_memory_variables += f"name: {name}, value: {var_value}\n"
            elif default_value:
                long_term_memory_variables += f"name: {name}, value: {default_value}\n"
                logger.warning(
                    f"No value found for variable '{name}', using default value."
                )
            else:
                continue
        if long_term_memory_variables:
            long_term_memory_variables = f"[记忆变量信息]：{long_term_memory_variables}"
        return long_term_memory_variables

    async def get_memory_variables_dict(self):
        """get memory variables dict"""
        if (
            not self.agent_config.context.enable_memory
            or not self.agent_config.context.mem_variables
        ):
            return {}
        user_id = request_json.get().get("userId", "")
        scope_id = request_json.get().get("agentId", "")
        if not user_id or not scope_id:
            return {}
        return await self._memory_proxy.get_variables(
            names=None, user_id=user_id, scope_id=scope_id
        )

    def _initialize_workflow_contexts(self):
        """初始化所有工作流上下文"""
        # 处理常规工作流
        if self.agent_config.workflows:
            for workflow_config in self.agent_config.workflows:
                self._create_workflow_context_from_config(
                    workflow_config, WorkflowType.GENERAL
                )

        # 处理开始工作流
        if self.agent_config.start_workflow:
            self._create_workflow_context_from_config(
                self.agent_config.start_workflow, WorkflowType.START
            )

        # 处理全局工作流
        if self.agent_config.global_workflows:
            for workflow_config in self.agent_config.global_workflows:
                self._create_workflow_context_from_config(
                    workflow_config, WorkflowType.GLOBAL
                )

        # 处理结束工作流
        if self.agent_config.end_workflow:
            self._create_workflow_context_from_config(
                self.agent_config.end_workflow, WorkflowType.END
            )

        # 处理默认工作流
        if self.agent_config.default_workflow:
            self._create_workflow_context_from_config(
                self.agent_config.default_workflow, WorkflowType.DEFAULT
            )

        # 处理意图工作流
        if self.agent_config.intent_workflows:
            for workflow_config in self.agent_config.intent_workflows:
                self._create_workflow_context_from_config(
                    workflow_config, WorkflowType.INTENT
                )

    def _create_workflow_context_from_config(self, workflow_config, workflow_type):
        """从工作流IR创建工作流上下文"""
        config_name = workflow_config.config_name
        workflow_ir = workflow_config.workflow_ir
        action_after_completion = workflow_config.action_after_completion
        workflow_id = workflow_ir.get("workflowId")
        workflow_name = workflow_ir.get("workflowName")
        if workflow_config.config_description:
            description = workflow_config.config_description
        else:
            description = workflow_ir.get("description")
        workflow_params = WorkspaceUtils.get_workflow_params(workflow_ir)
        workflow_params["arguments"] = workflow_config.arguments
        intent_name = (
            workflow_config.intent_name
            if hasattr(workflow_config, "intent_name")
            else None
        )
        intent_description = (
            workflow_config.intent_description
            if hasattr(workflow_config, "intent_description")
            else None
        )

        # 生成唯一键
        unique_key = self.generate_unique_key(workflow_id, workflow_type)

        # 创建工作流上下文并存储IR
        context = WorkflowContext(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            description=description,
            workflow_parameters=workflow_params,
            workflow_ir=workflow_ir,
            action_after_completion=action_after_completion,
            type=workflow_type,
            config_name=config_name,
            intent_name=intent_name,
            intent_description=intent_description,
        )
        self.workflow_contexts[unique_key] = context
        return context
