/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.constant;

import com.fasterxml.jackson.core.type.TypeReference;

import java.util.Map;

/**
 * 常量
 *
 */
public interface Constants {
    /**
     * JsonString 解析 Map
     */
    @SuppressWarnings({"checkstyle: all"})
    TypeReference<Map<String, Object>> MAP_TYPE_REFERENCE = new TypeReference<>() {};

    /**
     * 最新发布版本
     */
    String LATEST_PUBLISH_VERSION = "latest";

    /**
     * 百宝箱发布版本
     */
    String TREASURE_PUBLISH_VERSION = "treasure";

    /**
     * OBS发布元数据目录
     */
    String OBS_METADATA_DIR = "metadata";

    /**
     * 下划线
     */
    String UNDERLINE_STR = "_";

    /**
     * lakeSearch endpoint
     */
    String LAKE_SEARCH_ENDPOINT =
        "/v1/1ed40ceefc8d40f8b884edb6a84e7768/applications/fb9731ab-7085-474fb6c7-64473586f0f3/uni-search";

    /**
     * id
     */
    String ID = "id";

    /**
     * ir version id
     */
    String VERSION_ID = "version_id";

    /**
     * ir name
     */
    String NAME = "name";

    /**
     * 中文语言id
     */
    String ZH_LANGUAGE_ID = "zh";

    /**
     * 使用kerberos认证的lakeSearch实现类名
     */
    String LAKE_SEARCH_SERVICE_NAME_WITH_KERBEROS = "KerLakeSearch";

    /**
     * KooSearch限流错误码
     */
    String KOS_RATE_LIMIT_ERROR_CODE = "kos.00050008";

    /**
     * HCS环境
     */
    String HCS_ENV = "HCS";

    /**
     * 中文
     */
    String ZH_CN = "zh-cn";

    /**
     * 工具id
     */
    String TOOL_ID = "tool_id";

    /**
     * true字符常量
     */
    String TRUE = "true";

    /**
     * ir version id
     */
    String TOOL_USE = "ToolUse";

    /**
     * 插件已授权
     */
    String AUTHENTICATED = "AUTHENTICATED";

    /**
     * 插件未授权
     */
    String UNAUTHENTICATED = "UNAUTHENTICATED";

    /**
     * 插件无需鉴权
     */
    String AUTHENTICATED_NONE = "NONE";

    /**
     * 图片base64开头
     */
    String IMAGE_BASE64 = "data:image/";

    /**
     * 记忆库配置
     */
    String MEMORY_CONFIG = "memory_config";


    /**
     * 工作流相关常量定义
     */
    interface Workflow {
        /**
         * 全局配置 key
         */
        String CONFIGS = "configs";

        /**
         * 插件校验
         */
        String NODES = "nodes";

        /**
         * 敏感词 key
         */
        String CONTENT_REVIEW = "content_review";

        /**
         * 安全护栏 key
         */
        String SAFETY_BARRIER = "safety_barrier";

        /**
         * 开关
         */
        String ENABLED = "enabled";

        /**
         * 用户画像配置
         */
        String USER_PROFILE = "user_profile";

        /**
         * 工作流节点上的记忆开关
         */
        String ENABLE_MEMORY = "enable_memory";

        /**
         * 九问IR中的记忆配置
         */
        String MEMORY = "memory";

        /**
         * 记忆库配置
         */
        String MEMORY_CONFIG = "memory_config";

        /**
         * 单组敏感词最大长度
         */
        int CR_KEYWORDS_MAX_LENGTH = 1000;

        /**
         * 单类型敏感词最大组数
         */
        int CR_GROUP_MAX_SIZE = 10;

        /**
         * 输入审核最大长度
         */
        int INPUT_TEXT_MAX_LENGTH = 1000;

        /**
         * 输出审核最大长度
         */
        int OUTPUT_TEXT_MAX_LENGTH = 1000;

        /**
         * 替换词最大长度
         */
        int REPLACE_WORD_MAX_LENGTH = 1000;

        /**
         * 字符串常量 工作流汇中环境信息
         */
        String ENVIRONMENT = "environment";

        interface Event {
            /**
             * 消息事件event字段
             */
            String EVENT = "event";

            /**
             * 消息事件data字段
             */
            String DATA = "data";

            /**
             * 消息事件createdTime字段
             */
            String CREATED_TIME = "createdTime";
        }
    }

    /**
     * 请求头相关常量定义
     */
    interface Header {
        /**
         * X-Auth-Token常量
         */
        String X_AUTH_TOKEN = "X-Auth-Token";

        /**
         * 请求头X-Language常量
         */
        String X_LANGUAGE = "X-Language";

        /**
         * apikey 请求头
         */
        String AUTHORIZATION = "Authorization";

        /**
         * apikey value 前缀
         */
        String AUTHORIZATION_PREFIX = "Bearer ";

        /**
         * X-Subject-Token 常量
         */
        String X_SUBJECT_TOKEN = "X-Subject-Token";

        /**
         * X_ASSET_APP_INVOKE_IN_FREE_TRIAL
         */
        String X_ASSET_APP_INVOKE_IN_FREE_TRIAL = "x-asset-app-invoke-in-free";

        /**
         * X_ASSET_APP_ID
         */
        String X_ASSET_APP_ID = "x-asset-app-id";

        /**
         * X_ASSET_APP_CONVERSATION_ID
         */
        String X_ASSET_APP_CONVERSATION_ID = "x-asset-app-conversation-id";
    }

    interface CustomModel {

        /**
         * userid
         */
        String CUSTOM_USER_ID = "cust-userid";

        /**
         * token
         */
        String CUSTOM_TOKEN = "cust-token";
    }


    /**
     * 应用类型
     */
    interface AppType {
        /**
         * 工作流
         */
        String WORKFLOW = "workflow";

        /**
         * Agent
         */
        String AGENT = "agent";

        /**
         * 控制器
         */
        String CONTROLLER = "controller";

        /**
         * 高代码智能体
         */
        String AGENT_NEW = "agent_new";
    }

    interface KnowledgeBase {
        /**
         * 第三方知识库
         */
        String THIRD_PARTY_KNOWLEDGE_BASE = "thirdPartyKnowledgeBase";

        /**
         * 默认知识库
         */
        String KNOWLEDGE_BASE = "knowledgeBase";

        /**
         * 数据存储
         */
        String KNOWLEDGE_BASE_DATESET_STORAGE = "knowledgeBaseDatesetStorage";

        /**
         * 三方知识库连接
         */
        String THIRD_PARTY_KNOWLEDGE_BASE_CONNECTION = "thirdPartyKnowledgeBaseConnection";

        /**
         * 知识库节点文档返回数目
         */
        String TOP_K = "top_k";

        /**
         * 知识库节点默认返回个数
         */
        int DEFAULT_TOP_K = 5;

        /**
         * 意图识别节点绑定知识库键值
         */
        String RECALL_THRESHOLD = "recall_threshold";

        /**
         * 意图识别节点默认知识库阈值
         */
        float DEFAULT_RECALL_THRESHOLD = 0.5f;

        /**
         * 知识库FAQ直出阈值键值
         */
        String FAQ_THRESHOLD = "faq_threshold";

        /**
         * 知识库FAQ直出阈值默认值
         */
        float DEFAULT_FAQ_THRESHOLD = 0.9f;

        /**
         * 知识库检索模式
         */
        String SEARCH_MODE = "search_mode";

        /**
         * FAQ拓展搜索
         */
        String NEED_EXTRAS_FAQ_SEARCH = "need_extras_faq_search";

        /**
         * 召回图片
         */
        String RETRIEVE_IMAGE = "retrieve_image";

        /**
         * 展示来源
         */
        String SHOW_SOURCE = "show_source";


    }

    /**
     * ENS OBS 存储路径
     */
    String ESN_OBS_PATH = "abc/56A894768BBC281CEE9CF911490E620";

    /**
     * 系统用户免校验标记 request attribute key
     */
    String SYSTEM_USER_SKIP_ATTR = "SYSTEM_USER_SKIP";

    /**
     * 服务部署环境类型
     */
    interface EnvType {
        /**
         * lite 版本
         */
        String SIMPLE = "simple";

        /**
         * 公有云版本
         */
        String HC = "hc";

        /**
         * 私有云版本
         */
        String HCS = "hcs";
    }
}
