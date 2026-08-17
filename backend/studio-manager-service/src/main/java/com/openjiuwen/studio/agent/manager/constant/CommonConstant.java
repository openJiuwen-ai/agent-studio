/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.constant;

import com.openjiuwen.studio.agent.common.enums.NodeType;

import java.util.List;

/**
 * 功能描述 常量
 *
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
     * expires 常量
     */
    String X_EXPIRES = "expires";

    /**
     * isImage 常量
     */
    String X_IS_IMAGE = "isImage";

    /**
     * Authorization常量
     */
    String AUTHORIZATION = "Authorization";

    /**
     * 用户id
     */
    String X_USER_ID = "X-USER-ID";

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
     * obs类型agent
     */
    String WRITING_TEMPLATE = "writing_template";

    /**
     * 控制器类型
     */
    String CONTROLLER = "controller";

    /**
     * obs类型tool
     */
    String TOOL = "tool";

    /**
     * 导入类型Plugin
     */
    String PLUGIN = "Plugin";

    /**
     * 导入类型Environment
     */
    String ENVIRONMENT = "Environment";

    /**
     * 导入类型字段
     */
    String IMPORT_TYPE = "import_type";

    String EXPORT_V2_TYPE = "EXPORT_V2";

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
     * Agent默认名称
     */
    String AGENT_NAME_DEFAULT_EN = "agent";

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
     * all
     */
    String  ALL = "all";

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
     * 工作空间
     */
    String WORKSPACE_ID = "workspace_id";

    /**
     * 工作空间
     */
    String DEFAULT_WORKSPACE_ID = "default";

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
     * form-data
     */
    String MULTIPART_FORM_DATA = "multipart/form-data";

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

    String MEMORY_REPO_ID = "memory_repo_id";

    /**
     * 字符串常量
     */
    String TRUE = "true";

    String PLUGIN_INNER_TYPE = "inner";

    String DEFAULT_PROJECT_ID = "default";

    String RESP_SUCCESS_MSG = "success";

    int RESP_SUCCESS_CODE = 200;

    String INSTRUCTIONS = "instructions";

    String TEMPLATE = "reference";

    String SKILLS_CATALOG = "skills_catalog";

    String SKILL_TYPE = "skill";

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

        String SOURCE = "source";

        String REF_VAR_NAME = "ref_var_name";

        String TASK = "task";

        String AUTH_INFO = "auth_info";

        String PLUGINS = "plugins";

        String MODEL = "model";

        String VARIABLES = "variables";

        String ID = "workflow_id";

        String NAME = "workflow_name";

        String VERSION_ID = "workflow_version_id";

        String LOOP_BODY = "loop_body";

        String LLM = "llm";
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
     * ds agent类型
     */
    String DEEPRESEARCH_TYPE = "deepresearch";

    /**
     * pe agent类型
     */
    String PLANEXECUTE_TYPE = "planexecute";

    /**
     * 通用agent类型
     */
    String COMMON_AGENT_TYPE = "common";
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
     * 图片转base64插件名、input schema、output schema、ICON、REQUEST_INFO、AuthInfo
     */
    String IMAGE_BASE64 = "Image2Base64";

    String IMAGE_BASE64_INPUT_SCHEMA
            = "[{\"tool_id\":\"0\",\"input_schema\":\"{\\\"type\\\":\\\"object\\\",\\\"properties\\\":{\\\"url\\\":{\\\"location\\\":\\\"Body\\\",\\\"validate_rule\\\":\\\"\\\",\\\"validate_type\\\":\\\"CHAR\\\",\\\"validated\\\":false,\\\"name_cn\\\":\\\"\\\",\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"图片url链接\\\"},\\\"isDataUrl\\\":{\\\"location\\\":\\\"Body\\\",\\\"validate_rule\\\":\\\"\\\",\\\"validate_type\\\":\\\"NUM\\\",\\\"validated\\\":false,\\\"name_cn\\\":\\\"\\\",\\\"type\\\":\\\"boolean\\\",\\\"description\\\":\\\"是否携带dataUrl前缀\\\"}},\\\"required\\\":[\\\"url\\\"]}\"}]";
    String IMAGE_BASE64_OUTPUT_SCHEMA
            = "[{\"tool_id\":\"0\",\"output_schema\":\"{\\\"type\\\":\\\"object\\\",\\\"properties\\\":{\\\"success\\\":{\\\"type\\\":\\\"boolean\\\",\\\"description\\\":\\\"是否成功\\\"},\\\"message\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"信息\\\"},\\\"base64\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"base64字符串\\\"},\\\"mimetype\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"图片类型\\\"},\\\"filesize\\\":{\\\"type\\\":\\\"integer\\\",\\\"description\\\":\\\"图片大小\\\"}},\\\"required\\\":[\\\"success\\\",\\\"message\\\",\\\"base64\\\",\\\"mimetype\\\",\\\"filesize\\\"]}\"}]";
    String IMAGE_BASE64_REQUEST_INFO
            = "{\"basic_info\":{\"host\":\"\",\"path\":\"\",\"protocol\":\"https\",\"input_schema\":\"{\\\"type\\\":\\\"object\\\",\\\"properties\\\":{},\\\"required\\\":[]}\"},\"tool_info\":[{\"tool_id\":\"0\",\"tool_display_name\":\"ImageToBase64\",\"tool_chinese_name\":\"图片转换base64\",\"tool_desc\":\"输入图片obs链接,将图片转换为base64格式字符串\",\"method\":\"POST\",\"path\":\"/v1/inner-tools/image-convert/url2base64\"}]}";

    String IMAGE_BASE64_IS_INPUT_LIST
            = "[{\"tool_id\":\"0\",\"is_input_list\":false}]";

    String IMAGE_BASE64_IS_OUTPUT_LIST
            = "[{\"tool_id\":\"0\",\"is_output_list\":false}]";

    String IMAGE_BASE64_INTF_TYPE
            = "[{\"tool_id\":\"0\",\"intf_type\":\"blocking\"}]";

    /**
     * base64转图片插件名、input schema、output schema、ICON、REQUEST_INFO、AuthInfo
     */
    String BASE64_IMAGE = "Base64ToImage";

    String BASE64_IMAGE_INPUT_SCHEMA
            = "[{\"tool_id\":\"0\",\"input_schema\":\"{\\\"type\\\":\\\"object\\\",\\\"properties\\\":{\\\"base64\\\":{\\\"location\\\":\\\"Body\\\",\\\"validate_rule\\\":\\\"\\\",\\\"validate_type\\\":\\\"CHAR\\\",\\\"validated\\\":false,\\\"name_cn\\\":\\\"base64字符串\\\",\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"base64字符串\\\"},\\\"mimetype\\\":{\\\"location\\\":\\\"Body\\\",\\\"validate_rule\\\":\\\"\\\",\\\"validate_type\\\":\\\"CHAR\\\",\\\"validated\\\":false,\\\"name_cn\\\":\\\"图片类型\\\",\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"图片类型如PNG、JPG\\\"}},\\\"required\\\":[\\\"base64\\\",\\\"mimetype\\\"]}\"}]";
    String BASE64_IMAGE_OUTPUT_SCHEMA
            = "[{\"tool_id\":\"0\",\"output_schema\":\"{\\\"type\\\":\\\"object\\\",\\\"properties\\\":{\\\"success\\\":{\\\"type\\\":\\\"boolean\\\",\\\"description\\\":\\\"是否成功\\\"},\\\"message\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"输出信息\\\"},\\\"url\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"返回图片url\\\"},\\\"mimetype\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"返回图片类型\\\"},\\\"filesize\\\":{\\\"type\\\":\\\"integer\\\",\\\"description\\\":\\\"图片大小\\\"},\\\"path\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"图片保存路径\\\"}},\\\"required\\\":[\\\"success\\\",\\\"message\\\",\\\"url\\\",\\\"mimetype\\\",\\\"filesize\\\",\\\"path\\\"]}\"}]";
    String BASE64_IMAGE_REQUEST_INFO
            = "{\"basic_info\":{\"host\":\"\",\"path\":\"\",\"protocol\":\"https\",\"input_schema\":\"{\\\"type\\\":\\\"object\\\",\\\"properties\\\":{},\\\"required\\\":[]}\"},\"tool_info\":[{\"tool_id\":\"0\",\"tool_display_name\":\"Image2Base64\",\"tool_chinese_name\":\"Base642Image\",\"tool_desc\":\"将Base64编码转为图片，返回图片url\",\"method\":\"POST\",\"path\":\"/v1/inner-tools/image-convert/base64ToImage\"}]}";

    String BASE64_IMAGE_IS_INPUT_LIST
            = "[{\"tool_id\":\"0\",\"is_input_list\":false}]";

    String BASE64_IMAGE_IS_OUTPUT_LIST
            = "[{\"tool_id\":\"0\",\"is_output_list\":false}]";

    String BASE64_IMAGE_INTF_TYPE
            = "[{\"tool_id\":\"0\",\"intf_type\":\"blocking\"}]";

    /**
     * 每日英语插件名、input schema、output schema、ICON、REQUEST_INFO、AuthInfo
     */
    String DAILY_ENGLISH = "Daily_English";

    String DAILY_ENGLISH_INPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"Content-Type\":{\"default\":\"application/x-www-form-urlencoded\",\"location\":\"Headers\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"Content-Type\"}},\"required\":[\"Content-Type\"]}";

    String DAILY_ENGLISH_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"code\":{\"type\":\"integer\",\"description\":\"状态码\"},\"msg\":{\"type\":\"string\",\"description\":\"错误信息\"},\"result\":{\"type\":\"object\",\"description\":\"返回结果集\",\"properties\":{\"id\":{\"type\":\"integer\",\"description\":\"数据ID\"},\"content\":{\"type\":\"string\",\"description\":\"句子内容\"},\"note\":{\"type\":\"string\",\"description\":\"释义\"},\"source\":{\"type\":\"string\",\"description\":\"来源\"},\"date\":{\"type\":\"string\",\"description\":\"时间\"}},\"required\":[]}},\"required\":[\"code\",\"msg\"]}";

    String DAILY_ENGLISH_REQUEST_INFO
        = "{\"url\":\"\",\"method\":\"POST\",\"headers\":{\"Content-Type\":\"application/x-www-form-urlencoded\"}}";

    String DAILY_ENGLISH_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

    /**
     * 高德地图插件名、input schema、output schema、ICON、REQUEST_INFO、AUTHINFO
     */
    String GAUD_MAP = "Gaud_Map";

    String GAUD_MAP_INPUT_SCHEMA
            = "{\"type\":\"object\",\"properties\":{\"address\":{\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"结构化地址信息\",\"type\":\"string\",\"description\":\"结构化地址信息\"},\"output\":{\"default\":\"JSON\",\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"返回数据格式类型\",\"type\":\"string\",\"description\":\"返回数据格式类型，可选输入内容包括：JSON，XML。设置 JSON 返回结果数据将会以 JSON 结构构成；如果设置 XML 返回结果数据将以 XML 结构构成。\"}},\"required\":[\"address\"]}";
    String GAUD_MAP_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"status\":{\"type\":\"string\",\"description\":\"返回结果状态值，0 表示请求失败；1 表示请求成功。\"},\"info\":{\"type\":\"string\",\"description\":\"返回状态说明，当 status 为 0 时，info 会返回具体错误原因，否则返回“OK”。\"},\"count\":{\"type\":\"string\",\"description\":\"返回结果数量\"},\"geocodes\":{\"type\":\"array\",\"description\":\"地理编码信息列表\",\"items\":{\"type\":\"object\",\"properties\":{\"formatted_address\":{\"type\":\"string\",\"description\":\"结构化地址\"},\"country\":{\"type\":\"string\",\"description\":\"国家\"},\"province\":{\"type\":\"string\",\"description\":\"地址所在省\"},\"citycode\":{\"type\":\"string\",\"description\":\"地址所在市编码\"},\"city\":{\"type\":\"string\",\"description\":\"地址所在市\"},\"district\":{\"type\":\"string\",\"description\":\"地址所在区\"},\"adcode\":{\"type\":\"string\",\"description\":\"区域编码\"},\"street\":{\"type\":\"string\",\"description\":\"地址所在街道\"},\"number\":{\"type\":\"string\",\"description\":\"地址所在门牌号\"},\"location\":{\"type\":\"string\",\"description\":\"地址坐标点\"},\"level\":{\"type\":\"string\",\"description\":\"匹配级别\"}},\"required\":[]}},\"infocode\":{\"type\":\"string\",\"description\":\"状态码\"}},\"required\":[\"status\",\"info\",\"infocode\"]}";

    String GAUD_MAP_REQUEST_INFO = "{\"url\":\"\",\"method\":\"GET\",\"headers\":{}}";

    String GAUD_MAP_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

    /**
     * 高德天气插件名、input schema、output schema、ICON、REQUEST_INFO、AUTHINFO
     */
    String GAUD_WEATHER = "Gaud_Weather";

    String GAUD_WEATHER_INPUT_SCHEMA
            = "{\"type\":\"object\",\"properties\":{\"city\":{\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"城市编码\",\"type\":\"string\",\"description\":\"城市编码adcode，可参考 城市编码表\"},\"output\":{\"default\":\"JSON\",\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"返回格式\",\"type\":\"string\",\"description\":\"返回格式，可选值：JSON,XML\"}},\"required\":[\"city\"]}";
    String GAUD_WEATHER_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"status\":{\"type\":\"string\",\"description\":\"返回状态，值为0或1  1：成功；0：失败\"},\"count\":{\"type\":\"string\",\"description\":\"返回结果总数目\"},\"info\":{\"type\":\"string\",\"description\":\"返回的状态信息\"},\"lives\":{\"type\":\"array\",\"description\":\"实况天气数据信息\",\"items\":{\"type\":\"object\",\"properties\":{\"province\":{\"type\":\"string\",\"description\":\"省份名\"},\"city\":{\"type\":\"string\",\"description\":\"城市名\"},\"adcode\":{\"type\":\"string\",\"description\":\"区域编码\"},\"weather\":{\"type\":\"string\",\"description\":\"天气现象（汉字描述）\"},\"temperature\":{\"type\":\"string\",\"description\":\"实时气温，单位：摄氏度\"},\"winddirection\":{\"type\":\"string\",\"description\":\"风向描述\"},\"windpower\":{\"type\":\"string\",\"description\":\"风力级别，单位：级\"},\"humidity\":{\"type\":\"string\",\"description\":\"空气湿度\"},\"reporttime\":{\"type\":\"string\",\"description\":\"数据发布的时间\"},\"temperature_float\":{\"type\":\"string\",\"description\":\"温度浮动\"},\"humidity_float\":{\"type\":\"string\",\"description\":\"湿度浮动\"}},\"required\":[]}},\"infocode\":{\"type\":\"string\",\"description\":\"状态码\"}},\"required\":[\"status\",\"info\",\"infocode\"]}";

    String GAUD_WEATHER_REQUEST_INFO = "{\"url\":\"\",\"method\":\"GET\",\"headers\":{}}";

    String GAUD_WEATHER_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

    /**
     * 高德行政区域插件名、input schema、output schema、ICON、REQUEST_INFO、AUTHINFO
     */
    String GAUD_REGIONS = "Querying_Administrative_Regions";

    String GAUD_REGIONS_INPUT_SCHEMA
            = "{\"type\":\"object\",\"properties\":{\"keywords\":{\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"查询关键字\",\"type\":\"string\",\"description\":\"查询关键字，只支持单个关键词语搜索关键词支持：行政区名称、citycode、adcode\"},\"page\":{\"default\":\"1\",\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"页数\",\"type\":\"string\",\"description\":\"需要第几页数据\"},\"offset\":{\"default\":\"20\",\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"最外层返回数据个数\",\"type\":\"string\",\"description\":\"最外层返回数据个数\"},\"output\":{\"default\":\"JSON\",\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"返回数据格式类型\",\"type\":\"string\",\"description\":\"返回数据格式类型，可选值：JSON，XML\"}},\"required\":[]}";

    String GAUD_REGIONS_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"status\":{\"type\":\"string\",\"description\":\"返回结果状态值，值为0或1，0表示失败；1表示成功\"},\"info\":{\"type\":\"string\",\"description\":\"返回状态说明\"},\"infocode\":{\"type\":\"string\",\"description\":\"状态码\"},\"districts\":{\"type\":\"array\",\"description\":\"行政区列表\",\"items\":{\"type\":\"object\",\"properties\":{\"citycode\":{\"type\":\"string\",\"description\":\"城市编码\"},\"adcode\":{\"type\":\"string\",\"description\":\"区域编码\"},\"name\":{\"type\":\"string\",\"description\":\"行政区名称\"},\"center\":{\"type\":\"string\",\"description\":\"区域中心点\"},\"level\":{\"type\":\"string\",\"description\":\"行政区划级别\"},\"districts\":{\"type\":\"array\",\"description\":\"行政区列表\",\"items\":{\"type\":\"object\",\"properties\":{\"citycode\":{\"type\":\"string\",\"description\":\"城市编码\"},\"adcode\":{\"type\":\"string\",\"description\":\"区域编码\"},\"name\":{\"type\":\"string\",\"description\":\"行政区名称\"},\"center\":{\"type\":\"string\",\"description\":\"区域中心点\"},\"level\":{\"type\":\"string\",\"description\":\"行政区划级别\"}},\"required\":[]}}},\"required\":[]}}},\"required\":[\"status\",\"info\",\"infocode\"]}";

    String GAUD_REGIONS_REQUEST_INFO = "{\"url\":\"\",\"method\":\"GET\",\"headers\":{}}";

    String GAUD_REGIONS_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

    /**
     * 全网热搜榜插件名、input schema、output schema、ICON、REQUEST_INFO、AUTHINFO
     */
    String NETWORK_HOT = "Network_Hot_Search";

    String NETWORK_HOT_INPUT_SCHEMA
            = "{\"type\":\"object\",\"properties\":{\"Content-Type\":{\"default\":\"application/x-www-form-urlencoded\",\"location\":\"Headers\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"Content-Type\"}},\"required\":[\"Content-Type\"]}";

    String NETWORK_HOT_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"code\":{\"type\":\"integer\",\"description\":\"状态码\"},\"msg\":{\"type\":\"string\",\"description\":\"错误信息\"},\"result\":{\"type\":\"object\",\"description\":\"返回结果集\",\"properties\":{\"list\":{\"type\":\"array\",\"description\":\"热搜榜单\",\"items\":{\"type\":\"object\",\"properties\":{\"title\":{\"type\":\"string\",\"description\":\"热搜话题\"},\"hotnum\":{\"type\":\"integer\",\"description\":\"热搜榜指数\"},\"digest\":{\"type\":\"string\",\"description\":\"话题简介（可能为空）\"}},\"required\":[]}}},\"required\":[]}},\"required\":[\"code\",\"msg\"]}";

    String NETWORK_HOT_REQUEST_INFO
        = "{\"url\":\"\",\"method\":\"POST\",\"headers\":{\"Content-Type\":\"application/x-www-form-urlencoded\"}}";

    String NETWORK_HOT_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

    /**
     * 抖音热搜榜插件名、input schema、output schema、ICON、REQUEST_INFO、AUTHINFO
     */
    String TIKTOK_HOT = "TikTok_Hot_Search";

    String TIKTOK_HOT_INPUT_SCHEMA
            = "{\"type\":\"object\",\"properties\":{\"Content-Type\":{\"default\":\"application/x-www-form-urlencoded\",\"location\":\"Headers\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"Content-Type\"}},\"required\":[\"Content-Type\"]}";

    String TIKTOK_HOT_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"code\":{\"type\":\"integer\",\"description\":\"状态码\"},\"msg\":{\"type\":\"string\",\"description\":\"错误信息\"},\"result\":{\"type\":\"object\",\"description\":\"返回结果集\",\"properties\":{\"list\":{\"type\":\"array\",\"description\":\"热搜榜单\",\"items\":{\"type\":\"object\",\"properties\":{\"hotindex\":{\"type\":\"integer\",\"description\":\"热搜榜指数\"},\"label\":{\"type\":\"integer\",\"description\":\"标签类型，1新，2荐，3热\"},\"word\":{\"type\":\"string\",\"description\":\"热点话题\"}},\"required\":[]}}},\"required\":[]}},\"required\":[\"code\",\"msg\"]}";

    String TIKTOK_HOT_REQUEST_INFO
        = "{\"url\":\"\",\"method\":\"POST\",\"headers\":{\"Content-Type\":\"application/x-www-form-urlencoded\"}}";

    String TIKTOK_HOT_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

    /**
     * 世界时区时间插件名、input schema、output schema、ICON、REQUEST_INFO、AUTHINFO
     */
    String UNIVERSAL_ZONE = "Universal_Zone_Time";

    String UNIVERSAL_ZONE_INPUT_SCHEMA
            ="{\"type\":\"object\",\"properties\":{\"c\":{\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"区域\",\"type\":\"string\",\"description\":\"区域, 可选择:\\nafrica(非洲)\\namerica(美洲)\\nantarctica(南极洲)\\narctic(北极)\\nasia(亚洲)\\natlantic(大西洋)\\neurope(欧洲)\\npacific(太平洋)\"},\"Content-Type\":{\"default\":\"application/x-www-form-urlencoded\",\"location\":\"Headers\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"Content-Type\"}},\"required\":[\"c\",\"Content-Type\"]}";

    String UNIVERSAL_ZONE_OUTPUT_SCHEMA
        = "{\"type\":\"object\",\"properties\":{\"reason\":{\"type\":\"string\",\"description\":\"返回说明\"},\"result\":{\"type\":\"object\",\"description\":\"返回结果集\",\"properties\":{\"name\":{\"type\":\"string\",\"description\":\"区域\"},\"name_en\":{\"type\":\"string\",\"description\":\"区域英文名\"},\"tz\":{\"type\":\"array\",\"description\":\"信任区域\",\"items\":{\"type\":\"object\",\"properties\":{\"tz_name\":{\"type\":\"string\",\"description\":\"信任区域名称\"},\"tz_simple\":{\"type\":\"string\",\"description\":\"信任区域简写名称\"},\"time\":{\"type\":\"string\",\"description\":\"当前时间\"},\"timestamp\":{\"type\":\"number\",\"description\":\"时间戳\"},\"timezone\":{\"type\":\"string\",\"description\":\"时区\"},\"week\":{\"type\":\"string\",\"description\":\"星期\"},\"timezone_abbreviation\":{\"type\":\"string\",\"description\":\"时区缩写\"}},\"required\":[]}}},\"required\":[]},\"error_code\":{\"type\":\"integer\",\"description\":\"状态码\"}},\"required\":[\"reason\",\"error_code\"]}";

    String UNIVERSAL_ZONE_REQUEST_INFO
        = "{\"url\":\"\",\"method\":\"POST\",\"headers\":{\"Content-Type\":\"application/x-www-form-urlencoded\"}}";

    String UNIVERSAL_ZONE_AUTHINFO
        = "{\"scope\":\"SERVICE\",\"domain\":\"QUERY\",\"auth_keys\":[{\"target_name\":\"key\",\"auth_key\":\"\"}]}";

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

    String TOOL_CATEGORY_EFFICIENCY_TOOLS_ID = "3a9f8c2e-1b5d-4e7f-a2c6-8d3b9f1e5a7c";

    String TOOL_CATEGORY_MULTIMODAL_ID = "9d5a1c7e-2b8f-4e3d-a6c1-7b9f2d5e8a3c";

    String TOOL_CATEGORY_GEOLOCATION_AND_TRAVEL_ID = "5e8c2a7d-9b1f-4c3e-d6a8-3b7f9e5c2d1a";

    String TOOL_CATEGORY_NEWS_AND_UPDATE_ID = "7f2d9a5c-1b8e-4c3f-d7a9-6b5c8f2e3a1d";

    String TOOL_CATEGORY_QUERY_AND_SEARCH_ID = "2c7e9a5d-1f8b-4d3e-b9a6-5c8f1e7d2a3b";
    /**
     * 云产品部署类型
     */
    interface EnvType {
        String SIMPLE = "simple";

        String HC = "hc";

        String HCS = "hcs";
    }

    /**
     * agent类型
     */
    String AGENT_TYPE = "agent";

    /**
     * controller类型
     */
    String CONTROLLER_TYPE = "controller";

    /**
     * 知识库类型
     */
    String REPO_TYPE = "repo";

    /**
     * 插件类型
     */
    String TOOL_TYPE = "tool";

    /**
     * 插件类型
     */
    String PLUGIN_TYPE = "plugin";

    /**
     * 工作流类型
     */
    String WORKFLOW_TYPE = "workflow";

    /**
     * 卡片类型
     */
    String EXPORT_WORKFLOW = "WORK";

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
     * 智能生成描述的兜底回复
     */
    String DESCRIPTIOPN
        = "该智能体是一款多功能人工智能助手，具备理解用户需求、提供信息响应和执行任务协助的能力。它可根据不同场景灵活调整服务方式，支持问答交互、内容生成、建议提供等常见功能，致力于为用户提供高效、便捷的智能化体验。适用于各类日常应用，是您值得信赖的通用AI伙伴。";

    /**
     * 智能生成描述的兜底回复英文版
     */
    String DESCRIPTIOPN_EN
        = "This intelligent agent is a multifunctional AI assistant capable of understanding user needs, providing informational responses, and assisting with task execution. It can flexibly adjust its service methods according to different scenarios, supporting common functions such as Q&A interaction, content generation, and suggestion provision, aiming to deliver an efficient and convenient intelligent experience for users. Suitable for various daily applications, it is a trustworthy general AI companion for you.";

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
     * 导出文件
     */
    String EXPORT = "export";

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
     * 云商店通道类型
     */
    String CLOUD_STORE_CHANNEL = "CLOUD_STORE";

    /**
     * 工作流关联关系唯一值模板（不带版本）
     */
    String UNIQUE_MAPPING_KEY_FORMAT = "%s_%s";

    /**
     * 异常类别
     */
    String EXCEPTION_CATEGORY = "异常";

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
     * 知识库相关
     */

    String EXTRA_KEY = "key";

    String EXTRA_VALUE = "value";

    int EXTRA_KEY_LENGTH = 64;

    int EXTRA_VALUE_LENGTH = 255;

    /**
     * 工具不存在时默认工具名
     */
    String TOOL_NOT_EXIST = "unknown";

    /**
     * 预置的供应商及模型归属空间及项目id
     */
    String SYSTEM_DEFAULT = "SYSTEM";

    /**
     * agent的发布状态
     */
    String AGENT_PUBLISHED = "published";

    /**
     * 工作流涉及大模型配置节点
     */
    List<String> LLM_CONFIG_NODE = List.of(NodeType.LLM.getType(), NodeType.QUESTIONER.getType(),
        NodeType.INTENT_DETECTION.getType(), NodeType.INTENT_COMPLEX_INTENT.getType(), NodeType.TASK_FLOW.getType(),
        NodeType.AGENT.getType());

    interface ProviderParam {
        String NO_AUTH = "NO_AUTH";

        String IMPORT_DEFAULT_PROVIDER_NAME = "import-default";
    }

    /**
     * OpenAPI中的扩展字段，将插件转换为OpenAPI定义时使用
     */
    interface OpenAPI {
        /**
         * 参数在path
         */
        String IN_PATH = "path";

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

        /**
         * HIS_IAM鉴权方式
         */
        String HIS_IAM = "HisIam";

        /**
         * HIS_IAM鉴权方式参数
         */
        String IAM_URL = "x-iam-url";

        String IAM_ACCOUNT = "x-iam-account";

        String IAM_PROJECT = "x-iam-project";

        String IAM_SECRET = "x-iam-secret";

        String IAM_ENTERPRISE = "x-iam-enterprise";

        /**
         * SGOV鉴权方式
         */
        String HIS_SGOV = "HisSgov";

        /**
         * SGOV鉴权方式参数
         */
        String APP_ID = "x-app-id";

        String CREDENTIAL = "x-credential";

        String SGOV_URL = "x-sgov-url";

        /**
         * 自定义IAM鉴权方式
         */
        String CUSTOM_IAM = "custom_iam";

        /**
         * custom iam url
         */
        String CUSTOM_IAM_URL = "x-custom-iam-url";

        /**
         * custom iam domain
         */
        String CUSTOM_IAM_DOMAIN = "x-custom-iam-domain";

        /**
         * custom iam project
         */
        String CUSTOM_IAM_PROJECT = "x-custom-iam-project";

        /**
         * custom iam user
         */
        String CUSTOM_IAM_USER = "x-custom-iam-user";

        /**
         * custom iam password
         */
        String CUSTOM_IAM_PASSWORD = "x-custom-iam-password";

        /**
         * custom iam ak
         */
        String CUSTOM_IAM_AK = "x-custom-iam-ak";

        /**
         * custom iam sk
         */
        String CUSTOM_IAM_SK = "x-custom-iam-sk";
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
        String STREAMABLE_HTTP = "streamable_http";
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
    int MAX_TRIGGER_NUMS = 3;

    /**
     * 消息模板数量限制
     */
    int MAX_MESSAGE_TEMPLATE_NUMS = 200;

    /**
     * Excel文件最大行数限制（预检查）
     */
    int EXCEL_MAX_ROWS_PRECHECK = 201;

    /**
     * Excel文件最大列数限制
     */
    int EXCEL_MAX_COLUMNS = 20;

    /**
     * 工作流触发器数量限制
     */
    int MAX_TRIGGER_WORKFLOW_NUMS = 3;

    /**
     * 分隔符
     */
    String SEPARATOR = ",";

    interface ModelParam {
        String MODEL = "model";

        String DEFAULT_MODEL = "default_model";

        String MODEL_PUBLISH_STATUS_ONLINE = "online";

        String MODEL_NAME = "model_name";

        String MODEL_TYPE = "model_type";

        String MODEL_API_TYPE = "openai";

        String MODEL_DEPLOYMENT_ID = "model_deployment_id";

        String DEFAULT_MODEL_SWITCH = "default_model_switch";

        String FREQUENCY_PENALTY = "frequency_penalty";

        String MAX_TOKENS = "max_tokens";

        String EXTENSION = "extension";

        String VL_ENABLE = "vl_enable";

        String THINKING = "thinking";

        String TYPE = "type";
    }

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

    interface MAS {
        /**
         * MAS MCP Auth APIKEY
         */
        String APIKEY = "X-Studio-Apikey";

        /**
         * MAS MCP Auth APPCODE
         */
        String APPCODE = "X-Apig-Appcode";

        /**
         * 空间映射类型
         */
        String WORKSPACE_SOURCE_TYPE = "MAS";
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

        String CONTROLLER_TYPE = "Controller";
    }

    /**
     * 委托名环境变量的名称
     */
    String AGENCY_NAME_KEY = "agency.name";

    /**
     * 部署环境的环境变量名称
     */
    String ENV_TYPE_KEY = "env.type";

    /**
     * 导入导出V2版本标识
     */
    String EXPORT_V2_TAG = "EXPORT_V2";

    /**
     * 工作空间
     */
    interface WORKSPACE {
        interface TYPE {
            /**
             * 个人空间
             */
            String PERSON_TYPE = "PERSON";
            /**
             * 团队空间
             */
            String TEAM_TYPE = "TEAM";
        }

        interface STATUS {
            /**
             * 可用
             */
            String ENABLE = "ENABLE";
            /**
             * 不可用
             */
            String DISABLE = "DISABLE";
        }

        /**
         * 个人空间名称
         */
        String PERSON_NAME = "个人空间";

        /**
         * 默认个人空间ID
         */
        String DEFAULT_PERSON_ID = "default";
    }

    /**
     * 字节转换
     */
    int KB = 1024;

    interface SKU_ATTR_CODE {

        String TEAM_SPACE_COUNT = "team_spaces_count";

        String TEAM_SPACE_MEMBER_COUNT = "members_count";

        String APP_COUNT = "app_count";

        String CROSS_SPACE_COPY = "cross_space_replication_enable";

        String EXPORT_AND_IMPORT = "agent_export_import_enable";
    }

    interface MCP_AUTH_TYPE {
        String USE_IAM_TOKEN = "USE-IAM-TOKEN";

        String IAM_TOKEN = "IAM-TOKEN";
    }

    /**
     * 文件的软删除后缀
     */
    String DELETED_SUFFIX = ".deleted";

    /**
     * 资源无限制标识
     */
    Long UNLIMITED_RESOURCE_VALUE = -1L;

    /**
     *  Dify迁移相关定义
     */
    interface DIFY {
        String TASK_WORKFLOW = "workflow";

        String CHAT_WORKFLOW = "advanced-chat";

        String START = "start";

        String END = "end";

        String LOOP_START = "loop-start";

        String ITERATION_START = "iteration-start";

        String CONFIG_DEFAULT_NAME = "isDefaultName";

        String TEMPERATURE = "temperature";

        String TOP_P = "top_p";

        String THINKING = "enable_thinking";

        String ENABLE_HISTORY = "enable_history";

        String SYS_VARIABLE = "sys";

        String ENV_VARIABLE = "env";

        String CONVERSATION_VARIABLE = "conversation";

        String SYSTEM_PROMPT = "system_prompt";

        String TEMPLATE_CONTENT = "template_content";

        String ERROR_STRATEGY = "error_strategy";

        String FAIL_BRANCH = "fail-branch";

        String HANDLE_TYPE = "handle_type";

        String EXCEPTION_PROCESS = "exception_process";

        String ERROR_BRANCH = "errorbranch";

        String INTERRUPT = "interrupt";

        String DEFAULT_VALUE = "default-value";

        String LOOP_BODY = "loop_body";

        // 循环类型
        String LOOP_TYPE = "loop_type";

        String TRIGGER = "trigger";

        String CODE = "code";

        String EXEC_ENV = "exec_env";

        String URL = "url";

        String HEADERS = "headers";

        String BODY = "body";

        String STATUS_CODE = "status_code";

        String ERROR_MESSAGE = "error_message";

        String METHOD = "method";

        String ENDPOINT = "endpoint";

        String REQUEST_TYPE = "request_type";

        String REQUEST_BODY = "request_body";

        String PATH = "path";

        String QUERY = "query";

        String AUTH_INFO = "auth_info";

        String EXCEPTION_ENABLE = "exception_enable";

        String EXCEPTION_SUPPRESSION = "exception_suppression";

        String MAX_ITERATION = "max_iteration";

        String IS_IN_LOOP = "isInLoop";

        String IS_IN_ITERATION = "isInIteration";

        String DESCRIPTION_TEXT = "descriptionText";

    }

    /**
     * Skill 相关
     */
    interface Skill {

        // {user-id}/skills/{skill-id}/{version-id}/{skill-name.zip}
        String SKILL_VERSION_FILE_PATH_TEMPLATE = "%s/skills/%s/%s/%s";

        String SKILL_VERSION_DIR_TEMPLATE = "%s/skills/%s/%s";

        String SKILL_BASE_PATH_TEMPLATE = "%s/skills/%s";

        String NAME = "name";

        String DESCRIPTION = "description";

    }
}
