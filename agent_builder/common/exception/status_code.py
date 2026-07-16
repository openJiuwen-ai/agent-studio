# 2026/02/24 九问BUG 临时覆盖 新增错误码： 模型能力不足，响应格式错误
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Definition of response status codes"""

from enum import Enum


class StatusCode(Enum):
    """状态码枚举类"""

    SUCCESS = (200, "success")
    INTERNAL_ERROR = (500, "error")

    # example
    ERROR = (-1, "error")

    # 各组件错误码段：
    # 公共           100000~100999
    # 公共   - restFul server 异常 100000 - 100050
    RESOURCE_NOT_FOUND_ERROR = (100000, "Error occur when resource not found")
    PARAM_CHECK_FAILED_ERROR = (
        100002,
        "Error occur when input parameter verification failed",
    )
    STS_DECRYPT_ERROR = (100007, "Sts decrypt data failed!")
    STS_INIT_ERROR = (100009, "Sts init data failed!")
    AUTHENTICATION_ERROR = (10010, "Authentication failed!")

    LOG_MAX_BYTES_ERROR = (
        1000_20,
        "The value of max bytes must be a positive integer. Check the config file.",
    )
    LLM_CONFIG_MISS_ERROR = (
        100021,
        "LLM service configuration information is missing: {error_msg}",
    )
    LLM_FORMAT_ERROR = (100022, "LLM service format field missing error: {error_msg}")
    LLM_RESPONSE_SCHEMA_ERROR = (100023, "LLM service format error: {error_msg}")
    LLM_REQUEST_ERROR = (100025, "Model request error: {error_msg}")
    LLM_LOAD_ERROR = (100026, "Model load error: {error_msg}")
    LLM_TYPE_ERROR = (100027, "Model type error: {error_msg}")
    LLM_RESOLVER_DECODER_ERROR = (100028, "Model resolver decoder error: {error_msg}")
    LLM_RESULT_ERROR = (100029, "Model response error: {error_msg}")

    # 公共    -mysql存储 异常 100700-100799
    MYSQL_CHECK_CONFIG_ERROR = (
        100702,
        "Necessary Mysql configuration items are incorrect. Mysql code: {errno}, reason: {reason}",
    )
    MYSQL_EXECUTION_ERROR = (
        100703,
        "Execute sql command failed. Mysql code: {errno}, reason: {reason}",
    )
    MYSQL_SQL_COMMAND_ERROR = (
        100704,
        "Check sql command failed. root cause = {error_msg}",
    )

    # Prompt引擎     102000~102999
    # Prompt 引擎  - 模板管理 102050 - 102080
    LLM_FALSE_RESULT_ERROR = (
        102003,
        "LLM service returned false result due to: {error_msg}",
    )
    LLM_CONNECTION_ERROR = (102004, "Error connecting llm service: {error_msg}")
    LLM_SERVICE_TYPE_ERROR = (102011, "Unrecognized LLM service type: {error_msg}")
    # Prompt 引擎  - 模板组装 102050 - 102099
    PROMPT_ASSEMBLER_VARIABLE_INIT_ERROR = (
        102050,
        "Wrong arguments for initializing the variable",
    )
    PROMPT_ASSEMBLER_INIT_ERROR = (
        102051,
        "Wrong arguments for initializing the assembler",
    )
    PROMPT_ASSEMBLER_INPUT_KEY_ERROR = (
        102052,
        "Missing or unexpected key-value pairs passed in as arguments for the assembler or variable when updating",
    )
    PROMPT_ASSEMBLER_TEMPLATE_FORMAT_ERROR = (
        102053,
        "Errors occur when formatting the template content due to wrong format",
    )
    # Prompt 引擎  - 模板管理 102100 - 102149
    PROMPT_TEMPLATE_DUPLICATED_ERROR = (102101, "Template duplicated")
    PROMPT_TEMPLATE_NOT_FOUND_ERROR = (
        102102,
        "Template not found, root cause = {error_msg}",
    )
    PROMPT_DATA_INCORRECT_ERROR = (102103, "Template data incorrect")

    # Prompt 引擎  - 模板自优化 102150 - 102199
    PROMPT_TEMPLATE_MUTATE_ERROR = (
        102150,
        "LLM mutate operation failed to generate the same placeholder "
        "as the original template, root cause = {error_msg}.",
    )
    PROMPT_TEMPLATE_CROSSOVER_ERROR = (
        102151,
        "LLM crossover operation failed to generate the same placeholder "
        "as the parent templates, root cause = {error_msg}.",
    )
    PROMPT_TEMPLATE_CASE_PLACEHOLDER_ERROR = (
        102152,
        "Template placeholder in case messages does not match with any rawTemplate.",
    )
    PROMPT_TEMPLATE_CASE_CONTENT_ERROR = (
        102153,
        "Template content in case messages does not match with any rawTemplate.",
    )
    PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR = (
        102154,
        "Prompt optimize params are invalid, root cause = {error_msg}.",
    )
    PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR = (102155, "Prompt optimize job not found.")
    PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED_ERROR = (
        102156,
        "Prompt optimize job status is not expected, root cause = {error_msg}.",
    )
    PROMPT_OPTIMIZE_EVALUATE_ERROR = (
        102157,
        "Prompt optimize evaluate failed, root cause = {error_msg}.",
    )
    PROMPT_OPTIMIZE_START_TASK_ERROR = (
        102158,
        "Prompt optimize task start failed, due to {error_msg}.",
    )
    PROMPT_OPTIMIZE_RESTART_TASK_ERROR = (
        102159,
        "Prompt optimize task restart failed, due to {error_msg}.",
    )
    PROMPT_OPTIMIZE_CASE_CONTENT_ERROR = (
        102160,
        "Prompt optimize task can not get the label from message history",
    )
    PROMPT_OPTIMIZE_CASE_VALIDATION_ERROR = (
        102161,
        "Prompt optimize validate input case failed, root cause = {error_msg}.",
    )
    PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR = (
        102162,
        "Prompt optimize refine instruction failed, root cause = {error_msg}.",
    )
    PROMPT_OPTIMIZE_STORAGE_ERROR = (
        102170,
        "Prompt optimize storage failed, root cause = {error_msg}.",
    )
    # Prompt 引擎  - 模板生成  102200 - 102249
    PROMPT_META_TEMPLATE_NOT_EXIST_ERROR = (102202, "Meta template not exist")
    PROMPT_META_TEMPLATE_TOOL_PARSE_ERROR = (
        102203,
        "Meta template input tool parse failed",
    )
    PROMPT_META_TEMPLATE_BUILD_FAILED_ERROR = (102204, "Meta template build failed")
    PROMPT_META_TEMPLATE_MISSING_KEYS_ERROR = (
        102205,
        "Meta template input missing keys",
    )
    PROMPT_LLM_GENERATION_FAILED_ERROR = (
        102207,
        "Failed to generate the LLM result, root cause = {error_msg}",
    )
    PROMPT_TEMPLATE_EDITOR_ERROR = (102208, "Failed to edit template")
    PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR = (
        102209,
        "Failed to match, root cause = {error_msg}",
    )
    PROMPT_MODULE_INIT_ERROR = (
        102210,
        "Failed to init Prompt config, root cause = {error_msg}",
    )
    PROMPT_OPTIMIZE_FEEDBACK_ERROR = (
        102213,
        "optimize feedback exception, root cause = {error_msg}",
    )
    PROMPT_OPTIMIZE_BAD_CASE_ERROR = (
        102214,
        "optimize badcase exception, root cause = {error_msg}",
    )

    # Nl2Agent -102300 - 102305
    NL2AGENT_MODEL_INFO_INVALID_ERROR = (
        102301,
        "The input parameter modelInfo is invalid, root cause = {error_msg}",
    )
    NL2AGENT_TRANSFORM_IR_TO_EICLOUD_ERROR = (
        102302,
        "Transform simple ir to eicloud DSL failed, root cause = {error_msg}",
    )
    NL2AGENT_PREPROCESS_ERROR = (
        102303,
        "Failed at nl2agent clarification = {error_msg}",
    )
    NL2AGENT_DESIGN_ERROR = (
        102304,
        "Failed to design workflow structure, root cause = {error_msg}",
    )
    NL2AGENT_IR_GENERATION_ERROR = (
        102305,
        "Failed to generate workflow IR, root cause = {error_msg}",
    )
    NL2AGENT_LLM_SERVICE_ERROR = (102306, "LLM service error, root cause = {error_msg}")
    NL2AGENT_WORKFLOW_STATE_ERROR = (
        102307,
        "Worklfow state error, root cause = {error_msg}",
    )
    NL2AGENT_IR_REFLECT_ERROR = (
        102308,
        "Failed to reflect workflow IR, root cause = {error_msg}",
    )
    NL2AGENT_LLM_PARSE_FAILED = (
        102309,
        "Unparseable model response. The output does not conform to the expected schema. root cause = {error_msg}",
    )

    @property
    def code(self):
        """获取状态码"""
        return self.value[0]

    @property
    def errmsg(self):
        """获取状态码信息"""
        return self.value[1]
