# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
# N2L临时覆盖，适配该特性：运行时提供可用插件/知识库列表（按NL2Agent/Workflow的结构）
# 将前端传入的resource传入ResourceRetriever
import asyncio
import json
import random
import re
from datetime import datetime

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.nl_to_agent.adapter.input_adapter import InputAdapter
from agent_builder.nl_to_agent.base import OperatorInput
from agent_builder.nl_to_agent.common.chatbot import ChatBot
from agent_builder.nl_to_agent.common.llm_service import Nl2AgentProcessor
from agent_builder.nl_to_agent.llm_agent.agent_builder import LlmAgentBuilder
from agent_builder.nl_to_agent.storage.history import (
    AsyncHistoryStorage,
    AsyncSessionStorage,
    HistoryStorage,
    SessionStorage,
)
from agent_builder.nl_to_agent.workflow_agent.workflow_agent_builder import (
    WorkflowAgentBuilder,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage

from .context_manager import ContextManager
from .prompt import (
    AGENT_TYPE_IDENTIFIER_PROMPT_FOR_LLM_AGENT,
    AGENT_TYPE_IDENTIFIER_PROMPT_FOR_WORKFLOW,
)


class AgentTypeIdentifier:
    def __init__(self, model, agent_type):
        super().__init__()
        self.sys_prompt = (
            AGENT_TYPE_IDENTIFIER_PROMPT_FOR_LLM_AGENT
            if agent_type == "llm_agent"
            else AGENT_TYPE_IDENTIFIER_PROMPT_FOR_WORKFLOW
        )
        self.model = model

    @staticmethod
    def find_braces_content(text):
        """正则表达式匹配大括号及其内容"""
        pattern = r"(\{[^{}]*\})"
        matches = re.findall(pattern, text)
        return matches

    @staticmethod
    def parse_class(content):
        """解析分类结果"""
        content = json.loads(content)
        identified_class = content.get("class")
        return identified_class

    def identify(self, query):
        """分类"""
        logger.info("----- standard request -----")
        if len(query) == 1:
            chat_history = ""
        else:
            chat_history = "；".join([item["content"] for item in query[:-1]])
        user_prompt = f"对话历史：{chat_history}\n当前输入：{query[-1]['content']}\n"
        messages = [
            SystemMessage(content=self.sys_prompt),
            HumanMessage(content=user_prompt),
        ]
        for item in self.model.chat(messages, method="stream", add_prefix=False):
            if item.content:
                res = self.find_braces_content(item.content)[0]
                return res
        raise JiuWenBaseException(
            StatusCode.LLM_RESULT_ERROR.code,
            StatusCode.LLM_RESULT_ERROR.errmsg.format(
                error_msg="Failed to identify user intentions."
            ),
        )

    async def aidentify(self, query):
        """分类"""
        logger.info("----- standard request -----")
        if len(query) == 1:
            chat_history = ""
        else:
            chat_history = "；".join([item["content"] for item in query[:-1]])
        user_prompt = f"对话历史：{chat_history}\n当前输入：{query[-1]['content']}\n"
        messages = [
            SystemMessage(content=self.sys_prompt),
            HumanMessage(content=user_prompt),
        ]
        async for item in self.model.achat(messages, method="stream", add_prefix=False):
            if item.content:
                res = self.find_braces_content(item.content)[0]
                yield res
        raise JiuWenBaseException(
            StatusCode.LLM_RESULT_ERROR.code,
            StatusCode.LLM_RESULT_ERROR.errmsg.format(
                error_msg="Failed to identify user intentions."
            ),
        )

    def invoke(self, query):
        """执行分类"""
        retry_cnt = 0
        max_retries = 3
        while retry_cnt <= max_retries:
            try:
                content = self.identify(query)
                identified_class = self.parse_class(content)
                if identified_class in ["分类1", "分类2"]:
                    return identified_class, content
                retry_cnt += 1
            except Exception:
                logger.error("AgentTypeIdentifier run error")
                retry_cnt += 1
            if retry_cnt > max_retries:
                raise JiuWenBaseException(
                    StatusCode.LLM_RESULT_ERROR.code,
                    StatusCode.LLM_RESULT_ERROR.errmsg.format(
                        error_msg="Failed to identify user intentions."
                    ),
                )

    async def ainvoke(self, query):
        """执行分类"""
        retry_cnt = 0
        max_retries = 3
        llm_request_error_msg = None

        while retry_cnt <= max_retries:
            try:
                async for content in self.aidentify(query):
                    identified_class = self.parse_class(content)
                    if identified_class in ["分类1", "分类2"]:
                        yield identified_class, content
                        return
                retry_cnt += 1
            except Exception as e:
                llm_request_error_msg = str(e)
                logger.error("AgentTypeIdentifier run error")
                if retry_cnt < max_retries:
                    wait_time = (2 * retry_cnt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                    retry_cnt += 1
                else:
                    if isinstance(e, JiuWenBaseException):
                        raise e
                    raise JiuWenBaseException(
                        StatusCode.LLM_RESULT_ERROR.code, llm_request_error_msg
                    ) from e


class Controller:
    """对话控制器，负责控制状态和管理上下文。

    Controller 提供统一接口来控制Agent生成阶段，并绑定上下文管理器。

    Attributes:
        task_id: 对话ID。
        workflow_state: 工作流状态。
        _history_size: 已存储的历史对话长度。
        context_manager (ContextManager): 上下文管理器。
    """

    def __init__(self, task_id):
        self.context_manager = ContextManager()
        self.task_id = task_id
        self.workflow_state = 0
        self._history_size = 0
        self.resource_config = {"plugin": [], "knowledge": [], "workflow": []}
        self.plugin_dict = {}
        self.workflow_dict = {}
        if not self.load_session():
            self.context_manager.add_message(
                task_id, role="system", content="你是一个助手, 请用中文回答"
            )

    @staticmethod
    def create_controller(task_id):
        """工厂方法：创建一个 Controller 对象。

        Args:
                task_id (str): 当前任务ID。

        Returns:
                Controller: 新创建的 Controller 实例。
        """
        return Controller(task_id=task_id)

    @staticmethod
    def datetime_to_str(dt: datetime):
        """将 datetime 对象转换为字符串格式。

        Args:
                dt (datetime): 需要转换的 datetime 对象。
        Returns:
                str: 转换后的字符串。
        """
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def str_to_datetime(dt_str: str):
        """将字符串格式转换为 datetime 对象。

        Args:
                dt_str (str): 需要转换的字符串。
        Returns:
                datetime: 转换后的 datetime 对象。
        """
        if dt_str is None:
            return None
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

    def clarify_llm(self, clarifier_output):
        """LLM Agent 意图澄清阶段使用，保存会话状态"""
        self.context_manager.add_assistant_message(
            self.task_id, clarifier_output, "分类3"
        )
        self.save_session()

    def design_llm(self, designer_output):
        """LLM Agent 设计阶段使用，保存会话状态"""
        self.context_manager.add_assistant_message(
            self.task_id, designer_output, "分类3"
        )
        self.save_session()

    def reset_llm_agent(self, agent_constructor_output):
        """LLM Agent 构造阶段使用，重置会话内容，保存最终的 Agent 定义"""
        self.delete_session()
        self.context_manager.clear_dialogue(self.task_id)
        self.context_manager.add_user_message(
            self.task_id, f"原始的Agent设计为：{agent_constructor_output}", "分类3"
        )
        self.save_session()

    def start_workflow(self):
        """更新 Workflow Agent 生成阶段状态为流程判断阶段(1)，并保存会话状态"""
        self.workflow_state = 1
        self.save_session()

    def design_workflow(self):
        """更新 Workflow Agent 生成阶段状态为流程设计阶段(2)，并保存会话状态"""
        self.workflow_state = 2
        self.save_session()

    def refine_workflow(self):
        """更新 Workflow Agent 生成阶段状态为流程修改阶段(3)，并保存会话状态"""
        self.workflow_state = 3
        self.save_session()

    def construct_workflow(self):
        """更新 Workflow Agent 生成阶段状态为流程构造阶段(4)，并保存会话状态"""
        self.workflow_state = 4
        self.save_session()

    def finish_workflow(self):
        """完成 Workflow Agent 生成，重置为初始状态"""
        self.workflow_state = 0
        self.context_manager.clear_dialogue(self.task_id)
        self.delete_session()
        self.context_manager.add_message(
            self.task_id, role="system", content="你是一个助手, 请用中文回答"
        )

    def load_session(self):
        """加载会话状态"""
        data = SessionStorage.load(self.task_id)
        state = data["state"]
        resource_config = data["resource_config"]
        plugin_dict = data["plugin_dict"]
        workflow_dict = data["workflow_dict"]
        history_str_list = HistoryStorage().get_all(f"history:{self.task_id}")
        if history_str_list:
            if state:
                self.workflow_state = int(state)
            if resource_config:
                self.resource_config = json.loads(resource_config)
            if plugin_dict:
                self.plugin_dict = json.loads(plugin_dict)
            if workflow_dict:
                self.workflow_dict = json.loads(workflow_dict)
            history_list = [
                json.loads(history_str.decode("utf-8"))
                for history_str in history_str_list
            ]
            self._history_size = len(history_list)
            for history_item in history_list:
                self.context_manager.add_message(
                    self.task_id,
                    **{
                        "role": history_item.get("role"),
                        "content": history_item.get("content"),
                        "timestamp": self.str_to_datetime(
                            history_item.get("timestamp")
                        ),
                        "intent_label": history_item.get("intent", ""),
                    },
                )
            return True
        return False

    def save_session(self):
        """保存会话状态"""
        SessionStorage.save(
            self.task_id,
            self.workflow_state,
            self.resource_config,
            self.plugin_dict,
            self.workflow_dict,
        )
        messages = self.context_manager.get_dialogue_history(self.task_id)
        for message in messages[self._history_size:]:
            HistoryStorage().add(
                f"history:{self.task_id}",
                {
                    "role": message.role,
                    "content": message.content,
                    "timestamp": self.datetime_to_str(message.timestamp),
                    "intent": message.intent_label or "",
                },
            )
        self._history_size = len(messages)

    def delete_session(self):
        """删除会话状态"""
        SessionStorage.delete(self.task_id)
        HistoryStorage().delete(f"history:{self.task_id}")
        self._history_size = 0

    async def async_load_session(self):
        data = await AsyncSessionStorage.load(self.task_id)
        state = data["state"]
        resource_config = data["resource_config"]
        plugin_dict = data["plugin_dict"]
        workflow_dict = data["workflow_dict"]
        history_str_list = await AsyncHistoryStorage().get_all(f"history:{self.task_id}")
        if history_str_list:
            if state:
                self.workflow_state = int(state)
            if resource_config:
                self.resource_config = json.loads(resource_config)
            if plugin_dict:
                self.plugin_dict = json.loads(plugin_dict)
            if workflow_dict:
                self.workflow_dict = json.loads(workflow_dict)
            history_list = [
                json.loads(
                    history_str.decode("utf-8")
                    if isinstance(history_str, bytes)
                    else history_str
                )
                for history_str in history_str_list
            ]
            self._history_size = len(history_list)
            for history_item in history_list:
                self.context_manager.add_message(
                    self.task_id,
                    **{
                        "role": history_item.get("role"),
                        "content": history_item.get("content"),
                        "timestamp": self.str_to_datetime(
                            history_item.get("timestamp")
                        ),
                        "intent_label": history_item.get("intent", ""),
                    },
                )
            return True
        return False

    async def async_save_session(self):
        await AsyncSessionStorage.save(
            self.task_id,
            self.workflow_state,
            self.resource_config,
            self.plugin_dict,
            self.workflow_dict,
        )
        messages = self.context_manager.get_dialogue_history(self.task_id)
        for message in messages[self._history_size:]:
            await AsyncHistoryStorage().add(
                f"history:{self.task_id}",
                {
                    "role": message.role,
                    "content": message.content,
                    "timestamp": self.datetime_to_str(message.timestamp),
                    "intent": message.intent_label or "",
                },
            )
        self._history_size = len(messages)

    async def async_delete_session(self):
        await AsyncSessionStorage.delete(self.task_id)
        await AsyncHistoryStorage().delete(f"history:{self.task_id}")
        self._history_size = 0

    async def async_clarify_llm(self, clarifier_output):
        self.context_manager.add_assistant_message(
            self.task_id, clarifier_output, "分类3"
        )
        await self.async_save_session()

    async def async_design_llm(self, designer_output):
        self.context_manager.add_assistant_message(
            self.task_id, designer_output, "分类3"
        )
        await self.async_save_session()

    async def async_reset_llm_agent(self, agent_constructor_output):
        await self.async_delete_session()
        self.context_manager.clear_dialogue(self.task_id)
        self.context_manager.add_user_message(
            self.task_id, f"原始的Agent设计为：{agent_constructor_output}", "分类3"
        )
        await self.async_save_session()

    async def async_start_workflow(self):
        self.workflow_state = 1
        await self.async_save_session()

    async def async_design_workflow(self):
        self.workflow_state = 2
        await self.async_save_session()

    async def async_refine_workflow(self):
        self.workflow_state = 3
        await self.async_save_session()

    async def async_construct_workflow(self):
        self.workflow_state = 4
        await self.async_save_session()

    async def async_finish_workflow(self):
        self.workflow_state = 0
        self.context_manager.clear_dialogue(self.task_id)
        await self.async_delete_session()
        self.context_manager.add_message(
            self.task_id, role="system", content="你是一个助手, 请用中文回答"
        )


class Executor:
    def __init__(self, state, model_info, schema_config_dict, resource):
        self.query = state.get("query")
        self.task_id = state.get("task_id")
        self.agent_type = state.get("agent_type")
        input_adapter = InputAdapter(schema_config_dict, resource, agent_type=state.get("agent_type"))
        nl2agent_processor = Nl2AgentProcessor(model_info)
        self.model = nl2agent_processor
        self.controller = Controller.create_controller(task_id=self.task_id)
        self.identifier = AgentTypeIdentifier(self.model, self.agent_type)
        self.llm_agent_builder = LlmAgentBuilder(
            model=self.model, input_adapter=input_adapter, controller=self.controller
        )
        self.workflow_agent_builder = WorkflowAgentBuilder(
            model=self.model, input_adapter=input_adapter, controller=self.controller
        )

    def invoke(self, query):
        """执行对话或Agent生成流程"""
        self.controller.context_manager.add_user_message(self.task_id, self.query)
        chat_history = self.controller.context_manager.get_latest_k_chat_history(
            self.task_id, 10
        )
        identified_class, _ = self.identifier.invoke(
            chat_history[1:]
        )  # 去掉system prompt
        inputs = OperatorInput(query=query)
        # 根据意图选择对应的 LLM
        if identified_class == "分类2":
            try:
                return ChatBot(
                    self.model, self.controller.context_manager, self.task_id
                ).invoke(inputs)
            except Exception as e:
                logger.error(f"分类2大模型回复失败：{str(e)}")
                raise JiuWenBaseException(
                    StatusCode.LLM_RESULT_ERROR.code,
                    StatusCode.LLM_RESULT_ERROR.errmsg.format(
                        error_msg=f"分类2大模型回复失败：{str(e)}"
                    ),
                ) from e
        if self.agent_type == "llm_agent":
            try:
                self.controller.context_manager.update_latest_message_intent(
                    self.task_id, "分类3"
                )
                return self.llm_agent_builder.invoke(inputs)
            except JiuWenBaseException as e:
                logger.error(f"LLM Agent失败：{str(e)}")
                raise
        if self.agent_type == "workflow":
            try:
                self.controller.context_manager.update_latest_message_intent(
                    self.task_id, "分类1"
                )
                return self.workflow_agent_builder.invoke(inputs)
            except JiuWenBaseException as e:
                logger.error(f"Workflow Agent失败：{str(e)}")
                raise
        raise JiuWenBaseException(
            StatusCode.LLM_RESULT_ERROR.code,
            StatusCode.LLM_RESULT_ERROR.errmsg.format(error_msg="'无法识别的意图'"),
        )

    async def ainvoke(self, query):
        """执行对话或Agent生成流程"""
        self.controller.context_manager.add_user_message(self.task_id, self.query)
        chat_history = self.controller.context_manager.get_latest_k_chat_history(
            self.task_id, 10
        )  # 去掉system prompt

        async for identified_class, _ in self.identifier.ainvoke(chat_history[1:]):
            inputs = OperatorInput(query=query)

            # 路由分发：确定执行器、对应的意图以及错误日志前缀
            if identified_class == "分类2":
                runner = ChatBot(
                    self.model, self.controller.context_manager, self.task_id
                )
                intent = None
                err_prefix = "Classification 2 LLM response failed"
            elif self.agent_type == "llm_agent":
                runner = self.llm_agent_builder
                intent = "分类3"
                err_prefix = "LLM Agent failed"
            elif self.agent_type == "workflow":
                runner = self.workflow_agent_builder
                intent = "分类1"
                err_prefix = "Workflow Agent failed"
            else:
                raise JiuWenBaseException(
                    StatusCode.LLM_RESULT_ERROR.code,
                    StatusCode.LLM_RESULT_ERROR.errmsg.format(
                        error_msg="'Unrecognized intent'"
                    ),
                )

            # 状态更新：如果用户存在意图，则更新
            if intent:
                self.controller.context_manager.update_latest_message_intent(
                    self.task_id, intent
                )

            # 统一执行与异常处理
            try:
                async for item in runner.ainvoke(inputs):
                    yield item
                return  # 全局唯一的正常退出点

            except Exception as e:
                logger.error(f"{err_prefix}：{str(e)}", exc_info=True)

                # 针对特定类型的特殊处理
                if self.agent_type == "workflow":
                    await self.controller.async_finish_workflow()

                # 统一抛出异常
                if isinstance(e, JiuWenBaseException):
                    raise
                raise JiuWenBaseException(
                    StatusCode.LLM_RESULT_ERROR.code,
                    StatusCode.LLM_RESULT_ERROR.errmsg.format(
                        error_msg=f"{err_prefix}：{str(e)}"
                    ),
                ) from e
