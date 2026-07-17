# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
IntentDetection - 意图识别组件

迁移自商用版本 jiuwen/orchestration/flow/components/intent_detection.py，
适配开源版本 openjiuwen 框架。

功能特性:
- 通过 LLM 识别用户输入意图，将其分类到预定义类别
- 支持 FAQ 知识库匹配（优先于 LLM 推理）
- 支持全局意图合并与中断
- 支持用户画像/记忆集成
- 支持对话历史上下文
- 完整的 LLM 输出后处理与验证
- 支持状态管理（reset/load_state/get_state）

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 使用 Session 进行状态管理和交互中断
- 使用 Model 进行 LLM 调用
- 使用 PromptTemplate 进行提示词管理
- 使用 context.get_messages() 获取对话历史
- 使用 build_intent_detection_error() 进行异常构建
"""

import ast
import copy
import json
import logging
import os
import re
import time
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from typing import Callable, Union

from jiuwen.extension.workflow_node.utils import get_workflow_param
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm import (
    BaseMessage,
    Model,
    SystemMessage,
    UserMessage,
)
from openjiuwen.core.foundation.prompt import PromptTemplate
from openjiuwen.core.graph.base import Graph
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.condition.condition import Condition
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
from pydantic import BaseModel, Field, StrictStr

# ==============================================================================
# 常量定义（与 jiuwen 原组件保持一致）
# ==============================================================================

LLM = "llm"
NAME = "name"
MODEL = "model"
CLASS = "class"
REASON = "reason"
INPUT = "input"
USER_PROMPT = "user_prompt"
CATEGORY_INFO = "category_info"
CATEGORY_LIST = "category_list"
CATEGORY_NAME_LIST = "category_name_list"
DEFAULT_CLASS = "default_class"
CHAT_HISTORY = "chat_history"
EXAMPLE_CONTENT = "example_content"
ENABLE_HISTORY = "enable_history"
ENABLE_INPUT = "enable_input"
LLM_INPUTS = "llm_inputs"
LLM_OUTPUTS = "llm_outputs"
MODEL_SOURCE = "modelType"
MODEL_NAME = "modelName"
HYPTER_PARAM = "hyperParameters"
EXTENSION = "extension"
CHAT_HISTORY_MAX_TURN = "chat_history_max_turn"
INTENT_DETECTION_TEMPLATE = "intent_detection_template"
ROLE = "role"
CONTENT = "content"
ROLE_MAP = {"user": "用户", "assistant": "助手", "system": "系统"}
JSON_PARSE_FAIL_REASON = "当前意图识别的输出:'{result}'格式不符合有效的JSON规范，导致解析失败，因此返回默认分类。"
CLASS_KEY_MISSING_REASON = (
    "当前意图识别的输出 '{result}' 缺少必要的输出'class'分类信息，因此返回默认分类。"
)
VALIDATION_FAIL_REASON = (
    "当前意图识别的输出类别 '{intent_class}' 不在预定义的分类列表: '{category_list}'中，"
    "因此系统返回默认分类。"
)
RESULT = "result"
FEW_SHOT_NUM = 5
ENABLE_Q2L = "enableKnowledge"
RECALLTHREASHOLD = "recallThreshold"
DEFAULT_QUERY_CATE = "title"
DEFAULT_CLASS_CATE = "content"
DEFAULT_INT = "不确定，其他的意图"
SEARCH_TYPE = "faq"
SEARCH_NUM = 1
CLASSIFICATION_ID = "classificationId"
CLASSIFICATION_DEAFULT_ID = "分类0"
CLASSIFICATION_DEAFULT_OLD = "分类1"
CLASSIFICATION_NAME = "name"
CLASSIFICATION_DEAFULT_NAME = "其他意图"
KG_FILTER_KEY = "filter_string"
KG_FILTER_PREFIX = "category:"
KG_SCOPE = "scope"
QUERY = "query"
MEMORY_MESSAGE = "memory_message"
USER_PROFILE_KEY = "userProfile"
ENABLE_KEY = "enable"
WORKFLOW_GLOBAL_INTENTS = "global_intents"
WORKFLOW_CHAT_HISTORY = "workflow_chat_history"

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class IntentDetectionStatusCode(Enum):
    """IntentDetection 组件专用错误码"""

    WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR = (
        101300,
        "intent detection user input error, reason: {error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_LLM_INIT_ERROR = (
        101301,
        "intent detection llm init error, reason: {error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR = (
        101302,
        "intent detection llm invoke error, reason: {error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR = (
        101303,
        "intent detection prompt template error, reason: {error_msg}",
    )


def build_intent_detection_error(
    status: IntentDetectionStatusCode,
    error_msg: str = "",
    cause: Optional[Exception] = None,
):
    """
    构建 IntentDetection 组件异常

    Args:
        status: 错误状态码枚举
        error_msg: 错误信息
        cause: 原始异常

    Returns:
        JiuWenBaseException 实例
    """
    from jiuwen.extension.workflow_node.utils import (
        JiuWenBaseException,
    )

    return JiuWenBaseException(
        error_code=status.value[0],
        message=status.value[1].format(error_msg=error_msg),
    )


DEFAULT_SYSTEM_PROMPT = "你是一个识别用户输入意图的AI助手。"

DEFAULT_USER_PROMPT = """
{{user_prompt}}

当前可供选择的功能分类如下：
{{category_info}}

用户与助手的对话历史：
{{chat_history}}

当前输入：
{{input}}

请根据当前输入和对话历史分析并输出最适合的功能分类。输出格式为 JSON，包含以下两个字段：
class: 代表分类结果
reason: 说明为何选择该分类
例如: {{"class": "分类xx", "reason": "当前输入xxx"}}
请参考以下示例：
{{example_content}}
如果没有合适的分类，请输出 {{default_class}}。
"""


# ==============================================================================
# 配置类
# ==============================================================================


class IntentDetectionLLMConfig(BaseModel):
    """LLM 配置模型。"""

    model_type: StrictStr = Field(min_length=1)
    model_name: StrictStr = Field(min_length=1)
    hyper_parameters: dict = Field(default_factory=dict)
    extension: dict = Field(default_factory=dict)


@dataclass
class IntentDetectionConfig:
    """意图识别组件配置。"""

    user_prompt: str
    category_info: str
    category_list: list[str]
    intent_detection_template: Any  # PromptTemplate 实例
    category_name_list: list[str]
    default_class: str = CLASSIFICATION_DEAFULT_ID
    enable_history: bool = False
    enable_input: bool = True
    chat_history_max_turn: int = 3
    example_content: list[str] = field(default_factory=list)
    overridable: bool = False
    enable_knowledge: bool = False
    enalbe_q2fewshot: bool = True
    enable_validate: bool = True
    recall_threshold: float = 0.9
    levenshtein_ration: float = 0.8
    q2label_few_shot_score: float = 0.7

    # 别名映射，用于兼容旧字段名
    enableKnowledge: bool = None
    recallThreshold: float = None

    def __post_init__(self):
        # 兼容旧字段名映射到新字段名
        if self.enableKnowledge is not None:
            self.enable_knowledge = self.enableKnowledge
        if self.recallThreshold is not None:
            self.recall_threshold = self.recallThreshold


@dataclass
class KnowledgeConfig:
    """知识库配置。"""

    category: str = None
    scope: str = "faq"


class ExecutionStatus(str, Enum):
    """执行状态枚举。"""

    START = "START"
    END = "END"
    USER_INTERACT = "USER_INTERACT"


@dataclass
class IntentDetectionState:
    """意图识别组件执行状态。"""

    status: ExecutionStatus = ExecutionStatus.START


# ==============================================================================
# 工具函数
# ==============================================================================


def refix_llm_output(input_str: str) -> str:
    """大模型输出后处理，提取 JSON 部分。"""
    res = input_str
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    match = re.search(json_pattern, input_str, re.DOTALL)
    if match:
        res = match.group(0)
        res = (
            res.replace("false", "False")
            .replace("true", "True")
            .replace("null", "None")
        )
    else:
        return input_str
    if "</cot>" in res:
        tmp = res.split("</cot>")
        res = tmp[-1]
    return res


def filter_enable_history(chat_history: list) -> list:
    """过滤 enable_history 为 False 的对话记录。"""
    filtered_history = []
    for his in chat_history:
        if isinstance(his, dict):
            enable_history = his.get("enable_history", True)
            if enable_history:
                filtered_history.append(his)
        else:
            # BaseMessage 对象默认保留
            filtered_history.append(his)
    return filtered_history


def _get_default_prompt_template() -> PromptTemplate:
    """获取默认意图识别 prompt 模板。"""
    return PromptTemplate(
        content=[
            SystemMessage(content=DEFAULT_SYSTEM_PROMPT),
            UserMessage(content=DEFAULT_USER_PROMPT),
        ]
    )


# ==============================================================================
# 主组件
# ==============================================================================


class IntentDetection(WorkflowComponent):
    """意图识别组件，完整迁移自 jiuwen IntentDetection。

    功能包括：
    - LLM 意图识别
    - FAQ 知识库匹配
    - 全局意图合并与中断
    - 用户画像/记忆集成
    - 对话历史上下文
    - 输出后处理与验证
    - 状态管理

    Args:
        conf: 组件配置字典（含 branches、llm、kg、memory 等配置）。
        node_id: 节点 ID。
        node_name: 节点名称。
        node_type: 节点类型。
    """

    def __init__(self, conf: dict) -> None:
        super().__init__()
        self._llm_conf = conf
        self.llm = None
        self.intent_config = IntentDetectionConfig(**self._get_config_info(conf))
        self.intent_config_retry = IntentDetectionConfig(**self._get_config_info(conf))
        self.node_state = IntentDetectionState()
        self.node_state_retry = IntentDetectionState()
        self.search = {}
        self.faq_config = conf.get("kg", {})
        self.get_kg_instance(self.faq_config)
        llm_configs = conf.get(LLM, {})
        model_configs = llm_configs.get(MODEL, {})
        self.few_shot_example = ""
        self.conversation_id = ""
        self.matching_items = [
            item for item in conf.get("branches") if item.get("id") == "branch_0"
        ]
        if len(self.matching_items) == 0:
            self.intent_config.default_class = CLASSIFICATION_DEAFULT_OLD
        self.mem_conf = conf.get("memory", {})
        self._router = BranchRouter()  # 分支路由器

    # --------------------------------------------------------------------------
    # 状态管理
    # --------------------------------------------------------------------------

    def reset(self) -> bool:
        """重置组件状态。"""
        self.intent_config = copy.deepcopy(self.intent_config_retry)
        self.node_state = copy.deepcopy(self.node_state_retry)
        self.few_shot_example = ""
        if len(self.matching_items) == 0:
            self.intent_config.default_class = CLASSIFICATION_DEAFULT_OLD
        return True

    def get_state(self) -> IntentDetectionState:
        """获取当前执行状态。"""
        return self.node_state

    def load_state(self, state: IntentDetectionState) -> None:
        """从输入状态恢复。"""
        self.node_state = deepcopy(state)

    # --------------------------------------------------------------------------
    # 主入口
    # --------------------------------------------------------------------------
    def add_branch(
        self,
        condition: Union[str, Callable[[], bool], Condition],
        target: Union[str, list[str]],
        branch_id: str = None,
    ):
        """添加分支条件。

        Args:
            condition: 分支条件，可以是表达式字符串、函数或 Condition 对象
            target: 目标节点 ID（单个或列表）
            branch_id: 分支 ID（可选）
        """
        if isinstance(target, str):
            target = [target]
        self._router.add_branch(condition, target, branch_id=branch_id)

    def router(self) -> BranchRouter:
        """获取分支路由器。"""
        return self._router

    def add_component(
        self, graph: Graph, node_id: str, wait_for_all: bool = False
    ) -> None:
        """将组件添加到工作流图。

        Args:
            graph: 工作流图
            node_id: 节点 ID
            wait_for_all: 是否等待所有前置节点完成
        """
        graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
        graph.add_conditional_edges(node_id, self._router)

    def to_executable(self):
        """返回可执行实例。"""
        return self

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext, **kwargs
    ) -> Output:
        start_time = time.perf_counter()
        self.conversation_id = session.get_session_id()
        self._session = session

        self._router.set_session(session)

        chat_history = self._get_chat_history(context, session)
        current_inputs = dict()
        global_intents = get_workflow_param(session, WORKFLOW_GLOBAL_INTENTS)
        global_intent_map = {}
        intent_class = self.intent_config.default_class

        try:
            current_inputs = self._prepare_detection_inputs(
                inputs, chat_history, global_intents
            )
            global_intent_map = current_inputs.pop("global_intent_map", {})
        except Exception as e:
            self._raise_input_error(
                str(e) if LOG_VERBOSE_MODE else str(type(e).__name__)
            )

        if self.intent_config.enable_knowledge:
            try:
                intent_class = await self.get_faq_result(
                    current_inputs, chat_history, **kwargs
                )
            except Exception as exc:
                raise build_intent_detection_error(
                    IntentDetectionStatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR,
                    error_msg="Search is wrong",
                    cause=exc,
                ) from exc

        if (
            intent_class != self.intent_config.default_class
            and intent_class is not None
        ):
            get_intent_end_time = time.perf_counter()
            get_intent_duration = round((get_intent_end_time - start_time) * 1000)
            workflow_logger.info(
                f"{self.conversation_id}|intent faq cost {get_intent_duration}ms",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str="IntentDetection",
                session_id=self.conversation_id,
            )
            intent_id_name = self._get_intent_id_name(self.intent_config, intent_class)
            return dict(
                result=intent_class,
                reason="",
                classificationId=intent_id_name.get(CLASSIFICATION_ID, ""),
                name=intent_id_name.get(CLASSIFICATION_NAME, ""),
            )

        llm_output = await self.get_llm_result(current_inputs)
        workflow_logger.info(
            f"{self.conversation_id}|get llm result successfully",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_id=session.get_component_id(),
            component_type_str="IntentDetection",
            session_id=self.conversation_id,
        )

        intent_res = self._handle_detection_result(llm_output, global_intent_map)
        get_intent_end_time = time.perf_counter()
        get_intent_duration = round((get_intent_end_time - start_time) * 1000)
        workflow_logger.info(
            f"{self.conversation_id}|intent llm cost {get_intent_duration}ms",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_id=session.get_component_id(),
            component_type_str="IntentDetection",
            session_id=self.conversation_id,
        )
        # 对齐 OLD wf_performance_buffer：额外通过 session.trace 把性能指标送入调试信息
        if self._session:
            await self._session.trace(data={
                "performance_metric": {
                    "intent llm cost": get_intent_duration,
                }
            })
        return intent_res

    # --------------------------------------------------------------------------
    # FAQ / 知识库匹配
    # --------------------------------------------------------------------------

    def get_kg_instance(self, conf: dict) -> None:
        """获取知识库服务实例。

        与原组件 jiuwen/orchestration/flow/components/intent_detection.py 中的
        get_kg_instance 方法保持一致。

        Args:
            conf: 知识库配置字典。
        """
        self.api_id = conf.get("apiId", "")
        self.api = None
        if self.intent_config.enable_knowledge:
            if not self.api_id:
                self.api_id = conf.get("id", "")
                try:
                    self.api = self._create_api_from_ir(conf)
                except Exception as e:
                    workflow_logger.debug(f"未提交知识库信息: {type(e).__name__}")
                    self.intent_config.enable_knowledge = False
            else:
                try:
                    self.api = self._get_api_by_id(self.api_id)
                except Exception as e:
                    workflow_logger.debug(f"未提交知识库信息: {type(e).__name__}")
                    self.intent_config.enable_knowledge = False
        try:
            self.kg_conf = KnowledgeConfig(
                category=getattr(conf, "category", "")
                if not isinstance(conf, dict)
                else conf.get("category", ""),
                scope=conf.get("scope", "faq"),
            )
        except Exception:
            self.kg_conf = KnowledgeConfig()
            self.intent_config.enable_knowledge = False

    def _create_api_from_ir(self, conf: dict):
        """从 IR 配置创建 API 实例。

        Args:
            conf: IR 配置字典。

        Returns:
            API 实例。
        """
        from openjiuwen.core.runner import Runner

        tool_id = conf.get("id", "")
        if tool_id:
            return Runner.resource_mgr.get_tool(tool_id=tool_id)
        return None

    def _get_api_by_id(self, api_id: str):
        """通过 ID 获取已注册的 API 实例。

        Args:
            api_id: API ID。

        Returns:
            API 实例。
        """
        from openjiuwen.core.runner import Runner

        return Runner.resource_mgr.get_tool(tool_id=api_id)

    async def get_faq_result(
        self, current_inputs: dict, chat_history: list, **kwargs
    ) -> str:
        """获取 FAQ 匹配结果。

        Args:
            current_inputs: 当前输入参数。
            chat_history: 对话历史。
            **kwargs: 可含 session 参数。

        Returns:
            匹配到的意图分类，若未匹配则返回默认分类。
        """
        few_shot_example = ""
        intent_class = self.intent_config.default_class
        user_query = self.build_kg_query(current_inputs, chat_history)
        qq_result = await self.get_search_answer(user_query, **kwargs)
        if self.kg_conf and self.kg_conf.scope == "faq":
            qq_result_ans = qq_result.get("output_list", [])
            match_result = []
            qq_threshold = float("-inf")
            for temp in qq_result_ans:
                if (
                    temp["score"] > self.intent_config.q2label_few_shot_score
                    and len(match_result) < FEW_SHOT_NUM
                ):
                    temp_category = self.intent_config.default_class
                    for i, cate_name in enumerate(
                        self.intent_config.category_name_list
                    ):
                        if temp["content"] == cate_name:
                            temp_category = self.intent_config.category_list[i]
                    if (
                        temp["score"] > self.intent_config.recall_threshold
                        and temp["score"] > qq_threshold
                    ):
                        intent_class = temp_category
                        qq_threshold = temp["score"]
            few_shot_example = self.get_few_shot_ex(
                qq_result.get("output_list", []),
                self.intent_config.q2label_few_shot_score,
            )
            workflow_logger.debug(
                f"{self.conversation_id}|search_result|{str(match_result)}"
            )
        elif SEARCH_TYPE == "doc_line":
            few_shot_example = self.doc_search(qq_result)
        else:
            few_shot_example = str(qq_result)
        current_inputs.update({"example_content": few_shot_example})
        self.few_shot_example += "\n" + few_shot_example
        return intent_class

    async def get_search_answer(self, user_query: dict, **kwargs) -> dict:
        """调用知识库搜索 API 获取结果。

        与原组件 jiuwen/orchestration/flow/components/intent_detection.py 中的
        get_search_answer 方法保持一致。

        Args:
            user_query: 查询参数。
            **kwargs: 可含 runtime_auth_headers 参数。

        Returns:
            搜索结果字典。
        """
        all_headers = kwargs.get("runtime_auth_headers", {})
        cur_headers = all_headers.get(str(self.api_id)) or all_headers.get(
            "default", {}
        )
        start_time = time.perf_counter()
        inputs = user_query
        data = {}
        if self.api is None:
            return data
        try:
            res = await self.api.ainvoke(inputs, runtime_auth={"headers": cur_headers})
            # workflow_logger 是 LazyLogger→DefaultLogger，会先做格式化再判级别，
            # 故需显式守卫，避免 DEBUG 关闭时仍对 res 做 str() 拼接（KB 检索结果可能很大）。
            if workflow_logger.logger().isEnabledFor(logging.DEBUG):
                workflow_logger.debug(f"{self.conversation_id}|search_result|{str(res)}")
            if isinstance(res, dict) and res.get("errCode") == 0:
                data = res.get("data", {})
            elif hasattr(res, "err_code") and res.err_code == 0:
                data = getattr(res, "data", {})
        except Exception as e:
            workflow_logger.debug(
                f"{self.conversation_id}|search api error: {str(e)}\n{traceback.format_exc()}"
            )
        search_duration = round((time.perf_counter() - start_time) * 1000)
        workflow_logger.debug(
            f"{self.conversation_id}|onlysearch cost {search_duration}ms"
        )
        return data

    def anayls_search(self, search_data: dict) -> list:
        """分析搜索结果（文档类型）。"""
        res = []
        query_category = DEFAULT_QUERY_CATE
        class_category = DEFAULT_CLASS_CATE
        try:
            doc_list = search_data.get("doc_list")
            for item in doc_list:
                addlist = {}
                addlist["title"] = item[query_category]
                addlist["content"] = item[class_category]
                addlist["score"] = item["score"]
                if (
                    item["score"] > self.intent_config.recall_threshold
                    and len(res) < FEW_SHOT_NUM
                ):
                    res.append(addlist)
        except Exception as e:
            workflow_logger.debug(
                f"{self.conversation_id}|search analysis error: {str(e)}\n{traceback.format_exc()}"
            )
        return res

    def get_few_shot_ex(self, qqresult: list, q2label_few_shot_score: float) -> str:
        """构造 few-shot 示例。"""
        res = "\n"
        cnt = 0
        origin_str = """
            样例{}:\n用户输入: {}\n分类结果：{}\n
        """
        for temp in qqresult:
            if cnt >= FEW_SHOT_NUM:
                break
            cnt += 1
            if "title" in temp:
                userinput = temp["title"]
            else:
                userinput = temp["document_name"]
            classid = self._get_intent_id(self.intent_config, temp["content"])
            addstr = origin_str.format(cnt, userinput, classid)
            if classid != -1 and temp["score"] > q2label_few_shot_score:
                res += addstr
        return res

    def doc_search(self, qqresult) -> str:
        """文档搜索结果处理。"""
        res = ""
        try:
            if isinstance(qqresult, str):
                qqresult = json.loads(qqresult)
            reslist = qqresult["output_list"]
            num = 0
            for item in reslist:
                if (
                    item["score"] > self.intent_config.recall_threshold
                    and num < SEARCH_NUM
                ):
                    res += str(item["content"]) + "\n"
                    num += 1
        except Exception as e:
            res = str(qqresult)
            workflow_logger.debug(
                f"{self.conversation_id}|search analysis doc wrong: {str(e)}\n{traceback.format_exc()}"
            )
        return res

    def build_kg_query(self, current_inputs: dict, chat_history: list) -> dict:
        """构造知识库的查询参数。"""
        query = current_inputs.get("input", "")
        request_data = {
            QUERY: query,
            KG_SCOPE: "faq" if self.kg_conf.scope == "faq" else "doc",
        }
        filter_string = self.faq_config.get("filterString")
        if filter_string:
            request_data.update({"filter_string": filter_string})
        return request_data

    # --------------------------------------------------------------------------
    # LLM 调用
    # --------------------------------------------------------------------------

    async def _get_llm_instance(self, conf: dict) -> Model:
        from agent_runtime.common.model_adapters import adapt_intent_detection_config
        from jiuwen.serve.controllers.execution.ir_converter import _get_model_config_provider

        adapted_conf = adapt_intent_detection_config(conf)

        provider = _get_model_config_provider()
        llm_comp_config = await provider.get_llm_config(adapted_conf)

        return Model(
            model_client_config=llm_comp_config.model_client_config,
            model_config=llm_comp_config.model_config,
        )

    async def get_llm_result(self, current_inputs: dict) -> str:
        # Lazy initialization of LLM (cannot await in __init__)
        if self.llm is None:
            self.llm = await self._get_llm_instance(self._llm_conf)

        template = self.intent_config.intent_detection_template
        if template is None:
            template = _get_default_prompt_template()
        llm_inputs = template.format(current_inputs).to_messages()

        user_profile = self.mem_conf.get(USER_PROFILE_KEY)
        if isinstance(user_profile, dict) and user_profile.get(ENABLE_KEY, False):
            memory_msg = self._session.get_global_state(MEMORY_MESSAGE)
            if isinstance(memory_msg, BaseMessage):
                llm_inputs.append(memory_msg)

        workflow_logger.debug(
            f"{self.conversation_id}|intent detection llm_inputs prepared"
        )

        # 对齐 OLD process_on_invoke_info：在 LLM 调用前发送调试信息
        # 载荷字段与 OLD 一致（input / llm_inputs / chat_history 等合并到 current_inputs）
        trace_data = dict(current_inputs)
        trace_data[LLM_INPUTS] = llm_inputs
        if self._session:
            await self._session.trace(data=trace_data)

        try:
            llm_output = await self.llm.invoke(messages=llm_inputs)
            llm_output = llm_output.content
        except Exception as e:
            self._raise_llm_invoke_error(type(e).__name__)
        return llm_output

    # --------------------------------------------------------------------------
    # 全局意图处理
    # --------------------------------------------------------------------------

    def add_global_intents(self, global_intents: list, global_intent_map: dict) -> str:
        """合并全局意图到分类信息中。

        Args:
            global_intents: 全局意图列表。
            global_intent_map: 分类名到全局意图的映射（会被修改）。

        Returns:
            合并后的 category_info 字符串。
        """
        category_info = self.intent_config.category_info
        workflow_logger.debug(
            f"{self.conversation_id}|category_info and global_intents received"
        )

        if global_intents:
            category_info_list = []
            if category_info:
                category_info_list = category_info.split("\n")

            other_index = next(
                (
                    i
                    for i, category in enumerate(category_info_list)
                    if "其他" in category
                ),
                -1,
            )
            other_in_local_detection = other_index > -1

            if self.intent_config.overridable and other_in_local_detection:
                for intent in global_intents:
                    if hasattr(intent, "name") and "其他" in intent.name:
                        if hasattr(intent, "description") and intent.description:
                            category_name = f"分类{other_index}"
                            category_info_list[other_index] = (
                                f"{category_name}: {intent.description}"
                            )
                            global_intent_map[category_name] = intent
                        break

            cur_index = (
                len(category_info_list) - 1
                if "分类0" in category_info
                else len(category_info_list)
            )

            for intent in global_intents:
                if hasattr(intent, "description") and intent.description:
                    if intent.name in category_info:
                        continue
                    category_name = f"分类{cur_index + 1}"
                    category_info_list.append(f"{category_name}: {intent.description}")
                    cur_index += 1
                    global_intent_map[category_name] = intent

            category_info = "\n".join(category_info_list)
        workflow_logger.debug(
            f"{self.conversation_id}|global intent map: {global_intent_map}"
        )
        return category_info

    def _handle_global_intent(
        self, intent_class: str, reason: str, global_intent_map: dict
    ) -> dict:
        matched_intent = global_intent_map[intent_class]
        result = dict(intent_id=matched_intent.intent_id, reason=reason)
        interrupt_message = {
            "type": "GLOBAL_INTENT",
            "intent": result,
        }
        self.node_state.status = ExecutionStatus.USER_INTERACT
        return self._session.interact(interrupt_message)

    def _handle_global_other_intent(self) -> Any:
        result = dict(intent_id="0", reason="其他")
        interrupt_message = {
            "type": "GLOBAL_INTENT",
            "intent": result,
        }
        self.node_state.status = ExecutionStatus.USER_INTERACT
        return self._session.interact(interrupt_message)

    # --------------------------------------------------------------------------
    # 输入准备与后处理
    # --------------------------------------------------------------------------

    def _get_chat_history(self, context: ModelContext, session: Session) -> list:
        """从上下文中获取聊天历史。

        使用 context.get_messages() 直接获取消息列表，
        然后根据 chat_history_max_turn 进行轮次截取。

        Args:
            context: 模型上下文
            session: 工作流会话

        Returns:
            消息列表
        """
        messages = []

        if self.intent_config.enable_history and context is not None:
            try:
                messages = context.get_messages()
            except Exception as e:
                workflow_logger.error(f"Failed to get messages from context: {e}")

        if not messages:
            chat_history_obj = session.get_global_state(WORKFLOW_CHAT_HISTORY)
            if chat_history_obj:
                if hasattr(chat_history_obj, "get_conversation_history"):
                    messages = chat_history_obj.get_conversation_history()
                elif isinstance(chat_history_obj, list):
                    messages = chat_history_obj

        return messages

    def _prepare_detection_inputs(
        self, inputs: dict, chat_history: list, global_intents: Any
    ) -> dict:
        """准备意图检测所需的输入参数。"""
        current_inputs = {}
        global_intent_map = {}

        # 处理全局意图，合并到 category_info
        category_info = self.intent_config.category_info
        if global_intents and isinstance(global_intents, list):
            category_info = self.add_global_intents(global_intents, global_intent_map)

        current_inputs.update(
            {
                USER_PROMPT: self.intent_config.user_prompt,
                CATEGORY_INFO: category_info,
                DEFAULT_CLASS: self.intent_config.default_class,
                ENABLE_HISTORY: self.intent_config.enable_history,
                ENABLE_INPUT: self.intent_config.enable_input,
                EXAMPLE_CONTENT: "\n\n".join(self.intent_config.example_content),
                CHAT_HISTORY_MAX_TURN: self.intent_config.chat_history_max_turn,
            }
        )

        if (
            not self.intent_config.enable_history
            and not self.intent_config.enable_input
        ):
            raise ValueError(
                "AT LEAST ONE OF INTENT_DETECTION'S ENABLE_HISTORY AND ENABLE_INPUT SHOULD ENABLE."
            )

        if self.intent_config.enable_history:
            chat_history_str = self._format_chat_history(chat_history)
            current_inputs.update({CHAT_HISTORY: chat_history_str})

        if self.intent_config.enable_input:
            current_inputs.update({INPUT: inputs.get(INPUT)})

        current_inputs["global_intent_map"] = global_intent_map
        return current_inputs

    def _format_chat_history(self, chat_history: list) -> str:
        """格式化聊天历史记录。"""
        filtered_chat_history = filter_enable_history(chat_history)
        chat_history_str = ""
        for history in filtered_chat_history[
            -self.intent_config.chat_history_max_turn :
        ]:
            chat_history_str += "{}：{}\n".format(
                ROLE_MAP.get(history.get(ROLE, CONTENT), "用户"), history.get(CONTENT)
            )
        return chat_history_str

    def intent_detection_post_process(self, result: str) -> tuple[str, str]:
        """后处理 LLM 输出。

        Args:
            result: LLM 原始输出字符串。

        Returns:
            (intent_class, reason) 元组。
        """
        try:
            result = refix_llm_output(result)
            parsed_dict = ast.literal_eval(result)
            if not isinstance(parsed_dict, dict):
                return self.intent_config.default_class, JSON_PARSE_FAIL_REASON.format(
                    result=result
                )
        except Exception:
            return self.intent_config.default_class, JSON_PARSE_FAIL_REASON.format(
                result=result
            )

        if parsed_dict.get(CLASS) is None and parsed_dict.get(RESULT) is None:
            return self.intent_config.default_class, CLASS_KEY_MISSING_REASON.format(
                result=parsed_dict
            )

        intent_class = parsed_dict.get(CLASS)
        if not intent_class:
            intent_class = str(parsed_dict.get(RESULT))

        if isinstance(parsed_dict.get(CLASS), int):
            intent_class = str(intent_class)
        else:
            intent_class = (
                intent_class.replace("\n", "")
                .replace(" ", "")
                .replace("'", "")
                .replace('"', "")
            )
        if "分类" not in intent_class:
            intent_class = "分类" + intent_class
        parsed_dict.update({CLASS: intent_class})

        return parsed_dict.get(CLASS), parsed_dict.get(REASON, "")

    def output_validation(self, result: str) -> bool:
        """验证 LLM 输出是否在预定义分类列表中。"""
        return result in self.intent_config.category_list

    def _handle_detection_result(
        self, llm_output: str, global_intent_map: dict
    ) -> dict:
        intent_class, reason = self.intent_detection_post_process(llm_output)
        workflow_logger.debug(f"{self.conversation_id}|intent_class: {intent_class}")

        if intent_class in global_intent_map:
            return self._handle_global_intent(intent_class, reason, global_intent_map)
        if (
            intent_class == "分类0"
            and self.intent_config.overridable
            and global_intent_map
        ):
            return self._handle_global_other_intent()

        if not self.output_validation(intent_class):
            intent_id_name = self._get_intent_id_name(
                self.intent_config, self.intent_config.default_class
            )
            return dict(
                result=self.intent_config.default_class,
                reason=VALIDATION_FAIL_REASON.format(
                    intent_class=intent_class,
                    category_list=self.intent_config.category_list,
                ),
                classificationId=intent_id_name.get(CLASSIFICATION_ID, ""),
                name=intent_id_name.get(CLASSIFICATION_NAME, ""),
            )
        self.node_state.status = ExecutionStatus.END
        intent_id_name = self._get_intent_id_name(self.intent_config, intent_class)
        return dict(
            result=intent_class,
            reason=reason,
            classificationId=intent_id_name.get(CLASSIFICATION_ID, ""),
            name=intent_id_name.get(CLASSIFICATION_NAME, ""),
        )

    # --------------------------------------------------------------------------
    # 辅助方法
    # --------------------------------------------------------------------------

    def _get_intent_id_name(
        self, intent_config: IntentDetectionConfig, intent_class: str
    ) -> dict:
        """获取意图的 id 和 name。"""
        intent_res = {
            CLASSIFICATION_ID: self.intent_config.default_class,
            CLASSIFICATION_NAME: CLASSIFICATION_DEAFULT_NAME,
        }
        idx = -1
        idlist = -1
        for i, category in enumerate(intent_config.category_list):
            if category == intent_class:
                idx = int(category.replace("分类", ""))
                idlist = i
        if idx > -1:
            intent_res = {
                CLASSIFICATION_ID: idx,
                CLASSIFICATION_NAME: intent_config.category_name_list[idlist],
            }
        return intent_res

    def _get_intent_id(
        self, intent_config: IntentDetectionConfig, intent_name: str
    ) -> int:
        idx = next(
            (
                i
                for i, category in enumerate(intent_config.category_name_list)
                if category == intent_name
            ),
            -1,
        )
        return idx

    def _raise_input_error(self, error_msg: str) -> None:
        """抛出输入错误异常。"""
        raise build_intent_detection_error(
            IntentDetectionStatusCode.WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR,
            error_msg=error_msg,
        )

    def _raise_llm_invoke_error(self, error_msg: str) -> None:
        """抛出 LLM 调用错误异常。"""
        raise build_intent_detection_error(
            IntentDetectionStatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR,
            error_msg=error_msg,
        )

    # --------------------------------------------------------------------------
    # 配置解析
    # --------------------------------------------------------------------------

    def _inner_get_config_info(
        self, cur_conf: dict, is_need_category_name: bool = False
    ) -> dict:
        formatted_config = dict()
        category_info_list = []
        category_list = []
        category_name_list = []
        try:
            for branch in cur_conf.get("branches"):
                branch_id = branch.get("id")
                match = re.search(r"branch_(\d+)", branch_id)
                if match:
                    branch_index = match.group(1)
                    category_list.append(f"分类{branch_index}")
                    category_info_list.append(
                        f"分类{branch_index}: {branch.get('catalog')}"
                    )
                    category_name_list.append(f"{branch.get('catalog')}")

            category_info = "\n".join(category_info_list)
            formatted_config[CATEGORY_LIST] = category_list
            formatted_config[CATEGORY_INFO] = category_info
            if is_need_category_name:
                formatted_config[CATEGORY_NAME_LIST] = category_name_list
        except Exception as e:
            raise build_intent_detection_error(
                IntentDetectionStatusCode.WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR,
                error_msg="FAILED TO MATCH VALID CATEGORIES.",
                cause=e,
            ) from e

        formatted_config[USER_PROMPT] = cur_conf.get("prompt", "")

        formatted_config[INTENT_DETECTION_TEMPLATE] = _get_default_prompt_template()

        if isinstance(cur_conf.get("enableHistory"), bool):
            formatted_config[ENABLE_HISTORY] = cur_conf.get("enableHistory")

        if isinstance(cur_conf.get("enableInput"), bool):
            formatted_config[ENABLE_INPUT] = cur_conf.get("enableInput")

        if isinstance(cur_conf.get("chatHistoryMaxTurn"), int):
            formatted_config[CHAT_HISTORY_MAX_TURN] = cur_conf.get("chatHistoryMaxTurn")

        if isinstance(cur_conf.get("exampleContent"), list):
            formatted_config[EXAMPLE_CONTENT] = cur_conf.get("exampleContent")

        formatted_config["overridable"] = cur_conf.get("overridable", False)
        return formatted_config

    def _get_config_info(self, cur_conf: dict) -> dict:
        formatted_config = self._inner_get_config_info(cur_conf, True)
        category_name_list = formatted_config[CATEGORY_NAME_LIST]
        if DEFAULT_INT in category_name_list:
            default_idx = category_name_list.index(DEFAULT_INT)
            formatted_config[DEFAULT_CLASS] = "分类" + str(default_idx)

        if RECALLTHREASHOLD in cur_conf:
            formatted_config[RECALLTHREASHOLD] = cur_conf.get("recallThreshold")

        if ENABLE_Q2L in cur_conf:
            formatted_config[ENABLE_Q2L] = cur_conf.get("enableKnowledge")
        return formatted_config
