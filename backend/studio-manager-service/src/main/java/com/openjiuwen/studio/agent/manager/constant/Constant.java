/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.constant;

/**
 * 常量
 *
 */
public interface Constant {
    interface Workflow {
        String NODE_START = "node_start";

        String NODE_END = "node_end";

        String REF = "ref";

        String REF_START = "${";

        String RAW_END = ".raw_output}";

        String TOKENS = "tokens";

        /**
         * 流式调用workflow超时时间
         */
        long WORKFLOW_TIMEOUT = 120000L;
    }

    interface AppType {
        String WORKFLOW = "workflow";

        String AGENT = "agent";

        String CONTROLLER = "controller";

        String DEEP_RESEARCH = "deepresearch";

        String PLAN_EXECUTE = "plan";
    }

    interface Obs {
        String CONTENT = "CONTENT";

        String MD5 = "MD5";
    }

    interface Jiuwen {
        String RESPONSE_MODE_STREAMING = "streaming";

        String RESPONSE_MODE_BLOCKING = "blocking";

        String USER_MSG_FIELD = "query";

        String END_NODE_DEFAULT_OUTPUT_FIELD = "responseContent";

        String NODE_TYPE_PREFIX = "jiuwen.";

        String ERROR_CODE_FIELD = "code";

        String ERROR_MSG_FIELD = "message";

        /**
         * 控制器指定执行workflow id序列
         */
        String WORKFLOW_SEQUENCE_FIELD = "workflowSequence";

        /**
         * 控制器激活的workflow id序列
         */
        String ACTIVE_WORKFLOWS_FIELD = "activeWorkflows";

        /**
         * 控制器指定意图参数
         */
        String INTENT_FIELD = "intent";

        String IMAGE_TYPE = "image_url";

        String VIDEO_TYPE = "video_url";
    }

    interface DeepResearch {
        String MESSAGE_FIELD = "message";

        String FEEDBACK_FIELD = "interrupt_feedback";

        String TEMPLATE_FIELD = "template";

        String FILE_NAME_FIELD = "file_name";

        String FILE_PATH_FIELD = "file_path";

        String IS_TEMPLATE_FIELD = "is_template";

        String FEEDBACK_ACCEPTED = "accepted";

        String SUB_REPORTER_NODE = "sub_reporter";
    }

    interface File {
        /**
         * txt文件后缀
         */
        String TXT = "txt";

        /**
         * doc文件后缀
         */
        String DOC = "doc";

        /**
         * docx文件后缀
         */
        String DOCX = "docx";

        /**
         * xlsx 文件后缀
         */
        String XLSX = "xlsx";

        /**
         * xls 文件后缀
         */
        String XLS = "xls";

        /**
         * csv文件后缀
         */
        String CSV = "csv";
    }

    interface Agent {
        /**
         * 百宝箱Agent类型
         */
        String TREASURE_BOX_AGENT = "PUBLISHED";

        /**
         * DEBUG调用类型
         */
        String DEBUG = "DEBUG";

        /**
         * EXPERIMENT调用类型
         */
        String EXPERIMENT = "EXPERIMENT";

        /**
         * API调用类型
         */
        String API = "API";

        /**
         * Agent运行模式，取值DEBUG或PUBLISHED，在请求头中
         */
        String INVOKE_HEADER_KEY = "X-Invoke-Mode";

        /**
         * 记忆参数用户级生命周期
         */
        String MEMORY_VAR_LIFE_CYCLE_USER = "user";

        /**
         * 记忆参数会话级生命周期
         */
        String MEMORY_VAR_LIFE_CYCLE_CONVERSATION = "conversation";
    }

    interface Common {
        String X_AUTH_TOKEN = "X-Auth-Token";

        String X_SUBJECT_TOKEN = "X-Subject-Token";

        String INVOKE_MOD_DEBUG = "debug";

        String INVOKE_MOD_PUBLISHED = "published";

        String AUTHORIZATION = "Authorization";

        String X_USER_ID = "X-USER-ID";

        String X_KNOWLEDGE_ENDPOINT = "X-Knowledge-Endpoint";

        String X_WORKSPACE_ID = "X-Workspace-Id";
    }

    /**
     * 生成追问prompt
     */
    String ADDITIONAL_QUESTIONS_PROMPT = "prompts/additional_questions_prompt.pt";

    /**
     * 生成英文追问prompt
     */
    String ADDITIONAL_QUESTIONS_PROMPT_EN = "prompts/additional_questions_prompt_en.pt";

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
     * 生成记忆片段prompt
     */
    String MEMORY_CHUNK_PROMPT = "prompts/memory_chunk_prompt.pt";

    /**
     * 模型复调次数
     */
    int MODEL_CALLS = 3;

    /**
     * 最多生成的追问个数
     */
    int MAX_QUESTION_NUMS = 3;

    /**
     * promptBuilder流式返回超时时间
     */
    long PROMPT_BUILDER_STREAM_TIMEOUT = 120000L;

    /**
     * 字符串常量
     */
    String CONFIGS = "configs";

    /**
     * 字符串常量
     */
    String MODEL_CONFIG = "modelConfig";

    /**
     * 字符串常量
     */
    String LLM_CONFIG = "llm_config";

    /**
     * 字符串常量
     */
    String CONTEXT = "context";

    /**
     * 字符串常量
     */
    String METADATA = "metadata";

    /**
     * 字符串常量
     */
    String CONTENT_TYPE = "Content-Type";

    /**
     * 字符串常量
     */
    String APPLICATION_JSON = "application/json";

    /**
     * form-data
     */
    String MULTIPART_FORM_DATA = "multipart/form-data";

    /**
     * 字符串常量
     */
    String UTF_8 = "UTF-8";

    /**
     * 字符串常量
     */
    String USER = "user";

    /**
     * 字符串常量
     */
    String NAME = "name";

    /**
     * 用户自定义追问提示词模板变量
     */
    String USER_PROMPT = "user_prompt";

    /**
     * 字符串常量
     */
    String PROMPT = "prompt";

    /**
     * 字符串常量
     */
    String HISTORY_MESSAGES = "history_messages";

    /**
     * 字符串常量
     */
    String CHOICES = "choices";

    /**
     * 字符串常量
     */
    String MESSAGE = "message";

    /**
     * 字符串常量
     */
    String CONTENT = "content";

    /**
     * 分隔符
     */
    String SEPARATOR = ",";

    /**
     * 字符串常量
     */
    String LAST_MEMORY_CHUNK = "last_memory_chunk";

    /**
     * POC环境
     */
    String ENV_SIMPLE = "simple";

    /**
     * 网页发布通道类型
     */
    String WEB_PAGE_CHANNEL = "WEB_PAGE";

    /**
     * 应用百宝箱通道类型
     */
    String APP_STORE_CHANNEL = "APP_STORE";

    /**
     *云商店通道类型
     */
    String CLOUD_STORE_CHANNEL = "CLOUD_STORE";

    /**
     * UniFactory图片解析方式：TEXT
     */
    String TEXT_STR = "TEXT";

    /**
     * UniFactory切分模式：AUTO
     */
    String AUTO_MODE = "AUTO";

    /**
     * AGENT运行失败报错内容
     */
    String AGENT_ERROR_CONTENT = "Agent运行失败，错误码：%s，错误信息：%s，请参考产品文档解决或联系系统管理员。";

    /**
     * request-id
     */
    String REQUEST_ID = "request-id";

    String X_REQUEST_ID = "X-Request-Id";

    String TASK_ID = "task-id";

    String X_TASK_ID = "X-Execution-Id";

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
     * 插件响应状态码
     */
    interface ToolCode {
        /**
         * 成功
         */
        int SUCCEED = 1;

        /**
         * 失败
         */
        int FAILED = 0;
    }

    /**
     * 任务状态
     */
    interface TaskStatus {
        /**
         * 成功
         */
        String SUCCESS = "SUCCESS";

        /**
         * 失败
         */
        String ERROR = "ERROR";

        /**
         * 排队中
         */
        String PENDING = "PENDING";

        /**
         * 解析中
         */
        String RUNNING = "RUNNING";

        /**
         * 完成
         */
        String FINISHED = "FINISHED";
    }

    /**
     * KooSearch中停用知识库被检索时的错误码
     */
    String KOS_CLOSE_REPO_ERROR_CODE = "KOS.00080003";

    /**
     * KooSearch中ES错误
     */
    String KOS_ES_ERROR_CODE = "KOS.00020001";

    /**
     * 字符串
     */
    String X_AUTH_TOKEN = "X-Auth-Token";

    /**
     * 工行自定义用户Id
     */
    String ICBC_USER_ID = "cust-userid";

    String OWNER_PROJECT_ID = "X-Owner-Project-Id";

    /**
     * 性能相关常量
     */
    interface Performance {
        /**
         * 记录结束时间
         */
        String END = "END";

        /**
         * 记录管理端耗时
         */
        String MANAGER = "MANAGER";

        /**
         * 记录请求引擎开始时间
         */
        String ENGINE_START = "ENGINE_START";

        /**
         * 记录请求引擎结束时间
         */
        String ENGINE_END = "ENGINE_END";

        /**
         * 记录首事件时间
         */
        String FIRST_EVENT = "FIRST_EVENT";

        /**
         * 加载ir耗时
         */
        String LOAD_IR = "LOAD_IR";
    }

    /**
     * 心跳模式
     */
    interface Heartbeat {
        String ALWAYS = "always";

        String DEBUG = "debug";

        String OFF = "off";
    }

    /**
     * 知识检索节点
     */
    interface KnowledgeRetrievalNode {

        /**
         * 判断是否是智能体中检索节点
         */
        String RETRIEVAL = "retrieval";

        /**
         * 工作流中知识检索节点的类型为Plugin
         */
        String PLUGIN = "Plugin";
    }

    interface KnowledgeConstant {

        /**
         * 图片ID在redis缓存中key的前缀
         */
        String KNOWLEDGE_IMAGE_CACHE_PREFIX = "knowledge:image:";

        /**
         * 文件id在redis缓存中key的前缀
         */
        String KNOWLEDGE_FILE_CACHE_PREFIX = "knowledge:file:";

        String KNOWLEDGE_FILE_TYPE_DOC = "doc";

        String KNOWLEDGE_FILE_TYPE_FAQ = "faq";

        /**
         * 分页每页最大展示数量，kooSearch限制最大数量100
         */
        int KNOWLEDGE_MAX_PAGE_SIZE = 100;
    }
}
