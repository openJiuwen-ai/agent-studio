#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import ast
import copy
import json
import os
import re
import time
import traceback
from copy import deepcopy
from dataclasses import dataclass, field

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.messages import BaseMessage
from jiuwen.common.log.base import logger
from jiuwen.context.memory_engine.config.memory_ir_config import (
    USER_PROFILE_KEY,
    ENABLE_KEY,
)
from jiuwen.controller.common.message_type import MessageSubType
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.common.perf_log import wf_performance_buffer
from jiuwen.orchestration.flow.components.util import (
    process_on_invoke_info,
    filter_enable_history,
)
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_CHAT_HISTORY,
    WORKFLOW_GLOBAL_INTENTS,
    MEMORY_MESSAGE,
)
from jiuwen.orchestration.flow.enum import ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.state import State
from jiuwen.orchestration.utils import Input, Output
from jiuwen.planner.planning_modules.base import PromptPlanningModule
from jiuwen.planner.planning_modules.detect_intention import DetectIntention
from jiuwen.plugin import PluginManager
from jiuwen.plugin.common.constant import QUERY
from jiuwen.plugin.common.utils.ir_utils import PluginIRConverter
from jiuwen.prompt import TemplateManager, Template
from pydantic import BaseModel, StrictStr, Field, ValidationError

LLM = "llm"
NAME = "name"
MODEL = "model"
CLASS = "result"
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
VALIDATION_FAIL_REASON = "当前意图识别的输出类别 '{intent_class}' 不在预定义的分类列表: '{category_list}'中，因此系统返回默认分类。"
# EI 增加
RESULT = "result"
CATEGORY_NAME_LIST = "category_name_list"
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

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class IntentDetectionLLMConfig(BaseModel):
    model_type: StrictStr = Field(min_length=1)
    model_name: StrictStr = Field(min_length=1)
    hyper_parameters: dict = Field(default={})
    extension: dict = Field(default={})


@dataclass
class IntentDetectionState(State):
    status: ExecutionStatus = ExecutionStatus.START


@dataclass
class IntentDetectionConfig:
    user_prompt: str
    category_info: str
    category_list: list[str]
    intent_detection_template: Template
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
class KnowledgeConfig(BaseModel):
    category: str = None
    scope: str = "faq"


def refix_llm_output(input_str):
    """大模型输出后处理"""
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


class IntentDetection(Invokable):
    """
    IntentDetection节点定义
    """

    def __init__(
        self,
        conf: dict,
        metadata: WorkflowMetadata,
        runtime_context: RuntimeContext = None,
    ):
        """
        IntentDetection节点初始化方法
        """
        super().__init__()
        self.runtime_context = runtime_context
        self.metadata = metadata
        self.llm = self._get_llm_instance(conf)
        self.intent_config = IntentDetectionConfig(**self._get_config_info(conf))
        self.intent_config_retry = IntentDetectionConfig(**self._get_config_info(conf))
        self.node_state = IntentDetectionState()
        self.node_state_retry = IntentDetectionState()
        self.search = {}
        self.prompt_engine = PromptPlanningModule()
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
        # 意图判定prompts
        intent_prompt = TemplateManager().get(
            name="ei_intent_detection",
            filters={"tag": model_configs.get(MODEL_NAME, "")},
        )
        # 时延问题，暂时不支持枚举值修复
        if intent_prompt is not None and hasattr(intent_prompt, "content"):
            self.intent_prompt = intent_prompt.content
        # memory config
        self.mem_conf = conf.get("memory", {})

    def reset(self) -> bool:
        self.intent_config = copy.deepcopy(self.intent_config_retry)
        self.node_state = copy.deepcopy(self.node_state_retry)
        self.few_shot_example = ""
        if len(self.matching_items) == 0:
            self.intent_config.default_class = CLASSIFICATION_DEAFULT_OLD
        return True

    def get_state(self):
        return self.node_state

    def load_state(self, state: IntentDetectionState):
        """
        load intent detection state from input state
        """
        self.node_state = deepcopy(state)

    def get_kg_instance(self, conf):
        """获取知识库服务"""
        self.api_id = conf.get("apiId", "")
        if self.intent_config.enable_knowledge:
            if not self.api_id:
                self.api_id = conf.get("id", "")
                try:
                    self.api = PluginIRConverter.ir_to_plugin(conf)
                except Exception as e:
                    logger.debug(f"未提交知识库信息: {type(e).__name__}")
                    self.intent_config.enable_knowledge = False
            else:
                try:
                    res = PluginManager().get_plugin_by_id(int(self.api_id))
                    plugin_list = res.get("body")
                    self.api = plugin_list[0]
                except Exception as e:
                    logger.debug(f"未提交知识库信息: {type(e).__name__}")
                    self.intent_config.enable_knowledge = False
        self.kg_conf = KnowledgeConfig.model_validate(conf)

    def invoke(self, inputs: Input, **kwargs) -> Output:
        """invoke IntentDetection节点"""
        return dict()

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """invoke IntentDetection节点"""
        # 提取上下文数据
        start_time = time.perf_counter()
        self.conversation_id = self.runtime_context.get(
            "workflow_execute_debug_info", {}
        ).get("workflow_conversation_id", "")
        chat_history = self._get_chat_history_from_context()
        current_inputs = dict()
        global_intents = self.runtime_context.get(WORKFLOW_GLOBAL_INTENTS, None)
        global_intent_map = {}
        intent_class = self.intent_config.default_class
        # 处理意图检测输入
        try:
            current_inputs = self._prepare_detection_inputs(
                inputs, chat_history, global_intents
            )
            global_intent_map = current_inputs.pop("global_intent_map", {})
        except Exception as e:
            self._raise_input_error(
                str(e) if LOG_VERBOSE_MODE else str(type(e).__name__)
            )
        # 进行 faq 匹配
        if self.intent_config.enable_knowledge:
            try:
                intent_class = await self.get_faq_result(
                    current_inputs, chat_history, **kwargs
                )
            except Exception:
                raise JiuWenBaseException(
                    message=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR.errmsg.format(
                        error_msg="Search is wrong"
                    ),
                    error_code=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR.code,
                ) from e
        if (
            intent_class != self.intent_config.default_class
            and intent_class is not None
        ):
            get_intent_end_time = time.perf_counter()
            get_intent_duration = round((get_intent_end_time - start_time) * 1000)
            logger.info(f"{self.conversation_id}|********use faq model.")
            wf_performance_buffer.info(
                f"{self.conversation_id}|intent faq cost",
                get_intent_duration,
                uid=self.conversation_id,
                is_record=True,
            )
            intent_id_name = self._get_intent_id_name(self.intent_config, intent_class)
            return dict(
                result=intent_class,
                reason="",
                classificationId=intent_id_name.get(CLASSIFICATION_ID, ""),
                name=intent_id_name.get(CLASSIFICATION_NAME, ""),
            )
        # 获取大模型结果
        llm_output = await self.get_llm_result(current_inputs, kwargs.get("span"))
        logger.info(
            f"{llm_output}|********llm result.",
            simple_log="get llm result successfully|********llm result.",
        )
        # 后处理意图检测结果
        intent_res = self._handle_detection_result(llm_output, global_intent_map)
        get_intent_end_time = time.perf_counter()
        get_intent_duration = round((get_intent_end_time - start_time) * 1000)
        logger.info(f"{self.conversation_id}|********use llm model.")
        wf_performance_buffer.info(
            f"{self.conversation_id}|intent llm cost",
            get_intent_duration,
            uid=self.conversation_id,
            is_record=True,
        )
        return intent_res

    async def get_faq_result(self, current_inputs, chat_history, **kwargs):
        """获取faq结果"""
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
                        # 解决不按正常顺序排序
                        qq_threshold = temp["score"]
            few_shot_example = self.get_few_shot_ex(
                qq_result.get("output_list", []),
                self.intent_config.q2label_few_shot_score,
            )
            logger.info(
                f"{self.conversation_id}|search_result|{str(match_result)}",
                simple_log=f"{self.conversation_id}| get search_result",
            )
        elif SEARCH_TYPE == "doc_line":
            # 这里直接看doc 取几条，如果能json解析则根据默认参数取/score取
            few_shot_example = self.doc_search(qq_result)
        else:
            few_shot_example = str(qq_result)
        current_inputs.update({"example_content": few_shot_example})
        self.few_shot_example += "\n" + few_shot_example
        return intent_class

    async def get_search_answer(self, user_query, **kwargs):
        """获取faq搜索结果"""
        all_headers = kwargs.get("runtime_auth_headers", {})
        cur_headers = all_headers.get(str(self.api_id)) or all_headers.get(
            "default", {}
        )
        start_time = time.perf_counter()
        inputs = user_query
        data = {}
        try:
            res = await self.api.ainvoke(inputs, runtime_auth={"headers": cur_headers})
            logger.info(
                f"{self.conversation_id}|search_result|{str(res)}",
                simple_log=f"{self.conversation_id}|get search_result",
            )
            if res.get("errCode") == StatusCode.SUCCESS.code:
                data = res.get("data")
        except Exception as e:
            logger.info(
                f"{self.conversation_id}|search api error: {str(e)}\n{traceback.format_exc()}",
                simple_log=f"{self.conversation_id}|search api error: {type(e).__name__}",
            )
        prepare_params_end_time = time.perf_counter()
        prepare_params_duration = round((prepare_params_end_time - start_time) * 1000)
        wf_performance_buffer.debug(
            f"{self.conversation_id}|onlysearch",
            prepare_params_duration,
            uid=self.conversation_id,
            is_record=True,
        )
        return data

    def anayls_search(self, search_data):
        """分析搜索结果"""
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
            logger.info(
                f"{self.conversation_id}|search analysis error: {str(e)}\n{traceback.format_exc()}",
                simple_log=f"{self.conversation_id}|search analysis error: {type(e).__name__}",
            )
        return res

    def get_few_shot_ex(self, qqresult, q2label_few_shot_score):
        """构造few-shot示例"""
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
            if (
                classid != -1
                and temp["score"] > self.intent_config.q2label_few_shot_score
            ):
                res += addstr
        return res

    def doc_search(self, qqresult):
        """doc搜索"""
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
            # 兜底直接字符串化
            res = str(qqresult)
            logger.info(
                f"{self.conversation_id}|search analysis doc wrong: {str(e)}\n{traceback.format_exc()}",
                simple_log=f"{self.conversation_id}|search analysis doc wrong: {type(e).__name__}",
            )
        return res

    async def get_llm_result(self, current_inputs, span_input):
        """获取llm"""
        llm_inputs = DetectIntention.pre_process(current_inputs, self.intent_config)
        user_profile = self.mem_conf.get(USER_PROFILE_KEY)
        if isinstance(user_profile, dict) and user_profile.get(ENABLE_KEY, False):
            memory_msg = self.runtime_context.get(MEMORY_MESSAGE)
            if isinstance(memory_msg, BaseMessage):
                llm_inputs["messages"].append(memory_msg)
        logger.info(
            f"{self.conversation_id}|intent detection llm_inputs|{llm_inputs}",
            simple_log=f"{self.conversation_id}|intent detection llm_inputs",
        )
        current_inputs.update({LLM_INPUTS: llm_inputs})
        await process_on_invoke_info(
            component_metadata={},
            runtime_context=self.runtime_context,
            data=current_inputs,
            span=span_input,
        )

        # 获取LLM输出并处理
        try:
            llm_output = await self.llm.ainvoke(llm_inputs)
            llm_output = llm_output.content
        except Exception as e:
            self._raise_llm_invoke_error(type(e).__name__)
        return llm_output

    def build_kg_query(self, current_inputs, chat_history):
        """构造知识库的query"""
        query = current_inputs.get("input", "")
        request_data = {
            QUERY: query,
            KG_SCOPE: "faq" if self.kg_conf.scope == "faq" else "doc",
        }
        filter_string = self.faq_config.get("filterString")
        if filter_string:
            request_data.update({"filter_string": filter_string})
        return request_data

    def add_global_intents(self, global_intents, global_intent_map):
        """add global intents"""
        # 处理category_info，将global_intents中的description加入
        category_info = self.intent_config.category_info
        logger.info(
            f"{self.conversation_id}|category_info: {category_info} and global_intents: {global_intents}",
            simple_log=f"{self.conversation_id}|get category_info and global_intents",
        )
        # 意图识别节点是否配置有其他意图
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
                        # 若配置overridable, 用全局意图的其他意图覆盖子工作流中的其他意图
                        if hasattr(intent, "description") and intent.description:
                            category_name = f"分类{other_index}"
                            category_info_list[other_index] = (
                                f"{category_name}: {intent.description}"
                            )
                            global_intent_map[category_name] = intent
                        break

            # 获取现有分类的数量，作为新分类的起始索引
            cur_index = (
                len(category_info_list) - 1
                if "分类0" in category_info
                else len(category_info_list)
            )

            # 从global_intents中提取description并拼接
            for intent in global_intents:
                if hasattr(intent, "description") and intent.description:
                    if intent.name in category_info:
                        continue
                    category_name = f"分类{cur_index + 1}"
                    category_info_list.append(f"{category_name}: {intent.description}")
                    cur_index += 1
                    # 建立分类名称到全局意图的映射
                    global_intent_map[category_name] = intent

            # 合并category_info
            category_info = "\n".join(category_info_list)
        logger.info(
            f"{self.conversation_id}|global intent map: {global_intent_map}",
            simple_log=f"{self.conversation_id}|get global intent map",
        )
        return category_info

    def intent_detection_post_process(self, result):
        """
        Post-process the result
        Args:
            result: The result is a dict string.
        Returns:
            The processed results are 'class' and 'reason'
        """
        try:
            # 对推理模型的返回做后处理
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

        # post_process class information
        if not parsed_dict.get(CLASS):
            return self.intent_config.default_class, CLASS_KEY_MISSING_REASON.format(
                result=parsed_dict
            )

        if isinstance(parsed_dict.get(CLASS), int):
            intent_class = str(parsed_dict.get(CLASS))
        else:
            intent_class = (
                parsed_dict.get(CLASS)
                .replace("\n", "")
                .replace(" ", "")
                .replace("'", "")
                .replace('"', "")
            )
        if "分类" not in intent_class:
            intent_class = "分类" + intent_class
        parsed_dict.update({CLASS: intent_class})

        return parsed_dict.get(CLASS), parsed_dict.get(REASON, "")

    def output_validation(self, result):
        """
        Validation of LLM output
        Args:
            result: LLM output
        Returns:
            True: Validation passed
            False: Validation failed
        """
        return result in self.intent_config.category_list

    def _inner_get_config_info(self, cur_conf: dict, is_need_category_name=False):
        # 进行代码赋值
        formatted_config = dict()
        # category info: use branches construct
        # like:
        # 分类1:订餐
        # 分类2:旅游
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
            # category_list: ['分类1', '分类2', ...]
            formatted_config[CATEGORY_LIST] = category_list
            # category_info: "分类1: xxx\n分类2: xxx\n ..."
            formatted_config[CATEGORY_INFO] = category_info
            if is_need_category_name:
                formatted_config[CATEGORY_NAME_LIST] = category_name_list
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR.code,
                message=StatusCode.WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR.errmsg.format(
                    msg="FAILED TO MATCH VALID CATEGORIES."
                ),
            ) from e
        # system prompt provided by user
        formatted_config[USER_PROMPT] = cur_conf.get("prompt", "")

        # intent_detection_template
        try:
            model_name = cur_conf.get(LLM, {}).get(MODEL, {}).get(MODEL_NAME, "")
            # get intent_detection_template from prompt resource
            intent_detection_template = TemplateManager().get(
                name="ei_intent_detection", filters={"tag": model_name}
            )
            formatted_config[INTENT_DETECTION_TEMPLATE] = intent_detection_template
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR.errmsg.format(
                    error_msg=str(type(e).__name__)
                ),
                error_code=StatusCode.WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR.code,
            ) from e
        # enable_history switch
        if isinstance(cur_conf.get("enableHistory"), bool):
            formatted_config[ENABLE_HISTORY] = cur_conf.get("enableHistory")

        # enable_input switch
        if isinstance(cur_conf.get("enableInput"), bool):
            formatted_config[ENABLE_INPUT] = cur_conf.get("enableInput")

        # chatHistoryMaxTurn
        if isinstance(cur_conf.get("chatHistoryMaxTurn"), int):
            formatted_config[CHAT_HISTORY_MAX_TURN] = cur_conf.get("chatHistoryMaxTurn")
        # exampleContent
        if isinstance(cur_conf.get("exampleContent"), list):
            formatted_config[EXAMPLE_CONTENT] = cur_conf.get("exampleContent")
        formatted_config["overridable"] = cur_conf.get("overridable", False)
        return formatted_config

    def _get_config_info(self, cur_conf: dict):
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

    def _get_llm_instance(self, conf: dict):
        """
        Get LLM instance
        """
        llm_configs = conf.get(LLM, {})
        model_configs = llm_configs.get(MODEL, {})
        _model_name = model_configs.get(MODEL_NAME, "")
        _model_type = model_configs.get(MODEL_SOURCE, "")
        _hypter_params = model_configs.get(HYPTER_PARAM, {})
        _extension = model_configs.get(EXTENSION, {})
        try:
            llm_chain_configs_model = IntentDetectionLLMConfig.model_validate(
                dict(
                    model_type=_model_type,
                    model_name=_model_name,
                    hyper_parameters=_hypter_params,
                    extension=_extension,
                )
            )
        except ValidationError as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INIT_ERROR.code,
                message=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INIT_ERROR.errmsg.format(
                    msg=str(type(e).__name__)
                ),
            ) from e
        return ModelFactory().get_model(
            model_type=llm_chain_configs_model.model_type,
            model_name=llm_chain_configs_model.model_name,
            runtime_context=self.runtime_context,
            **llm_chain_configs_model.hyper_parameters,
            **llm_chain_configs_model.extension,
        )

    def _get_chat_history_from_context(self):
        """从上下文中获取并处理聊天历史"""
        chat_history_obj = self.runtime_context.get(WORKFLOW_CHAT_HISTORY, None)
        if chat_history_obj:
            return chat_history_obj.get_conversation_history()
        return []

    def _prepare_detection_inputs(self, inputs, chat_history, global_intents):
        """准备意图检测所需的输入"""
        current_inputs = {}
        global_intent_map = {}

        # 添加基本配置参数
        current_inputs.update(
            {
                USER_PROMPT: self.intent_config.user_prompt,
                CATEGORY_INFO: self.intent_config.category_info,
                DEFAULT_CLASS: self.intent_config.default_class,
                ENABLE_HISTORY: self.intent_config.enable_history,
                ENABLE_INPUT: self.intent_config.enable_input,
                EXAMPLE_CONTENT: "\n\n".join(self.intent_config.example_content),
                CHAT_HISTORY_MAX_TURN: self.intent_config.chat_history_max_turn,
            }
        )

        # 检查输入配置有效性
        if (
            not self.intent_config.enable_history
            and not self.intent_config.enable_input
        ):
            raise ValueError(
                "AT LEAST ONE OF INTENT_DETECTION'S ENABLE_HISTORY AND ENABLE_INPUT SHOULD ENABLE."
            )

        # 处理历史记录
        if self.intent_config.enable_history:
            chat_history_str = self._format_chat_history(chat_history)
            current_inputs.update({CHAT_HISTORY: chat_history_str})

        # 处理当前输入
        if self.intent_config.enable_input:
            current_inputs.update({INPUT: inputs.get(INPUT)})

        # 保存全局意图映射用于后续处理
        current_inputs["global_intent_map"] = global_intent_map

        return current_inputs

    def _format_chat_history(self, chat_history):
        """格式化聊天历史记录"""
        filtered_chat_history = filter_enable_history(chat_history)
        chat_history_str = ""
        for history in filtered_chat_history[
            -self.intent_config.chat_history_max_turn :
        ]:
            # 兼容 dict 与 ConversationMessage/BaseMessage 对象（role/content 为属性，无 .get()）
            if isinstance(history, dict):
                role = history.get(ROLE, "") or ""
                content = history.get(CONTENT, "") or ""
            else:
                role = getattr(history, "role", None) or getattr(history, "type", None) or ""
                content = getattr(history, "content", None)
                if content is None:
                    content = getattr(history, "text", "") or ""
                if not isinstance(content, str):
                    content = str(content)
            chat_history_str += "{}：{}\n".format(
                ROLE_MAP.get(role, "用户"), content
            )
        return chat_history_str

    def _raise_input_error(self, error_msg):
        """抛出输入错误异常"""
        raise JiuWenBaseException(
            message=StatusCode.WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR.errmsg.format(
                error_msg=error_msg
            ),
            error_code=StatusCode.WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR.code,
        )

    def _raise_llm_invoke_error(self, error_msg):
        """抛出LLM调用错误异常"""
        raise JiuWenBaseException(
            message=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR.errmsg.format(
                error_msg=error_msg
            ),
            error_code=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR.code,
        )

    def _handle_detection_result(self, llm_output, global_intent_map):
        """处理意图检测结果"""
        intent_class, reason = self.intent_detection_post_process(llm_output)
        logger.info(
            f"{self.conversation_id}|intent_class: {intent_class}",
            simple_log=f"{self.conversation_id}|get intent class",
        )

        # 检查是否是全局意图
        if intent_class in global_intent_map:
            return self._handle_global_intent(intent_class, reason, global_intent_map)
        if (
            intent_class == "分类0"
            and self.intent_config.overridable
            and global_intent_map
        ):
            return self._handle_global_other_intent()
        # 验证输出有效性
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

    def _handle_global_intent(self, intent_class, reason, global_intent_map):
        """处理全局意图并触发中断"""
        matched_intent = global_intent_map[intent_class]
        result = dict(intent_id=matched_intent.intent_id, reason=reason)

        # 触发全局意图的中断处理
        interrupt_message = {
            "type": MessageSubType.GLOBAL_INTENT.value,
            "intent": result,
        }
        self.node_state.status = ExecutionStatus.USER_INTERACT
        return self.interrupt(interrupt_message)

    def _handle_global_other_intent(self):
        """处理全局意图并触发中断"""
        result = dict(intent_id="0", reason="其他")
        # 触发全局意图的中断处理
        interrupt_message = {
            "type": MessageSubType.GLOBAL_INTENT.value,
            "intent": result,
        }
        self.node_state.status = ExecutionStatus.USER_INTERACT
        return self.interrupt(interrupt_message)

    # 获取意图的id和name，用于下一节点调用
    def _get_intent_id_name(self, intent_config, intent_class):
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

    def _get_intent_id(self, intent_config, intent_name):
        idx = next(
            (
                i
                for i, category in enumerate(intent_config.category_name_list)
                if category == intent_name
            ),
            -1,
        )
        return idx
