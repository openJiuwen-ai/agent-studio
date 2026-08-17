/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.common.constant;

import java.util.List;

/**
 * 功能描述 常量
 */
public interface CommonConstant {
    /**
     * 模型连通性测试query
     */
    String TEST_QUERY = "你好";

    /**
     * embedding模型连通性类型
     */
    String EMBEDDING_TYPE = "query2query";

    /**
     * app id常量
     */
    String X_HW_ID = "X-HW-ID";

    /**
     * app key常量
     */
    String X_HW_APPKEY = "X-HW-APPKEY";

    /**
     * X_AUTH_TOKEN常量
     */
    String X_AUTH_TOKEN = "X-Auth-Token";

    /**
     * X_APIG_APPCODE常量
     */
    String X_APIG_APPCODE = "x-apig-appcode";

    /**
     * Authorization常量
     */
    String AUTHORIZATION = "Authorization";

    /**
     * 用户id
     */
    String X_USER_ID = "X-USER-ID";

    /**
     * contextPath参数名
     */
    String SERVLET_CONTEXT_PATH = "server.servlet.context-path";

    /**
     * LakeSearch访问的endpoint
     */
    String X_KNOWLEDGE_ENDPOINT = "X-Knowledge-Endpoint";

    /**
     * KooSearch中ES错误
     */
    String KOS_ES_ERROR_CODE = "KOS.00020001";

    /**
     * model-service use range
     */
    String RUNNING_STATE = "running";

    /**
     * obs类型workflow
     */
    String WORKFLOW = "workflow";

    /**
     * obs类型model
     */
    String OBS_PREFIX_MODEL = "model";

    /**
     * obs类型agent
     */
    String AGENT = "agent";

    /**
     * obs类型tool
     */
    String TOOL = "tool";

    /**
     * 导入类型Plugin
     */
    String PLUGIN = "Plugin";

    /**
     * 导入类型字段
     */
    String IMPORT_TYPE = "import_type";

    /**
     * 流式调用workflow超时时间
     */
    long WORKFLOW_TIMEOUT = 120000L;

    /**
     * agent流式运行超时时间
     */
    long AGENT_STREAM_TIMEOUT = 120000L;

    /**
     * Agent默认名称
     */
    String AGENT_NAME_DEFAULT = "智能体";

    /**
     * Agent名称最大长度
     */
    int NAME_MAX_LEN = 61;

    /**
     * projectId
     */
    String PROJECT_ID = "projectId";

    /**
     * domainId
     */
    String DOMAIN_ID = "domainId";

    /**
     * agentId
     */
    String AGENT_ID = "agentId";

    /**
     * 触发器id
     */
    String TRIGGER_ID = "triggerId";

    /**
     * 定时触发器prompt
     */
    String PROMPT = "prompt";

    /**
     * 字符串常量
     */
    String TRACE_IAM_ENDPOINT = "traceIamEndpoint";

    /**
     * 字符串常量
     */
    String AGENCY_TOKEN_URL = "agencyTokenUrl";

    /**
     * 时间格式
     */
    String TIME_FORMAT = "yyyy-MM-dd HH:mm:ss";

    /**
     * 字符串常量
     */
    String ASSUME_ROLE = "assume_role";

    /**
     * 字符串常量
     */
    String AGENT_RUNTIME_ENDPOINT = "agentRuntimeEndpoint";

    /**
     * agent会话接口（流式）
     */
    String RUN_AGENT_STREAM_URL = "runAgentStreamUrl";

    /**
     * agent应用名称
     */
    String NAME = "name";

    /**
     * agent应用描述
     */
    String DESCRIPTION = "description";

    /**
     * 字符串常量
     */
    String AGENT_BUILDER = "agentBuilder";

    /**
     * http请求体格式类型
     */
    String CONTENT_TYPE = "Content-Type";

    /**
     * http请求体格式
     */
    String APPLICATION_JSON = "application/json";

    /**
     * 流式传输的媒体类型
     */
    String TEXT_EVENT_STREAM = "text/event-stream";

    /**
     * 编码格式
     */
    String UTF_8 = "UTF-8";

    /**
     * X-Subject-Token常量
     */
    String X_SUBJECT_TOKEN = "X-Subject-Token";

    /**
     * 获取异步请求响应结果的超时时间
     */
    int ASYNC_MAX_WAIT_SECONDS = 300;

    /**
     * 字符串常量
     */
    String EVENT_DATA_PREFIX = "data:";

    /**
     * agent会话流式输出
     */
    String STREAM = "stream";

    /**
     * 记忆变量
     */
    String MEMORY = "memory";

    /**
     * 字符串常量
     */
    String TRUE = "true";

    interface Workflow {
        String NODE_START = "node_start";

        String NODE_END = "node_end";

        String REF = "ref";

        String REF_START = "${";

        String RAW_END = ".raw_output}";

        String TOKENS = "tokens";

        String IR = "ir";

        String FLOW = "flow";

        int MAX_PARAM_SIZE = 100;

        String REF_NODE_ID = "ref_node_id";

        String REF_VAR_NAME = "ref_var_name";

        String TASK = "task";

        String AUTH_INFO = "auth_info";

        String PLUGINS = "plugins";

        String MODEL = "model";

        String ID = "workflow_id";

        String NAME = "workflow_name";

        String VERSION_ID = "workflow_version_id";

        String LOOP_BODY = "loop_body";
    }

    /**
     * workflow发布态
     */
    String WORKFLOW_PUBLISHED = "published";

    /**
     * workflow开发态
     */
    String WORKFLOW_DEVELOP = "draft";

    /**
     * workflow可运行态
     */
    Integer WORKFLOW_EXECUTABLE = 2;

    /**
     * workflow内置插件类型
     */
    String WORKFLOW_INNER = "inner";

    /**
     * workflow个人插件类型
     */
    String WORKFLOW_PERSONAL = "personal";

    /**
     * workflow对话型应用
     */
    String CHAT = "chat";

    /**
     * model params
     */
    List<String> MODEL_PARAMS = List.of("model_name", "model_type", "model_deployment_id");

    /**
     * model failed message
     */
    String MODEL_MSG = "model is empty or not valid";

    /**
     * 默认创建用户名
     */
    String DEFAULT_USERNAME = "官方预置";

    /**
     * 默认创建英文用户名
     */
    String DEFAULT_ENGLISH_USERNAME = "official";

    /**
     * 模型复调次数
     */
    int MODEL_CALLS = 3;

    /**
     * 追问配置默认参考对话轮数
     */
    int ROUNDS_DEFAULT = 1;

    /**
     * 最大生成的推荐问个数
     */
    int MAX_QUESTION_NUMS = 3;

    /**
     * 开场白最大长度
     */
    int MAX_PROLOGUE_LENGTH = 500;

    /**
     * 分页每页最大展示数量，kooSearch限制最大数量100
     */
    int MAX_PAGE_SIZE = 100;

    /**
     * 知识库调用kooSearch接口需要传应用id
     */
    String KOO_SEARCH_APPLICATION_ID = "123";

    /**
     * NLP模型资产类型
     */
    String NLP_ASSET_TYPE = "NLP";

    /**
     * 搜索大模型资产类型
     */
    String SEARCH_ASSET_TYPE = "EmbeddingRank";

    /**
     * 盘古模型类型
     */
    String AGENT_BUILDER_MODEL_TYPE = "ei_agentBuilder";

    /**
     * 千问模型类型
     */
    String QWEN_MODEL_TYPE = "qwen";

    /**
     * POST请求类型
     */
    String POST_METHOD = "POST";

    /**
     * GET请求类型
     */
    String GET_METHOD = "GET";

    /**
     * ir刷新备份路径
     */
    String IR_BACKUP = "ir-backup";

    /**
     * 代码解释器插件名
     */
    String PYTHON_INTERPRETER_NAME = "python_interpreter";

    /**
     * 代码解释器 input schema
     */
    String PYTHON_INTERPRETER_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"code\":{\"type\":\"string\",\"description\":\"python代码\",\"location\":\"Body\",\"default\":\"\",\"name_cn\":\"代码\",\"validated\":false,\"validate_rule\":\"\",\"validate_type\":\"CHAR\"}},\"required\":[\"code\"]}";

    /**
     * 代码解释器 output schema
     */
    String PYTHON_INTERPRETER_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"cot_string\":{\"type\":\"string\",\"description\":\"代码运行结果\"}},\"required\":[\"cot_string\"]}";

    /**
     * 文件解析插件名
     */
    String READ_FILE_NAME = "Read_File";

    /**
     * 文件解析插件 input schema
     */
    String READ_FILE_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"file_url\":{\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文件链接\",\"type\":\"string\",\"description\":\"文件链接\"}},\"required\":[\"file_url\"]}";

    /**
     * 文件解析插件 output schema
     */
    String READ_FILE_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"content\":{\"type\":\"string\",\"description\":\"文件内容\"}},\"required\":[\"content\"]}";

    /**
     * OCR插件名
     */
    String OCR_NAME = "OCR";

    /**
     * OCR插件 input schema
     */
    String OCR_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"urls\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"图片链接\",\"type\":\"array\",\"description\":\"数组形式的图片链接\",\"items\":{\"type\":\"string\"}}},\"required\":[\"urls\"]}";

    /**
     * OCR插件 output schema
     */
    String OCR_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"data\":{\"type\":\"array\",\"description\":\"识别结果\",\"items\":{\"type\":\"object\",\"properties\":{\"words_block_count\":{\"type\":\"integer\",\"description\":\"识别到的文字块数量\"},\"words_block_list\":{\"type\":\"array\",\"description\":\"文字块列表\",\"items\":{\"type\":\"object\",\"properties\":{\"words\":{\"type\":\"string\",\"description\":\"文字块内容\"},\"confidence\":{\"type\":\"string\",\"description\":\"识别置信度\"}},\"required\":[]}}},\"required\":[]}}},\"required\":[]}";

    /**
     * ASR插件名
     */
    String ASR_NAME = "ASR";

    /**
     * ASR插件 input schema
     */
    String ASR_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"urls\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文件链接\",\"type\":\"array\",\"description\":\"数组形式的文件链接\",\"items\":{\"type\":\"string\"}},\"add_punc\":{\"default\":\"true\",\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"NUM\",\"validated\":false,\"name_cn\":\"是否在识别结果中添加标点\",\"type\":\"boolean\",\"description\":\"是否在识别结果中添加标点\"},\"digit_norm\":{\"default\":\"true\",\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"NUM\",\"validated\":false,\"name_cn\":\"是否将语音中的数字识别为阿拉伯数字\",\"type\":\"boolean\",\"description\":\"是否将语音中的数字识别为阿拉伯数字\"}},\"required\":[\"urls\",\"add_punc\",\"digit_norm\"]}";

    /**
     * ASR插件 output schema
     */
    String ASR_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"data\":{\"type\":\"array\",\"description\":\"识别结果\",\"items\":{\"type\":\"object\",\"properties\":{\"status\":{\"type\":\"string\",\"description\":\"识别状态\"},\"segments\":{\"type\":\"array\",\"description\":\"识别内容列表\",\"items\":{\"type\":\"object\",\"properties\":{\"text\":{\"type\":\"string\",\"description\":\"识别内容\"},\"analysis_info\":{\"type\":\"object\",\"description\":\"分析结果\",\"properties\":{\"role\":{\"type\":\"string\",\"description\":\"角色类型\"},\"emotion\":{\"type\":\"string\",\"description\":\"角色情绪\"}},\"required\":[]}},\"required\":[]}},\"error_message\":{\"type\":\"string\",\"description\":\"错误信息\"}},\"required\":[\"status\"]}}},\"required\":[\"data\"]}";

    /**
     * 文档解析插件名
     */
    String READ_DOCUMENT_NAME = "Read_Document";

    /**
     * 文档解析插件 input schema
     */
    String READ_DOCUMENT_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"urls\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文档链接\",\"type\":\"array\",\"description\":\"数组形式的文档链接\",\"items\":{\"type\":\"string\"}},\"ocr_enabled\":{\"default\":\"true\",\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"NUM\",\"validated\":false,\"name_cn\":\"是否打开OCR增强\",\"type\":\"boolean\",\"description\":\"是否打开OCR增强，默认打开：true\"}},\"required\":[\"urls\"]}";

    /**
     * 文档解析插件 output schema
     */
    String READ_DOCUMENT_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"data\":{\"type\":\"array\",\"description\":\"解析结果列表，与文档链接一一对应\",\"items\":{\"type\":\"object\",\"properties\":{\"status\":{\"type\":\"string\",\"description\":\"解析状态\"},\"pages\":{\"type\":\"array\",\"description\":\"分页解析结果\",\"items\":{\"type\":\"object\",\"properties\":{\"content\":{\"type\":\"array\",\"description\":\"每一页的分片解析结果\",\"items\":{\"type\":\"string\"}},\"page_num\":{\"type\":\"integer\",\"description\":\"页码\"}},\"required\":[]}},\"error_message\":{\"type\":\"string\",\"description\":\"错误信息\"}},\"required\":[\"status\"]}}},\"required\":[\"data\"]}";

    /**
     * 文档生成插件名
     */
    String CREATE_DOCUMENT_NAME = "Create_Document";

    /**
     * 文档生成插件 input schema
     */
    String CREATE_DOCUMENT_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"input\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文档内容\",\"type\":\"string\",\"description\":\"文档内容\"},\"document_name\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文档名\",\"type\":\"string\",\"description\":\"文档名，不允许含有以下非法字符：\\\\/:*?\\\"<>|\"}},\"required\":[\"input\",\"document_name\"]}";

    /**
     * 文档生成插件 output schema
     */
    String CREATE_DOCUMENT_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"url\":{\"type\":\"string\",\"description\":\"文档下载链接\"}},\"required\":[]}";

    /**
     * 追问自定义prompt
     */
    String ADDITIONAL_QUESTIONS_PROMPT_CUSTOM
        = "- 问题应该与你最后一轮的回复紧密相关\n- 问题不要与上文已经提问或者回答过的内容重复\n- 每句话只包含一个问题，但也可以不是问句而是一句指令\n- 推荐你有能力回答的问题";

    /**
     * 追问自定义prompt英文版
     */
    String ADDITIONAL_QUESTIONS_PROMPT_CUSTOM_EN
        = "- The question should be closely related to your last round of responses\n- Do not repeat questions that have been asked or answered above\n- Each sentence contains only one question, but it can also be a command instead of a question\n- Recommend questions that you can answer";

    /**
     * 云产品部署类型
     */
    interface EnvType {
        String POC = "poc";

        String HC = "hc";

        String HCS = "hcs";
    }

    /**
     * agent类型
     */
    String AGENT_TYPE = "agent";

    /**
     * 知识库类型
     */
    String REPO_TYPE = "repo";

    /**
     * 插件类型
     */
    String TOOL_TYPE = "tool";

    /**
     * 工作流类型
     */
    String WORKFLOW_TYPE = "workflow";

    /**
     * mcp 服务类型
     */
    String MCP_TYPE = "mcp";

    /**
     * mcp dsl config key
     */
    String VALID = "valid";

    /**
     * MCP 服务工具名
     */
    String TOOL_NAME = "tool_name";

    /**
     * 字符串常量
     */
    String USER = "user";

    /**
     * 字符串常量
     */
    String CHOICES = "choices";

    /**
     * 发布状态：normal
     */
    String NORMAL = "normal";

    /**
     * 模型响应体Key：message
     */
    String MESSAGE = "message";

    /**
     * 模型响应体key：content
     */
    String CONTENT = "content";

    /**
     * 字符串：file
     */
    String FILE = "file";

    /**
     * 字符串：icon
     */
    String ICON = "icon";

    /**
     * 字符串：image
     */
    String IMAGE = "image";

    /**
     * 智能生成开场白的兜底回复
     */
    String PROLOGUE = "你好，你可以问我一些感兴趣的问题。";

    /**
     * 智能生成开场白的兜底回复英文版
     */
    String PROLOGUE_EN = "Hi, you can ask me some questions of interest.";

    /**
     * lakeSearch的project_id
     */
    String LAKE_SEARCH_PROJECT_ID = "1ed40ceefc8d40f8b884edb6a84e7768";

    /**
     * lakeSearch的application_id
     */
    String LAKE_SEARCH_APP_ID = "fb9731ab-7085-474fb6c7-64473586f0f3";

    /**
     * dsl
     */
    String DSL_STR = "dsl";

    /**
     * 文件夹分隔符
     */
    String FOLDER_SEPARATOR = "/";

    /**
     * 字符串常量
     */
    String TOOL_LIST = "tool_list";

    /**
     * 字符串常量
     */
    String QUERY = "query";

    /**
     * 历史数据
     */
    String CONVERSATION_HISTORY = "conversation_history";

    /**
     * 系统变量
     */
    String SYS = "sys";

    /**
     * 循环节点的输出节点id后缀
     */
    String LOOP_OUTPUT = "_output";

    /**
     * 循环节点的输入节点id后缀
     */
    String LOOP_INPUT = "_input";

    /**
     * 当前系统时间变量
     */
    String CURRENT_TIME = "current_time";

    /**
     * 工作流用户的唯一标识
     */
    String USER_ID = "userId";

    /**
     * 网页发布通道类型
     */
    String WEB_PAGE_CHANNEL = "WEB_PAGE";

    /**
     * 应用百宝箱通道类型
     */
    String APP_STORE_CHANNEL = "APP_STORE";

    /**
     * 工作流关联关系唯一值模板（不带版本）
     */
    String UNIQUE_MAPPING_KEY_FORMAT = "%s_%s";

    /**
     * 工作流关联关系唯一值模板（带版本）
     */
    String UNIQUE_MAPPING_KEY_WITH_VERSION_FORMAT = "%s_%s_%s";

    /**
     * agent节点相关插件
     */
    String PLUGINS = "plugins";

    /**
     * 知识库相关
     */
    String REPOS = "repos";

    /**
     * 工具不存在时默认工具名
     */
    String TOOL_NOT_EXIST = "unknown";

    interface ModelParam {
        String MODEL = "model";

        String DEFAULT_MODEL = "default_model";

        String MODEL_NAME = "model_name";

        String MODEL_TYPE = "model_type";

        String MODEL_DEPLOYMENT_ID = "model_deployment_id";

        String DEFAULT_MODEL_SWITCH = "default_model_switch";

        String FREQUENCY_PENALTY = "frequency_penalty";

        String MAX_TOKENS = "max_tokens";
    }

    /**
     * OpenAPI中的扩展字段，将插件转换为OpenAPI定义时使用
     */
    interface OpenAPI {
        /**
         * 参数在query
         */
        String IN_QUERY = "query";

        /**
         * 参数在header
         */
        String IN_HEADER = "header";

        /**
         * APIKey鉴权方式
         */
        String API_KEY = "ApiKeyAuth";

        /**
         * 用户配置的header或apikey的取值（加密）
         */
        String X_VALUE = "x-value";

        /**
         * 是否封装为数组
         */
        String X_ARRAY_ENCAPSULATION = "x-array-encapsulation";

        /**
         * IAM鉴权方式
         */
        String IAM = "iam";

        /**
         * projectId
         */
        String X_PROJECT_ID = "x-project-id";

        /**
         * domainId
         */
        String X_DOMAIN_ID = "x-domain-id";
    }

    /**
     * 插件可见范围
     */
    interface VISIBILITY_SCOPE {
        String PROJECT = "project";

        String USER = "user";
    }

    /**
     * MCP服务类型
     */
    interface MCP_SERVER_TYPE {
        String SSE = "sse";
    }

    interface Plugin {
        String INTF_TYPE_BLOCKING = "blocking";

        String INTF_TYPE_STREAMING = "streaming";
    }

    /**
     * http和插件节点相关
     */
    interface Http {
        /**
         * 异常忽略开关
         */
        String EXCEPTION_ENABLE = "exception_enable";

        /**
         * 异常忽略
         */
        String EXCEPTION_SUPPRESSION = "exception_suppression";

        /**
         * http节点endpoint
         */
        String ENDPOINT = "endpoint";

        /**
         * http节点path
         */
        String PATH = "path";
    }

    /**
     * 触发器数量限制
     */
    int MAX_TRIGGER_NUMS = 10;

    /**
     * 分隔符
     */
    String SEPARATOR = ",";

    /**
     * 零宽空格
     */
    String ZERO_SPACE = "\u200B";

    /**
     * 模型deploymentId
     */
    String MODEL_DEPLOYMENT_ID = "modelDeploymentId";

    /**
     * 模型类型
     */
    String MODEL_TYPE = "modelType";

    /**
     * authToken
     */
    String AUTH_TOKEN = "auth_token";

    /**
     * 字符串
     */
    String FAIL = "fail";

    /**
     * 字符串
     */
    String SUCCESS = "success";

    /**
     * 中文
     */
    String ZH_CN = "zh-cn";

    /**
     * 模型调用错误信息
     */
    String ERROR_MESSAGE = "error_message";

    /**
     * 默认分支id
     */
    String DEFAULT_BRANCH_ID = "default";

    /**
     * 失败
     */
    String FAILED = "failed";

    /**
     * 匿名化显示文本
     */
    String ANONYMIZED_TEXT = "******";

    /**
     * 数据源调用错误信息
     */
    String ERROR_MSG = "error_msg";

    /**
     * obs凭证存放路径
     */
    String CREDENTIAL_IR = "credential/ir";

    interface Mcp {
        /**
         * 服务类型 inner
         */
        String TYPE_INNER = "inner";

        /**
         * 服务类型 custom
         */
        String TYPE_CUSTOM = "custom";

        /**
         * 服务类别: 公开
         */
        String CATEGORY_PUBLIC = "public";

        /**
         * 服务类别: 模版
         */
        String CATEGORY_TEMPLATE = "template";
    }

    interface CustomModel {
        /**
         * auth鉴权
         */
        String AUTHORIZATION = "Authorization";

        /**
         * appcode鉴权
         */
        String X_APIG_APPCODE = "x-apig-appcode";

        /**
         * token作为header
         */
        String TOKEN = "token";

        /**
         * userid作为header
         */
        String USER_ID = "userid";

        /**
         * 千问模型（已切换为openai兼容）
         */
        String QWEN = "qwen";

        /**
         * poc盘古接口（已切换为ei_agentBuilder）
         */
        String POC_AGENT_BUILDER_CHAT = "poc_agentBuilder_chat";

        /**
         * openai api兼容模型
         */
        String OPENAI = "openai";

        /**
         * 盘古api-service接口
         */
        String EI_AGENT_BUILDER = "ei_agentBuilder";

        /**
         * embedding模型
         */
        String EMBEDDING = "embedding";

        /**
         * rerank模型
         */
        String RERANK = "rerank";

        /**
         * ocr模型
         */
        String OCR = "ocr";

        /**
         * nlp模型
         */
        String NLP = "nlp";

        /**
         * 默认deployment id
         */
        String DEFAULT = "default";

        /**
         * userid
         */
        String CUSTOM_USER_ID = "cust-userid";

        /**
         * token
         */
        String CUSTOM_TOKEN = "cust-token";
    }

    interface ControllerConstants {
        String IR_ARG_BODY_METHOD = "Body";

        String INPUT_KEY = "node_start";

        String OUTPUT_KEY = "node_end";
    }

    /**
     * 委托名环境变量的名称
     */
    String AGENCY_NAME_KEY = "agency.name";

    /**
     * 部署环境的环境变量名称
     */
    String ENV_TYPE_KEY = "env.type";

    String OUTSIDE = "Outside";

    String INSIDE = "inside";
}
