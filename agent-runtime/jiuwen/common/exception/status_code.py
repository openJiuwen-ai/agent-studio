#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Definition of response status codes"""

from enum import Enum

from jiuwen.common.language import Language

_OVERWRITE_STATUS_CODE: dict = {}


class StatusCode(Enum):
    """状态码枚举类"""

    # example
    SUCCESS = (0, "success")
    ERROR = (-1, "error")
    REQUEST_TIMEOUT = (408, "request timeout")

    # 各组件错误码段：
    # 公共           100000~100999
    # 公共   - restFul server 异常 100000 - 100050
    RESOURCE_NOT_FOUND_ERROR = (100000, "Error occur when resource not found")
    AUTH_CHECK_FAILED_ERROR = (100001, "Error occur when authentication failed")
    PARAM_CHECK_FAILED_ERROR = (
        100002,
        "Error occur when input parameter verification failed",
    )
    SDK_REQUEST_ERROR = (100003, "Error occur when request sdk failed")
    ENCRYPT_ERROR = (100004, "Error occur when calling default encrypt method")
    DECRYPT_ERROR = (100005, "Error occur when calling default decrypt method")
    CRYPT_INIT_ERROR = (100006, "Encryption and decryption initialization failed")
    FUNCTION_RESERVED_ERROR = (
        100007,
        "This interface is reserved. This method cannot be invoked currently.",
    )

    CONNECTION_NO_AVAILABLE_SERVER = (1000_10, "No available connection server.")
    CONNECTION_SEND_TO_CLOSED = (
        1000_11,
        "Try to send function {name!r} by a closed connection {sdk_id!r}",
    )
    CONNECTION_NOT_EXIST = (
        1000_12,
        "Query for a connection (sdk_id={sdk}) which has not already bound to {server}.",
    )
    CONNECTION_WRONG_SSL_TYPE = (
        1000_13,
        "Invalid type {typename!r} of parameter ssl_context. Expected type is 'ssl.SSLContext'"
        " or 'jiuwen.serve.common.ssl_ctx.ContexConfigDict'.",
    )
    CONNECTION_INIT_FAILED = (
        1000_14,
        "Failed to start the persistent connection server ({key}).",
    )
    CONNECTION_WS_WRONG_PORT = (
        1000_15,
        "Try to start websocket server with wrong type of port. Expected int, got {typename}.",
    )
    CONNECTION_WS_WRONG_HOST = (
        1000_16,
        "Try to start websocket server with wrong type of host. Expected str or None, got {typename}.",
    )
    CONNECTION_WS_VALIDATE_FAIL = (
        1000_17,
        "New connection on {server} excepted to get echo {sdk_id!r} but got {echo!r}",
    )
    CONNECTION_SSL_CONTEXT_REQUIRED = (
        1000_18,
        "Connection mode '{mode}' requires a ssl_context. Please provide an instance of 'ssl.SSLContext'"
        " or 'jiuwen.serve.common.ssl_ctx.ContexConfigDict'.",
    )

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
    LLM_MODEL_SOURCE_ERROR = (100024, "LLM Model source error: {error_msg}")
    LLM_REQUEST_ERROR = (100025, "Model request error: {error_msg}")
    LLM_LOAD_ERROR = (100026, "Model load error: {error_msg}")
    LLM_TYPE_ERROR = (100027, "Model type error: {error_msg}")
    LLM_RESOLVER_DECODER_ERROR = (100028, "Model resolver decoder error: {error_msg}")
    LLM_AGENT_IR_VALIDATE_ERROR = (100029, "Agent ir field validate error: {error_msg}")

    # 公共 StateManager 关联异常 100040 - 100050
    IR_DATA_VALIDATION_ERROR = (100040, "IR data validation failed.")
    INVALID_STATE_STORAGE_MEDIUM_ERROR = (
        100041,
        "Invalid state storage medium value. Use 'redis' or 'memory'",
    )
    IR_VERSION_NOT_SUPPORTED = (100042, "IR version is currently not supported.")
    IR_VERSION_INCORRECTLY_CONFIGURED = (
        100043,
        "The value of EXECUTION_SUPPORTED_IR_VERSIONS is incorrectly configured. "
        "Please check your configuration or environment variables.",
    )
    IR_DATA_JSON_LOAD_FAILED = (100044, "Failed to load ir data from json")
    INVALID_EXECUTION_ID = (
        100045,
        "This key: {} does not exist in the state storage medium",
    )

    # 公共    -数据库相关异常  100051 - 100060
    DATABASE_CONNECTION_ERROR = (100051, "database connection error")
    DATABASE_EXECUTE_ERROR = (100052, "database execute error")

    # 公共  -序列化相关异常 100061 - 100065
    SERIALIZATION_ERROR = (
        100061,
        "Serialization error, please check the logs for details",
    )
    DESERIALIZATION_ERROR = (
        100062,
        "Deserialization error, please check the logs for details",
    )

    # 公共 -request相关异常 100066 - 100070
    REQUEST_GET_METHOD_ERROR = (
        100066,
        "The request get method error, reason: {reason}",
    )

    # 公共    -redis存储 异常 100100 - 100200
    REDIS_SERVICE_NOT_FOUND = (
        100100,
        "The Redis service does not exist or the connection is abnormal.",
    )
    REDIS_SERVICE_INIT_FAILED = (
        100115,
        "An error occurred during Redis connection initialization.",
    )
    REDIS_INSERT_ELEMENTS_FAILED = (
        100102,
        "An error occurs when the Redis inserts elements.",
    )
    REDIS_APPEND_ELEMENTS_FAILED = (
        100103,
        "Failed to insert an element to the end of the Redis list.",
    )
    REDIS_REMOVE_ELEMENTS_FAILED = (
        100104,
        "failed to remove an element from the redis list.",
    )
    REDIS_SET_SPECIFIED_ELEMENTS_FAILED = (
        100105,
        "Failed to set the value of the specified position in the Redis list.",
    )
    REDIS_GET_LIST_ELEMENTS_FAILED = (
        100106,
        "Failed to obtain a value in the Redis list.",
    )
    REDIS_POP_ELEMENTS_FAILED = (100107, "Failed to eject the element from the list.")
    REDIS_GET_LENGTH_ELEMENTS_FAILED = (100108, "Failed to obtain the list length.")
    REDIS_GET_HISTORY_FAILED = (100109, "Failed to get the history from redis")
    REDIS_SET_HISTORY_FAILED = (100110, "Failed to set the history to redis")
    REDIS_GET_ELEMENT_FAILED = (100110, "Failed to get the element from redis")
    REDIS_SET_ELEMENT_FAILED = (100111, "Failed to set the element to redis")
    REDIS_DELETE_ELEMENT_FAILED = (100112, "Failed to delete the element from redis")
    REDIS_CLUSTER_NODES_CONFIGURATION_ERROR = (
        100113,
        "The cluster_node configuration of redis must be <IP:PORT,IP:PORT>, please check your configuration",
    )
    REDIS_CLUSTER_NODES_GET_ERROR = (
        100114,
        "Failed to get cluster nodes list from redis.",
    )

    # 公共    -elastic search 异常 100201 - 100299
    ES_SERVICE_INIT_FAILED = (
        100201,
        "An error occurred during Elastic Search client initialization.",
    )

    # 公共    -embedding service 异常 100300 - 100310
    EMBEDDING_SERVICE_REQUEST_FAILED = (100300, "Failed to request embedding service.")

    # 公共    -tokenizer 异常 100311 - 100320
    TOKENIZER_GET_INSTANCE_ERROR = (
        100311,
        "JiebaTokenizerPool is not initialized. Please initialize JiebaTokenizerPool first.",
    )

    # 公共    -obs存储 异常 100500-100599
    OBS_CHECK_CONFIG_ERROR = (
        100502,
        "Necessary OBS configuration items are incorrect.",
    )
    OBS_CHECK_BUCKET_ERROR = (100503, "Head Bucket Failed.")
    OBS_PUT_CONTENT_ERROR = (100504, "Status Code {}. Failed to upload file.")
    OBS_GET_OBJECT_ERROR = (100505, "Get Object:{} in bucket:{} Failed")
    OBS_COPY_OBJECT_ERROR = (100506, "Copy Object:{} in bucket:{} Failed")
    OBS_DELETE_OBJECT_ERROR = (100507, "Delete Object:{} in bucket:{} Failed.")

    # 编排引擎        101000~101999
    # > 编排引擎静态编排
    DSL_PARAM_TYPE_ERROR = (
        101001,
        "Parameter action_map should be a dict type, not a '{}'",
    )
    DSL_INVALID_WRAP_CLS_USAGE_MODE = (
        101002,
        "Cannot specify 'wrap_cls' while using async_fn",
    )
    DSL_ASYNC_FUNCTION_ERROR = (101003, "The 'async_fn' only allows async function.")
    DSL_ILLEGAL_WRAP_CLS_TYPE = (
        101004,
        "Param 'wrap_cls' only allows a subclass of Invokable, not {}",
    )
    DSL_UNSUPPORTED_KEYWORD_ERROR = (
        101005,
        "The @invokable does not support necessary keyword parameter in __init__",
    )
    ENV_VARIABLE_TGF_ENABLE_VALUE_ERROR = (
        101006,
        "'TGF_ENABLE' in environ should be either 'true' or 'false'",
    )
    INVOKABLE_NOT_FOUND = (
        101007,
        "Invokable named {name!r} of {owner} not found in {ref!r}",
    )
    VALUE_NOT_FOUND = (101008, "Value named '{}' does not found in {}")
    IR_JSON_ILLEGAL = (101009, "Illegal orchestration IR json")
    IRS_TYPE_ILLEGAL = (
        101010,
        "The 'invokable_irs' should be a list of str (json format)",
    )
    INVOKABLE_IR_JSON_ILLEGAL = (
        101011,
        "Illegal Invokable IR json at index={index}: {detail}",
    )
    SYSTEM_CONFIGS_TYPE_ERROR = (
        101012,
        "The 'system_configs' is required as a list but got {}",
    )
    ID_AND_VERSION_MISSING = (
        101013,
        "Attributes <agentId> and <version> are needed for each agent to be deleted",
    )
    UNSUPPORTED_EXECUTOR_CODE = (
        101014,
        "Streaming callback of IrManager got an unsupported status code {}",
    )
    UNKNOWN_STREAM_CODE = (101015, "Unknown status code {}")
    IR_UNREGISTER_ERROR = (101016, "Failed to unregister {} with code=<{}>{}")
    IR_RUN_ERROR = (101017, "Failed to run <{}> with code=<{}>{}")
    IR_USERINPUT_SEND_FAILED = (
        101018,
        "Failed to send user input of session_id={} with code=<{}>{}",
    )
    IR_REGISTER_ERROR = (101019, "Failed to register <{}> with code=<{}>{}")
    IR_UPDATE_ERROR = (101020, "Failed to update <{}> with code=<{}>{}")
    IR_MANAGER_NAME_ERROR = (101021, "No available IR manager named {}")
    INVOKABLE_MANAGER_NAME_ERROR = (101022, "No available Invokable manager named {}")
    INVOKABLE_JSON_ILLEGAL = (101023, "Illegal Invokable json")
    INVOKABLE_REGISTER_PATH_TYPE_ERROR = (
        101024,
        "Register from directory of Invokable manager only accepts str, but got {}",
    )
    INVOKABLE_REGISTER_PATH_ILLEGAL = (
        101025,
        "Failed to register Invokable from the directory: The specified path is not a directory",
    )
    INVOKABLE_REGISTER_FROM_DIR_FAILED = (
        101026,
        "Register Invokable from directory failed, interrupted with an {}:{}",
    )
    REGISTER_TO_PLUGIN_MANAGER_FAILED = (
        101027,
        "{} Invokable to PluginManager {} (code={}): {} and {}",
    )
    OPERATOR_INVOKABLE_FAILED = (101028, "{} invokable failed with code={}: {}")
    HTTP_CONTENT_TYPE_ERROR = (
        101029,
        "The 'contentType' set to {} but got {} in user's inputs. "
        "Please set Content-Type to {}, or using param {} instead",
    )
    ORCHESTRATION_UNEXPECTED_ERROR = (101030, "Unexpected error")
    EXECUTOR_MGR_CONFIGS_MISSING = (
        101034,
        "Please provide {} (can be loaded from 'application.yaml') for Invokable management.",
    )
    EXECUTOR_WORKER_CONFIGS_MISSING = (
        101035,
        "Please provide {} (can be loaded from 'application.yaml') for AgentIR management.",
    )
    MODEL_NAME_ERROR = (101036, "Model class of {} not found.")
    IR_MANAGER_NOTIFY_SESSION_ERROR = (
        101037,
        "Failed to notify the session (session_id={session_id!r}) with code=<{code}>: {resp_msg}",
    )
    COMPONENT_STEP_DEBUG_ERROR = (101052, "The component step debug error,{reason}")
    COMPONENT_TYPE_ERROR = (
        101053,
        "The type of component does not support step debugging",
    )
    COMPONENT_IR_ILLEGAL = (101054, "The single component IR is illegal, {reason} ")
    COMPONENT_END_INVOKE_INPUTS_ERROR = (
        101055,
        "The 'userFields' of inputs except dict(), but got {}",
    )
    COMPONENT_RUNTIME_INPUTS_VALIDATE_FAILED = (
        101056,
        "Validate inputs for {comp} failed, {reason}",
    )
    COMPONENT_INIT_INPUTS_OUTPUTS_VALIDATE_FAILED = (
        101057,
        "Check {comp} inputs outputs failed, the field {key} of outputs should be the same as that of inputs",
    )
    COMPONENT_CONTEXT_TYPE_ERROR = (
        101058,
        "Global item already exists and it is not a dict.",
    )
    COMPONENT_INIT_CONFIG_LOAD_FAILED = (
        101099,
        "Loading configs for {comp} failed, {reason}",
    )
    COMPONENT_END_CONSTANT_NO_EXIST = (
        101100,
        "This field defined by 'userFields' in 'configs' do not exist in 'inputs': {}",
    )

    # > 编排引擎动态编排
    TASK_PLUGIN_TYPE_ERROR = (
        101101,
        "The functions of plugin {} should be a list/tuple/set of str but got {}",
    )
    TASK_PLUGIN_OPERATE_ERROR = (101102, "{} failed (code={}) with error message: {}")
    TASK_UPDATE_PLUGIN_WITH_TYPE_ERROR = (
        101103,
        "Please input list of RestFulApi or Function. not {}",
    )
    TASK_PARAM_FIELD_NAME_ERROR = (101104, "Found wrong field name: {}")
    TASK_PLAN_CONFIG_INTI_FAILED = (101105, "Plan config init failed")
    TASK_MODEL_INIT_FAILED = (101106, "Model init failed")
    TASK_PLUGIN_INIT_FAILED = (101107, "Plugin init failed")

    # > 编排引擎 Invokable/IrManager 关联异常 101200 - 101299
    ORCHESTRATION_VALIDATION_FAILED = (
        101_2_00,
        "{len} validation error{s} for {model}:{description}",
    )
    INVOKABLE_JSON_ROOT_TYPE_ERR = (
        101_2_01,
        "Component JSON can only be a component list or a single component (root type is list or dict), got {type}.",
    )
    IR_SUBGRAPH_FAILED = (
        101_2_60,
        "Failed to {op} sub Agent IR (id={id!r}, version={ver!r}) of root Agent IR (id={root_id!r}, version={root_v!r})"
        " (succeeded {success} sub Agent IR of {all}) with {type}: {e}",
    )
    IR_SUBGRAPH_FAILED_ROOT = (
        101_2_61,
        "Failed to {op} root Agent IR (id={id!r}, version={ver!r})"
        " (all {all} sub Agent IR succeeded) with {type}: {e}",
    )
    IR_COMPOSITE_NO_REFERENCE = (
        101_2_85,
        "Both AgentIR builder and Optional IR are missing in composite Invokable {type!r} of id {id!r}.",
    )
    IR_COMPOSITE_BUILDER_NOT_FOUND = (
        101_2_86,
        "AgentIR builder for composite Invokable {type!r} not found: {e}",
    )
    IR_COMPOSITE_BUILDER_IMPORT_FAILED = (
        101_2_87,
        "AgentIR builder {spec!r} for composite Invokable {type!r} import failed with {err}: {msg}",
    )
    IR_COMPOSITE_BUILDER_TYPEERROR = (
        101_2_88,
        "AgentIR builder {spec!r} for composite Invokable {type!r} is not an IR builder.",
    )
    IR_COMPOSITE_BUILDER_FAILED = (
        101_2_89,
        "AgentIR builder {spec!r} for composite Invokable {type!r} build {id!r} failed with {type_err}: {msg}",
    )
    MGR_FAILED_BY_INTERNAL = (
        101_2_90,
        "{op} failed because of builtin Invokable register failed with {t}: {msg}",
    )

    # > 编排引擎Workflow异常101500-101999
    # 【已定义的异常码除外】，新增的异常统一使用101500-101999之间的号码，每个组件划分30个，预留100个，通用报错划分100个
    # start组件 101500-101530
    WORKFLOW_START_MISSING_GLOBAL_VARIABLE_VALUE = (
        101501,
        "Start component: global variable(s) defined with no value assigned: {variable_names}",
    )

    # end组件 101531-101560
    WORKFLOW_END_INIT_ERROR = (101531, "End component init error. msg={msg}")
    WORKFLOW_END_TEMPLATE_ASSEMBLE_ERROR = (
        101532,
        "End component template assemble error",
    )
    WORKFLOW_END_STREAM_ERROR = (
        101533,
        "End component internal error: failed to process stream data",
    )

    # llm组件 101561-101590
    WORKFLOW_LLM_INIT_ERROR = (101561, "LLM component init error. msg={msg}")
    WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR = (
        101562,
        "LLM component template assemble error",
    )
    WORKFLOW_LLM_STREAMING_OUTPUT_ERROR = (
        101563,
        "Get model streaming output error, msg={msg}",
    )

    # code组件 101591-101620
    WORKFLOW_CODE_INIT_ERROR = (101591, "Code component init error. msg={msg}")
    WORKFLOW_CODE_SANDBOX_REQUEST_ERROR = (
        101592,
        "Code component sandbox request error",
    )
    WORKFLOW_CODE_SANDBOX_EXECUTE_ERROR = (
        101593,
        "Code component sandbox execute error. sandbox_code={sandbox_code}, sandbox_msg={sandbox_msg}",
    )
    WORKFLOW_CODE_SANDBOX_UNEXPECTED_ERROR = (
        101594,
        "Code component sandbox unexpected error",
    )
    WORKFLOW_CODE_INVOKE_UNEXPECTED_ERROR = (
        101595,
        "{error_msg} component execute error, error message={error_msg}",
    )

    # branch组件 101621-101650
    WORKFLOW_BRANCH_SYNTAX_ERROR = (101621, "Syntax error in expression")
    WORKFLOW_BRANCH_EVALUATE_ERROR = (
        101622,
        "Error evaluating expression: expression={expression}",
    )
    WORKFLOW_BRANCH_EXPRESSION_ERROR = (
        101623,
        "Expression contains illegal characters",
    )
    EXPRESSION_CONDITION_EVAL_ERROR = (
        101624,
        "Expression condition eval error, as {error_msg}",
    )

    # message组件 101651-101680
    WORKFLOW_MESSAGE_INIT_ERROR = (101651, "Message component init error. msg={msg}")
    WORKFLOW_MESSAGE_TEMPLATE_NOT_FOUND_ERROR = (
        101652,
        "Message component message template is needed",
    )
    WORKFLOW_MESSAGE_TEMPLATE_ASSEMBLE_ERROR = (
        101653,
        "Message component template assemble error",
    )
    WORKFLOW_MESSAGE_INVOKE_UNEXPECTED_ERROR = (
        101654,
        "Message component invoke unexpected error",
    )
    WORKFLOW_MESSAGE_AINVOKE_UNEXPECTED_ERROR = (
        101655,
        "Message component ainvoke unexpected error",
    )

    # intent detection组件 101681-101710
    WORKFLOW_INTENT_DETECTION_LLM_INIT_ERROR = (
        101681,
        "Intent detection component init llm error. msg={msg}",
    )
    WORKFLOW_INTENT_DETECTION_OUTPUT_ERROR = (
        101093,
        "Intent detection output has error with error message={error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_PROMPT_TEMPLATE_ERROR = (
        101094,
        "Prompt template create failed with error message={error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR = (
        101095,
        "User inputs pre-process failed with error message={error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR = (
        101096,
        "Model invoke failed with error message={error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_MODEL_INPUT_ERROR = (
        101097,
        "Model input switch message failed with error message={error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_PROMPT_INVOKE_ERROR = (
        101098,
        "Prompt invoke failed with error message={error_msg}",
    )
    WORKFLOW_INTENT_DETECTION_KG_ERROR = (
        101098,
        "Emmbedding Search failed with error message={error_msg}",
    )

    # questioner组件 101711-101740
    WORKFLOW_QUESTIONER_INVALID_RESPONSE = (101042, "Invalid response type")
    WORKFLOW_QUESTIONER_EXCEED_LOOP = (
        101043,
        "Exceeded the maximum number of conversation",
    )
    WORKFLOW_QUESTIONER_INVALID_QUESTION_METHOD = (
        101044,
        "Invalid question construction method.",
    )
    WORKFLOW_QUESTIONER_QUESTION_EMPTY_DIRECT_COLLECTION = (
        101045,
        "The question content cannot be empty in direct user response collection mode",
    )
    WORKFLOW_INITIAL_RAILS_ERROR = (101047, "Failed to initial the rails.")
    WORKFLOW_INPUT_RAILS_ERROR = (101048, "Failed to run the custom input rails.")
    WORKFLOW_EXECUTION_CUSTOM_RAILS_ERROR = (
        101049,
        "Failed to run the custom execution rails.",
    )
    WORKFLOW_EXECUTION_DEFAULT_RAILS_ERROR = (
        101050,
        "Failed to run the default execution rails.",
    )
    WORKFLOW_QUESTIONER_REFLECTION_ERROR = (
        101059,
        "Failed to perform reflection in questioner.",
    )

    # api组件 101741-101770
    WORKFLOW_API_INIT_ERROR = (101741, "Api component init error. msg={msg}")
    WORKFLOW_API_PARAMS_CHECK_ERROR = (
        101742,
        "Plugin flow components params check error",
    )
    WORKFLOW_API_INPUTS_ERROR = (101743, "Plugin flow components input not defined")
    WORKFLOW_API_OUTPUTS_ERROR = (101744, "Plugin flow components output is error")
    WORKFLOW_API_EXECUTE_ERROR = (101745, "Plugin flow components execute error")

    # planner组件 101771-101800
    WORKFLOW_PLANNER_TYPE_ERROR = (101041, "Planner type is invalid.")

    # 子workflow组件 101801 - 101810
    SUB_WORKFLOW_CONSTRUCTION_ERROR = (
        101801,
        "Failed to construct sub workflow, workflow name: {workflow_name}, "
        "workflow id: {workflow_id} based on IR, check if the sub workflow exists",
    )
    SUB_WORKFLOW_INIT_ERROR = (101802, "Sub workflow: {workflow_id} init error")
    SUB_WORKFLOW_CONFIGURATION_VALIDATION_FAILURE = (
        101803,
        "Sub workflow component configuration validation failure, msg={msg}",
    )
    SUB_WORKFLOW_EXECUTION_ERROR = (
        101804,
        "Sub workflow execution error, internal error msg={msg}",
    )
    SUB_WORKFLOW_INVALID_ID_ERROR = (
        101805,
        "The workflow_id of sub workflow: {sub_workflow_id} cannot be the same as parent workflow",
    )

    # 预留组件码 101811-101900
    # loop 组件
    WORKFLOW_LOOP_UNSUPPORTED_TYPE_ERROR = (
        101811,
        "Unsupported loop type: {loop_type}.",
    )
    WORKFLOW_LOOP_FIELD_EMPTY_TYPE_ERROR = (
        101812,
        "Field {field} should not be empty in {loop_type}.",
    )
    WORKFLOW_LOOP_FIELD_TYPE_ERROR = (
        101813,
        "Field '{field}' has an incorrect type '{type}' in {loop_type} loop.",
    )

    # aggregate组件
    WORKFLOW_AGGREGATE_TYPE_ERROR = (101831, "Type of group values should be the same.")
    WORKFLOW_AGGREGATE_STRATEGY_ERROR = (
        101832,
        "Unsupported aggregate strategy {agg_strategy}",
    )

    # input 组件
    WORKFLOW_INPUT_FIELD_EMPTY_ERROR = (101850, "Field {field} should not be empty.")

    WORKFLOW_LOOP_NUM_ERROR = (
        101862,
        "Invalid loop num {loop_num}, should in [1, 1000].",
    )

    # MCP 组件
    WORKFLOW_MCP_UNSUPPORTED_TYPE_ERROR = (101870, "Unsupported mcp type: {mcp_type}.")
    WORKFLOW_MCP_FIELD_EMPTY_TYPE_ERROR = (
        101872,
        "Field {field} should not be empty in {mcp_type}.",
    )
    WORKFLOW_MCP_EXECUTE_ERROR = (101873, "Mcp execute error, reason is {error}.")
    WORKFLOW_MCP_PARAM_METHOD_ERROR = (101874, "Unsupported mcp type: {method}.")
    WORKFLOW_MCP_PARAM_TYPE_ERROR = (
        101875,
        "Invalid mcp argument param type for {param}, expect type is {type}.",
    )

    # card组件
    WORKFLOW_CARD_INIT_ERROR = (101890, "Card component init error. msg={msg}")
    WORKFLOW_CARD_TEMPLATE_NOT_FOUND_ERROR = (
        101891,
        "Card component Card template is needed",
    )
    WORKFLOW_CARD_TEMPLATE_ASSEMBLE_ERROR = (
        101892,
        "Card component template assemble error",
    )
    WORKFLOW_CARD_INVOKE_UNEXPECTED_ERROR = (
        101893,
        "Card component invoke unexpected error",
    )
    WORKFLOW_CARD_AINVOKE_UNEXPECTED_ERROR = (
        101894,
        "Card component ainvoke unexpected error",
    )

    # workflow综合报错 101901-101999
    WORKFLOW_RUN_FAILED = (
        101032,
        "Invalid workflow definition, subsequent nodes cannot be access",
    )
    WORKFLOW_COMPONENT_EXECUTE_ERROR = (
        101039,
        "{} component execute error, error message={}",
    )
    WORKFLOW_EXECUTE_ERROR = (101040, "An error occurred during workflow execution: {}")
    WORKFLOW_LOOP_OUT_OF_LIMIT_ERROR = (
        101046,
        "The number of workflow cyclic execution times exceeds the limit.",
    )

    WORKFLOW_COLLECT_ON_INVOKE_EXCEPTION_CALLBACK_INFO_ERROR = (
        101051,
        "The workflow failed to collect exception info when the callback occurred.",
    )
    WORKFLOW_COLLECT_ON_INVOKE_CALLBACK_INFO_ERROR = (
        101052,
        "The workflow failed to collect on invoke info when the callback occurred.",
    )
    WORKFLOW_COLLECT_PRE_CALLBACK_INFO_ERROR = (
        101053,
        "The workflow failed to collect pre info when the callback occurred.",
    )
    WORKFLOW_COLLECT_POST_CALLBACK_INFO_ERROR = (
        101054,
        "The workflow failed to collect post info when the callback occurred.",
    )
    WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION = (
        101057,
        "The workflow failed to clear resources after execution",
    )
    WORKFLOW_INITIAL_CONFIG_ERROR = (
        101058,
        "Failed to initial the config. The error reason = {error_msg}",
    )
    WORKFLOW_COMPONENT_INIT_FAILED = (
        101901,
        "Loading configs for {comp} failed, {reason}",
    )
    WORKFLOW_IR_VALIDATION_ERROR = (
        101902,
        "An error occurred during workflow ir validation, details: {reason}",
    )
    WORKFLOW_INVALID_ID_ERROR = (
        101903,
        "Only numbers, letters, and underscores are allowed in the id",
    )
    WORKFLOW_INIT_WRONG_TYPE_ERROR = (
        101904,
        "Incorrect data type for workflow init. Either ir or workflow_state must be provided",
    )
    WORKFLOW_COMPONENT_EXECUTE_TIMEOUT = (
        101905,
        "Task {task_label} has exceeded the allowed timeout of {timeout} second(s), and has been canceled",
    )

    WORKFLOW_INITIALIZATION_ERROR = (
        101906,
        "The workflow failed to initialize, {reason}",
    )
    WORKFLOW_TERMINATION_OF_EXECUTION = (101907, "Execution {exec_id} is terminated")

    WORKFLOW_REACH_MAX_ITERATION = (
        101908,
        "Task {task_id} reached max iterations {max_iteration}",
    )

    # workflow异步执行报错 101911-101930
    WORKFLOW_ASYNC_EXECUTION_CONFLICT = (
        101911,
        "Workflow async execution conflict, reason={reason}",
    )
    WORKFLOW_ASYNC_GET_RESULT_ERROR = (
        101912,
        "Workflow get execution result failed, reason={reason}",
    )
    WORKFLOW_ASYNC_CANCEL_TASK_ERROR = (
        101913,
        "Cancel task {task_id} failed, reason={reason}",
    )

    WORKFLOW_ASYNC_CELERY_BROKER_INIT_ERROR = (
        101914,
        "Celery broker init failed, reason={reason}",
    )

    WORKFLOW_ASYNC_APS_WORKER_REGISTER_ERROR = (
        101920,
        "ApsWorker register failed, reason={reason}",
    )
    WORKFLOW_ASYNC_REDIS_LISTENER_ERROR = (
        101921,
        "ApsWorker redis listener error, reason={reason}",
    )
    WORKFLOW_ASYNC_GET_LOCAL_HOST_NAME_ERROR = (
        101922,
        "ApsWorker get local host name error, reason={reason}",
    )
    WORKFLOW_ASYNC_EXECUTION_WORKER_ID_ERROR = (
        101923,
        "ApsWorker execution worker_id error, reason={reason}",
    )
    WORKFLOW_EXCEPTION_END_ERROR = (
        101924,
        "The workflow anomaly termination component terminates execution",
    )

    # workflow流式报错 101931-101940
    WORKFLOW_STREAM_CALLBACK_INSTANCE_INVALID_ERROR = (
        101931,
        "Workflow stream callback instance is invalid",
    )

    # 自定义组件报错    101951~101999
    COMPONENT_POOL_REGISTER_DUPLICATED_CLASS = (
        101951,
        "There is already a component class type '{comp_type}' already exists in the component pool",
    )
    COMPONENT_POOL_REGISTER_INVALID_CLASS_NAME = (
        101952,
        "The component class type '{comp_type}' is invalid. err_msg={err_msg}",
    )
    COMPONENT_POOL_REGISTER_TYPE_ERROR = (
        101953,
        "The component to register must be a class",
    )
    COMPONENT_POOL_GET_CLASS_ERROR = (
        101954,
        "Component class type '{comp_type}' not found in the component pool. Please register the component class first",
    )
    COMPONENT_POOL_INSTANTIATION_ERROR = (
        101955,
        "Failed to instantiate Component class type '{comp_type}'",
    )
    COMPONENT_POOL_INIT_ERROR = (
        101956,
        "Component pool initialization failed, reason={reason}",
    )

    # Prompt引擎     102000~102999
    # Prompt 引擎  - 模板管理 102050 - 102080
    LLM_NO_RET_ERROR = (102001, "LLM service return is None.")
    HTTP_NET_WORK_ERROR = (102002, "Http request error")
    LLM_FALSE_RESULT_ERROR = (
        102003,
        "LLM service returned false result due to: {error_msg}",
    )
    LLM_CONNECTION_ERROR = (102004, "Error connecting llm service: {error_msg}")
    LLM_NO_ENV_ERROR = (102005, "Failed to get env from context.")
    OUTPUT_PARSER_INIT_ERROR = (
        102006,
        "Failed to initialize output parser, root cause = {error_msg}",
    )
    OUTPUT_PARSER_INVOKE_ERROR = (
        102007,
        "Failed to invoke output parser, root cause = {error_msg}",
    )
    MEP_FALSE_RESULT_ERROR = (102008, "MEP returned false result due to: {error_msg}")
    RUNTIME_CONTEXT_ERROR = (102009, "Failed to get runtime_context.")
    IR_BUILD_ERROR = (102010, "Error building IR: {error_msg}")
    LLM_SERVICE_TYPE_ERROR = (102011, "Unrecognized LLM service type: {error_msg}")
    LLM_INTERRUPTED_ERROR = (
        102012,
        "LLM Component received interruption signal from runtime_context",
    )
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
    PROMPT_COMPONENT_INIT_ERROR = (
        102054,
        "Failed to initialize prompt component, root cause = {error_msg}",
    )
    PROMPT_COMPONENT_INVOKE_ERROR = (
        102055,
        "Failed to invoke prompt component, root cause = {error_msg}",
    )
    PROMPT_JSON_SCHEMA_ERROR = (
        102056,
        "Invalid json schema, root cause = {error_msg}.",
    )
    PROMPT_VARIABLE_FORMAT_ERROR = (
        102056,
        "Error formatting variables, root cause= {error_msg}.",
    )
    # Prompt 引擎  - 模板管理 102100 - 102149
    PROMPT_TEMPLATE_DUPLICATED_ERROR = (102101, "Template duplicated")
    PROMPT_TEMPLATE_NOT_FOUND_ERROR = (
        102102,
        "Template not found, root cause = {error_msg}",
    )
    PROMPT_DATA_INCORRECT_ERROR = (102103, "Template data incorrect")
    PROMPT_STORAGE_LOAD_ERROR = (
        102104,
        "Load Template data form prompt storage failed.",
    )
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
    PROMPT_OPTIMIZE_STORAGE_ERROR = (
        102170,
        "Prompt optimize storage failed, root cause = {error_msg}.",
    )
    # Prompt 引擎  - 模板生成  102200 - 102249
    PROMPT_META_TEMPLATE_NOT_SUPPORTED_ERROR = (
        102201,
        "Meta template not found in supported list",
    )
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
    PROMPT_LLM_TYPE_NOT_SUPPORTED_ERROR = (
        102206,
        "The configuration type of the LLM is not supported",
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
    PROMPT_UNEXPECT_ERROR = (
        102211,
        "Catching unknown exception, root cause = {error_msg}",
    )
    PROMPT_MODEL_SSL_VERIFY_ENV_ERROR = (
        102212,
        "SSL verify env json decoder exception, root cause = {error_msg}",
    )
    PROMPT_OPTIMIZE_FEEDBACK_ERROR = (
        102213,
        "optimize feedback exception, root cause = {error_msg}",
    )
    PROMPT_OPTIMIZE_BAD_CASE_ERROR = (
        102214,
        "optimize badcase exception, root cause = {error_msg}",
    )
    # 规划引擎        103000~103999
    PLANNER_CONFIG_CHECK_FAILED = (103001, "Failed to check planner config")
    PLANNER_PROMPT_NAME_MISSING = (103002, "Failed to input prompt name")
    PLANNER_MODEL_MISSING = (103003, "Failed to input model")
    INVOKE_LLM_FAILED = (103004, "Failed to call model")
    PLANNER_GET_PLAN_STATE_FAILED = (
        103005,
        "Failed to get plan state class based on specified plan mode type. ",
    )
    PLANNER_REGULAR_PARSE_FAILED = (
        103006,
        "Failed to parse the paragraph using the regular expression. ",
    )
    PLANNER_INDEX_FAILED = (103007, "Failed to get element by indexing. ")
    PLANNER_GET_PLUGINS_CONFIG_VALUE_FAILED = (
        103008,
        "Failed to get plugin config value from global configs",
    )
    PLANNER_COMPARE_PARSE_FAILED = (
        103009,
        "Fail to return boolean result because of illegal compare expression",
    )
    PLANNER_GET_IR_TEMPLATE_FAILED = (
        103010,
        "Fail to get template ir file based on specified plan mode type. ",
    )
    PLANNER_PROMPT_FORMAT_FAILED = (103011, "Fail to perform prompt template format")
    PLANNER_GET_SKILLS_CONFIG_VALUE_FAILED = (103012, "Fail to get skills config value")
    PLANNER_GET_SKILL_TYPE_FAILED = (103013, "Fail to get skill type")
    PLANNER_RAILS_EXECUTION_FAILED = (103011, "Fail to execute planner rails. ")
    PLANNER_WORKFLOW_PARSE_FAILED = (103014, "Fail to parse workflow start component.")
    PLANNER_WORKFLOW_RUN_FAILED = (103015, "Fail to run workflow component")
    PLANNER_GET_IR_TEMPLATE_VERSION_FAILED = (
        103016,
        "Fail to get template ir file based on specified version {version}.",
    )
    PLANNER_VALIDATION_CONFIGURATION_FAILED = (
        103017,
        "Invalid type of {configuration}, should be {required_type} but "
        "found {actual_type}",
    )
    PLANNER_STREAM_EXCEPTION_ERROR = (
        103018,
        "Planner stream exception, reason={reason}",
    )
    # agent模块       103025~103050
    AGENT_INPUT_TYPE_ERROR = (103025, "The input type {} is not supported now.")
    AGENT_TOOL_SWITCH_ERROR = (103028, "tool switch dict type invalid")
    AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR = (
        103029,
        "Please input list of RestFulApi or Function. not {}",
    )
    AGENT_TASK_ID_INVALID_ERROR = (
        103030,
        "The length of task_id exceeds the maximum {}.",
    )
    AGENT_UPDATE_MCP_WITH_TYPE_ERROR = (
        103031,
        "Please input list of MCP or Function. not {}",
    )

    # 控制器        103100~103200
    CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR = (
        103100,
        "Controller atomic skill--ExtractParams invoke error.",
    )
    CONTROLLER_REFINE_PARAMS_INVOKE_ERROR = (
        103101,
        "Controller atomic skill--RefineParams invoke error.",
    )
    CONTROLLER_INTERRUPT_ERROR = (103102, "controller interrupt error")
    CONTROLLER_GLOBAL_INTENT_MAX_REPEAT_ERROR = (
        103103,
        "exceed the most jump times for global intent",
    )
    CONTROLLER_INTENT_DETECTION_ERROR = (
        103104,
        "Controller intent detection--Error {}",
    )
    CONTROLLER_INTENT_WORKFLOW_EXECUTION_ERROR = (
        103105,
        "Controller intent workflow execution--Error {}",
    )

    # 多Agent        103200~103299
    # > 多Agent运行器异常 103200-103230
    MULTI_AGENT_RUNNER_ALREADY_STARTED = (103200, "Runner is already started")
    MULTI_AGENT_TARGET_MEMBER_NOT_FOUND = (103201, "Target member not found: {}")
    MULTI_AGENT_MESSAGE_SUSPENDED = (
        103202,
        "Message suspended, waiting for user input: {}",
    )
    MULTI_AGENT_PROCESSING_INTERRUPTED = (103203, "Processing interrupted: {}")
    MULTI_AGENT_RUNNER_NOT_RUNNING = (103204, "Runner not running: {}")
    MULTI_AGENT_RUNNER_NOT_STARTED = (103205, "Runner not started: {}")

    # > 多Agent运行空间异常 103231-103260
    MULTI_AGENT_RUN_SPACE_EXECUTION_ERROR = (
        103231,
        "AgentRunSpace execution error: {}",
    )
    MULTI_AGENT_RUN_SPACE_SHUTDOWN_QUEUE_ERROR = (
        103232,
        "Failed to shutdown message queue: {}",
    )
    MULTI_AGENT_RUN_SPACE_STOP_TASK_ERROR = (103233, "Failed to stop run task: {}")
    MULTI_AGENT_RUN_SPACE_STOP_IDLE_ERROR = (103234, "Failed to stop when idle: {}")
    MULTI_AGENT_RUN_SPACE_CHECK_CONDITION_ERROR = (
        103235,
        "Failed to check stop condition: {}",
    )
    MULTI_AGENT_RUN_SPACE_EXECUTE_STOP_WHEN_ERROR = (
        103236,
        "Failed to execute stop_when: {}",
    )

    # > 多Agent成员异常 103261-103290
    MULTI_AGENT_MEMBER_PROCESS_MESSAGE_ERROR = (
        103261,
        "Failed to process message in member {}: {}",
    )
    MULTI_AGENT_MEMBER_PROCESSING_ERROR = (
        103262,
        "Error occurred while processing message: {}",
    )

    # > 多Agent消息队列异常 103291-103299
    MULTI_AGENT_MESSAGE_NOT_PROCESSING = (
        103291,
        "Message {} is not currently being processed",
    )

    # > 多Agent Group异常 103300-103309
    MULTI_AGENT_GROUP_ALREADY_STARTED = (103300, "Agent group already running")
    MULTI_AGENT_GROUP_NOT_INITIALIZED = (
        103301,
        "AgentGroup is not running or not properly initialized",
    )
    MULTI_AGENT_GROUP_EXECUTE_ERROR = (
        103302,
        "An error occurred during executing agent group, details: {reason}",
    )
    MULTI_AGENT_GROUP_AGENT_REGISTRATION_ERROR = (
        103303,
        "Failed to register agents in group, reason: {reason}",
    )

    # 执行引擎        104000~104999
    RUN_WITH_STREAM_ERROR = (104001, "Run with stream error")
    EXECUTOR_ERROR = (104002, "Executor error")
    GENERAL_REQUEST_ERROR = (104003, "General request error")
    OPERATOR_EXECUTION_ERROR = (104004, "Failed to execute operator")
    EXECUTOR_PULL_FROM_MANAGER_ERROR = (
        104005,
        "Failed to pull workers list from manager",
    )
    EXECUTOR_CLEAN_SESSION_ERROR = (104006, "Failed to clean session")
    EXECUTOR_USER_INPUT_ERROR = (104007, "Failed to execute user input")
    EXECUTOR_STREAM_DATA_ERROR = (104008, "Failed to process StreamData")
    # 插件管理        105000~105999
    PLUGIN_UNEXPECTED_ERROR = (105001, "Plugin unexpected error")
    PLUGIN_ALREADY_EXISTS = (105002, "Plugin already exists")
    PLUGIN_NOT_FOUND = (105003, "Plugin not found")
    PLUGIN_PARAMS_CHECK_FAILED = (105004, "Plugin params check failed")
    PLUGIN_VALID = (105005, "Plugin valid")
    PLUGIN_DATABASE_EXCEPTION = (105006, "Plugin database exception")
    PLUGIN_EXECUTE_SQLEXCEPTION = (105007, "Plugin execute sql exception")
    PLUGIN_INTER_ERROR = (105008, "Plugin internal error")
    PLUGIN_EMBEDDING_ERROR = (105009, "Plugin embedding infer failed")
    PLUGIN_RESTFULAPI_AUTH_ERROR = (105010, "Plugin restful api auth failed")

    PLUGIN_RESPONSE_HTTP_CODE_ERROR = (
        105011,
        "Plugin restful api response http code error",
    )
    PLUGIN_REQUEST_TIMEOUT_ERROR = (105012, "Plugin restful api request timeout error")
    PLUGIN_RESPONSE_TOO_BIG_ERROR = (105013, "Plugin restful api response too big")
    PLUGIN_PROXY_CONNECT_ERROR = (105014, "Plugin restful api proxy connect failed")

    # 记忆管理        106000~106999
    # 数据增强        107000~107999
    # Insight       108000~108999
    INSIGHT_CHILD_EXECUTION_ORDER_INDEX_ERROR = (
        108003,
        "Parent invoke with invoke_id {parent_invoke_id} doesn't has child_execution_order_index.",
    )
    INSIGHT_INVOKE_ID_NOT_EXIST_ERROR = (108004, "Invoke id does not exist.")
    INSIGHT_INVOKE_TYPE_ERROR = (
        108005,
        "Expect prompt type, but found {invoke_type} for current invoke id.",
    )
    INSIGHT_PROJECT_ID_EMPTY_ERROR = (
        108006,
        "Insight x-insight-project-id cannot be empty.",
    )

    # 高级意图节点模块 109000~109010
    COMPLEX_INTENT_INIT_ERROR = (109000, "complex intent init error, msg={msg}")

    # 动态规划模块 109011~109020
    STRATEGY_ENV_VAR_NOT_EXIST_ERROR = (
        109011,
        "The environment variable JIUWEN_CUSTOM_STRATEGY_PATH is not configured.",
    )
    STRATEGY_FILE_NOT_EXIST_ERROR = (109012, "The strategy path does not exist.")
    STRATEGY_FILE_NOT_FILEPATH_ERROR = (109013, "The strategy path is not a file path.")
    STRATEGY_REGISTRY_NOT_INIT_ERROR = (
        109014,
        "Registry not initialized. Call initialize() first.",
    )
    STRATEGY_NOT_FOUND_ERROR = (
        109015,
        "Strategy {strategy_name} not found for provider {provider}.",
    )
    BUILTIN_STRATEGY_PATH_NOT_FOUND_ERROR = (109016, "Strategy {path} not found.")
    AINVOKE_STREATEGY_ERROR = (109017, "Strategy component ainvoke unexpected error")
    AGENT_MAX_ITERATION_INVALID = (
        109018,
        "Agent config max_iteration must be an integer > 0",
    )
    PLUGIN_NOT_FOUND_ERROR = (109019, "Plugin url not found")

    # 记忆引擎模块 109300~109499
    MEMORY_ENGINE_IR_CONFIG_ERROR = (
        109300,
        "Memory ir config is incorrectly configured, root cause = {error_msg}",
    )
    # 上下文引擎模块 109500~109999
    CONTEXT_ENGINE_CONFIG_ERROR = (
        109500,
        "Context config is incorrectly configured, root cause = {error_msg}",
    )
    CONTEXT_ENGINE_PROXY_INIT_ERROR = (
        109501,
        "Memory client init failed, root cause = {error_msg}",
    )
    CONTEXT_ENGINE_CREATE_PROCESSOR_ERROR = (
        109510,
        "Create processor error, root cause = {error_msg}",
    )

    # 自定义组件预留，请不要使用该范围内的错误码     120000~129999
    # 迁移本地执行代码节点的错误码
    WORKFLOW_CODE_RETURN_VALUE_UNEXPECTED_ERROR = (
        120007,
        "output keys should be in code return values",
    )
    WORKFLOW_CODE_RETURN_VALUE_TYPE_ERROR = (
        120008,
        "type of code return values should be dict",
    )

    @property
    def code(self):
        """获取状态码"""
        return self.value[0]

    @property
    def errmsg(self):
        """获取状态码信息"""
        return self._get_errmsg()

    @classmethod
    def register_overwrite_status_code(cls, status_code: dict):
        """注册用户覆写的状态码信息"""
        if status_code and isinstance(status_code, dict):
            _OVERWRITE_STATUS_CODE.clear()
            _OVERWRITE_STATUS_CODE.update(status_code)

    def _get_errmsg(self):
        language = Language.get_context_language()
        if not language:
            return self.value[1]
        overwrite_errmsg = _OVERWRITE_STATUS_CODE.get(language, {}).get(
            self.value[0], ""
        )
        return overwrite_errmsg if overwrite_errmsg else self.value[1]
