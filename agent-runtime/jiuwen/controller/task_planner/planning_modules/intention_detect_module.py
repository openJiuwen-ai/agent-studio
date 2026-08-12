#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import ast
import asyncio
import copy
import os
import re
import time
from collections import namedtuple
from typing import List, Union

from jiuwen.common.configs.env_constants import USE_EI_INTENT_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.intent_detection.layers.base import IntentInput
from jiuwen.common.intent_detection.layers.intent_detection import IntentDetection
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.messages import AIMessage, BaseMessage
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.controller.common.config import (
    IntentDetectionConfig,
    IntentIdentificationConfig,
)
from jiuwen.controller.common.constants import (
    IntentionDetectConstants,
    WorkflowConstants,
)
from jiuwen.controller.common.enum import (
    WorkflowType,
    HandlerType,
    IntentIdentificationMethod,
)
from jiuwen.controller.context_manager.workflow_context import WorkflowContext
from jiuwen.insight.handlers.async_handler import InsightHandler
from jiuwen.orchestration.common.perf_log import wf_performance_buffer
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.planner.common.exception import LLMInvocationFailedException
from jiuwen.planner.common.stream_post_utils import (
    convert_ai_message_to_llm_output,
    create_trace_manager,
    MODEL_STAT,
    MODEL_USAGE,
    LATENCY,
)
from jiuwen.plugin import Param
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.plugin import BasePlugin
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.plugin.models.tool import WORKFLOW_END_TYPE
from jiuwen.prompt import TemplateManager, Prompt, Template

DEFAULT_INTENT = "意图不明"
WORKFLOW_HANDLER_TYPE = "WORKFLOW"
AGENT_HANDLER_TYPE = "AGENT"
LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


def _get_config_info(model_name: str):
    formatted_config = dict()
    formatted_config[IntentionDetectConstants.USER_PROMPT] = ""
    # default class is '分类0' if '分类0' in category_list, otherwise '分类1'
    formatted_config[IntentionDetectConstants.DEFAULT_CLASS] = "分类1"

    # 根据环境变量USE_EI_INTENT决定使用哪个模板，默认为true
    use_ei_intent = os.getenv(USE_EI_INTENT_KEY, "true").lower() == "true"

    if use_ei_intent:
        template_name = "ei_intent_detection"
    else:
        template_name = "controller_intent_detection"

    # get intent_detection_template from prompt resource
    intent_detection_template = TemplateManager().get(
        name=template_name, filters={"tag": model_name}
    )
    formatted_config[IntentionDetectConstants.INTENT_DETECTION_TEMPLATE] = (
        intent_detection_template
    )

    # enable_history switch
    formatted_config[IntentionDetectConstants.ENABLE_HISTORY] = True

    # enable_input switch
    formatted_config[IntentionDetectConstants.ENABLE_INPUT] = False

    # chatHistoryMaxTurn
    formatted_config[IntentionDetectConstants.CHAT_HISTORY_MAX_TURN] = 10

    # exampleContent
    return formatted_config


class IntentionDetectModule:
    """
    Planning intention detect module class
    """

    def __init__(self, plan_config, llm, context_manager):
        self.llm = llm
        self.context_manager = context_manager
        self.plan_config = plan_config
        self.category_2_intent_function_map = {}
        self.intent_function_2_category_map = {}
        self.intent_config = IntentDetectionConfig(
            **_get_config_info(self.llm.model_name if self.llm else "")
        )
        # 保存当前使用的模板类型
        self.use_ei_intent = os.getenv(USE_EI_INTENT_KEY, "true").lower() == "true"
        # 新增：专门记录全局意图的映射
        self.category_2_global_intent_map = {}
        self.global_intent_2_category_map = {}
        self.intent_id_to_function_map = {}
        self.category_2_agent_name_map = {}
        self.agent_name_2_category_map = {}
        self.category_2_child_id_map = {}
        self.intent_id_to_child_category_map = {}
        self.workflow_handler = None

        self.enable_multi_layer_detection = False
        if plan_config.intent_identification:
            self.enable_multi_layer_detection = (
                plan_config.intent_identification.enable_multi_layer_detection
            )
            if self.enable_multi_layer_detection:
                self.multi_layer_id_cfg = (
                    plan_config.intent_identification.multi_layer_id_cfg
                )
                self.multi_layer_id_cfg.llm_matcher_config.user_prompt = (
                    plan_config.user_prompt
                )

    def _handle_latest_intent(self, task_id):
        """处理LATEST意图的逻辑

        LATEST 语义：沿用上一次的意图/中断工作流，跳过新一轮意图识别。
        优先级：
          1. 中断任务栈中的工作流（由 invoke 的 latest_intent 参数传入，
             本方法无法直接访问 task_queue，交由 invoke 的 L336-342 处理）
          2. 会话历史中上一条 user 消息的意图（get_second_latest_user_intent）

        注意：
          - 不能用 context_manager.get_latest_intent()，因为当前轮报文已被
            add_user_message 加入 _msgs[-1]，其 intent 为空；必须用
            get_second_latest_user_intent() 取上一条 user 消息的意图。
          - 上一轮意图为"意图不明"等无效值时不应沿用，返回 None 以回落到
            LLM 意图识别（与修复前行为保持一致）。

        Args:
            task_id: 任务ID

        Returns:
            str or None: 上一次的意图/工作流名称，如果无法确定或无效则返回None
        """
        logger.info(
            f"task_id: {task_id}| handle LATEST intent, use interrupted task if there is any"
        )

        # 返回会话历史中上一条 user 消息的意图
        history_intent = self.context_manager.get_second_latest_user_intent()
        if history_intent and history_intent not in (
            "分类1",
            "分类0",
            "意图不明",
        ):
            logger.info(
                f"task_id: {task_id}| LATEST resolved from history: {history_intent}",
                simple_log=f"task_id: {task_id}| LATEST from history",
            )
            return history_intent

        logger.info(
            f"task_id: {task_id}| LATEST has no valid prior intent, will fall back to detection",
            simple_log=f"task_id: {task_id}| LATEST no valid prior intent",
        )
        return None

    @staticmethod
    def _detect_intent_with_api_method(task_id: str):
        """使用API方式进行意图识别"""
        logger.info(f"task_id {task_id}| Using API-based intent detection")
        pass

    @staticmethod
    def _get_default_intent() -> str:
        """获取默认意图"""
        return DEFAULT_INTENT

    @staticmethod
    def _need_fine_grained_detection(intent_function: str, task_id: str) -> bool:
        """判断是否需要进行细粒度检测

        Args:
            intent_function: 识别出的意图函数名
            task_id: 任务ID

        Returns:
            bool: 是否需要细粒度检测
        """
        # 如果意图函数无效（默认意图或None），需要细粒度检测
        if not intent_function:
            logger.info(
                f"task_id {task_id}| Intent function is invalid ({intent_function}), need fine-grained detection",
                simple_log=f"task_id {task_id}| Intent function is invalid, need fine-grained detection",
            )
            return True

        logger.info(
            f"task_id {task_id}| Intent function {intent_function} is valid, no need for fine-grained detection",
            simple_log=f"task_id {task_id}| Intent function is valid, no need for fine-grained detection",
        )
        return False

    @staticmethod
    def _extract_usage_metadata(llm_message):
        """提取元数据"""
        model_stat = {}
        model_usage = {}

        if hasattr(llm_message, "usage_metadata") and llm_message.usage_metadata:
            stats = getattr(llm_message.usage_metadata, "model_stats", {})
            model_stat.update(
                stats if isinstance(stats, dict) else getattr(stats, "__dict__", {})
            )
            model_usage["input_tokens"] = llm_message.usage_metadata.input_tokens
            model_usage["output_tokens"] = llm_message.usage_metadata.output_tokens
            model_usage["total_tokens"] = llm_message.usage_metadata.total_tokens

        return model_stat, model_usage

    @staticmethod
    def _prepare_insights_output(result):
        """insight输出"""
        llm_output = dict(role="assistant", content="")
        llm_output.update(result.converted_output.dict(exclude_defaults=True))

        if (
            hasattr(result.llm_message, "usage_metadata")
            and result.llm_message.usage_metadata
        ):
            if hasattr(result.llm_message.usage_metadata, "latency"):
                llm_output["latency"] = result.llm_message.usage_metadata.latency

        output_on_insights = copy.deepcopy(llm_output)
        output_on_insights.update(
            {
                LATENCY: {"total_latency": result.total_time},
                MODEL_STAT: result.model_stat,
                MODEL_USAGE: result.model_usage,
            }
        )

        return output_on_insights

    @staticmethod
    def _get_insight_queue_from_trace_handlers(runtime_data: dict):
        """从 runtime_data 中的 trace_handlers 获取 insight_queue

        Args:
            runtime_data: 运行时数据，包含 trace_handlers

        Returns:
            Queue: insight_queue 用于发送调试信息，如果未找到则返回 None
        """
        trace_handlers = runtime_data.get("trace_handlers")
        if trace_handlers is None:
            return None

        # 从 TraceManager 获取 InsightHandler
        for handler in getattr(trace_handlers, "trace_handlers", []):
            if isinstance(handler, InsightHandler):
                return getattr(handler.client, "data_queue", None)

        return None

    @staticmethod
    async def _send_intent_workflow_debug_info(
        output, insight_queue: asyncio.Queue, task_id: str
    ):
        """将意图识别工作流的调试信息发送到 insight_queue

        Args:
            output: 工作流流式输出的 StreamData 对象
            insight_queue: 调试信息队列
            task_id: 任务ID
        """
        try:
            # 构造调试信息数据，标记为意图识别工作流的调试信息
            debug_data = output.data.copy() if output.data else {}
            # 使用 workflow_node_message 事件类型，保持与普通工作流调试信息一致的格式
            msg = {
                "data": debug_data,
                "event": "workflow_node_message",  # 指定事件类型
            }
            try:
                insight_queue.put_nowait(msg)
            except asyncio.QueueFull:
                await asyncio.wait_for(insight_queue.put(msg), timeout=0.2)

            logger.info(
                f"task_id: {task_id} | Sent intent workflow debug info to insight_queue"
            )
        except TimeoutError as e:
            logger.error(f"task_id: {task_id} | Timeout error: {str(e)}")
        except Exception as e:
            logger.warning(
                f"task_id: {task_id} | Failed to send intent workflow debug info: {str(e)}"
            )

    def format_tools(
        self, plugins: List[Union[Function, BasePlugin, RestFulAPI]] = None
    ):
        """
        格式化插件和工作流工具为标准接口格式

        Args:
            plugins: 插件列表，可以是Function或BasePlugin对象的列表
            workflows: 工作流列表，是ControllerWorkflow对象的列表

        Returns:
            list: 格式化后的工具列表
        """
        formatted_tools = []

        # 处理插件
        if plugins:
            for plugin in plugins:
                if isinstance(plugin, (Function, BasePlugin, RestFulAPI)):
                    # 格式化Function或BasePlugin
                    formatted_tools.append(Param.format_functions(plugin))

        if self.context_manager.workflow_contexts:
            for _, context in self.context_manager.workflow_contexts.items():
                workflow_info = {
                    "name": context.workflow_name,
                    "description": context.config_description,
                    "parameters": context.workflow_parameters,
                }
                formatted_tools.append(workflow_info)

        return formatted_tools

    async def invoke(self, active_workflows: list, **kwargs):
        """基于活动工作流列表执行意图识别

        Args:
            active_workflows: 活动工作流列表

        Returns:
            str: 检测到的意图（工作流ID）
        """
        task_id = kwargs.get("task_id")
        start_time = time.perf_counter()
        global_only = kwargs.get("global_only", False)
        latest_intent = kwargs.get("latest_intent")

        intent_function = None

        # =============================== 指定意图，保持原有处理逻辑 ===================================
        # 第一步：检查是否有指定意图
        specified_intent = self.context_manager.get_global_variables(
            WorkflowConstants.INTENT, None
        )
        if specified_intent == "LATEST":
            # 处理LATEST逻辑
            intent_function = self._handle_latest_intent(task_id)
            if latest_intent:
                logger.info(
                    f"latest_intent is {latest_intent}, "
                    f"message list is {self.context_manager.engine.get_messages()}",
                    simple_log="get latest_intent",
                )
                intent_function = latest_intent
        elif specified_intent:
            # 有值但不是LATEST，执行指定意图匹配逻辑
            intent_function = self._handle_specified_intent(
                specified_intent, active_workflows, task_id
            )

        # 如果指定意图处理失败或没有指定意图，使用默认识别方式
        if intent_function is None:
            # 多级意图匹配
            if self.enable_multi_layer_detection:
                layered_start = time.perf_counter()
                intent_function = await self._detect_with_multi_layer_intent_detection(
                    task_id, active_workflows, global_only
                )
                layered_duration_ms = round(
                    (time.perf_counter() - layered_start) * 1000
                )
                wf_performance_buffer.info(
                    f"time for layered intent detection-{task_id}",
                    layered_duration_ms,
                    is_record=True,
                )
            else:
                message = kwargs.get("message")
                runtime_data = message.runtime_data if message is not None else {}

                if self.plan_config.intent_identification is not None:
                    # 使用新的粗粒度意图识别逻辑
                    intent_function = (
                        await self._detect_intent_with_coarse_grained_method(
                            active_workflows,
                            task_id,
                            global_only=global_only,
                            runtime_data=runtime_data,
                        )
                    )
                elif self.llm is not None:
                    # 使用现有的 LLM 意图识别逻辑（细粒度识别）
                    intent_function = await self._detect_intent_with_llm(
                        active_workflows,
                        task_id,
                        global_only=global_only,
                        runtime_data=runtime_data,
                    )
                else:
                    # 如果没有配置意图识别工作流和大模型，意图识别报错
                    raise JiuWenBaseException(
                        StatusCode.WORKFLOW_INTENT_DETECTION_OUTPUT_ERROR.code,
                        StatusCode.WORKFLOW_INTENT_DETECTION_OUTPUT_ERROR.errmsg.format(
                            error_msg="Intention detection workflow and LLM not configured"
                        ),
                    )

        # 记录性能数据
        end_time = time.perf_counter()
        intent_function_time = round((end_time - start_time) * 1000)
        wf_performance_buffer.info(
            f"controller intent function-{task_id}",
            intent_function_time,
            is_record=True,
        )
        if intent_function not in ("分类1", "分类0", "意图不明"):
            self.context_manager.set_latest_intent(intent_function)
        return intent_function

    def intent_detection_post_process(self, result):
        """
        Post-process the result
        Args:
            result: The result is a dict string.
        Returns:
            The processed results are 'class' and 'reason'
        """
        if "```" in result:
            # 提取代码块内容
            code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", result)
            if code_block_match:
                result = code_block_match.group(1).strip()
        try:
            parsed_dict = ast.literal_eval(result)
            if not isinstance(parsed_dict, dict):
                return self.intent_config.default_class
        except Exception:
            return self.intent_config.default_class

        # 根据使用的模板类型处理不同的输出格式
        if self.use_ei_intent:
            # ei_intent_detection 格式: {"result": "int"}
            if not parsed_dict.get("result"):
                return self.intent_config.default_class

            result_value = parsed_dict.get("result")
            # 如果result是数字，转换为分类格式
            if isinstance(result_value, int):
                intent_class = f"分类{result_value}"
            elif isinstance(result_value, str):
                # 如果已经是字符串，尝试提取数字或直接使用
                if result_value.isdigit():
                    intent_class = f"分类{result_value}"
                else:
                    # 尝试从字符串中提取分类信息
                    match = re.search(r"分类(\d+)", result_value)
                    if match:
                        intent_class = f"分类{match.group(1)}"
                    else:
                        # 如果无法解析，返回默认分类
                        return self.intent_config.default_class
            else:
                return self.intent_config.default_class
        else:
            # controller_intent_detection 格式: {"class": "分类xx"}
            if not parsed_dict.get(IntentionDetectConstants.CLASS):
                return self.intent_config.default_class

            intent_class = (
                parsed_dict.get(IntentionDetectConstants.CLASS)
                .replace("\n", "")
                .replace(" ", "")
                .replace("'", "")
                .replace('"', "")
            )
            match = re.search(r"分类\d+", intent_class)
            if match:
                intent_class = match.group(0)
            else:
                return self.intent_config.default_class

        logger.info(
            f"Finish detect intention, class: {intent_class}",
            simple_log="Finish detect intention",
        )
        return intent_class

    def get_function_category_info(
        self, active_workflows: list, global_only: bool = False
    ):
        """基于传入的活动工作流列表和全局意图生成分类信息

        Args:
            active_workflows: 活动工作流列表
            global_only: 是否只使用全局意图

        Returns:
            str: 格式化的分类信息，如 "分类1: 闲聊\n分类2: 查询订单"
        """
        # 获取基础的意图列表
        intents = self._build_intent_mappings_and_list(active_workflows, global_only)

        # 转换为带"分类X:"前缀的格式
        category_parts = []
        for intent in intents:
            category_parts.append(f"分类{intent['id']}: {intent['description']}")

        category_info = "\n".join(category_parts) if category_parts else "分类1: 闲聊"

        logger.info(
            f"Generated category info with global "
            f"intents{'(only)' if global_only else ' and active workflows'}: {category_info}",
            simple_log="Generated category info",
        )
        logger.info(
            f"Global intent mappings: {self.category_2_global_intent_map}",
            simple_log="get Global intent mappings",
        )

        return category_info

    async def create_intention_detect_llm_input(self, category_info, chat_history, query):
        """create intent detect llm input"""
        current_inputs = {
            IntentionDetectConstants.CATEGORY_INFO: category_info,
            IntentionDetectConstants.DEFAULT_CLASS: self.intent_config.default_class,
            IntentionDetectConstants.ENABLE_HISTORY: self.intent_config.enable_history,
            IntentionDetectConstants.ENABLE_INPUT: self.intent_config.enable_input,
            IntentionDetectConstants.EXAMPLE_CONTENT: "\n\n".join(
                self.intent_config.example_content
            ),
            IntentionDetectConstants.CHAT_HISTORY_MAX_TURN: self.intent_config.chat_history_max_turn,
            IntentionDetectConstants.INPUT: query,
            IntentionDetectConstants.USER_PROMPT: self.plan_config.user_prompt,
        }

        if self.intent_config.enable_history:
            chat_history_sliced = chat_history[
                -self.intent_config.chat_history_max_turn :
            ]

            def format_history_entry(entry):
                role = IntentionDetectConstants.ROLE_MAP.get(
                    entry.get(
                        IntentionDetectConstants.ROLE, IntentionDetectConstants.CONTENT
                    ),
                    "助手",
                )
                content = entry.get(IntentionDetectConstants.CONTENT)
                return f"{role}：{content}"

            current_inputs[IntentionDetectConstants.CHAT_HISTORY] = "\n".join(
                format_history_entry(h) for h in chat_history_sliced
            )
        llm_inputs, final_prompts = await self._pre_process(current_inputs)
        return llm_inputs, final_prompts

    def _handle_specified_intent(self, specified_intent, active_workflows, task_id):
        """处理指定意图的逻辑

        Args:
            specified_intent: 指定的意图
            active_workflows: 活动工作流列表
            task_id: 任务ID
            **kwargs: 其他参数

        Returns:
            str or None: 匹配的工作流名称，如果无效则返回None
        """
        # 构建意图映射和列表
        intents = self._build_intent_mappings_and_list(active_workflows)

        # 检查指定意图是否被包含在意图列表的description/name中
        matched_intents = []

        for intent in intents:
            # 调整判断逻辑，name优先
            if (
                specified_intent == intent["name"]
                or specified_intent in intent["description"]
            ):
                matched_intents.append(
                    {
                        "id": intent["id"],
                        "name": intent["name"],
                        "description": intent["description"],
                    }
                )

        if len(matched_intents) == 1:
            # 仅匹配到一条，返回对应的工作流名称
            matched_intent = matched_intents[0]
            matched_workflow_name = self._resolve_route_key(matched_intent["id"])
            logger.info(
                f"task_id: {task_id}|使用指定意图: '{specified_intent}' 唯一匹配到描述 '{matched_intent['description']}' "
                f"-> {matched_workflow_name}",
                simple_log=f"task_id: {task_id}|使用指定意图匹配成功",
            )
            return matched_workflow_name
        if len(matched_intents) > 1:
            # 匹配到多条，记录日志并返回None
            matched_descriptions = [intent["description"] for intent in matched_intents]
            logger.warning(
                f"task_id: {task_id}| 指定意图 '{specified_intent}' 匹配到多个工作流描述: {matched_descriptions}，"
                f"清除并使用默认识别方式,",
                simple_log=f"task_id: {task_id}|使用指定意图匹配多个工作流，清除并使用默认识别方式",
            )
        else:
            # 未匹配到任何工作流
            logger.warning(
                f"task_id: {task_id}|指定意图 '{specified_intent}' 未在活动工作流描述中找到匹配，清除并使用默认识别方式",
                simple_log=f"task_id: {task_id}|使用指定意图未找到匹配，清除并使用默认识别方式",
            )

        # 清除全局变量中的指定意图
        self.context_manager.set_global_variables(WorkflowConstants.INTENT, None)

        # 返回None，由invoke方法决定使用哪种默认识别方式
        return None

    async def _detect_intent_with_coarse_grained_method(
        self, active_workflows: list, task_id: str, **kwargs
    ):
        """使用粗粒度意图识别方法"""
        intent_config = self.plan_config.intent_identification
        query = self.context_manager.get_latest_user_content()

        logger.info(
            f"task_id {task_id}| Using coarse-grained intent identification method: {intent_config.method}"
        )
        intent_function = None
        candidate_intents = None

        # 根据配置的方法进行粗粒度识别
        if intent_config.method == IntentIdentificationMethod.WORKFLOW:
            # 工作流方式识别
            (
                intent_function,
                candidate_intents,
            ) = await self._detect_intent_with_workflow_method(
                query, active_workflows, task_id, intent_config, **kwargs
            )
        if intent_config.method == IntentIdentificationMethod.API:
            # API方式识别
            intent_function = self._detect_intent_with_api_method(task_id)

        # 检查是否需要进一步的细粒度识别
        if self._need_fine_grained_detection(intent_function, task_id):
            if self.llm is not None:
                logger.info(
                    f"task_id {task_id}| Coarse-grained result requires fine-grained detection"
                )

                # 过滤和处理候选意图
                filtered_candidate_intents = self._filter_valid_candidate_intents(
                    candidate_intents, task_id
                )

                if filtered_candidate_intents:
                    logger.info(
                        f"task_id {task_id}| Using filtered candidate intents for fine-grained detection, "
                        f"count: {len(filtered_candidate_intents)}"
                    )
                    # 将候选意图转化为active_workflows
                    candidate_active_workflows = (
                        self._convert_candidates_to_active_workflows(
                            filtered_candidate_intents, task_id
                        )
                    )
                    if candidate_active_workflows:
                        intent_function = await self._detect_intent_with_llm(
                            candidate_active_workflows, task_id, **kwargs
                        )
                    else:
                        logger.warning(
                            f"task_id {task_id}| Failed to convert candidates to active workflows, "
                            f"using default detection"
                        )
                        intent_function = await self._detect_intent_with_llm(
                            active_workflows, task_id, **kwargs
                        )
                else:
                    logger.info(
                        f"task_id {task_id}| No valid candidate intents found, using default fine-grained detection"
                    )
                    intent_function = await self._detect_intent_with_llm(
                        active_workflows, task_id, **kwargs
                    )
            else:
                raise JiuWenBaseException(
                    StatusCode.WORKFLOW_INTENT_DETECTION_OUTPUT_ERROR.code,
                    StatusCode.WORKFLOW_INTENT_DETECTION_OUTPUT_ERROR.errmsg.format(
                        error_msg="Intention detect workflow recognition failed"
                    ),
                )

        logger.info(
            f"task_id {task_id}| Final intent function: {intent_function}",
            simple_log=f"task_id {task_id}| Final intent function",
        )
        return intent_function

    async def _detect_intent_with_llm(
        self, active_workflows: list, task_id: str, **kwargs
    ):
        """使用 LLM 进行细粒度意图识别（原有逻辑）"""
        chat_history = self.context_manager.get_latest_k_chat_history(
            self.plan_config.chat_history_max_turn
        )
        category_info = self.get_function_category_info(
            active_workflows, kwargs.get("global_only", False)
        )
        query = self.context_manager.get_latest_user_content()
        llm_input, final_prompts = await self.create_intention_detect_llm_input(
            category_info, chat_history, query
        )
        memory_message = await self.context_manager.get_memory_message(query)
        if isinstance(memory_message, BaseMessage):
            final_prompts.append(
                dict(role=memory_message.type, content=memory_message.content)
            )
            llm_input["messages"].append(memory_message)

        logger.info(
            f"task_id {task_id}| <LLM Input> {llm_input}",
            simple_log=f"task_id {task_id}| <LLM Input>",
        )

        runtime_data = kwargs.get("runtime_data", {})
        llm_output = await self._invoke_llm_with_insight(
            messages=final_prompts, llm_input=llm_input, runtime_data=runtime_data
        )

        logger.info(
            f"task_id {task_id}| <LLM Response>:Received {llm_output}",
            simple_log=f"task_id {task_id}| Received <LLM Response>",
        )

        intent_class = self.intent_detection_post_process(llm_output.content)
        intent_function = intent_class

        # 优先检查是否为全局意图
        if self.category_2_global_intent_map.get(intent_class, None):
            intent_function = self.category_2_global_intent_map.get(intent_class)
            logger.info(
                f"task_id {task_id}| Detected global intent: {intent_function}",
                simple_log=f"task_id {task_id}| Detected global intent",
            )
        elif self.category_2_intent_function_map.get(intent_class, None):
            intent_function = self.category_2_intent_function_map.get(intent_class)
            logger.info(
                f"task_id {task_id}| Detected workflow intent: {intent_function}",
                simple_log=f"task_id {task_id}| Detected workflow intent",
            )
        elif self.category_2_child_id_map.get(intent_class, None):
            # A.1(C-09): 返回 category(每 child 唯一),由 controller_planner 按 child.id 路由,
            # 不返回 child.name,避免重名时塌成同一 name
            intent_function = intent_class
            logger.info(
                f"task_id {task_id}| Detected agent intent: {intent_function}",
                simple_log=f"task_id {task_id}| Detected agent intent",
            )

        logger.info(
            f"task_id {task_id}| intent_function: {intent_function}",
            simple_log=f"task_id {task_id}| intent_function",
        )

        return intent_function

    async def _invoke_llm_with_insight(
        self, messages: List[dict], llm_input, runtime_data
    ):
        """调测信息输出"""
        trace_manager = create_trace_manager(
            llm=self.llm,
            functions=[],
            trace_handlers=runtime_data.get("trace_handlers"),
        )

        await trace_manager.on_llm_start(messages)

        try:
            result = await self._execute_llm_call(llm_input)
            output_on_insights = self._prepare_insights_output(result)
            await trace_manager.on_llm_end(output_on_insights)

            return result.converted_output

        except Exception as e:
            await trace_manager.on_llm_error(e)
            raise LLMInvocationFailedException(
                str(e) if LOG_VERBOSE_MODE else "Failed to invoke LLM"
            ) from e

    async def _execute_llm_call(self, llm_input):
        """调用llm"""
        start_time = time.time()

        llm_message: AIMessage = await self.llm.ainvoke(llm_input)
        converted_output = convert_ai_message_to_llm_output(llm_message)

        total_time = time.time() - start_time

        model_stat, model_usage = self._extract_usage_metadata(llm_message)

        ResultTuple = namedtuple(
            "ResultTuple",
            [
                "converted_output",
                "total_time",
                "model_stat",
                "model_usage",
                "llm_message",
            ],
        )

        return ResultTuple(
            converted_output=converted_output,
            total_time=round(total_time, 2),
            model_stat=model_stat,
            model_usage=model_usage,
            llm_message=llm_message,
        )

    async def _detect_intent_with_workflow_method(
        self,
        query: str,
        active_workflows: list,
        task_id: str,
        intent_config: IntentIdentificationConfig,
        **kwargs,
    ):
        """使用工作流方式进行意图识别"""
        logger.info(f"task_id {task_id}| Using workflow-based intent detection")
        runtime_data = kwargs.get("runtime_data", {})

        try:
            # 根据 intent_config.id 获取对应的工作流上下文
            intent_workflow_context = (
                self.context_manager.get_workflow_context_by_config_name(
                    intent_config.id
                )
            )
            # 准备工作流输入数据
            workflow_input = self._prepare_workflow_input(
                query,
                intent_workflow_context,
                active_workflows,
                intent_config,
                **kwargs,
            )
            logger.info(
                f"task_id {task_id}| Workflow input: {workflow_input}",
                simple_log=f"task_id {task_id}| get Workflow input",
            )

            # 执行意图识别工作流
            workflow_output = await self._execute_intent_workflow(
                workflow_input,
                intent_workflow_context,
                intent_config,
                task_id,
                runtime_data=runtime_data,
            )
            logger.info(
                f"task_id {task_id}| Workflow output: {workflow_output}",
                simple_log=f"task_id {task_id}| get Workflow output",
            )

            # 解析工作流输出结果
            return self._parse_workflow_output(workflow_output, task_id)

        except Exception as e:
            logger.error(
                f"task_id {task_id}| Workflow-based intent detection failed: {e}",
                simple_log=f"task_id {task_id}| Workflow-based intent detection failed",
            )
            raise e

    def _filter_valid_candidate_intents(
        self, candidate_intents: list, task_id: str
    ) -> list:
        """过滤有效的候选意图

        Args:
            candidate_intents: 候选意图列表
            task_id: 任务ID

        Returns:
            list: 过滤后的有效候选意图列表
        """
        if not candidate_intents:
            logger.debug(f"task_id {task_id}| No candidate intents to filter")
            return []

        filtered_intents = []

        for candidate in candidate_intents:
            try:
                intent_id = candidate.get("intent_id")
                score = candidate.get("score", 0)

                # 基本验证
                if not intent_id:
                    logger.warning(
                        f"task_id {task_id}| Skipping candidate with missing intent_id"
                    )
                    continue

                # 转换为字符串并检查映射
                intent_id_str = str(intent_id)
                workflow_name = self.intent_id_to_function_map.get(intent_id_str)

                if not workflow_name:
                    logger.warning(
                        f"task_id {task_id}| Skipping unmapped intent_id: {intent_id_str}",
                        simple_log=f"task_id {task_id}| Skipping unmapped intent_id",
                    )
                    continue

                # 添加工作流名称到候选项中
                filtered_candidate = {
                    "intent_id": intent_id_str,
                    "workflow_name": workflow_name,
                    "score": score,
                }
                filtered_intents.append(filtered_candidate)

                logger.info(
                    f"task_id {task_id}| Added valid candidate: intent_id={intent_id_str}, "
                    f"workflow_name={workflow_name}, score={score}",
                    simple_log=f"task_id {task_id}| Added valid candidate",
                )

            except Exception as e:
                logger.warning(
                    f"task_id {task_id}| Error processing candidate intent: {candidate}, error: {str(e)}",
                    simple_log=f"task_id {task_id}| Error processing candidate intent: {candidate}",
                )
                continue

        logger.info(
            f"task_id {task_id}| Filtered {len(filtered_intents)} valid candidates from {len(candidate_intents)} total"
        )
        return filtered_intents

    def _convert_candidates_to_active_workflows(
        self, filtered_candidate_intents: list, task_id: str
    ) -> list:
        """将候选意图转化为active_workflows列表

        Args:
            filtered_candidate_intents: 过滤后的候选意图列表
            task_id: 任务ID

        Returns:
            list: workflow_id列表
        """
        if not filtered_candidate_intents:
            logger.warning(f"task_id {task_id}| No candidate intents to convert")
            return []

        active_workflows = []

        for candidate in filtered_candidate_intents:
            try:
                workflow_name = candidate.get("workflow_name")
                if not workflow_name:
                    logger.warning(
                        f"task_id {task_id}| Skipping candidate with missing workflow_name"
                    )
                    continue

                # 通过workflow_name获取workflow_context
                workflow_context = (
                    self.context_manager.get_workflow_context_by_name_and_type(
                        workflow_name, WorkflowType.GENERAL
                    )
                )

                if not workflow_context:
                    logger.warning(
                        f"task_id {task_id}| Workflow context not found for workflow_name: {workflow_name}"
                    )
                    continue

                # 获取workflow_id
                workflow_id = workflow_context.workflow_id
                if not workflow_id:
                    logger.warning(
                        f"task_id {task_id}| Workflow_id not found in context for workflow_name: {workflow_name}"
                    )
                    continue

                active_workflows.append(workflow_id)
                logger.debug(
                    f"task_id {task_id}| Added workflow_id {workflow_id} for workflow_name: {workflow_name}"
                )

            except Exception as e:
                logger.error(
                    f"task_id {task_id}| Error converting candidate to workflow_id: {candidate}, error: {str(e)}",
                    simple_log=f"task_id {task_id}| Error converting candidate to workflow_id: {candidate}",
                )
                continue

        logger.info(
            f"task_id {task_id}| Converted {len(active_workflows)} candidate intents to "
            f"active workflows: {active_workflows}",
            simple_log=f"task_id {task_id}| Converted candidate intents to active workflows",
        )
        return active_workflows

    def _prepare_workflow_input(
        self,
        query: str,
        intent_workflow_context,
        active_workflows: list,
        intent_config: IntentIdentificationConfig,
        **kwargs,
    ) -> dict:
        """准备工作流输入数据"""
        # 获取聊天历史
        messages = self.context_manager.get_latest_k_chat_history(
            self.plan_config.chat_history_max_turn
        )

        # 使用通用方法构建意图列表和映射关系
        intents = self._build_intent_mappings_and_list(
            active_workflows, global_only=kwargs.get("global_only", False)
        )

        # 转换聊天历史格式
        workflow_handler = self._get_workflow_handler()

        context_workflow_req_params = self.context_manager.get_global_variables(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
        )
        workflow_req_params = workflow_handler.prepare_workflow_params(
            context_workflow_req_params, intent_workflow_context
        )
        workflow_req_params.setdefault("global_variables", {}).update(
            {"intents": intents, "messages": messages}
        )
        # 构建工作流输入
        workflow_input = {"inputs": query, "params": workflow_req_params}
        return workflow_input

    async def _execute_intent_workflow(
        self,
        workflow_input: dict,
        intent_workflow_context,
        intent_config: IntentIdentificationConfig,
        task_id: str,
        **kwargs,
    ) -> dict:
        """执行意图识别工作流"""
        if intent_workflow_context is None:
            raise ValueError(
                f"Intent workflow context not found for id: {intent_config.id}"
            )

        # 获取当前对话ID
        conversation_id = self.context_manager.get_global_variables(
            WorkflowConstants.CONVERSATION_ID
        )
        logger.info(
            f"task_id: {task_id} | Starting intent identification workflow execution, config_id: {intent_config.id}"
        )

        # 获取 insight_queue 用于发送调试信息
        insight_queue = self._get_insight_queue_from_trace_handlers(
            kwargs.get("runtime_data", {})
        )

        try:
            # 创建或获取 WorkflowHandler 实例
            workflow_handler = self._get_workflow_handler()
            # 收集流式执行的结果
            result = {"intent_id": None, "intent_name": None, "candidate_intents": None}

            logger.info(
                f"task_id: {task_id} | Starting streaming execution of intent identification workflow"
            )

            async for (
                output
            ) in workflow_handler.stream_execute_workflow_for_intent_detection(
                workflow_input, intent_workflow_context, conversation_id
            ):
                logger.debug(
                    f"task_id: {task_id} | Received output {output}, node_type: "
                    f"{output.data.get('node_type')}, code: {output.code}"
                )

                # 处理 workflow_node_message 事件，发送到 insight_queue
                if (
                    output.code == StreamCode.WORKFLOW_NODE_MESSAGE.value
                    and insight_queue is not None
                ):
                    await self._send_intent_workflow_debug_info(
                        output, insight_queue, task_id
                    )

                if (
                    output.data.get("node_type") == WORKFLOW_END_TYPE
                    and output.code == StreamCode.FINISH.value
                ):
                    user_fields = output.data.get("user_fields", {})
                    result["intent_id"] = user_fields.get("intent_id")
                    result["intent_name"] = user_fields.get("intent_name")
                    result["candidate_intents"] = user_fields.get("candidate_intents")

                    logger.info(
                        f"task_id: {task_id} | Workflow execution completed, detected intent_id: {result['intent_id']}"
                    )
                    logger.debug(
                        f"task_id: {task_id} | Number of candidate intents: "
                        f"{len(result['candidate_intents']) if result['candidate_intents'] else 0}"
                    )
                    break

            # 验证执行结果
            if result["intent_id"] is None:
                logger.warning(
                    f"task_id: {task_id} | Intent identification workflow completed but no valid intent_id received"
                )

            logger.info(
                f"task_id: {task_id} | Intent identification workflow executed successfully, returning result"
            )
            return result

        except Exception as e:
            logger.error(
                f"task_id: {task_id} | Failed to execute intent identification workflow, "
                f"config_id: {intent_config.id}, error: {str(e)}",
                simple_log=f"task_id: {task_id} | Failed to execute intent identification workflow, ",
                exc_info=True,
            )
            raise

    def _get_workflow_handler(self):
        """获取或创建 WorkflowHandler 实例"""
        # 如果当前类中已有 workflow_handler，直接使用
        if self.workflow_handler is None:
            from jiuwen.controller.task_executor.handler.workflow_handler import (
                WorkflowHandler,
            )

            self.workflow_handler = WorkflowHandler(
                context_manager=self.context_manager,
            )

        return self.workflow_handler

    def _get_intent_workflow_context(self, workflow_id: str) -> WorkflowContext:
        """根据ID获取意图识别工作流上下文"""
        workflow_context = self.context_manager.get_workflow_context_by_id(
            workflow_id, WorkflowType.INTENT
        )
        if workflow_context:
            return workflow_context

        logger.warning(f"Intent workflow context not found for id: {workflow_id}")
        return None

    def _parse_workflow_output(self, workflow_output: dict, task_id: str) -> tuple:
        """解析工作流输出，提取意图函数和候选意图

        Args:
            workflow_output: 工作流执行的输出结果
            task_id: 任务ID

        Returns:
            tuple: (intent_function, candidate_intents)
                - intent_function: 识别到的意图函数名称（字符串）
                - candidate_intents: 候选意图列表
        """
        logger.debug(f"task_id: {task_id} | Parsing workflow output")

        if not workflow_output:
            logger.warning(f"task_id: {task_id} | Workflow output is empty")
            return None, None

        try:
            # 提取 intent_id 和 candidate_intents
            intent_id = workflow_output.get("intent_id")
            candidate_intents = workflow_output.get("candidate_intents")

            logger.debug(
                f"task_id: {task_id} | Extracted raw intent_id: {intent_id}, "
                f"candidate_intents count: {len(candidate_intents) if candidate_intents else 0}"
            )

            # 将 intent_id 转换为 intent_function
            intent_function = None
            if intent_id is not None:
                # 确保 intent_id 是字符串
                intent_id_str = str(intent_id)

                # 通过映射获取 intent_function
                intent_function = self._resolve_route_key(intent_id_str)

                if intent_function:
                    logger.info(
                        f"task_id: {task_id} | Successfully mapped intent_id '{intent_id_str}' "
                        f"to intent_function '{intent_function}'",
                        simple_log=f"task_id {task_id}| Successfully mapped intent_id  to intent_function",
                    )
                else:
                    logger.warning(
                        f"task_id: {task_id} | Intent_id '{intent_id_str}' not found in intent_id_to_function_map"
                    )
            else:
                logger.warning(
                    f"task_id: {task_id} | No intent_id found in workflow output"
                )

            return intent_function, candidate_intents

        except Exception as e:
            logger.error(
                f"task_id: {task_id} | Failed to parse workflow output: {str(e)}",
                exc_info=True,
            )
            return None, None

    def _build_intent_mappings_and_list(
        self, active_workflows: list, global_only: bool = False
    ):
        """构建意图映射关系和意图列表的通用方法

        Args:
            active_workflows: 活动工作流列表
            global_only: 是否只使用全局意图

        Returns:
            list: 意图列表，格式为 [{"id": "1", "description": "闲聊"}, {"id": "2", "description": "描述", "workflow_id": "xxx"}...]
        """
        # 重置映射字典
        self.category_2_intent_function_map = {}
        self.intent_function_2_category_map = {}
        self.category_2_global_intent_map = {}
        self.global_intent_2_category_map = {}
        self.intent_id_to_function_map = {}
        self.category_2_agent_name_map = {}
        self.agent_name_2_category_map = {}
        self.category_2_child_id_map = {}
        self.intent_id_to_child_category_map = {}

        # 初始化意图列表
        intents = []

        # 添加默认的"闲聊"意图
        intents.append(
            {
                "id": "1",
                "name": DEFAULT_INTENT,
                "description": DEFAULT_INTENT,
                "handler": {"type": WORKFLOW_HANDLER_TYPE},
                "enable": True,
            }
        )

        self.intent_id_to_function_map["1"] = DEFAULT_INTENT  # 或者你的默认处理函数名

        category_index = 2

        # 处理全局意图
        if (
            hasattr(self.plan_config, "global_intents")
            and self.plan_config.global_intents
        ):
            category_index = self._process_global_intents(intents, category_index)

        # 如果global_only为True，则跳过工作流处理
        if not global_only:
            category_index = self._process_workflows(
                intents, category_index, active_workflows
            )
            # 处理子agent的描述
            if self.plan_config.child_agents_metadata:
                self._process_child_agents(intents, category_index)

        return intents

    def _process_global_intents(self, intents, category_index):
        """处理全局意图"""
        for global_intent in self.plan_config.global_intents:
            if global_intent.description and global_intent.name:
                category_value = global_intent.description
                if global_intent.name == "其他":
                    continue

                # 如果是工作流类型的全局意图，获取实际描述
                if global_intent.handler_type == HandlerType.WORKFLOW.value:
                    workflow_config_name = global_intent.handler.get("name", None)
                    workflow_context = (
                        self.context_manager.get_workflow_context_by_config_name(
                            workflow_config_name
                        )
                    )
                    if not workflow_context:
                        logger.error(
                            f"Workflow context {workflow_config_name} does not exist"
                        )
                        continue
                    logger.info(
                        f"found workflow context {workflow_context.workflow_name} with "
                        f"type {workflow_context.type}",
                        simple_log="found workflow context with type",
                    )
                    category_value = workflow_context.description

                # 添加意图
                intent_id = str(category_index)
                intents.append(
                    {
                        "id": intent_id,
                        "description": category_value,
                        "name": global_intent.name,
                        "handler": {"type": WORKFLOW_HANDLER_TYPE},
                        "enable": True,  # 默认开启
                    }
                )

                # 建立映射关系
                category_id = f"分类{category_index}"
                self.category_2_global_intent_map[category_id] = global_intent.name
                self.global_intent_2_category_map[global_intent.name] = category_id
                self.intent_id_to_function_map[intent_id] = (
                    global_intent.name
                )  # 直接映射
                category_index += 1
        return category_index

    def _process_workflows(self, intents, category_index, active_workflows):
        """处理工作流"""
        # 处理传入的active_workflows中的工作流
        workflows_to_process = []
        if active_workflows:
            for workflow_id in active_workflows:
                workflow_context = self.context_manager.get_workflow_context_by_id(
                    workflow_id, WorkflowType.GENERAL
                )
                if workflow_context:
                    workflows_to_process.append(workflow_context)
        else:
            # 不传入使用全部的业务工作流进行跳转
            logger.warning("No active workflows found, use all general workflows.")
            workflows_to_process = self.context_manager.get_normal_workflow_contexts()

        # 处理工作流
        for workflow_context in workflows_to_process:
            workflow_description = workflow_context.description
            workflow_name = workflow_context.workflow_name
            # 工作流中文名字
            workflow_config_name = workflow_context.config_name
            # 工作流的intent_name字段
            workflow_intent_name = (
                workflow_context.intent_name
                if hasattr(workflow_context, "intent_name")
                and workflow_context.intent_name
                else workflow_config_name
            )
            # 工作流的intent_description字段
            workflow_intent_description = (
                workflow_context.intent_description
                if (
                    hasattr(workflow_context, "intent_description")
                    and workflow_context.intent_description
                )
                else workflow_description
            )
            # 添加意图
            intent_id = str(category_index)
            intents.append(
                {
                    "id": intent_id,
                    "name": workflow_intent_name,
                    "description": workflow_intent_description,
                    "handler": {"type": WORKFLOW_HANDLER_TYPE},
                    "enable": True,  # 默认开启
                }
            )

            # 建立映射关系
            category_id = f"分类{category_index}"
            self.category_2_intent_function_map[category_id] = workflow_name
            self.intent_function_2_category_map[workflow_name] = category_id
            self.intent_id_to_function_map[intent_id] = workflow_name  # 直接映射
            category_index += 1
        return category_index

    def _process_child_agents(self, intents, category_index):
        """处理子agent"""
        for child_agent in self.plan_config.child_agents_metadata:
            if child_agent.description and child_agent.name:
                # 获取子agent的intent_name字段，如果没有则使用description
                agent_intent_name = (
                    child_agent.intent_name
                    if child_agent.intent_name
                    else child_agent.name
                )
                agent_intent_description = (
                    child_agent.intent_description
                    if child_agent.intent_description
                    else child_agent.description
                )
                # 添加子agent意图
                intent_id = str(category_index)
                intent_obj = {
                    "id": intent_id,
                    "description": agent_intent_description,
                    "name": agent_intent_name,
                    "handler": {"type": AGENT_HANDLER_TYPE},
                    "enable": True,  # 默认开启
                }
                intents.append(intent_obj)

                # 建立映射关系
                category_id = f"分类{category_index}"
                # 使用子agent的名称作为意图函数名
                self.category_2_agent_name_map[category_id] = child_agent.name
                self.agent_name_2_category_map[child_agent.name] = category_id
                # A.1(C-09): category → child.id(唯一),供 controller_planner 按 id 路由,
                # 不经 name first-match,允许同名子成员
                self.category_2_child_id_map[category_id] = child_agent.id
                # A.1: intent_id → category(唯一)
                # 供非 LLM 识别入口(多级/工作流式/指定/_map)返回 category
                self.intent_id_to_child_category_map[intent_id] = category_id
                self.intent_id_to_function_map[intent_id] = child_agent.name

                category_index += 1
                logger.info(
                    f"Added child agent intent: id={intent_id}, name={agent_intent_name}, "
                    f"description={child_agent.description}, intent={agent_intent_description}",
                    simple_log="Added child agent intent",
                )

    def _resolve_route_key(self, intent_id):
        """A.1:统一 route key 解析,供所有识别入口返回,controller_planner 按 category 路由。

        AGENT 意图 → category(每 child 唯一,重名可区分);
        workflow/global 意图 → name(不变)。
        不动 intent_id_to_function_map 的 name 值(候选标签/LLM 输入仍用 name)。
        """
        key = intent_id if isinstance(intent_id, str) else str(intent_id)
        if key in self.intent_id_to_child_category_map:
            return self.intent_id_to_child_category_map[key]
        return self.intent_id_to_function_map.get(key)

    def _map_intent_id_to_function(self, intent_id: str, task_id: str) -> str:
        """将意图ID映射到实际的意图函数 route key(A.1:AGENT→category,workflow/global→name)"""
        try:
            intent_function = self._resolve_route_key(intent_id)
            if intent_function:
                logger.info(
                    f"task_id {task_id}| Mapped intent_id {intent_id} to function: {intent_function}",
                    simple_log=f"task_id {task_id}| Mapped intent_id to function",
                )
                return intent_function
            logger.warning(
                f"task_id {task_id}| Failed to map intent_id {intent_id}, using default intent"
            )
            return self._get_default_intent()

        except Exception as e:
            logger.error(
                f"task_id {task_id}| Error mapping intent_id {intent_id}: {e}",
                simple_log=f"task_id {task_id}| Error mapping intent_id {intent_id}",
            )
            return self._get_default_intent()

    async def _pre_process(self, inputs: dict):
        """
        Pre-process inputs for model
        """
        try:
            final_prompts = []
            for prompt_message in self.intent_config.intent_detection_template.content:
                rendered_content = await Prompt(
                    template=Template(name="template", content=[prompt_message])
                ).ainvoke(inputs)
                final_prompts.append(
                    {
                        IntentionDetectConstants.ROLE: prompt_message.get(
                            IntentionDetectConstants.ROLE, ""
                        ),
                        IntentionDetectConstants.CONTENT: rendered_content,
                    }
                )
            llm_inputs = LanguageModelInput(
                messages=ModelUtil.switch_message(final_prompts), tools=[]
            )
        except Exception as e:
            raise e
        return llm_inputs, final_prompts

    async def _detect_with_multi_layer_intent_detection(
        self, task_id, active_workflows, global_only
    ):
        """多级意图识别。

        A.1(C-09):multi-layer 用 name-keyed 字典(valid_intents),effective intent name
        重复时会在 matcher 前塌成一条、再按字典位置反推 intent_id → 错路由。检测到
        effective intent name 重复时回退细粒度 LLM(用 description 区分、返回 category),
        不约束用户内容(用户可自行用 intent_name 区分以走原 multi-layer)。
        """
        intents = self._build_intent_mappings_and_list(active_workflows, global_only)
        names = [i.get("name") for i in intents if i.get("name")]
        if len(names) != len(set(names)):
            logger.info(
                f"task_id {task_id}| Multi-layer fallback to fine-grained LLM: "
                f"duplicate effective intent names, name-keyed dict would collapse",
                simple_log="multi-layer fallback to llm on dup intent name",
            )
            return await self._detect_intent_with_llm(
                active_workflows, task_id, global_only=global_only
            )

        multi_layer_id_input = self._prepare_multi_layer_id_input(
            active_workflows, global_only
        )
        multi_layer_id = IntentDetection(self.multi_layer_id_cfg)
        result = await multi_layer_id.invoke(multi_layer_id_input)
        logger.info(
            f"task_id {task_id}| Multi-layer intent detection result : {result}",
            simple_log="succeed to get multilayer result",
        )
        if result.is_matched:
            intent_function = self._resolve_route_key(result.intent_id)
            logger.info(
                f"task_id {task_id}| Multi-layer intent detection matched intent : {intent_function}"
            )
        else:
            logger.info(
                f"task_id {task_id}| Multi-layer intent detection dit not match any intent"
            )
            intent_function = self._get_default_intent()

        return intent_function

    def _prepare_multi_layer_id_input(
        self, active_workflows, global_only
    ) -> IntentInput:
        """
        构建多级意图识别输入
        """
        intents = self._build_intent_mappings_and_list(active_workflows, global_only)
        valid_intents = {intent["name"]: intent["description"] for intent in intents}

        return IntentInput(
            query=self.context_manager.get_latest_user_content(),
            dialogue_history=self.context_manager.get_latest_k_chat_history(
                self.plan_config.chat_history_max_turn
            ),
            valid_intents=valid_intents,
        )
