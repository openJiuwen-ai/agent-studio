#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import secrets
from typing import List, Optional, Union, Callable

from jiuwen.common.log.base import logger
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import HandlerType, WorkflowType
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType, TaskSubType


class Rule:
    """规则类，用于规则引擎中的条件和动作"""

    def __init__(self, rule_id: str, condition: Callable, action: Callable):
        """初始化规则

        Args:
            rule_id: 规则ID
            condition: 条件函数，接收消息和上下文，返回布尔值
            action: 动作函数，接收消息和上下文，返回任务或消息
        """
        self.rule_id = rule_id
        self.condition = condition
        self.action = action

    def apply(self, message: Message) -> Optional[Union[Task, Message]]:
        """应用规则

        Args:
            message: 要处理的消息
            context: 当前上下文

        Returns:
            如果条件匹配则执行动作并返回结果，否则返回None
        """
        if self.condition(message):
            return self.action(message)
        return None


class RuleModule:
    """规则库，管理一组规则"""

    def __init__(self, controller_config=None, context_manager=None):
        """初始化规则库

        Args:
            controller_config: 控制器配置，包含开始工作流、结束工作流和全局意图
        """
        self.rules: List[Rule] = []
        self.controller_config = controller_config
        self.context_manager = context_manager
        self.task_id = self.controller_config.task_id
        self.load_predefined_rules()  # 初始化时自动加载预定义规则

    @staticmethod
    def create_plugin_param_miss_task(msg):
        """创建插件参数缺失任务

        Args:
            msg: 消息对象

        Returns:
            Task: 生成的任务对象
        """
        return Task(
            task_type=TaskType.WORKFLOW_INTERRUPT,
            input_data={
                "reason": "插件参数缺失",
                "interrupt_type": "plugin_param_miss",
                "message": msg.content,
                "plugin_name": msg.runtime_data.get("plugin_name"),
                "missing_params": msg.runtime_data.get("missing_params", []),
            },
            workflow_id=msg.runtime_data.get("workflow_id"),
            sub_task_type=TaskSubType.ASK_USER_FOR_PARAM,
        )

    @staticmethod
    def create_plugin_call_confirm_task(msg):
        """创建插件调用确认任务

        Args:
            msg: 消息对象

        Returns:
            Task: 生成的任务对象
        """
        return Task(
            task_type=TaskType.WORKFLOW_INTERRUPT,
            input_data={
                "reason": "插件调用需要确认",
                "interrupt_type": "plugin_call_confirm",
                "message": msg.content,
                "plugin_name": msg.runtime_data.get("plugin_name"),
                "plugin_params": msg.runtime_data.get("params", {}),
                "confirmation_type": msg.runtime_data.get(
                    "confirmation_type", "standard"
                ),
            },
            workflow_id=msg.runtime_data.get("workflow_id"),
            sub_task_type=TaskSubType.PLUGIN_PARAM_REVISE,
        )

    @staticmethod
    def _condition_is_workflow_completion(msg):
        return msg.is_workflow_completion

    @staticmethod
    def _condition_is_plugin_param_miss(msg):
        return msg.is_plugin_param_miss

    @staticmethod
    def _condition_is_plugin_call_confirm(msg):
        return msg.is_plugin_call_confirm

    @staticmethod
    def _condition_is_global_intent(msg):
        return msg.is_global_intent

    def handle_workflow_completion(self, msg):
        """处理开始工作流完成

        Args:
            msg: 消息对象

        Returns:
            Task: 工作流完成任务
        """
        # 通过context_manager标记开始工作流已完成
        start_workflow_context = self.context_manager.get_start_workflow_contexts()
        end_workflow_context = self.context_manager.get_end_workflow_contexts()
        if (
            start_workflow_context
            and msg.content.get("workflow_name") == start_workflow_context.workflow_name
        ):
            logger.info("Start workflow completed")
            self.context_manager.mark_start_workflow_completed()
        if (
            end_workflow_context
            and msg.content.get("workflow_name") == end_workflow_context.workflow_name
        ):
            logger.info("End workflow completed")
            self.context_manager.mark_end_workflow_completed()

    def handle_start_workflow(self, msg):
        """处理开始工作流请求

        Args:
            msg: 消息对象

        Returns:
            Task: 生成的工作流开始任务
        """
        self.context_manager.mark_start_workflow_executed()
        logger.info("Start workflow execution requested")
        start_workflow_context = self.context_manager.get_start_workflow_contexts()
        return self.create_workflow_start_task(
            msg, start_workflow_context.workflow_id, WorkflowType.START
        )

    def create_workflow_start_task(self, msg, workflow_id, workflow_type):
        """创建工作流任务对象

        Args:
            workflow_type:
            msg: 消息对象
            workflow_info: 工作流对象，如果不提供，则从消息中获取

        Returns:
            Task: 创建的工作流任务对象
        """
        try:
            # 获取时间信息和任务ID
            task_id = getattr(msg, "task_id", "task")

            # 获取工作流信息
            logger.debug("Creating workflow task for: %s", workflow_id)

            # 创建唯一任务ID
            task_unique_id = f"{task_id}_workflow_{workflow_id}_{secrets.token_hex(4)}"

            # 获取工作流参数
            runtime_context = msg.runtime_data.get("runtime_context", {})
            if hasattr(runtime_context, "agent_workflow_context"):
                workflow_req_params = runtime_context.agent_workflow_context.get(
                    WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
                )
            else:
                workflow_req_params = {}

            # 添加全局意图
            if hasattr(msg, "controller_config") and hasattr(
                msg.controller_config, "global_intents"
            ):
                workflow_req_params["global_intents"] = (
                    msg.controller_config.global_intents
                )
            workflow_req_params = self.context_manager.get_global_variables(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
            )
            workflow_req_params["global_intents"] = (
                self.controller_config.global_intents
            )
            # 准备输入数据
            input_data = {
                "query": self.context_manager.get_latest_user_content(),  # 使用消息内容作为查询
                "workflow_req_params": workflow_req_params,
            }

            workflow_context = self.context_manager.get_workflow_context_by_id(
                workflow_id, workflow_type
            )
            # 增加工作流意图标签
            self.context_manager.add_intent_to_latest_user_message(
                workflow_context.workflow_name
            )
            return Task(
                id=task_unique_id,
                task_type=TaskType.WORKFLOW_START,
                input_data=input_data,
                sub_task_type=TaskSubType.STARTED_FROM_CONTROLLER,
                workflow_context=workflow_context,
            )
        except Exception as e:
            logger.error(
                f"Error creating workflow task: {str(e)}",
                simple_log="Error creating workflow task.",
            )
            return None

    def create_global_intent_task_by_interrupt_message(self, msg):
        """根据中断消息为全局意图创建工作流开始任务

        Args:
            msg: 意图消息

        Returns:
            Task: 生成的工作流开始任务对象
        """
        try:
            # 获取时间信息和任务ID
            task_id = getattr(msg, "task_id", "task")

            # 获取处理器信息
            intent_message = json.loads(msg.content)
            intent_id = intent_message.get("intent", {}).get("intent_id", None)
            global_intent = None
            for intent_config in self.controller_config.global_intents:
                if intent_config.intent_id == intent_id:
                    global_intent = intent_config
                    break
            return self.create_global_intent_task(global_intent, task_id)
        except Exception as e:
            logger.error(
                f"Error creating intent workflow task: {str(e)}",
                simple_log=f"Error creating intent workflow task: {type(e)}",
            )
            return None

    def create_global_intent_task(self, global_intent, task_id):
        """为全局意图创建工作流开始任务"""
        intent_id = global_intent.intent_id
        if global_intent.handler_type == HandlerType.WORKFLOW.value:
            workflow_config_name = global_intent.handler.get("name", None)
            if workflow_config_name:
                task_unique_id = (
                    f"{task_id}_workflow_intent_{intent_id}_{secrets.token_hex(4)}"
                )
                workflow_req_params = self.context_manager.get_global_variables(
                    WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
                )
                # 准备输入数据
                input_data = {
                    "query": self.context_manager.get_latest_user_content(),
                    "workflow_req_params": workflow_req_params,
                }
                workflow_context = (
                    self.context_manager.get_workflow_context_by_config_name(
                        workflow_config_name
                    )
                )
                if not workflow_context:
                    logger.error(
                        f"Workflow context {workflow_config_name} does not exist"
                    )
                else:
                    logger.info(
                        f"found workflow context {workflow_context.workflow_name} with "
                        f"type {workflow_context.type}"
                    )

                # 增加全局意图标签
                self.context_manager.add_intent_to_latest_user_message(
                    workflow_context.workflow_name
                )
                return Task(
                    id=task_unique_id,
                    task_type=TaskType.WORKFLOW_START,
                    input_data=input_data,
                    sub_task_type=TaskSubType.STARTED_FROM_CONTROLLER,
                    workflow_context=workflow_context,
                )
        if global_intent.handler_type == HandlerType.TEXT.value:
            task_unique_id = (
                f"{task_id}_workflow_intent_固定话术_{secrets.token_hex(4)}"
            )
            response = global_intent.handler
            input_data = {
                "response": response,
                "termination": global_intent.termination,
                "action": global_intent.action_after_completion,
            }
            return Task(
                id=task_unique_id,
                task_type=TaskType.WORKFLOW_MESSAGE,
                input_data=input_data,
            )
        return None

    def create_handoff_father_agent_task(self, task_id):
        """为agent handoff创建任务

        Args:
            task_id: 任务ID

        Returns:
            Task: 生成的agent handoff任务对象
        """
        try:
            task_unique_id = f"{task_id}_agent_handoff_father_{secrets.token_hex(4)}"
            # 准备输入数据
            father_agent = self.controller_config.parent_agent_metadata
            input_data = {
                "father_agent_id": father_agent.id,
                "father_agent_name": father_agent.name,
                "father_agent_description": father_agent.description,
                "query": self.context_manager.get_latest_user_content(),
            }
            logger.info(
                f"Creating agent handoff task for father agent {father_agent.name}"
            )
            return Task(
                id=task_unique_id,
                task_type=TaskType.AGENT_HANDOFF,
                input_data=input_data,
                sub_task_type=TaskSubType.HANDOFF_TO_FATHER,
            )
        except Exception as e:
            logger.error(
                f"Error creating agent handoff task: {str(e)}",
                simple_log="Error creating agent handoff task",
            )
            return None

    def create_handoff_child_agent_task(self, child_agent, task_id):
        """为agent handoff创建任务

        Args:
            child_agent: 子agent元数据
            task_id: 任务ID

        Returns:
            Task: 生成的agent handoff任务对象
        """
        try:
            task_unique_id = (
                f"{task_id}_agent_handoff_{child_agent.id}_{secrets.token_hex(4)}"
            )
            # 准备输入数据
            input_data = {
                "child_agent_id": child_agent.id,
                "child_agent_name": child_agent.name,
                "child_agent_description": child_agent.description,
                "child_agent_ir_path": getattr(child_agent, "ir_path", None),
                "child_agent_mode": getattr(child_agent, "mode", None),
                "query": self.context_manager.get_latest_user_content(),
            }
            logger.info(
                f"Creating agent handoff task for child agent: {child_agent.name}",
                simple_log="Creating agent handoff task for child agent successfully",
            )
            return Task(
                id=task_unique_id,
                task_type=TaskType.AGENT_HANDOFF,
                input_data=input_data,
                sub_task_type=TaskSubType.HANDOFF_TO_CHILD,
            )
        except Exception as e:
            logger.error(
                f"Error creating agent handoff task: {str(e)}",
                simple_log="Error creating agent handoff task",
            )
            return None

    def add_rule(self, rule):
        """添加规则

        Args:
            rule: 要添加的规则
        """
        self.rules.append(rule)

    def remove_rule(self, rule_id: str):
        """移除规则

        Args:
            rule_id: 要移除的规则ID
        """
        self.rules = [rule for rule in self.rules if rule.rule_id != rule_id]

    def apply_rules(self, message: Message) -> Optional[Union[Task, Message]]:
        """应用所有规则

        Args:
            message: 要处理的消息

        Returns:
            第一个匹配的规则执行结果，如果没有匹配的规则则返回None
        """
        for rule in self.rules:
            result = rule.apply(message)
            if result is not None:
                return result
        return None

    def is_start_workflow_executed(self):
        """判断start_workflow是否已执行

        Returns:
            bool: 是否已执行
        """
        return self.context_manager.is_start_workflow_executed()

    def is_new_user_input_before_workflow_start(self, msg):
        """检查是否为工作流开始前的新用户输入"""
        logger.info(
            f"task_id: {self.task_id}, start workflow wxecuted: {self.is_start_workflow_executed()}"
        )
        return (
            msg.message_type == MessageType.USER_INPUT
            and not self.is_start_workflow_executed()
        )

    def load_predefined_rules(self):
        """加载预定义规则"""
        # 如果有开始工作流，修改工作流完成规则来检测start_workflow完成
        self.add_rule(
            Rule(
                rule_id="workflow_completion",
                condition=self._condition_is_workflow_completion,
                action=self.handle_workflow_completion,
            )
        )

        # 工作流中断规则 - 插件参数缺失
        self.add_rule(
            Rule(
                rule_id="plugin_param_miss",
                condition=self._condition_is_plugin_param_miss,
                action=self.create_plugin_param_miss_task,
            )
        )

        # 工作流中断规则 - 插件调用确认
        self.add_rule(
            Rule(
                rule_id="plugin_call_confirm",
                condition=self._condition_is_plugin_call_confirm,
                action=self.create_plugin_call_confirm_task,
            )
        )

        # 控制器相关规则 - 开始工作流
        if self.controller_config.start_workflow:
            # 使用context_manager判断状态
            self.add_rule(
                Rule(
                    rule_id="start_workflow",
                    condition=self.is_new_user_input_before_workflow_start,
                    action=self.handle_start_workflow,
                )
            )

        # 控制器相关规则 - 全局意图
        if self.controller_config.global_intents:
            self.add_rule(
                Rule(
                    rule_id="global_intent",
                    condition=self._condition_is_global_intent,
                    action=self.create_global_intent_task_by_interrupt_message,
                )
            )
