# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
prompt tuning cases
"""


class TuneConstant:
    """
    A class that contains all the common constants used in the tuning module.
    """

    """ 消息角色常量 """
    SYSTEM_ROLE: str = "system"
    ASSISTANT_ROLE: str = "assistant"
    USER_ROLE: str = "user"
    TOOL_ROLE: str = "tool"

    """ 消息关键字常量 """
    MESSAGE_KEY: str = "messages"
    TOOLS_KEY: str = "tools"
    MESSAGE_ROLE_KEY: str = "role"
    MESSAGE_CONTENT_KEY: str = "content"
    MESSAGE_TOOL_CALLS_KEY: str = "tool_calls"
    QUESTION_KEY: str = "question"
    REASON_KEY: str = "reason"
    LABEL_KEY: str = "label"
    NAME_KEY: str = "name"
    VARIABLE_KEY: str = "variable"

    """ 优化参数常量 """
    ROOT_CASE_INDEX: int = -1
    EVALUATION_METHOD_TEXT = "TEXT"
    EVALUATION_METHOD_LLM = "LLM"
    EVALUATION_METHOD_JSON = "JSON"
    OPTIMIZE_METHOD_JOINT = "JOINT"
    LLM_EVALUATION_TYPE_SUBJECTIVE = "subjective"
    LLM_EVALUATION_TYPE_OBJECTIVE = "objective"

    """ 优化参数默认值 """
    DEFAULT_EXAMPLE_NUM: int = 0
    DEFAULT_COT_EXAMPLE_NUM: int = 0
    DEFAULT_ITERATIONS: int = 3
    DEFAULT_EVAL_MAX_EXAMPLE_SAMPLE_NUM: int = 10
    DEFAULT_LLM_PARALLEL_DEGREE: int = 1
    DEFAULT_LLM_CHAT_RETRY_TIMES: int = 5
    DEFAULT_COT_EXAMPLE_RATIO: float = 0.25
    DEFAULT_MAX_CASE_NUM: int = 300
    DEFAULT_OPTIMIZE_METHOD: str = OPTIMIZE_METHOD_JOINT
    DEFAULT_EVALUATION_METHOD: str = EVALUATION_METHOD_LLM
    DEFAULT_MAX_RUNNING_TASK_NUM: int = 64
    DEFAULT_PROMPT_CANDIDATES_NUM: int = 3
    DEFAULT_EVAL_EXECUTE_NUM: int = 3
    DEFAULT_TRAIN_DATASET_NUM: int = 32
    DEFAULT_STOP_SCORE: float = 1.0

    """ 优化参数上下限阈值 """
    MIN_ITERATION_NUM: int = 1
    MAX_ITERATION_NUM: int = 20
    MIN_LLM_PARALLEL_DEGREE: int = 1
    MAX_LLM_PARALLEL_DEGREE: int = 10
    MIN_EXAMPLE_NUM: int = 0
    MAX_EXAMPLE_NUM: int = 10
    MIN_COT_EXAMPLE_NUM: int = 0
    MAX_COT_EXAMPLE_NUM: int = 5
    MIN_EARLY_STOPPING_SCORE: float = 0.0
    MAX_EARLY_STOPPING_SCORE: float = 1.0

    """ 持久化配置 """
    MYSQL_STORAGE: str = "MYSQL"
    GAUSSDB_STORAGE: str = "GAUSSDB"
    STATUS_CHECK_INTERVAL: float = 5.0
    RUNNING_CHECK_PERIOD: int = 4
    RUNNING_STATUS_TIMEOUT: int = 120

    """ 默认前缀系统提示词 """
    RAW_PROMPT_TAG: str = "<RAW_PROMPT>"
    DEFAULT_SYSTEM_PROMPT_PREFIX: str = """
    你是一个AI系统，你的角色为assistant，请按照用户要求的输出格式或默认的输出
    格式根据给定的API说明和对话历史1..t，为角色assistant生成在步骤t+1中应该调用的API请求或对话闲聊。
    当用户没有指定具体的API输出格式时，请遵照以下默认的格式[ApiName(key1='value1', key2='value2', ...)]输出，
    将ApiName替换为实际的API名称，将key1、key2等替换为实际的参数名称，将value1、value2替换为实际参数取值。
    输出应以方括号\"[\"开头，以\"]\"结尾。API请求有多个时以英文逗号隔开，
    比如[ApiName(key1='value1', key2='value2', ...), ApiName(key1='value1', key2='value2', ...), ...]。
    不要在输出中输出任何其他解释或提示或API调用的结果。如果API参数描述未指定取值格式要求，则该参数取值使用用户原文。
    如果不需要输出API，请直接回答用户问题。
    角色说明：
    user: 用户
    assistant: 与用户互动，提供解答和解决方案
    tool：工具执行结果
    API说明：
    {{APIS_DESCRIPTION}}
    """
