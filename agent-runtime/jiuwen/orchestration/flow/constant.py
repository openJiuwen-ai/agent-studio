#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
workflow 框架中常量定义
"""

# 非流式情况下，当bpmn.is_completed()后，向异步队列里传入此信号
BPMN_COMPLETED_MESSAGE = "BPMN EXECUTION IS COMPLETED"

# workflow未获取到执行结果的默认返回信息
DEFAULT_ANSWER = "输出节点未获取到结果，请检查输出参数是否设置正确"

WORKFLOW_UNIFIED_ERROR_INFORMATION = (
    "执行报错，错误码：{}，请参考产品文档解决或联系系统管理员。"
)

WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE = (
    "执行报错，错误码：{}，错误信息：{}，请参考产品文档解决或联系系统管理员。"
)

CHAT_CONVERSATION_FINISHED = "当前会话已超时，请重新开始对话"

# workflow执行时校验
SCHEMA_IN_WRONG_FORMAT = "The schema of {k} is wrong."

SCHEMA_VALIDATION_WRONG_TYPE = "Incorrect type for key: {k}, expected: {t}"

SCHEMA_TYPE_NOT_SUPPORTED = "Type {t} is not supported for key: {k}"

# workflow 的 runtime_context 中 ChatManager对象唯一关键字
WORKFLOW_CHAT_MANAGER = "workflow_chat_manager"

# workflow 的 runtime_context 中执行时请求头对象唯一关键字
WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME = "workflow_execute_requests_headers_name"

# workflow 的 runtime_context 存放 g.project_id
WORKFLOW_EXECUTE_PROJECT_ID = "workflow_execute_project_id"

# workflow 的 runtime_context 存放 g.conversation
WORKFLOW_EXECUTE_CONVERSATION_ID = "workflow_conversation_id"

# workflow 的 runtime_context 存放 g.user
WORKFLOW_EXECUTE_USER_ID = "workflow_user_id"

# workflow 的 runtime_context 存放 cust_headers中的x-invoke-mode参数，用于中断恢复情况下获取调测模式
WORKFLOW_X_INVOKE_MODE = "workflow_x_invoke_mode"

# workflow 的 runtime_context 中 LLM 需要的 额外认证配置 唯一关键字
WORKFLOW_LLM_EXTRA_CONFIGS = "workflow_llm_extra_configs"

# workflow 的 runtime_context 中执行时插件动态配置对象唯一关键字
WORKFLOW_API_CONFIGS = "workflow_api_configs"

# workflow 的 runtime_context 中的全局意图唯一关键字
WORKFLOW_GLOBAL_INTENTS = "workflow_global_intents"

WORKFLOW_GLOBAL_VARIABLES = "workflow_global_variables"

# workflow 的 runtime_context 中内存记忆对象唯一关键字
WORKFLOW_LLM_HISTORY_IN_MEMORY = "workflow_llm_history_in_memory"

# workflow 的 runtime_context 中调试信息对象唯一关键字
WORKFLOW_EXECUTE_DEBUG_INFO = "workflow_execute_debug_info"

# workflow 的 runtime_context 中外部记忆唯一关键字
WORKFLOW_CHAT_HISTORY = "workflow_chat_history"

# runtime_context 中 存储workflow_id与实例map的唯一关键字
WORKFLOW_INSTANCE_DICT = "workflow_instance_dict"

# workflow 的 runtime_context 中流式生成器对象唯一关键字
CUR_STREAM_GENERATOR = "cur_stream_generator"

# workflow 的 runtime_context 中共享线程池
WORKFLOW_THREAD_POOL = "workflow_thread_pool"

# workflow 的 runtime_context 可共享线程锁
WORKFLOW_THREAD_RLOCK = "workflow_thread_rlock"

# workflow runtime_context 中的环境变量
ENVIRONMENT_VARIABLES = "environment_variables"

# workflow runtime_context 中全局变量的变量空间
REQUEST_VARIABLES = "_request"

# workflow runtime_context 中的记忆变量
MEMORY_VARIABLES = "memory_variables"

# workflow runtime_context 中的记忆变量映射关系
MEM_MAP = "mem_map"

MEMORY_MESSAGE = "memory_message"

# workflow runtime_context 中的记忆用户画像开关
ENABLE_MEMORY_RETRIEVE = "enable_memory_retrieve"

# workflow runtime_context 中的userId
USER_ID = "user_id"

# workflow runtime_context 中的appId
APP_ID = "app_id"

# 全局变量引用前缀
REQUEST_PREFIX = "_request."

# 环境变量前缀
ENV_PREFIX = "_env."

# loop节点循环执行的默认次数限制
LOOP_DEFAULT_LOOP_MAX_NUM = 1000
# 单次任务执行最长时间
TASK_EXECUTE_TIMEOUT = 300

# 节点超时时间设置，默认为2小时
DEFAULT_EXECUTION_NODE_TIMEOUT = 7200

# MCP 超时兜底上限，与任务级超时 TASK_EXECUTE_TIMEOUT 对齐
DEFAULT_MCP_TIME_OUT_SECONDS = float(TASK_EXECUTE_TIMEOUT)

# workflow节点循环执行的默认次数限制
WORKFLOW_DEFAULT_LOOP_MAX_NUM = 30
# loop节点循环执行的默认次数限制
LOOP_DEFAULT_LOOP_MAX_NUM = 1000

TASK_EXECUTE_TIMEOUT_ERROR_MESSAGE = (
    "任务执行时长达 {} 秒，任务自动取消。请重新开始对话".format(TASK_EXECUTE_TIMEOUT)
)

# 等待用户输入最长时间，超时则自动取消此次任务
WAIT_FOR_USER_INPUT_TIMEOUT = 300

WAIT_FOR_USER_INPUT_TIMEOUT_ERROR_MESSAGE = (
    "等待输入时长达 {} 秒，对话关闭。请重新开始对话".format(WAIT_FOR_USER_INPUT_TIMEOUT)
)

# 子workflow的关键字
SUB_WORKFLOW_IRS = "sub_workflow_irs"
SUB_WORKFLOW_IR = "sub_workflow_ir"
SUB_WORKFLOW_IDS = "sub_workflow_ids"
WAIT_PANEL_WORKFLOW_TIMEOUT = 30000
WAIT_PANEL_MSG_TIMEOUT = 60000
WAIT_PANEL_WORKFLOW_ERROR_MESSAGE = "等待时长达 {} 秒，panel接收关闭".format(
    WAIT_PANEL_WORKFLOW_TIMEOUT
)
WORKFLOW_STATE = "workflow_state"
WORKFLOW_STATE_RUN = "running"
WORKFLOW_STATE_END = "end"
WORKFLOW_STATE_ERROR = "error"

# 异常处理
EXCEPTION_RETRY_MODEL = "retryModel"
EXCEPTION_EXCEPTION_PROCESS = "exceptionProcess"
EXCEPTION_TIMEOUT = "timeout"
EXCEPTION_RETRY_TIMES = "retryTimes"
EXCEPTION_HANDLE_TYPE = "handleType"
EXCEPTION_DEFAULT_OUTPUTS = "defaultOutputs"
EXCEPTION_HANDLE_INTERRUPT = "interrupt"
EXCEPTION_HANDLE_DEFAULT_OUTPUTS = "defaultOutputs"
EXCEPTION_HANDLE_ERROR_BRANCH = "errorbranch"
EXCEPTION_OUTPUT_RESULT = "result"
EXCEPTION_OUTPUT_IS_SUCCESS = "isSuccess"
EXCEPTION_OUTPUT_ERROR_BODY = "errorBody"
EXCEPTION_OUTPUT_ERROR_MESSAGE = "errorMessage"
EXCEPTION_OUTPUT_ERROR_CODE = "errorCode"
EXCEPTION_OUTPUT_RESULT_FAILED = "1"
EXCEPTION_OUTPUT_RESULT_SUCCESS = "0"

# loop节点常量
CONSTANT_NUM_LOOP_VAR = "numLoopVar"
CONSTANT_ARRAY_LOOP_VAR = "arrLoopVar"
CONSTANT_INTERMEDIATE_LOOP_VAR = "intermediateLoopVar"

CONSTANT_NODE_VARIABLE = "node_variable"

GLOBAL_CONFIG = "global_config"

WORKFLOW_ID = "workflow_id"
"""
工作流实例的唯一标识符。

用于标识和区分不同的工作流实例。
"""
CONVERSATION_ID = "conversation_id"
EXECUTION_ID = "execution_id"
X_EXECUTION_ID = "x-execution-id"
REQUEST_ID = "request_id"
X_REQUEST_ID = "x-request-id"
INVOKE_ID = "invoke_id"
PARENT_INVOKE_ID = "parent_invoke_id"


class ExtractorKeyword:
    """
    Keyword of Extractor
    """

    DEFAULT_SHOT = """用户输入: 我是小明，性别是男
指定参数：[name:姓名, age:年龄, gender:性别]
提取结果：{"name":"小明","age":None,"gender":"男"}
"""

    MODEL_MAP = "model_map"

    MODEL = "model"

    HYPER_PARAMETERS = "hyper_parameters"

    HYPER_PARAMETERS_CANAL = "hyperParameters"

    MODEL_NAME = "model_name"

    MODEL_TYPE = "model_type"

    X_AUTH_TOKEN = "X-Auth-Token"

    QUESTION = "question"
    QUESTION_STATUS = "STATUS"

    LLM_PARSE_FAIL_MESSAGE = (
        "Unavailable to parse llm result with SyntaxError, "
        "or AttributeError, or ValueError."
    )

    LLM_UNKNOWN_ERROR = "Unavailable to parse llm result with Unknown Error."

    NAME = "name"

    DESCRIPTION = "description"

    DESC = "desc"

    ROLE = "role"

    CONTENT = "content"

    QUESTIONKEYWORD = "questionKeyWord"

    TOP_P_KEYWORD = "top_p"

    USER_RESPONSE = "USER_RESPONSE"

    CN_FIELDS_NAME = "cn_fields_name"

    CN_FIELD_NAME = "cn_field_name"

    KEY_FIELDS = "key_fields"

    FIELD_NAME = "field_name"

    CHAT_HISTORY_MAX_ROUNDS = "chat_history_max_rounds"


class QuestionerKeyword:
    """
    Keyword of Questioner
    """

    LLM_QUESTIONER_PROMPT_TEMPLATE = [
        {
            "role": "system",
            "content": "你是一个智能助手，你为用户生成综合质量（有用性，事实性，无害性）极好的回复。",
        },
        {
            "role": "system",
            "content": "请你从目标数据中提取required parameter中指定的变量名称，目标数据未提供或者有歧义（如存在多个）"
            "的变量请保证取值为空''。请注意：不要使用任何工具、不用理会问题的具体含义，并保证你的输出仅有json格式"
            "的结果数据，以保证返回结果可以被json.dump直接解析。你的返回格式格式示例为："
            "{'A':'a', 'B':'', 'C':3}（这里的ABC仅为示例，请根据required parameter中变量"
            "来进行结果输出）",
        },
        {
            "role": "user",
            "content": "目标数据：我是小明，性别是男；required parameter：变量名称：name，"
            "变量描述：名字；变量名称：gender，变量描述：性别，相关样例：女；变量名称：age，变量描述：年龄",
        },
        {"role": "assistant", "content": "{'name':'小明','gender':'男','age':''}"},
        {
            "role": "user",
            "content": "{{current_input}}；required parameter：{{required_param}}",
        },
    ]

    DEFAULT_SHOT = """用户输入: 我是小明，性别是男
指定参数：[name:姓名, age:年龄, gender:性别]
提取结果：{"name":"小明","age":None,"gender":"男"}
"""

    MODEL_MAP = "model_map"

    MODEL = "model"

    HYPER_PARAMETERS = "hyper_parameters"

    HYPER_PARAMETERS_CANAL = "hyperParameters"

    MODEL_NAME = "model_name"

    MODEL_TYPE = "model_type"

    MODEL_SOURCE = "model_source"

    X_AUTH_TOKEN = "X-Auth-Token"

    QUESTION = "question"
    QUESTION_STATUS = "STATUS"

    EXTRACONFIG = "extraConfig"

    RESPONSE_TYPE = "response_type"

    DIRECT_RESPONSE = "direct_response"

    ENABLED = "enabled"

    TASK = "Task"

    ASKUSER_PROMPT_EXIST_MESSAGE = "askuser prompt already exists"

    LLM_PARSE_FAIL_MESSAGE = (
        "Unavailable to parse llm result with SyntaxError, "
        "or AttributeError, or ValueError."
    )

    LLM_UNKNOWN_ERROR = "Unavailable to parse llm result with Unknown Error."

    FAIL_TIME_PARSE_MESSAGE = (
        "Unavailable to perform time parsing with UnboundLocalError"
    )

    FAIL_CUSTOM_INPUT_RAILS_PARSE_MESSAGE = "Unavailable to perform custom inputs rails"

    FAIL_TIME_PARSE_MESSAGE_UNKNOWN = (
        "Unavailable to perform time parsing with Unknown Error"
    )

    FAIL_CUSTOM_EXECUTION_RAILS_PARSE_MESSAGE = (
        "Unavailable to perform custom execution rails"
    )

    FAIL_RAILS_PATH_INITIALIZATION_ERROR = (
        "Failed to initialize the rail. The rail content is configured "
        "but the rail path is not configured."
    )

    NAME = "name"

    CURRENT_INPUT = "current_input"

    TARGET_DATA = "目标数据："

    REQUIRED_PARAM = "required_param"

    SEMICOLON = "；"

    COMMA = ", "

    PARAM_NAME = "变量名称："

    PARAM_DESCRIPTION = "，变量描述："

    DESCRIPTION = "description"

    DESCRIPTIONS = "descriptions"

    DESC = "desc"

    ROLE = "role"

    CONTENT = "content"

    RESPONSE_ILLEGAL_MESSAGE = "the response type is illegal"

    SYSTEM_QUERY_TEMPLATE = "请您提供{data}相关的信息"

    TARGET_RESULT_TEMPLATE = "系统问题 - {question} 用户回答 - {response}"

    CASE = "case"

    RELATIVE_CASE = "，相关样例："

    QUESTIONKEYWORD = "questionKeyWord"

    TEMPERATURE_KEYWORD = "temperature"

    TOP_P_KEYWORD = "top_p"

    UNDERLINE = "_"

    VALUE = "value"

    USER = "user"

    ASSISTANT = "assistant"

    USER_RESPONSE = "USER_RESPONSE"

    TEMPLATE_CONTENT = "templateContent"

    CN_FIELDS_NAME = "cn_fields_name"

    CN_FIELD_NAME = "cn_field_name"

    KEY_FIELDS = "key_fields"

    FIELD_NAME = "field_name"

    CHAT_HISTORY_MAX_ROUNDS = "chat_history_max_rounds"

    TYPE_COMPLEMENT_MAP = {
        "YYYY-MM-DD HH:MM": "%Y-%m-%d %H:%M",
        "YYYY-MM-DD HH": "%Y-%m-%d %H",
        "YYYY-MM-DD": "%Y-%m-%d",
        "YYYY-MM": "%Y-%m",
        "YYYY": "%Y",
    }

    CHAT_HISTORY_MAX_ROUNDS_NUMBER = 5

    MAX_RESPONSE_NUMBER = 10

    TEMPERATURE = 0.2

    TOP_P = 0.15


INIT_WORKFLOW = {
    "id": "",
    "name": "",
    "description": "",
    "components": [
        {
            "id": "node_start",
            "type": "Start",
            "name": "开始",
            "outputs": [{"description": "用户输入", "name": "query", "type": "String"}],
        },
        {
            "id": "node_default_llm_chain",
            "type": "LLM",
            "name": "大模型",
            "inputs": [
                {"name": "query", "type": "ref", "value": "${node_start.query}"}
            ],
            "outputs": [
                {"description": "该节点原始输出", "name": "rawOutput", "type": "String"}
            ],
            "configs": [
                {
                    "name": "prompt",
                    "type": "prompt",
                    "value": {"history": True, "template": "{{query}}"},
                },
                {
                    "name": "llm",
                    "type": "llm",
                    "value": {
                        "config": {
                            "model": "",
                            "temperature": 0.5,
                            "top_p": 0.5,
                        },
                        "name": "",
                    },
                },
            ],
        },
        {
            "id": "node_end",
            "type": "End",
            "name": "结束",
            "inputs": [
                {
                    "name": "end_input",
                    "type": "ref",
                    "value": "${node_default_llm_chain.rawOutput}",
                }
            ],
            "outputs": [
                {"name": "output", "type": "String", "description": "最终输出"}
            ],
            "configs": [
                {"name": "template", "type": "String", "value": "{{end_input}}"}
            ],
        },
    ],
    "connections": [
        {"source": "node_start", "target": "node_default_llm_chain"},
        {"source": "node_default_llm_chain", "target": "node_end"},
    ],
    "metadata": {
        "layout": {
            "node_start": {"x": 130, "y": 440},
            "node_default_llm_chain": {"x": 510, "y": 440},
            "node_end": {"x": 910, "y": 440},
        }
    },
}

# IR userFields key
USER_FIELDS = "userFields"
# IR systemFields key
SYSTEM_FIELDS = "systemFields"
# bpmn 变量池key值变量分隔符
BPMN_VARIABLE_POOL_SEPARATOR = "."

# IR schema key
SCHEMA = "schema"

# IR schema structure position
STRUCTURE_POSITION_INPUTS = "inputs"
STRUCTURE_POSITION_OUTPUTS = "outputs"

# IR schema types
STRING = "string"
INTEGER = "integer"
NUMBER = "number"
BOOLEAN = "boolean"
OBJECT = "object"
ARRAY = "array"

# IR err ignore
EXCEPTIONENABLE = "exceptionEnable"
EXCEPTIONSUPPRESSION = "exceptionSuppression"

ERROR = "error"

SIMPLE_TYPE_DICT = {STRING: str, INTEGER: int, NUMBER: float, BOOLEAN: bool}

TYPE_DEFAULT_VALUE_DICT = {
    STRING: "",
    INTEGER: None,
    NUMBER: None,
    BOOLEAN: None,
    ARRAY: None,
    OBJECT: None,
    ERROR: None,
}

# custom component
BUILT_IN_COMPONENT_PREFIX = "jiuwen."
# maximum length of a regular match string, to prevent ReDos attacks.
MAXIMUM_LENGTH_OF_A_REGULAR_STRING = 1000
