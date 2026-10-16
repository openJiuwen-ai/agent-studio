/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.base.exception;

import lombok.Getter;

import org.springframework.http.HttpStatus;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

@Getter
public enum ErrorCode {

    /**
     * 服务内部错误，兜底的错误
     */
    SERVER_INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0000", "Internal Server Error."),

    /**
     * KooSearch调用失败
     */
    KOO_SEARCH_SERVICE_EXCEPTION(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0001", "Call KooSearch Error."),

    /**
     * lakeSearch服务调用异常
     */
    LAKE_SEARCH_SERVICE_EXCEPTION(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0002", "LakeSearch Service exception."),

    /**
     * obs连接失败
     */
    OBS_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0003", "Obs service failed."),

    /**
     * 知识库配置信息有误
     */
    INVALID_KNOWLEDGE_REPO_REQUEST(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0004", "Invalid knowledge repo request."),

    /**
     * 流式接口执行超时
     */
    STREAM_INTERFACE_EXECUTE_TIMEOUT(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0005", "Api request timeout"),

    /**
     * 构建SSLContext失败
     */
    SSL_CONTEXT_BUILD_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0006", "Build ssl context failed."),

    /**
     * 获取IAM上下文失败
     */
    IAM_CONTEXT_OBTAIN_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0007", "Get request iam context failed."),

    /**
     * 获取虚拟Token失败
     */
    VIRTUAL_TOKEN_OBTAIN_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0008", "Get virtual token failed."),

    /**
     * 获取解析后Token失败
     */
    TOKEN_OBTAIN_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0009", "Get token result error."),

    /**
     * 获取临时凭证失败
     */
    VIRTUAL_CREDENTIAL_OBTAIN_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0010", "Get virtual credential error."),

    /**
     * 读取Token文件失败
     */
    IAM_TOKEN_READ_FILE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0011", "read token file error."),

    /**
     * 获取缓存Token失败
     */
    IAM_TOKEN_CACHE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0012", "Get cache key error."),

    /**
     * 获取Token失败
     */
    IAM_TOKEN_ANALYZE_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0013", "Analyze Iam token error."),

    /**
     * 生成Token失败
     */
    IAM_TOKEN_GENERATE_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0014", "Generate iam token error."),

    /**
     * 转换Token失败
     */
    IAM_TOKEN_CONVERT_USER_TO_DOMAIN_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0015",
        "Convert to domain error."),

    /**
     * 系统配置项错误
     */
    SYSTEM_PARAMS_CONFIG_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0016", "system_params_config_error."),

    /**
     * obs文件内容为空
     */
    OBS_EMPTY_FILE_CONTENT_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0017", "Obs file content is empty."),

    /**
     * obs对象下载失败
     */
    OBS_OBJECT_DOWNLOAD_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0018", "Obs object download filed."),

    /**
     * obs对象删除失败
     */
    OBS_OBJECT_DELETE_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0019", "Obs object delete filed."),

    /**
     * OBS文件数量超出配置限制
     */
    OBS_FILE_COUNT_OUT_LIMIT(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0020",
        "OBS file count exceeds the configured limit."),

    /**
     * KooSearch认证模式配置错误
     */
    KOO_SEARCH_AUTH_MODE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0021", "incorrect KooSearch AuthMode."),

    /**
     * LakeSearch认证模式配置错误
     */
    LAKE_SEARCH_AUTH_MODE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0022", "incorrect LakeSearch AuthMode."),

    /**
     * 获取知识库默认连接信息错误
     */
    FAILED_TO_FIND_DEFAULT_CONNECTION_INFO(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0023",
        "Fail to get knowledge base default connection information."),

    /**
     * 知识源类型错误
     */
    KNOWLEDGE_SOURCE_TYPE_IS_WRONG(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0024", "Knowledge source type is wrong."),

    /**
     * 默认知识库连接错误
     */
    KNOWLEDGE_BASE_DEFAULT_CONNECTION_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0025",
        "Connect to Knowledge base failed."),

    /**
     * 知识库连接失败（未配置知识库或默认连接信息缺失）
     */
    KNOWLEDGE_BASE_NOT_CONFIGURED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "0026",
        "Connect to knowledge base failed."),

    /**
     * 仅支持配置默认知识库连接（请求的 kb_connection_id 不是默认占位 id）
     */
    DEFAULT_KNOWLEDGE_BASE_CONNECTION_UNSUPPORTED(HttpStatus.BAD_REQUEST.value(), "0027",
        "Only the default knowledge base connection is supported for configuration."),

    /********************************************** 业务通用的一些错误码 *************************************************/

    /**
     * 方法参数校验异常
     */
    METHOD_ARGUMENT_INVALID(HttpStatus.BAD_REQUEST.value(), "1000", "Method parameter is invalid"),

    /**
     * 参数校验异常
     */
    INVALID_PARAMETER(HttpStatus.BAD_REQUEST.value(), "1001", "parameter is invalid"),

    /**
     * 无权限
     */
    NO_PERMISSION(HttpStatus.FORBIDDEN.value(), "1002", "No permission"),

    /**
     * 资源不存在，使用此错误码时，必须自己指定抛出的异常信息
     */
    RESOURCE_NOT_EXIST(HttpStatus.NOT_FOUND.value(), "1003", "resource not exist."),

    /**
     * 资源名称重复，使用此错误码时，必须自己指定抛出的异常信息
     */
    RESOURCE_NAME_DUPLICATE(HttpStatus.BAD_REQUEST.value(), "1004", "Resource name duplicate."),

    /**
     * 资源ID重复，使用此错误码时，必须自己指定抛出的异常信息
     */
    RESOURCE_ID_DUPLICATE(HttpStatus.BAD_REQUEST.value(), "1005", "Resource id duplicate."),

    /**
     * 资源超出限制，使用此错误码时，必须自己指定抛出的异常信息
     */
    RESOURCE_CAPACITY_LIMIT_ERROR(HttpStatus.BAD_REQUEST.value(), "1006", "Resource count over limit."),

    /**
     * 非法文件名
     */
    ILLEGAL_FILE_NAME(HttpStatus.BAD_REQUEST.value(), "1007", "The file name is illegal."),

    /**
     * 非法文件类型
     */
    ILLEGAL_FILE_TYPE(HttpStatus.BAD_REQUEST.value(), "1008", "The file type is illegal."),

    /**
     * 文件大小超过系统限制
     */
    FILE_SIZE_EXCEED_LIMIT(HttpStatus.BAD_REQUEST.value(), "1009", "The file size exceeds the system limit"),

    /**
     * Icon Name 不合规
     */
    INVALID_ICON_NAME(HttpStatus.BAD_REQUEST.value(), "1010", "Invalid icon name."),

    /**
     * 查询知识库的license失败
     */
    QUERY_KNOWLEDGE_BASE_LICENSE_ITEM_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "1011",
        "query license item error"),

    /**
     * 任务已在执行中
     */
    TASK_IS_ALREADY_RUNNING(HttpStatus.BAD_REQUEST.value(), "1012", "Task is already running"),

    /**
     * 知识库不存在
     */
    KNOWLEDGE_BASE_NOT_EXIST(HttpStatus.NOT_FOUND.value(), "1014", "The knowledge base not exist."),

    /**
     * 知识库分层规则不存在
     */
    KNOWLEDGE_SEGMENT_RULE_NOT_EXIST(HttpStatus.NOT_FOUND.value(), "1015", "The segmentation rule not exist."),

    /**
     * 记忆不属于当前agent
     */
    MEMORY_NOT_BELONG_AGENT(HttpStatus.FORBIDDEN.value(), "1016", "This memory is not belong to the agent."),

    /**
     * 记忆不属于当前用户
     */
    MEMORY_NOT_BELONG_USER(HttpStatus.FORBIDDEN.value(), "1017", "This memory is not belong to the current user."),

    /**
     * 无权限上传文件
     */
    NO_PERMISSION_TO_UPLOAD_FILE(HttpStatus.FORBIDDEN.value(), "1018",
        "Can not upload file from external knowledge repo."),

    /**
     * 无权限删除文件
     */
    NO_PERMISSION_TO_DELETE_FILE(HttpStatus.FORBIDDEN.value(), "1019",
        "Can not delete file from external knowledge repo."),

    /**
     * 文件不属于当前知识库
     */
    THE_FILE_NOT_BELONG_KNOWLEDGE_BASE(HttpStatus.FORBIDDEN.value(), "1020",
        "The files are not belong current knowledge base."),

    /**
     * 文件内容为空
     */
    EMPTY_FILE_CONTENT(HttpStatus.FORBIDDEN.value(), "1021", "The file content is empty."),

    /**
     * 创建FAQ文件分块错误
     */
    CREATE_FAQ_FILE_CHUNK_ERROR(HttpStatus.FORBIDDEN.value(), "1022", "Create faq file chunk error."),

    /**
     * 删除FAQ文件分块错误
     */
    DELETE_FAQ_FILE_CHUNK_ERROR(HttpStatus.FORBIDDEN.value(), "1023", "Delete faq file chunk error."),

    /**
     * 更新FAQ文件分块错误
     */
    UPDATE_FAQ_FILE_CHUNK_ERROR(HttpStatus.FORBIDDEN.value(), "1024", "Update faq file chunk error."),

    /**
     * FAQ文件为空
     */
    FAQ_FILE_IS_EMPTY(HttpStatus.FORBIDDEN.value(), "1025", "File content is empty,can not download."),

    /**
     * 无权限删除知识库文件
     */
    NO_PERMISSION_DELETE_KNOWLEDGE_REPO_FILE(HttpStatus.FORBIDDEN.value(), "1026",
        "External knowledge base can not delete faq file."),

    /**
     * 无权限上传知识库文件
     */
    NO_PERMISSION_UPLOAD_KNOWLEDGE_REPO_FILE(HttpStatus.FORBIDDEN.value(), "1027",
        "External knowledge base can not upload faq file."),

    /**
     * 知识库OBS目录超出限制
     */
    KNOWLEDGE_OBS_DIRECTORY_DEPTH_OUT_OF_LIMIT(HttpStatus.BAD_REQUEST.value(), "1028",
        "OBS directory depth is out of limit."),

    /**
     * 知识库obs配置不存在
     */
    KNOWLEDGE_OBS_CONFIG_NOT_EXIST(HttpStatus.NOT_FOUND.value(), "1029", "KnowledgeBaseObsConfig not exist."),

    /**
     * 查询obs桶内容失败
     */
    KNOWLEDGE_OBS_RESOURCE_LIST_FAILED(HttpStatus.NOT_FOUND.value(), "1030", "List obs buckets failed."),

    /**
     * 知识库ID超出限制
     */
    KNOWLEDGE_BASE_NUM_EXCEED_LIMIT(HttpStatus.BAD_REQUEST.value(), "1031", "KnowledgeBase ids exceed limit."),

    /**
     * 知识库并非来自单一来源
     */
    KNOWLEDGE_BASE_NOT_FROM_ONE_SOURCE(HttpStatus.BAD_REQUEST.value(), "1032",
        "KnowledgeBases are not from one source."),

    /**
     * 知识库连接信息不存在
     */
    KNOWLEDGE_BASE_CONNECTION_NOT_EXIST(HttpStatus.BAD_REQUEST.value(), "1033",
        "KnowledgeBase connection are not exist."),

    /**
     * 创建重试文件任务错误
     */
    CREATE_RETRY_FILES_TASK_ERROR(HttpStatus.BAD_REQUEST.value(), "1034", "Create retry files task error."),

    /**
     * 无法删除第三方数据库
     */
    KNOWLEDGE_BASE_CONNECTION_DELETE_FOR_OPEN(HttpStatus.BAD_REQUEST.value(), "1035",
        "Can not delete third party knowledge base"),

    /**
     * 知识库连接失败
     */
    KNOWLEDGE_BASE_CONNECT_FAILED(HttpStatus.BAD_REQUEST.value(), "1036", "Connect failed."),

    /**
     * 获取能力失败
     */
    FAIL_TO_GET_ABILITY(HttpStatus.BAD_REQUEST.value(), "1037",
        "Fail to get the ability for connection or connector type"),

    /********************************************** 默认知识库相关的错误码 *************************************************/

    /**
     * 上传知识库文件失败
     */
    FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2001",
        "Fail to upload knowledge repo file."),

    /**
     * 知识库来源有误
     */
    INVALID_KNOWLEDGE_REPO_SOURCE(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2002",
        "Invalid knowledge type or knowledge source."),

    /**
     * 知识库搜索模型未注册
     */
    SEARCH_MODEL_NOT_REGISTER(HttpStatus.BAD_REQUEST.value(), "2003", "This search model was not registered in KOS."),

    /**
     * 知识库搜索模型路径有误
     */
    SEARCH_MODEL_URL_ERROR(HttpStatus.BAD_REQUEST.value(), "2004", "The search model url is incorrect."),

    /**
     * 知识库搜索模型类型不支持
     */
    UNSUPPORTED_SEARCH_MODEL_TYPE(HttpStatus.BAD_REQUEST.value(), "2005", "The search model type is not supported."),

    /**
     * ocr模型kooSearch要求唯一
     */
    OCR_MODEL_ALREADY_EXIST(HttpStatus.BAD_REQUEST.value(), "2006", "Ocr model already exist and must only exist one."),

    /**
     * 文件上传请求触发限流
     */
    UPLOAD_FILE_EXCEED_LIMITS(HttpStatus.BAD_REQUEST.value(), "2007", "The file upload exceeds rate limit."),

    /**
     * 文件大小错误
     */
    ERROR_FILE_SIZE_ERROR(HttpStatus.BAD_REQUEST.value(), "2008",
        "This file has been compressed due to the presence of a large amount of duplicate data, and the actual file size has exceeded limit."),

    /**
     * 知识库已被全部删除或已停用，无法检索
     */
    KNOWLEDGE_CAN_NOT_RETRIEVE_FOR_DELETED_OR_CLOSED(HttpStatus.NOT_FOUND.value(), "2010",
        "knowledge can not retrieve for delete or closed!"),

    /**
     * 不支持的知识库操作
     */
    UNSUPPORTED_OPERATION(HttpStatus.BAD_REQUEST.value(), "2012", "Unsupported the operation"),

    /**
     * 获取图标失败
     */
    ICON_OBTAIN_FAILED(HttpStatus.BAD_REQUEST.value(), "2013", "Obtain icon failed"),

    /**
     * 知识库已被删除或已停用，无法更新
     */
    KNOWLEDGE_CAN_NOT_UPDATE_FOR_OPEN(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2014",
        "The knowledge base has been activated, and updates are currently not supported"),

    /**
     * 知识库路由策略有误
     */
    INVALID_KNOWLEDGE_ROUTER_STRATEGY(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2015",
        "Fail to get knowledge router strategy"),

    /**
     * 知识库检索融合策略有误
     */
    INVALID_KNOWLEDGE_MERGING_STRATEGY(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2016",
        "Fail to get retrieve merging strategy"),

    /**
     * 查询知识源失败
     */
    FAILED_TO_FIND_DEFAULT_KNOWLEDGE_SOURCE(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2017",
        "Failed to find connectionId from context"),

    /**
     * 知识库已经被发布，不能停止
     */
    KNOWLEDGE_CAN_NOT_CLOSE_FOR_PUBLISH(HttpStatus.BAD_REQUEST.value(), "2018",
        "knowledge base is published, can not stop"),

    /**
     * 文件不存在或已过期
     */
    FILE_NOT_EXIST_OR_EXPIRED(HttpStatus.BAD_REQUEST.value(), "2019", "File not exist or expired"),

    /**
     * 标签名重复
     */
    TAG_NAME_ALREADY_EXIST(HttpStatus.BAD_REQUEST.value(), "2020", "Tag name already exist."),

    /********************************************** 第三方知识库相关的错误码 *************************************************/

    /**
     * 知识库连接信息重复
     */
    KNOWLEDGE_CONNECTION_ALREADY_EXIST(HttpStatus.BAD_REQUEST.value(), "2100", "connection info already exist"),

    /**
     * 知识库连接状态异常
     */
    KNOWLEDGE_BASE_CONNECTION_STATUS_ERROR(HttpStatus.BAD_REQUEST.value(), "2101",
        "Knowledge base connection status error."),

    /**
     * 连接第三方知识库失败
     */
    CALL_EXTERNAL_KNOWLEDGE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2102",
        "External knowledge base API Connection failed"),

    /**
     * 知识库创建失败
     */
    KNOWLEDGE_BASE_CREATE_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2103", "create knowledge base failed"),

    /**
     * 查询第三方知识库失败
     */
    QUERY_THIRD_PARTY_KNOWLEDGE_BASES_ERROR(HttpStatus.BAD_REQUEST.value(), "2104",
        "Query third party knowledge base error"),

    /**
     * 查询第三方知识库标签失败
     */
    QUERY_THIRD_PARTY_KNOWLEDGE_BASES_TAGS_ERROR(HttpStatus.BAD_REQUEST.value(), "2105",
        "Query third party knowledge base tag error"),

    /**
     * 第三方知识库不支持下载文件
     */
    EXTERNAL_KNOWLEDGE_BASE_NOT_SUPPORT_DOWNLOAD_FILE(HttpStatus.BAD_REQUEST.value(), "2106",
        "External knowledge base unsupported download file"),

    /**
     * 第三方知识连接不存在
     */
    THIRD_PARTY_KNOWLEDGE_CONNECTION_NOT_EXISTS(HttpStatus.BAD_REQUEST.value(), "2107",
        "Can not find third part connection"),

    /**
     * 连接rag_flow失败
     */
    RAG_FLOW_CONNECT_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2108", "Call rag flow to list dataset failed"),

    /**
     * 连接service_bridge失败
     */
    SERVICE_BRIDGE_CONNECT_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "2109",
        "Call service bridge to list dataset failed"),
    /********************************************** KooSearch相关的错误码,用来映射KooSearch返回的错误码(3001-3999) *************************************************/

    /**
     * JSON格式错误
     */
    JSON_FORMAT_ERROR(HttpStatus.BAD_REQUEST.value(), "3001", "JSON format error"),

    /**
     * 参数为空
     */
    EMPTY_PARAM(HttpStatus.BAD_REQUEST.value(), "3002", "Parameter error"),

    /**
     * url参数解析异常
     */
    URL_PARAM_PARSE_ERROR(HttpStatus.BAD_REQUEST.value(), "3003", "URL parameter parsing exception"),

    /**
     * url路径不合法
     */
    URL_PATH_ILLEGAL(HttpStatus.BAD_REQUEST.value(), "3004", "URL path is illegal"),

    /**
     * es查询异常
     */
    ES_QUERY_ERROR(HttpStatus.BAD_REQUEST.value(), "3005", "ES query error"),

    /**
     * es索引创建异常
     */
    ES_INDEX_CREATE_ERROR(HttpStatus.BAD_REQUEST.value(), "3006", "ES index creation error"),

    /**
     * es更新异常
     */
    ES_UPDATE_ERROR(HttpStatus.BAD_REQUEST.value(), "3007", "ES update error"),

    /**
     * es删除索引异常
     */
    ES_INDEX_DELETE_ERROR(HttpStatus.BAD_REQUEST.value(), "3008", "ES index deletion error"),

    /**
     * es批量删除异常
     */
    ES_BATCH_DELETE_ERROR(HttpStatus.BAD_REQUEST.value(), "3009", "ES batch deletion error"),
    /**
     * es批量创建索引异常
     */
    ES_INDEX_BATCH_CREATE_ERROR(HttpStatus.BAD_REQUEST.value(), "3010", "ES batch index creation error"),
    /**
     * es删除文档异常
     */
    ES_DELETE_DOC_ERROR(HttpStatus.BAD_REQUEST.value(), "3011", "ES document deletion error"),

    /**
     * es更新文档异常
     */
    ES_UPDATE_DOC_ERROR(HttpStatus.BAD_REQUEST.value(), "3012", "ES document update error"),

    /**
     * es批量操作异常
     */
    ES_BATCH_OPERATION_ERROR(HttpStatus.BAD_REQUEST.value(), "3013", "ES batch operation error"),

    /**
     * 连接es失败
     */
    ES_CONNECT_ERROR(HttpStatus.BAD_REQUEST.value(), "3014", "Failed to connect to ES"),

    /**
     * 更新es索引配置异常
     */
    ES_UPDATE_INDEX_CONFIG_ERROR(HttpStatus.BAD_REQUEST.value(), "3015", "ES index configuration update error"),

    /**
     * 调用盘古nlp模型异常
     */
    AGENT_BUILDER_NLP_CALL_ERROR(HttpStatus.BAD_REQUEST.value(), "3016", "AGENT_BUILDER NLP model invocation error"),

    /**
     * 调用多轮改写服务异常
     */
    MULTI_TURN_REWRITE_CALL_ERROR(HttpStatus.BAD_REQUEST.value(), "3017",
        "Multi-turn rewriting service invocation error"),

    /**
     * 调用文档解析服务异常
     */
    DOC_PARSE_CALL_ERROR(HttpStatus.BAD_REQUEST.value(), "3018", "Document parsing service invocation error"),

    /**
     * 文件不存在
     */
    FILE_NOT_FOUND(HttpStatus.NOT_FOUND.value(), "3019", "Knowledge repo operation failed"),

    /**
     * 读取文件内容失败
     */
    FILE_READ_ERROR(HttpStatus.BAD_REQUEST.value(), "3020", "Failed to read file content"),

    /**
     * 文件信息写入数据库异常
     */
    FILE_INFO_DB_WRITE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "3021", "File information database write error"),

    /**
     * 上传obs异常
     */
    OBS_UPLOAD_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "3022", "OBS upload error"),

    /**
     * json处理异常 (对应 KOS.00050005)
     */
    JSON_PROCESS_ERROR(HttpStatus.BAD_REQUEST.value(), "3023", "JSON processing error"), // 如果是请求数据问题

    /**
     * 处理中的文件不支持删除
     */
    FILE_PROCESSING_CANNOT_DELETE(HttpStatus.BAD_REQUEST.value(), "3024",
        "Files being processed cannot be deleted"), // 409 冲突

    /**
     * 数据库查询结果为空
     */
    DB_QUERY_RESULT_EMPTY(HttpStatus.NOT_FOUND.value(), "3025",
        "Database query result is empty"), // 404 或 200 都可能，404 更强调“不存在”

    /**
     * 数据库操作失败
     */
    DB_OPERATION_FAILED(HttpStatus.INTERNAL_SERVER_ERROR.value(), "3026", "Database operation failed"),

    /**
     * 数据库更新异常
     */
    DB_UPDATE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "3027", "Database update error"),

    /**
     * 模型不可用
     */
    MODEL_UNAVAILABLE(HttpStatus.BAD_REQUEST.value(), "3028", "Model is unavailable"), // 503

    /**
     * 资源已经存在
     */
    RESOURCE_ALREADY_EXIST(HttpStatus.BAD_REQUEST.value(), "3029", "Resource already exists"), // 409

    /**
     * 下载json文件异常
     */
    JSON_FILE_DOWNLOAD_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "3030", "JSON file download error"),

    /**
     * 写入json文件异常
     */
    JSON_FILE_WRITE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR.value(), "3031", "JSON file write error"),

    /**
     * 同名知识库已存在
     */
    KNOWLEDGE_BASE_DUPLICATE(HttpStatus.BAD_REQUEST.value(), "3032", "Failed to verify the knowledge base name."),

    /**
     * 知识库为空时不支持开启
     */
    KNOWLEDGE_BASE_EMPTY_CANNOT_ENABLE(HttpStatus.BAD_REQUEST.value(), "3033", "Knowledge base cannot be enabled"),

    /**
     * 知识库关闭时不允许当前操作
     */
    KNOWLEDGE_BASE_CLOSED_OPERATION_FORBIDDEN(HttpStatus.FORBIDDEN.value(), "3034", "Current operation is not allowed"),

    /**
     * 对话时间超期
     */
    CONVERSATION_EXPIRED(HttpStatus.BAD_REQUEST.value(), "3035", "Conversation has expired"), // 410 Gone

    /**
     * 知识库更新失败
     */
    KNOWLEDGE_BASE_UPDATE_FAILED(HttpStatus.BAD_REQUEST.value(), "3036", "Knowledge base update failed"),

    /**
     * 删除模型失败
     */
    DELETE_MODEL_FAILED(HttpStatus.BAD_REQUEST.value(), "3037", "Delete model error"),

    ADDRESS_ILLEGAL(HttpStatus.BAD_REQUEST.value(), "3038", "Address illegal"),

    /**
     * 图片不存在或已过期
     */
    IMAGE_NOT_EXIST_OR_EXPIRED(HttpStatus.BAD_REQUEST.value(), "3039", "Image not exist or expired"),

    /**
     * 共享知识库资源池不足
     */
    SHARE_REPO_IS_INSUFFICIENT(HttpStatus.INSUFFICIENT_STORAGE.value(), "3040", "Share repo capacity is not enough");

    /********************************************** KooSearch相关的错误码 end *************************************************/

    /**
     * 知识库的基础错误码
     */
    private static final String BASE_CODE = "0300";

    /**
     * 根据 code 查找枚举实例
     */
    private static final Map<String, ErrorCode> CODE_TO_ENUM = new HashMap<>();

    static {
        Set<String> uniqCodes = new HashSet<>(ErrorCode.values().length);
        Arrays.stream(ErrorCode.values()).forEach(e -> {
            if (uniqCodes.contains(e.code)) {
                throw new IllegalArgumentException("Duplicated error code for " + e);
            }
            uniqCodes.add(e.code);
        });
    }

    static {
        for (ErrorCode errorCode : values()) {
            CODE_TO_ENUM.put(errorCode.code, errorCode);
        }
    }

    /**
     * 错误码对应的http状态码
     */
    private final int httpCode;

    /**
     * 错误码对应的code信息，必须为4位数字
     * 其中0000~1000为系统型错误码，1001~9999为业务型错误码
     */
    private final String code;

    /**
     * 错误码对应的错误信息
     */
    private final String msg;

    /**
     * 构造器
     *
     * @param httpCode 对应的http状态码
     * @param code 长度为8的数字字符串，前三位是httpCode，后5位是我们服务内部细分的错误码
     * @param msg 错误描述信息
     */
    ErrorCode(int httpCode, String code, String msg) {
        this.httpCode = httpCode;
        this.code = "openjiuwen." + BASE_CODE + code;
        this.msg = msg;
    }

    public static ErrorCode fromCode(String code) {
        ErrorCode error = CODE_TO_ENUM.get(code);
        if (error == null) {
            throw new IllegalArgumentException("未知的错误码: " + code);
        }
        return error;
    }
}
