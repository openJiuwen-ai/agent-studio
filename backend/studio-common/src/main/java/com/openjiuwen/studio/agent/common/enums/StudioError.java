/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.enums;

import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.AGENT;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.ASSET;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.CODE_AGENT;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.COMMON;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.COMPONENT;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.CONFIG;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.EXPORT;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.KNOWLEDGE_BASE;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.LICENSE;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.MEMORY;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.MODEL;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.MULTI_AGENT;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.PE;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.SHARE_RESOURCE;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.WORKFLOW;
import static com.openjiuwen.studio.agent.common.enums.StudioError.Module.WORKSPACE;
import static org.springframework.http.HttpStatus.ACCEPTED;
import static org.springframework.http.HttpStatus.BAD_GATEWAY;
import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.CONFLICT;
import static org.springframework.http.HttpStatus.FORBIDDEN;
import static org.springframework.http.HttpStatus.GATEWAY_TIMEOUT;
import static org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR;
import static org.springframework.http.HttpStatus.NOT_ACCEPTABLE;
import static org.springframework.http.HttpStatus.NOT_FOUND;
import static org.springframework.http.HttpStatus.OK;
import static org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE;
import static org.springframework.http.HttpStatus.TOO_MANY_REQUESTS;
import static org.springframework.http.HttpStatus.UNAUTHORIZED;

import lombok.Getter;

import org.springframework.http.HttpStatus;

/**
 * agent-builder错误码，不同模块的code不得重复
 *
 */
@Getter
public enum StudioError {
    /**
     * ============================== COMMON ==============================
     */
    /**
     * Poc 鉴权失败
     */
    POC_AUTH_FAILED(UNAUTHORIZED, COMMON, "1001"),

    /**
     * 服务内部错误，兜底的错误
     */
    UNEXPECTED_ERROR(INTERNAL_SERVER_ERROR, COMMON, "1002"),

    /**
     * 接口参数校验异常
     */
    METHOD_ARGUMENT_NOT_VALID(BAD_REQUEST, COMMON, "1003"),

    /**
     * obs失败
     */
    OBS_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1004"),

    /**
     * css uni-search服务调用异常
     */
    CSS_UNI_SEARCH_SERVICE_EXCEPTION(INTERNAL_SERVER_ERROR, COMMON, "1005"),

    /**
     * 非法文件名
     */
    ILLEGAL_FILE_NAME(BAD_REQUEST, COMMON, "1006"),

    /**
     * 非法文件类型
     */
    ILLEGAL_FILE_TYPE(BAD_REQUEST, COMMON, "1007"),

    /**
     * 文件大小超过系统限制
     */
    FILE_SIZE_EXCEED_LIMIT(BAD_REQUEST, COMMON, "1008"),

    /**
     * 工作空间ID格式无效
     */
    WORKSPACE_FORMAT_INVALID(BAD_REQUEST, COMMON, "1009"),

    /**
     * 项目ID无效或者不匹配
     */
    PROJECT_ID_INVALID(BAD_REQUEST, COMMON, "1010"),

    /**
     * 工作空间ID无效或者不匹配
     */
    WORKSPACE_ID_INVALID(BAD_REQUEST, COMMON, "1011"),

    /**
     * 用户没有该空间的权限
     */
    USER_WORKSPACE_PERMISSION_INVALID(BAD_REQUEST, COMMON, "1012"),

    /**
     * 文件大小超过系统限制,头像文件大小超出限制：200KB
     */
    PICTURE_FILE_SIZE_EXCEED_LIMIT(BAD_REQUEST, COMMON, "1013"),

    /**
     * obs桶容量告急
     */
    OBS_BUCKET_CAPACITY_LIMIT(BAD_REQUEST, COMMON, "1014"),

    /**
     * 名称查询 正则匹配失败
     */
    SEARCH_NAME_FORMAT(BAD_REQUEST, COMMON, "1015"),

    /**
     * 名称校验失败
     */
    NAME_FORMAT(BAD_REQUEST, COMMON, "1016"),

    /**
     * API 调用超过License配额
     */
    AGENT_API_INVOKE_EXCEEDED_QUOTA(FORBIDDEN, COMMON, "1017"),

    /**
     * 语音时间超长
     */
    SIS_VOICE_DURATION_EXCEEDED(BAD_REQUEST, COMMON, "1018"),

    /**
     * 语音识别失败
     */
    SIS_VOICE_RECOGNITION_FAILED(BAD_REQUEST, COMMON, "1019"),

    /**
     * 配额超出套餐限制，请升级套餐
     */
    SKU_ATTR_LIMIT_EXCEEDED(BAD_REQUEST, COMMON, "1020"),

    /**
     * 套餐功能不支持，请升级套餐
     */
    SKU_ATTR_IS_NOT_ENABLE(BAD_REQUEST, COMMON, "1021"),

    /**
     * 文件必传
     */
    FILE_CANNOT_BE_EMPTY(FORBIDDEN, COMMON, "1022"),

    /**
     * OBS对象拷贝失败
     */
    COPY_FROM_OBS_FAIL(INTERNAL_SERVER_ERROR, COMMON, "1023"),

    /**
     * Upload file to obs failed.
     */
    UPLOAD_FILE_TO_OBS_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1024"),

    /**
     * do not have the modification permission.
     */
    NO_PERMISSION_MODIFY(INTERNAL_SERVER_ERROR, COMMON, "1025"),

    /**
     * 非法的URL
     */
    INVALID_URL(BAD_REQUEST, COMMON, "1026"),

    /**
     * URL is blocked by blacklist.
     */
    URL_BLOCKED_BLOCK_LIST(BAD_REQUEST, COMMON, "1027"),

    /**
     * Access to internal network is forbidden.
     */
    ACCESS_INTER_NETWORK_FORBIDDEN(BAD_REQUEST, COMMON, "1028"),

    /**
     * 开场白生成失败, Workflow configs is null.
     */
    GENERATE_PROLOGUE_FAILED(BAD_REQUEST, COMMON, "1029"),

    /**
     * 非法文件, file cannot be empty.
     */
    ILLEGAL_FILE(BAD_REQUEST, COMMON, "1030"),

    /**
     * Invalid icon name.
     */
    INVALID_ICON_NAME(BAD_REQUEST, COMMON, "1031"),

    /**
     * 工具信息不正确
     */
    TOOL_INFO_INCORRECT(BAD_REQUEST, COMMON, "1032"),

    /**
     * Tts API service exception.
     */
    TST_API_SERVICE_EXCEPTION(INTERNAL_SERVER_ERROR, COMMON, "1033"),

    /**
     * 接口调用异常, queryDomainToken error.
     */
    INTERFACE_CALL_EXCEPTION(INTERNAL_SERVER_ERROR, COMMON, "1034"),

    /**
     * you do not have permission to do this operation because you are not the creator.
     */
    NO_CREATOR_PERMISSION(FORBIDDEN, COMMON, "1035"),

    /**
     * Api delete api error
     */
    API_DELETE_API_ERROR(BAD_REQUEST, COMMON, "1036"),

    /**
     * The file upload exceeds rate limit, please try again later.
     */
    UPLOAD_FILE_EXCEED_LIMITS(BAD_REQUEST, COMMON, "1037"),

    /**
     * 流式接口执行超时
     */
    STREAM_INTERFACE_EXECUTE_TIMEOUT(BAD_REQUEST, COMMON, "1038"),

    /**
     * model is not exist or model config conversion failed.
     */
    GENERATE_PROLOGUE_FAILED_MODEL(BAD_REQUEST, COMMON, "1039"),

    /**
     * redisson获取bucket失败
     */
    REDISSON_GET_BUCKET_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1040"),

    /**
     * 获取用户 token 错误
     */
    IAM_GET_USERINFO_EXCEPTION(INTERNAL_SERVER_ERROR, COMMON, "1041"),

    /**
     * sql执行失败
     */
    SQL_EXECUTE_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1042"),

    /**
     * Fail get provider auth metadata. project:{0} provider: {1}
     */
    FAIL_GET_PROVIDE_AUTH_METADATA(BAD_REQUEST, COMMON, "1043"),

    /**
     * nodeType:not support.
     */
    NODE_TYPE_NOT_SUPPORT(BAD_REQUEST, COMMON, "1044"),

    /**
     * Unsupported data source type.
     */
    UNSUPPORTED_DATA_SOURCE(BAD_REQUEST, COMMON, "1045"),

    /**
     * Fail to parse event data answer.
     */
    FAIL_TO_PARSE_DATA(BAD_REQUEST, COMMON, "1046"),

    /**
     * import agents|workflows|tools error
     */
    IMPORT_AGENT_WORKFLOW_TOOL_ERROR(INTERNAL_SERVER_ERROR, COMMON, "1047"),

    /**
     * Auth type is not support.
     */
    AUTH_TYPE_UNSUPPORTED(BAD_REQUEST, COMMON, "1048"),

    /**
     * http client init failed.
     */
    HTTP_CLIENT_INIT_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1049"),

    /**
     * Get request iam context failed
     */
    GET_REQUEST_IAM_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1050"),

    /**
     * endpoint can not be found
     */
    ENDPOINT_CAN_NOT_FOUND(INTERNAL_SERVER_ERROR, COMMON, "1053"),

    /**
     * Cannot find class definitions for JsonReadFeature and JsonWriteFeature due to version conflict, use deprecated
     * JsonParser and JsonGenerator instead.
     */
    JSON_PARSER_INSTEAD(INTERNAL_SERVER_ERROR, COMMON, "1054"),

    /**
     * Failed to convert file to base64 string.
     */
    BASE_CONVERT_FAILED(BAD_REQUEST, COMMON, "1055"),

    /**
     * Failed to get icon image
     */
    FAILED_ICON_IMAGE(BAD_REQUEST, COMMON, "1056"),

    /**
     * The quota has exceeded
     */
    APP_COUNT_EXCEEDED_LIMIT(BAD_REQUEST, COMMON, "1057"),

    /**
     * 结构化信息导出失败
     */
    EXPORT_STRUCTURED_MESSAGES_FAILED(INTERNAL_SERVER_ERROR, COMMON, "1058"),

    /**
     * Error refresh environment
     */
    ERROR_REFRESH_ENVIRONMENT(BAD_REQUEST, COMMON, "1059"),

    /**
     * 结构化信息名字不合法
     */
    STRUCTURED_MESSAGES_NAME_INVALID(BAD_REQUEST, COMMON, "1060"),

    /**
     * 消息模板数量已达到上限
     */
    MESSAGE_TEMPLATE_SIZE_LIMIT(BAD_REQUEST, COMMON, "1061"),

    /**
     * 消息模板信息名字重复
     */
    MESSAGE_TEMPLATE_NAME_REPETITION(BAD_REQUEST, COMMON, "1062"),

    /**
     * 被授权空间不存在 Authorized space does not exist.
     */
    AUTH_WORKSPACE_NOT_FOUNT(BAD_REQUEST, COMMON, "1063"),

    /**
     * 共享的资源类型不合法 The shared resource type is invalid.
     */
    RESOURCE_TYPE_NOT_VALID(BAD_REQUEST, COMMON, "1064"),

    /**
     * 共享资源不存在 Shared resource does not exist.
     */
    SHARE_RESOURCE_NOT_FOUNT(BAD_REQUEST, COMMON, "1065"),

    /**
     * 存在引用资源的对象不能共享 Objects with referenced resources cannot be shared.
     */
    EXIST_SHARE_REFERENCE(BAD_REQUEST, COMMON, "1066"),

    /**
     * the current resource {} is not in share scope list
     */
    CURRENT_WORKSPACE_IS_NOT_IN_SHARE_SCOPE(BAD_REQUEST, COMMON, "1067"),

    /**
     * 调用 agent service 错误
     */
    CALL_RUNTIME_ERROR(INTERNAL_SERVER_ERROR, COMMON, "1068"),

    /**
     * api key 缺失
     */
    POC_API_KEY_MISSING(UNAUTHORIZED, COMMON, "1069"),

    /**
     * api key 错误
     */
    POC_API_KEY_INCORRECT(UNAUTHORIZED, COMMON, "1070"),

    /**
     * 租户权限错误
     */
    PROJECT_ID_ERROR(BAD_REQUEST, COMMON, "1071"),

    /**
     * web调用应用限流
     */
    CALL_LIMIT_ERROR(BAD_REQUEST, COMMON, "1072"),

    /**
     * 获取分布式锁失败
     */
    OBTAIN_DISTRIBUTED_LOCK_ERROR(BAD_REQUEST, COMMON, "1073"),

    /**
     * Json转换异常
     */
    JSON_CONVERT_ERROR(BAD_REQUEST, COMMON, "1074"),

    /**
     * 租户被冻结
     */
    FREEZE_TENANT(FORBIDDEN, COMMON, "1075"),

    /**
     * {0}功能未开通
     */
    TENANT_NOT_ACTIVATED(BAD_REQUEST, COMMON, "1076"),

    /**
     * 仅支持异常类型
     */
    ONLY_SUPPORTED_EXCEPTION_TYPE(BAD_REQUEST, COMMON, "1077"),

    /**
     * 租户资源清理权限不足
     */
    TENANT_DATA_CLEAN_FORBIDDEN(FORBIDDEN, COMMON, "1078"),

    /**
     * 消息模板未找到
     */
    MESSAGE_TEMPLATE_NOT_FOUND_OR_PERMISSION_DENIED(FORBIDDEN, COMMON, "1079"),

    /**
     * 服务白名单校验错误
     */
    URL_WHITELIST_CHECK_ERROR(BAD_REQUEST, COMMON, "1080"),

    /**
     * 未能查询到KMS datakey工作秘钥， 系统异常。正常不应该出此问题
     */
    NOT_FOUND_KMS_DATA_KEY(INTERNAL_SERVER_ERROR, COMMON, "1081"),

    /**
     * KMS 加解密失败，系统异常，正常不应该出此问题
     */
    KMS_CRYPTO_ERROR(INTERNAL_SERVER_ERROR, COMMON, "1082"),

    /**
     * 调用过于频繁，请稍后再试
     */
    CALL_EXCEED_LIMIT(FORBIDDEN, COMMON, "1083"),

    /**
     * resource reader error
     */
    RESOURCE_READER_ERROR(BAD_REQUEST, COMMON, "1084"),

    /**
     * Could not convert object to JSON string
     */
    COULD_NOT_CONVERT_OBJECT_TO_JSON(BAD_REQUEST, COMMON, "1085"),

    /**
     * Could not convert JSON string to object
     */
    COULD_NOT_CONVERT_JSON_STRING_TO_OBJECT(BAD_REQUEST, COMMON, "1086"),

    /**
     * Error converting list to JSON
     */
    LIST_TO_JSON_ERROR(BAD_REQUEST, COMMON, "1087"),

    /**
     * Error converting JSON to list
     */
    JSON_TO_LIST_ERROR(BAD_REQUEST, COMMON, "1088"),

    /**
     * 签名验证失败
     */
    VERIFY_SIGNATURE_FAILED(FORBIDDEN, COMMON, "1089"),

    /**
     * 签名验证失败
     */
    SERVICE_NOT_ACTIVATE(BAD_REQUEST, COMMON, "1090"),

    /**
     * 隐私协议验证失败
     */
    VERIFY_AGREEMENT_FAILED(FORBIDDEN, COMMON, "1091"),

    /**
     * 文件数量超过系统限制
     */
    FILE_COUNT_EXCEED_LIMIT(BAD_REQUEST, COMMON, "1092"),

    /**
     * domain 校验不通过
     */
    HOST_VALIDATION_DOMAIN_FAILED(FORBIDDEN, COMMON, "1093"),

    /**
     * 无效的域名
     */
    HOST_VALIDATION_INVALID(FORBIDDEN, COMMON, "1094"),


    /**
     * zip文件嵌套
     */
    FILE_NESTED_ZIP(BAD_REQUEST, COMMON, "1095"),

    /**
     * zip路径过深
     */
    ZIP_PATH_TOO_DEEP(BAD_REQUEST, COMMON, "1096"),

    /**
     * 解压文件夹数量不匹配
     */
    FILES_NUMBER_DOES_NOT_MATCH(BAD_REQUEST, COMMON, "1097"),

    /**
     * 缺少必填字段
     */
    DESCRIPTION_FIELD_MISSING(BAD_REQUEST, COMMON, "1098"),

    /**
     * 长度超过限制
     */
    DESCRIPTION_LENGTH_EXCEED(BAD_REQUEST, COMMON, "1099"),

    /**
     * 含有非法字符
     */
    INVALID_CHARACTER(BAD_REQUEST, COMMON, "1100"),

    /**
     * 租户不存在
     */
    TEANANT_NOT_EXIST(FORBIDDEN, COMMON, "1101"),

    /**
     * 缺少必填参数
     */
    PARAMS_IS_REQUIRED(BAD_REQUEST, COMMON, "1102"),

    /**
     * 无效的状态
     */
    INVALID_STATUS(BAD_REQUEST, COMMON, "1103"),

    /**
     * 无效的License项
     */
    INVALID_LICENSE(FORBIDDEN, COMMON, "1104"),

    /**
     * 无license可被消费
     */
    NO_LICENSE_CAN_BE_CONSUMED(FORBIDDEN, COMMON, "1105"),

    /**
     * 无license可被释放
     */
    NO_LICENSE_CAN_BE_RELEASED(FORBIDDEN, COMMON, "1106"),

    /**
     * 无充分的license释放
     */
    NO_ENOUGH_LICENSE_CAN_BE_RELEASED(FORBIDDEN, COMMON, "1107"),

    /**
     * 鉴权失败
     */
    AUTHENTICATION_ERROR(UNAUTHORIZED, COMMON, "1108"),

    /**
     * 长度超过限制
     */
    COMPATIBILITY_LENGTH_EXCEED(BAD_REQUEST, COMMON, "1109"),

    /**
     * skillId为空
     */
    SKILL_ID_IS_EMPTY(BAD_REQUEST, COMMON, "1110"),

    /**
     * skill不存在
     */
    SKILL_NOT_EXISTS(BAD_REQUEST, COMMON, "1111"),

    /**
     * skillVersion版本异常
     */
    SKILL_VERSION_IS_INCORRECT(BAD_REQUEST, COMMON, "1112"),

    /**
     * obs_url不存在
     */
    OBS_URL_NOT_EXISTS(BAD_REQUEST, COMMON, "1113"),

    /**
     * 预签名 obs_url不存在
     */
    GET_OBS_TEMPORARY_URL_NOT_EXIST(BAD_REQUEST, COMMON, "1114"),

    /**
     * SKILL.md文件不存在
     */
    SKILL_MD_IS_MISSING(BAD_REQUEST, COMMON, "1115"),

    /**
     * IO异常
     */
    IO_ERROR(BAD_REQUEST, COMMON, "1116"),

    /**
     * skill 已存在
     */
    SKILL_ALREADY_EXIST(BAD_REQUEST, COMMON, "1117"),

    /**
     *  同步删除高码数据失败
     */
    SYNC_DELETE_CODE_AGENT_FAILED(BAD_REQUEST, COMMON, "1118"),

    /**
     * ============================== SKILL ==============================
     */
    /**
     * Skill 文件大小超过限制
     */
    SKILL_SIZE_EXCEED_LIMIT(BAD_REQUEST, COMMON, "1121"),

    /**
     * Zip 文件条目数超过了限制
     */
    ZIP_FILE_COUNT_EXCEED_LIMIT(BAD_REQUEST, COMMON, "1122"),

    /**
     * Zip 路径穿越
     */
    INSECURE_PATH(BAD_REQUEST, COMMON, "1123"),

    /**
     * 路径不安全
     */
    UNSAFE_PATH(BAD_REQUEST, COMMON, "1124"),

    /**
     * Skill.md 使用了非白名单字段
     */
    SKILL_MD_INVALID_FIELD(BAD_REQUEST, COMMON, "1125"),

    /**
     * Skill.md 缺失必填字段
     */
    NAME_FIELD_MISSING(BAD_REQUEST, COMMON, "1126"),

    /**
     * 名称格式不匹配
     */
    NAME_FORMAT_MISMATCH(BAD_REQUEST, COMMON, "1127"),

    /**
     * 上传大小超出最大限制
     */
    MAX_UPLOAD_SIZE_EXCEEDED(BAD_REQUEST, COMMON, "1128"),


    /**
     * ============================== AGENT ==============================
     */
    /**
     * Agent应用名称错误
     */
    AGENT_NAME_INVALID(BAD_REQUEST, AGENT, "1001"),

    /**
     * 触发器不存在
     */
    AGENT_TRIGGER_EXIST(NOT_FOUND, AGENT, "1002"),

    /**
     * 触发器类型错误
     */
    AGENT_TRIGGER_TYPE_INCORRECT(BAD_REQUEST, AGENT, "1003"),

    /**
     * 触发器数量已达到上限
     */
    AGENT_TRIGGER_SIZE_LIMIT(BAD_REQUEST, AGENT, "1004"),

    /**
     * Agent图标不存在
     */
    AGENT_ICON_EXIST(NOT_FOUND, AGENT, "1005"),

    /**
     * Agent图标超过了上传最大尺寸
     */
    AGENT_ICON_SIZE_EXCEEDS_LIMIT(BAD_REQUEST, AGENT, "1006"),

    /**
     * agent不存在
     */
    AGENT_NOT_EXIST(NOT_FOUND, AGENT, "1007"),

    /**
     * Agent导入失败
     */
    AGENT_IMPORT_FILE(INTERNAL_SERVER_ERROR, AGENT, "1008"),

    /**
     * Agent导出失败
     */
    AGENT_EXPORT_FILE(INTERNAL_SERVER_ERROR, AGENT, "1009"),

    /**
     * agent绑定的工具数量超过上限
     */
    TOOL_NUMBER_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1010"),

    /**
     * agent绑定的知识库数量超过上限
     */
    KNOWLEDGE_REPO_NUMBER_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1011"),

    /**
     * agent绑定的工作流数量超过上限
     */
    WORKFLOW_NUMBER_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1012"),

    /**
     * AGENT发布通道类型错误
     */
    AGENT_CHANNEL_TYPE_INCORRECT(BAD_REQUEST, AGENT, "1013"),

    /**
     * 不支持的Agent类型
     */
    UNSUPPORTED_AGENT_TYPE(BAD_REQUEST, AGENT, "1014"),

    /**
     * 单智能体应用已被更新，请刷新页面后再试
     */
    AGENT_HAS_BEEN_UPDATED(INTERNAL_SERVER_ERROR, AGENT, "1015"),

    /**
     * Agent执行权限不足
     */
    INSUFFICIENT_AGENT_RUN_PRIVILEGES(FORBIDDEN, AGENT, "1016"),

    /**
     * agent信息校验失败
     */
    CHECK_AGENT_INFO_FAILED(BAD_REQUEST, AGENT, "1017"),

    /**
     * agent信息发送失败
     */
    AGENT_INFO_SEND_FAILED(BAD_REQUEST, AGENT, "1018"),

    /**
     * Agent运行超时
     */
    AGENT_RUN_TIMEOUT(INTERNAL_SERVER_ERROR, AGENT, "1019"),

    /**
     * 应用发布版本数量超过上限
     */
    RELEASE_VERSION_SIZE_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1020"),

    /**
     * Agent版本不存在
     */
    AGENT_VERSION_NOT_EXIST(INTERNAL_SERVER_ERROR, AGENT, "1021"),

    /**
     * agent发布通道不存在
     */
    AGENT_PUBLISH_CHANNEL_NOT_EXIST(NOT_FOUND, AGENT, "1022"),

    /**
     * 检查应用信息失败,应该首先发布一次应用
     */
    CHECK_APP_INFO_FAILED(INTERNAL_SERVER_ERROR, AGENT, "1023"),

    /**
     * agent绑定的mcp server数量超过上限
     */
    MCP_NUMBER_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1024"),

    /**
     * 调度器配置定时任务失败
     */
    SCHEDULER_EXCEPTION(BAD_REQUEST, AGENT, "1025"),

    /**
     * Run job failed.
     */
    SCHEDULER_EXCEPTION_RUN_JOB(BAD_REQUEST, AGENT, "1026"),

    /**
     * itep接口调用异常
     */
    CALL_GET_AGENCY_TOKEN_API_EXCEPTION(INTERNAL_SERVER_ERROR, AGENT, "1027"),

    /**
     * 转换UUID失败
     */
    ID_TO_UUID_FAIL(INTERNAL_SERVER_ERROR, AGENT, "1028"),

    /**
     * 不支持非流式调用   Non-streaming invoking is not supported.
     */
    NO_SUPPORT_NON_STREAMING_CALL(BAD_REQUEST, AGENT, "1029"),

    /**
     * 上传文件数量超出限制  The number of the uploaded files exceeds the limit.
     */
    AGENT_UPLOAD_FILE_NUM(BAD_REQUEST, AGENT, "1030"),

    /**
     * Agent不存在或无权限  The number of the uploaded files exceeds the limit.
     */
    AGENT_NOT_EXIST_OR_NO_PERMISSION(BAD_REQUEST, AGENT, "1031"),

    /**
     * Agent或版本不存在  The current Agent version does not exist.
     */
    AGENT_OR_VERSION_NOT_EXIST(BAD_REQUEST, AGENT, "1032"),

    /**
     * 一次会话最多上传10个文件  A maximum of {10} files can be uploaded per session.
     */
    AGENT_CONVERSATION_FILE_NUM(BAD_REQUEST, AGENT, "1033"),

    /**
     * Agent中定义的变量重复
     */
    AGENT_VARIABLE_DUPLICATE(BAD_REQUEST, AGENT, "1034"),

    /**
     * Agent解析全局变量失败
     */
    AGENT_PARSE_VARIABLE_FAILED(BAD_REQUEST, AGENT, "1035"),

    /**
     * 获取变量失败请检查资源ID、会话ID和变量名称是否正确
     */
    AGENT_GET_VARIABLE_FAILED(BAD_REQUEST, AGENT, "1036"),

    /**
     * 版本名称已经存在
     */
    VERSION_NAME_ALREADY_EXISTED(BAD_REQUEST, AGENT, "1037"),

    /**
     * 应用百宝箱仅能op账号才能发布
     */
    OP_ACCOUNT_ONLY_ALLOWED_TO_PUBLISH(BAD_REQUEST, AGENT, "1038"),

    /**
     * 当前渠道类型不支持删除
     */
    AGENT_CHANNEL_NOT_SUPPORT_DELETE(BAD_REQUEST, AGENT, "1039"),

    /**
     * Excel文件行数超过限制
     */
    EXCEL_ROW_COUNT_EXCEEDED(BAD_REQUEST, AGENT, "1040"),

    /**
     * Excel文件列数超过限制
     */
    EXCEL_COLUMN_COUNT_EXCEEDED(BAD_REQUEST, AGENT, "1041"),

    /**
     * Excel文件格式无效
     */
    EXCEL_FILE_FORMAT_INVALID(BAD_REQUEST, AGENT, "1042"),

    /**
     * 应用发布渠道不存在
     */
    APPLICATION_PUBLISH_CHANNEL_NOT_EXIST(BAD_REQUEST, AGENT, "1043"),

    /**
     * 缺少输入参数
     */
    MISSING_REQUIRED_PARAMETERS(BAD_REQUEST, AGENT, "1044"),

    /**
     * 智能生成图标失败
     */
    GENERATE_ICON_FAILED(BAD_REQUEST, AGENT, "1045"),

    /**
     * 指南数量超过限制
     */
    GUIDELINE_NUM_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1046"),

    /**
     * 不支持非流式调用
     */
    NOT_SUPPORT_UN_STREAM_INVOKE(BAD_REQUEST, AGENT, "1047"),

    /**
     * 不支持的关联资源类型
     */
    UNSUPPORTED_RESOURCE_TYPE(BAD_REQUEST, AGENT, "1048"),

    /**
     * Skill数量超过限制
     */
    SKILL_NUM_EXCEED_LIMIT(BAD_REQUEST, AGENT, "1049"),

    /**
     * Skill不存在
     */
    SKILL_NOT_EXIST(NOT_FOUND, AGENT, "1050"),

    /**
     * Skill版本无效
     */
    SKILL_VERSION_INVALID(BAD_REQUEST, AGENT, "1051"),

    /**
     * Skill id不存在或版本不匹配
     */
    SKILL_ID_OR_VERSION_NOT_MATCH(BAD_REQUEST, AGENT, "1052"),

    /**
     * 缺少系统提示词
     */
    MISSING_REQUIRED_INSTRUCTIONS(BAD_REQUEST, AGENT, "1053"),

    /**
     * {{latest}}变量对应的资源不存在替换
     */
    LATEST_REPLACE_NOT_EXISTS(BAD_REQUEST, AGENT, "1056"),

    /**
     * ============================== WORKFLOW ==============================
     */

    /**
     * 工作流导入失败
     */
    WORKFLOW_IMPORT_FILE(INTERNAL_SERVER_ERROR, WORKFLOW, "1001"),

    /**
     * 工作流组件ID不存在
     */
    WORKFLOW_NODE_ID_NULL(INTERNAL_SERVER_ERROR, WORKFLOW, "1002"),

    /**
     * workflow节点执行异常
     */
    WORKFLOW_NODE_EXECUTE_FAILED(INTERNAL_SERVER_ERROR, WORKFLOW, "1003"),

    /**
     * workflow不存在
     */
    WORKFLOW_NOT_EXIST(NOT_FOUND, WORKFLOW, "1004"),

    /**
     * workflow信息校验失败
     */
    CHECK_WORKFLOW_INFO_FAILED(BAD_REQUEST, WORKFLOW, "1005"),

    /**
     * Workflow name exceeds limit 64
     */
    WORKFLOW_NAME_EXCEEDS_LIMIT(BAD_REQUEST, WORKFLOW, "1006"),

    /**
     * Workflow icon is empty
     */
    WORKFLOW_ICON_EMPTY(BAD_REQUEST, WORKFLOW, "1007"),

    /**
     * Workflow导出失败
     */
    WORKFLOW_EXPORT_FILE(INTERNAL_SERVER_ERROR, WORKFLOW, "1008"),

    /**
     * workflow version not match
     */
    WORKFLOW_VERSION_NOT_MATCH(BAD_REQUEST, WORKFLOW, "1009"),

    /**
     * 工作流版本无权限删除
     */
    NO_PERMISSION_DELETE_WORKFLOW_VERSION(FORBIDDEN, WORKFLOW, "1010"),

    /**
     * WORKFLOW发布通道类型错误
     */
    WORKFLOW_CHANNEL_TYPE_INCORRECT(BAD_REQUEST, WORKFLOW, "1011"),

    /**
     * 工作流嵌套检查.
     */
    WORKFLOW_NESTED_CHECK(INTERNAL_SERVER_ERROR, WORKFLOW, "1012"),

    /**
     * 导出依赖的工作流版本不存在
     */
    DEPEND_WORKFLOW_VERSION(INTERNAL_SERVER_ERROR, WORKFLOW, "1013"),

    /**
     * 工作流中文名称重复
     */
    WORKFLOW_NAME_REPEATED(BAD_REQUEST, WORKFLOW, "1014"),

    /**
     * 工作流英文名称重复
     */
    WORKFLOW_EN_NAME_REPEATED(BAD_REQUEST, WORKFLOW, "1015"),

    /**
     * 工作流非游离节点数量超过最大限制
     */
    WORKFLOW_NODE_EXCEED_LIMITS(BAD_REQUEST, WORKFLOW, "1016"),

    /**
     * 工作流校验接口异常
     */
    WORKFLOW_VALIDATE_VERSION_ERROR(INTERNAL_SERVER_ERROR, WORKFLOW, "1017"),

    /**
     * 内容审核错误
     */
    CONTENT_REVIEW_ERROR(BAD_REQUEST, WORKFLOW, "1018"),

    /**
     * 控制器绑定工作流节点不合法
     */
    CONTROLLER_INVALID_WORKFLOW(INTERNAL_SERVER_ERROR, WORKFLOW, "1019"),

    /**
     * 工作流执行权限不足
     */
    INSUFFICIENT_WORKFLOW_RUN_PRIVILEGES(FORBIDDEN, WORKFLOW, "1020"),

    /**
     * 不是最新的工作流
     */
    NOT_LATEST_WORKFLOW(FORBIDDEN, WORKFLOW, "1021"),

    /**
     * 工作流运行超时
     */
    WORKFLOW_RUN_TIMEOUT(INTERNAL_SERVER_ERROR, WORKFLOW, "1022"),

    /**
     * 工作流异步任务不存在
     */
    WORKFLOW_ASYNC_TASK_NOT_FOUND(INTERNAL_SERVER_ERROR, WORKFLOW, "1023"),

    /**
     * 工作流异步任务状态不为PENDING
     */
    WORKFLOW_ASYNC_NOT_PENDING(INTERNAL_SERVER_ERROR, WORKFLOW, "1024"),

    /**
     * 工作流异步任务获取锁失败
     */
    WORKFLOW_ASYNC_GET_LOCK_FAILED(INTERNAL_SERVER_ERROR, WORKFLOW, "1025"),

    /**
     * 工作流异步任务执行失败
     */
    WORKFLOW_ASYNC_EXECUTE_FAILED(INTERNAL_SERVER_ERROR, WORKFLOW, "1026"),

    /**
     * This workflow was not created by you and you do not have permission to modify it
     */
    PRIVILEGE_ERROR(INTERNAL_SERVER_ERROR, WORKFLOW, "1027"),

    /**
     * 子工作流不存在
     */
    SUB_WORKFLOW_NOT_EXIST(NOT_FOUND, WORKFLOW, "1028"),

    /**
     * workflow version is not found
     */
    WORKFLOW_VERSION_NOT_FOUND(NOT_FOUND, WORKFLOW, "1029"),

    /**
     * workflow has not been published yet!
     */
    WORKFLOW_NOT_PUBLISHED(NOT_FOUND, WORKFLOW, "1030"),

    /**
     * 任务型工作流不允许使用%s类型的节点%s
     */
    WORKFLOW_TASK_INVALID_NODE(BAD_REQUEST, WORKFLOW, "1031"),

    /**
     * 该租户没有发布权限
     */
    WORKFLOW_TENANT_NOT_PERMISSION(INTERNAL_SERVER_ERROR, WORKFLOW, "1032"),

    /**
     * IR conversion ERROR, output reference type invalid
     */
    WORKFLOW_IR_FAILED_OUTPUT_TYPE_INVALID(BAD_REQUEST, WORKFLOW, "1033"),

    /**
     * IR conversation error There is no matching complex intent node
     */
    WORKFLOW_IR_ERROR_COMPLEX_INTENT_NODE(BAD_REQUEST, WORKFLOW, "1034"),

    /**
     * 安全护栏错误
     */
    SAFETY_BARRIER_ERROR(BAD_REQUEST, WORKFLOW, "1035"),

    /**
     * 没有发布的插件/工作流不能设置为自定义节点
     */
    PUBLISH_CUSTOMIZE_NODE_ERROR(BAD_REQUEST, WORKFLOW, "1036"),

    /**
     * workflow信息校验失败, Workflow icon size exceeds limit {0} KB
     */
    CHECK_WORKFLOW_INFO_FAILED_ICON(BAD_REQUEST, WORKFLOW, "1037"),

    /**
     * workflow信息校验失败, unsupported workflow field value type
     */
    CHECK_WORKFLOW_INFO_FAILED_VALUE_TYPE(BAD_REQUEST, WORKFLOW, "1038"),

    /**
     * workflow信息校验失败, json schema exceed max depth
     */
    CHECK_WORKFLOW_INFO_FAILED_DEPTH(BAD_REQUEST, WORKFLOW, "1039"),

    /**
     * 自定义节点数量超过最大限制
     */
    CUSTOMIZE_NODE_NUMBER_EXCEED_LIMIT(BAD_REQUEST, WORKFLOW, "1040"),

    /**
     * projectId:{0} do not have permission to publish or unpublish customize node.
     */
    NO_PERMISSION_PUBLISH_CUSTOMIZE_NODE(FORBIDDEN, WORKFLOW, "1041"),

    /**
     * 内容审核错误, size exceed {0} for type {1}
     */
    CONTENT_REVIEW_ERROR_SIZE(BAD_REQUEST, WORKFLOW, "1042"),

    /**
     * 内容审核错误, length exceed {0} for type {1}
     */
    CONTENT_REVIEW_ERROR_LENGTH(BAD_REQUEST, WORKFLOW, "1043"),

    /**
     * 输入审核长度错误
     */
    INPUT_TEXT_ERROR_LENGTH(BAD_REQUEST, WORKFLOW, "1044"),

    /**
     * 输出审核长度错误
     */
    OUTPUT_TEXT_ERROR_LENGTH(BAD_REQUEST, WORKFLOW, "1045"),

    /**
     * 替换词长度错误
     */
    REPLACE_WORD_ERROR_LENGTH(BAD_REQUEST, WORKFLOW, "1046"),

    /**
     * 子工作流不可用
     */
    SUB_WORKFLOW_CANNOT_USE(BAD_REQUEST, WORKFLOW, "1047"),

    /**
     * unsupported workflow branch field value type
     */
    WORKFLOW_BRANCH_FIELD_VALUE(BAD_REQUEST, WORKFLOW, "1048"),

    /**
     * unsupported validator
     */
    CONVERT_NODE_FAILED_VALIDATOR(BAD_REQUEST, WORKFLOW, "1049"),

    /**
     * parse date time format failed
     */
    CONVERT_NODE_FAILED_PARSE(BAD_REQUEST, WORKFLOW, "1050"),

    /**
     * parse length limit format failed
     */
    CONVERT_NODE_FAILED_PARSE_LENGTH(BAD_REQUEST, WORKFLOW, "1051"),

    /**
     * number format failed
     */
    CONVERT_NODE_FAILED_NUM_FORMAT(BAD_REQUEST, WORKFLOW, "1052"),

    /**
     * integer format failed
     */
    CONVERT_NODE_FAILED_INT_LENGTH(BAD_REQUEST, WORKFLOW, "1053"),

    /**
     * enum format failed
     */
    CONVERT_NODE_FAILED_ENUM_LENGTH(BAD_REQUEST, WORKFLOW, "1054"),

    /**
     * range param format failed
     */
    CONVERT_NODE_FAILED_PARAM_LENGTH(BAD_REQUEST, WORKFLOW, "1055"),

    /**
     * IR conversion error, settings format invalid
     */
    CONVERT_NODE_FAILED_INVALID_LENGTH(BAD_REQUEST, WORKFLOW, "1056"),

    /**
     * unexpected operator: {0}
     */
    WORKFLOW_UNEXPECTED_OPERATOR(BAD_REQUEST, WORKFLOW, "1057"),

    /**
     * JiuWen Service调用失败   JiuWen Service invoke exception.
     */
    JIU_WEN_SERVICE_EXCEPTION(INTERNAL_SERVER_ERROR, WORKFLOW, "1058"),

    /**
     * 客户端断开流式接口请求   "Client aborted request."
     */
    CLIENT_ABORT_REQUEST(INTERNAL_SERVER_ERROR, WORKFLOW, "1059"),

    /**
     * 工作流循环次数超过最大范围
     */
    WORKFLOW_LOOP_EXCEED_RANGE(BAD_REQUEST, WORKFLOW, "1060"),

    /**
     * 无权限使用该工作流，工作流id为：{}
     */
    WORKFLOW_NO_PERMISSION(BAD_REQUEST, WORKFLOW, "1061"),

    /**
     * 最多选择3个知识库
     */
    WORKFLOW_KNOWLEDGE_REPO_NUM(BAD_REQUEST, WORKFLOW, "1062"),

    /**
     * Run workflow failed.
     */
    WORKFLOW_RUN_FAILED(BAD_REQUEST, WORKFLOW, "1063"),

    /**
     * 节点异常处理配置不合法；节点名称：{}
     */
    WORKFLOW_EXCEPTION_CONFIG_INVALID(BAD_REQUEST, WORKFLOW, "1064"),

    /**
     * 节点超时时间范围应该在{0}到{1}之间
     */
    WORKFLOW_TIME_RANGE_INVALID(BAD_REQUEST, WORKFLOW, "1065"),

    /**
     * 子工作流不存在，子工作流id为：{}
     */
    CHILD_WORKFLOW_NOT_EXIST(NOT_FOUND, WORKFLOW, "1066"),

    /**
     * 工作流节点：{}引用的资源不存在或异常，请检查
     */
    WORKFLOW_FLOW_RESOURCE_IMPORT_FAILED(BAD_REQUEST, WORKFLOW, "1067"),

    /**
     * 异步运行需要账号开启IAM委托
     */
    ASYNC_TASK_ACCOUNT_FAILED(BAD_REQUEST, WORKFLOW, "1069"),

    /**
     * 异步运行执行超时
     */
    ASYNC_TASK_EXECUTE_TIMEOUT(BAD_REQUEST, WORKFLOW, "1070"),

    /**
     * 异步运行任务失败，原因：{0}
     */
    ASYNC_TASK_EXECUTE_FAILED(BAD_REQUEST, WORKFLOW, "1071"),

    /**
     * 代码节点不支持沙箱执行方式
     */
    CODE_NOT_SUPPORT_SANDBOX(BAD_REQUEST, WORKFLOW, "1072"),

    /**
     * 工作流发布渠道不存在
     */
    WORKFLOW_CHANNEL_NOT_EXIST(BAD_REQUEST, WORKFLOW, "1073"),

    /**
     * 当前指定渠道类型不支持删除
     */
    WORKFLOW_CHANNEL_NOT_SUPPORT_DELETE(BAD_REQUEST, WORKFLOW, "1074"),


    /**
     * 工作流异常配置重试次数设置不合法
     */
    WORKFLOW_EXCEPTION_RETRY_TIMES_INVALID(BAD_REQUEST, WORKFLOW, "1077"),

    /**
     * 节点流式输出，异常配置参数不合法
     */
    WORKFLOW_EXCEPTION_STREAM_INVALID(BAD_REQUEST, WORKFLOW, "1078"),

    /**
     * 大模型节点，异常处理类型设置不合法
     */
    WORKFLOW_EXCEPTION_LLM_HANDLE_TYPE_INVALID(BAD_REQUEST, WORKFLOW, "1079"),

    /**
     * 工作流节点不支持重试
     */
    WORKFLOW_EXCEPTION_WORKFLOW_NOT_SUPPORT_RETRY(BAD_REQUEST, WORKFLOW, "1080"),

    /**
     * 异常处理handler设置不合法
     */
    WORKFLOW_EXCEPTION_NOT_SUPPORT_HANDLER(BAD_REQUEST, WORKFLOW, "1081"),

    /**
     * 工作流未试运行成功不能发布
     */
    WORKFLOW_CANNOT_RELEASE_FOR_NOT_TEST_SUCCESS(BAD_REQUEST, WORKFLOW, "1082"),

    /**
     * 资源不存在
     */
    RESOURCE_NOT_EXISTS(BAD_REQUEST, WORKFLOW, "1083"),

    /**
     * 获取工作流调试事件失败
     */
    OBTAIN_DEBUG_EVENT_FAILED(BAD_REQUEST, WORKFLOW, "1084"),

    /**
     * 工作流包含隐藏节点
     */
    WORKFLOW_BLOCK_NODE_EXIST(BAD_REQUEST, WORKFLOW, "1085"),

    /**
     * 九问引擎连接异常
     */
    JIUWEN_CONNECTION_EXCEPTION(BAD_REQUEST, WORKFLOW, "1086"),

    /**
     * 九问引擎连接超时
     */
    JIUWEN_CONNECTION_TIMEOUT(BAD_REQUEST, WORKFLOW, "1087"),

    /**
     * 提问器节点配置长度超过最大限制
     */
    QUESTIONER_CONFIG_EXCEED_MAX_LENGTH(BAD_REQUEST, WORKFLOW, "1088"),


    INTERFACE_FORBIDDEN_ACCESS(FORBIDDEN, WORKFLOW, "1089"),

    /**
     * 解析第三方工作流文件失败
     */
    PARSE_THIRD_PARTY_WORKFLOW_FILE_FAILED(BAD_REQUEST, WORKFLOW, "1090"),

    /**
     * 工作流服务配置的目标地址受限（如包含内网IP或黑名单域名）
     */
    WORKFLOW_ADDRESS_RESTRICTED(BAD_REQUEST, WORKFLOW, "1091"),

    /**
     * 不支持的工作流类型
     */
    UNSUPPORTED_WORKFLOW_TYPE(BAD_REQUEST, WORKFLOW, "1092"),

    /**
     * 缺少定义输出格式
     */
    MISSING_FRAME_TEMPLATE(BAD_REQUEST, WORKFLOW, "1093"),

    /**
     * 输出格式非 JSON 格式
     */
    FRAME_TEMPLATE_INVALID_JSON(BAD_REQUEST, WORKFLOW, "1094"),

    /**
     * 缺少 transformer
     */
    MISSING_TRANSFORMER(BAD_REQUEST, WORKFLOW, "1095"),

    /**
     * 不支持导入的资源
     */
    UNSUPPORTED_RESOURCE_IMPORT(BAD_REQUEST, WORKFLOW, "1097"),

    /*
     * ============================== 多智能体相关错误码 ==============================
     */
    /**
     * multi agent缺失controller节点
     */
    MULTI_AGENT_LACK_CONTROLLER_NODE(BAD_REQUEST, MULTI_AGENT, "1001"),

    /**
     * 多agent节点为空
     */
    MULTI_AGENT_NODES_IS_EMPTY(BAD_REQUEST, MULTI_AGENT, "1002"),

    /**
     * 多agent子工作流重复
     */
    MULTI_AGENT_HAVE_DUPLICATE_SON_WORKFLOW(BAD_REQUEST, MULTI_AGENT, "1003"),

    /**
     * 多agent controller节点configs为空
     */
    MULTI_AGENT_CONTROLLER_CONFIGS_NULL(BAD_REQUEST, MULTI_AGENT, "1004"),

    /**
     * 不支持的工作流类型
     */
    MULTI_AGENT_UNSUPPORTED_WORKFLOW_TYPE(BAD_REQUEST, MULTI_AGENT, "1005"),

    /**
     * Intent workflow config is not valid!
     */
    MULTI_AGENT_WORKFLOW_CONFIG_VALID(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1006"),

    /**
     * Intent workflow input or output should not be empty
     */
    MULTI_AGENT_WORKFLOW_INPUT_EMPTY(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1007"),

    /**
     * Duplicated intent node
     */
    MULTI_AGENT_DUPLICATED_NODE(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1008"),

    /**
     * intent workflow param query is not valid
     */
    MULTI_AGENT_WORKFLOW_PARAM_VALID(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1009"),

    /**
     * intent workflow input param minScore is not valid
     */
    MULTI_AGENT_WORKFLOW_MIN_SCORE_VALID(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1010"),

    /**
     * intent workflow missing required inputs param: {0}
     */
    MULTI_AGENT_WORKFLOW_MISSING(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1011"),

    /**
     * intent workflow output param intent_id is not valid
     */
    MULTI_AGENT_WORKFLOW_INTENT_VALID(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1012"),

    /**
     * intent workflow missing output param: {0}
     */
    MULTI_AGENT_WORKFLOW_OUTPUT_MISSING(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1013"),

    /**
     * intent workflow input param messages sub param {0} is not valid
     */
    MULTI_AGENT_WORKFLOW_INPUT_SUB_PARAM_VALID(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1014"),

    /**
     * intent workflow message param missing properties: {0}
     */
    MULTI_AGENT_WORKFLOW_MESSAGE_MISSING(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1015"),

    /**
     * intent workflow param intents sub param {0} is not valid
     */
    MULTI_AGENT_WORKFLOW_INTENT_PARAM_VALID(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1016"),

    /**
     * intent workflow intents param missing properties: {0}
     */
    MULTI_AGENT_WORKFLOW_PROPERTY_MISS(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1017"),

    /**
     * Intent workflow should not contain interactive node
     */
    MULTI_AGENT_WORKFLOW_CONTAIN_NODE(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1018"),

    /**
     * sub workflow version {0} is not found!
     */
    MULTI_AGENT_SUB_WORKFLOW_VERSION_NOT_FOUND(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1019"),

    /**
     * 多智能体名称冲突
     */
    MULTI_AGENT_NAME_CONFLICT(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1020"),

    /**
     * 多agent子agent重复
     */
    MULTI_AGENT_HAVE_DUPLICATE_SON_AGENT(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1021"),

    /**
     * 多agent绑定的子控制器数量超过上限
     */
    MULTI_AGENT_NUMBER_EXCEED_LIMIT(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1022"),

    /**
     * 多agent绑定的子控制器版本不存在
     */
    MULTI_AGENT_VERSION_NOT_EXIST(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1023"),

    /**
     * 多控制器导出失败
     */
    MULTI_AGENT_EXPORT_FAILED(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1024"),

    /**
     * 多控制器子控制器嵌套达最大深度
     */
    MULTI_AGENT_EXCEED_MAX_DEPTH(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1025"),

    /**
     * 多agent输入参数默认值最大长度
     */
    MULTI_AGENT_INPUT_DEFAULT_VALUE_MAX_LENGTH(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1026"),

    /**
     * 多agent全局变量默认值最大长度
     */
    MULTI_AGENT_GLOBAL_VARIABLE_VALUE_MAX_LENGTH(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1027"),
    /**
     * 模型导出失败
     */
    MODEL_EXPORT_DATA(INTERNAL_SERVER_ERROR, MODEL, "1028"),
    /**
     * 模型不存在
     */
    MODEL_NOT_EXIST(NOT_FOUND, MODEL, "1029"),

    /**
     * 多agent模型配置或意图识别为空
     */
    MULTI_AGENT_MODEL_OR_INTENT_IS_NULL(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1028"),

    /**
     * 控制器只能挂载一个Plan&Execute模式的子Agent
     */
    MULTI_AGENT_ONLY_ONE_PLAN_EXECUTE_AGENT(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1029"),

    /**
     * Plan&Execute模式的子Agent只能挂在顶层控制器
     */
    MULTI_AGENT_PLAN_EXECUTE_ONLY_IN_TOP_CONTROLLER(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1030"),

    /**
     * 多智能体不能关联自身
     */
    MULTI_AGENT_CANNOT_ASSOCIATE_SELF(INTERNAL_SERVER_ERROR, MULTI_AGENT, "1031"),


    /*
     * ============================== 高代码智能体相关错误码 ==============================
     */
    /**
     * codeAgent不存在
     */
    CODE_AGENT_NOT_EXIST(NOT_FOUND, CODE_AGENT, "1001"),

    /**
     * codeAgent名称已存在
     */
    CODE_AGENT_NAME_EXIST(BAD_REQUEST, CODE_AGENT, "1002"),

    /**
     * 智能生成名称和描述失败
     */
    GENERATE_NAME_AND_DESCRIPTION_FAILED(BAD_REQUEST, CODE_AGENT, "1003"),

    /**
     * 删除session失败
     */
    DELETE_SESSION_FAILED(BAD_REQUEST, CODE_AGENT, "1004"),

    /*
     * ============================== 配置管理（意图、数据源）模块相关错误码 ==============================
     */
    /**
     * 导入意图包分支数量超过限制
     */
    BRANCHES_SIZE_EXCEEDS_LIMIT(BAD_REQUEST, CONFIG, "1001"),

    /**
     * 导入意图包失败
     */
    INTENT_IMPORT_FILE_ERROR(INTERNAL_SERVER_ERROR, CONFIG, "1002"),

    /**
     * 导入意图包，Exceeded file size limit
     */
    INTENT_IMPORT_FILE_SIZE_LIMIT(INTERNAL_SERVER_ERROR, CONFIG, "1003"),

    /**
     * 导出意图包失败
     */
    INTENT_EXPORT_FILE_ERROR(INTERNAL_SERVER_ERROR, CONFIG, "1004"),


    /**
     * 访问的静态资源不存在
     */
    STATIC_RESOURCE_NOT_EXIST(NOT_FOUND, CONFIG, "1007"),

    /**
     * 资源操作失败，Duplicate resource name, please check model name
     */
    RESOURCE_OP_ERROR(BAD_REQUEST, CONFIG, "1008"),

    /**
     * 资源操作失败, "branch_id {0} conflicts with existing intent {1} (branch name: {2})"
     */
    RESOURCE_OP_ERROR_CONFLICT(BAD_REQUEST, CONFIG, "1009"),

    /**
     * Duplicate resource embedding or rerank or ocr api model name, please check api model name
     */
    RESOURCE_EMBEDDING_RERANK_API_NAME(BAD_REQUEST, CONFIG, "1011"),

    /**
     * 资源操作失败, model name is not valid!
     */
    RESOURCE_MODEL_NAME_INVALID(BAD_REQUEST, CONFIG, "1012"),

    /**
     * unsupported auth type
     */
    RESOURCE_MODEL_UNSUPPORTED_AUTH_TYPE(BAD_REQUEST, CONFIG, "1013"),

    /**
     * \"******\" is not supported for api-key
     */
    RESOURCE_API_KEY_UNSUPPORTED(BAD_REQUEST, CONFIG, "1014"),

    /**
     * {0} is not supported for iam password and iam secret key
     */
    RESOURCE_IAM_KEY_UNSUPPORTED(BAD_REQUEST, CONFIG, "1015"),

    /**
     * 添加定时任务失败
     */
    ADD_QUARTZ_JOB_FAILED(BAD_REQUEST, CONFIG, "1018"),

    /**
     * 导入的意图包名称长度超过限制
     */
    IMPORT_BRANCH_NAME_EXCEED_LIMIT(BAD_REQUEST, CONFIG, "1019"),

    /**
     * 导入的意图样例名称超过限制
     */
    IMPORT_COMPLEX_INTENT_EXAMPLE_EXCEED_LIMIT(BAD_REQUEST, CONFIG, "1020"),

    /**
     * 导入的意图包名称无效
     */
    IMPORT_COMPLEX_INTENT_NAME_INVALID(BAD_REQUEST, CONFIG, "1021"),

    /**
     * 导入的意图名称无效
     */
    IMPORT_COMPLEX_INTENT_BRANCH_NAME_INVALID(BAD_REQUEST, CONFIG, "1022"),

    /**
     * 导入的意图样例无效
     */
    IMPORT_COMPLEX_INTENT_EXAMPLE_INVALID(BAD_REQUEST, CONFIG, "1023"),

    /**
     * 意图样例重复
     */
    COMPLEX_INTENT_EXAMPLE_REPEATED(BAD_REQUEST, CONFIG, "1024"),

    /* ***********************模型接入***********************/
    /**
     * 缺少模型配置
     */
    MODEL_CONFIG_MISS(BAD_REQUEST, Module.MODEL, "1001"),

    /**
     * 供应商名称重复
     */
    PROVIDER_NAME_REPEATED(BAD_REQUEST, Module.MODEL, "1002"),

    /**
     * 模型名称重复
     */
    MODEL_NAME_REPEATED(BAD_REQUEST, Module.MODEL, "1003"),

    /**
     * 路由策略名称重复
     */
    ROUTER_STRATEGY_NAME_REPEATED(BAD_REQUEST, Module.MODEL, "1004"),

    /**
     * model调用异常
     */
    CALL_MODEL_ERROR(INTERNAL_SERVER_ERROR, MODEL, "1005"),

    /**
     * 模型调用地址不满足要求
     */
    MODEL_URL_IS_ILLEGAL(BAD_REQUEST, MODEL, "1006"),

    /**
     * 模型调用被安全风控拦截
     */
    MODEL_SECURITY_CHECK_BLOCK(BAD_REQUEST, Module.MODEL, "1007"),

    /**
     * Model service provider auth info is invalid
     */
    MD_AUTH_INFO_INVALID(BAD_REQUEST, MODEL, "1008"),

    /**
     * provider not exist or not belong to project.
     */
    MD_PROVIDER_NOT_EXIST(NOT_FOUND, MODEL, "1009"),

    /**
     * provider_id and metadata_id cannot all empty
     */
    MD_REQUEST_PARAM_INVALID(BAD_REQUEST, MODEL, "1010"),

    /**
     * provider_id and auth_id cannot all empty
     */
    MD_REQUEST_PARAM_AUTH_INVALID(BAD_REQUEST, MODEL, "1011"),

    /**
     * Metadata of model is not exist
     */
    MD_AUTH_METADATA_MODEL_NOT_EXIST(NOT_FOUND, MODEL, "1012"),

    /**
     * Model service does not exist.
     */
    MD_DATA_NOT_EXIST(NOT_FOUND, MODEL, "1013"),

    /**
     * User no model service permission
     */
    MD_SERVICE_PERMISSION(FORBIDDEN, MODEL, "1014"),

    /**
     * auth data is not exist
     */
    MD_AUTH_DATA_NOT_EXIST(NOT_FOUND, MODEL, "1015"),

    /**
     * user no permission delete auth data.
     */
    MD_USER_NO_PERMISSION_DELETE(BAD_REQUEST, MODEL, "1016"),

    /**
     * auth metadata is not exist.
     */
    MD_AUTH_METADATA_NOT_EXIST(NOT_FOUND, MODEL, "1017"),

    /**
     * User not permission operate this provider
     */
    MD_USER_NOT_PERMISSION_OPERATE(BAD_REQUEST, MODEL, "1018"),

    /**
     * ModelService publish status is already
     */
    MD_MODEL_SERVICE_TARGET_STATUS_INVALID(CONFLICT, MODEL, "1019"),

    /**
     * Modification of the model service is not permitted
     */
    MD_MODEL_SERVICE_CANNOT_CHANGE(BAD_REQUEST, MODEL, "1020"),

    /**
     * Invalid request body, Duplicate model exists
     */
    MD_REQUEST_BODY_INVALID(BAD_REQUEST, MODEL, "1021"),

    /**
     * Invalid request body, Model is empty
     */
    MD_REQUEST_BODY_INVALID_MODEL(BAD_REQUEST, MODEL, "1022"),

    /**
     * Invalid request body, Some model is not exist.
     */
    MD_REQUEST_BODY_INVALID_MODEL_NOT_EXIST(BAD_REQUEST, MODEL, "1023"),

    /**
     * Model service auth config is not exist
     */
    MD_MODEL_SERVICE_AUTH_NOT_EXIST(BAD_REQUEST, MODEL, "1024"),

    /**
     * Model service publish status is already publish. cannot delete.
     */
    MD_MODEL_SERVICE_IS_PUBLISH(BAD_REQUEST, MODEL, "1025"),

    /**
     * Router strategy not exist
     */
    MD_ROUTER_STRATEGY_NOT_EXIST(BAD_REQUEST, MODEL, "1026"),

    /**
     * workspaceId is empty. miss workspaceId in query or header params.
     */
    MD_WORKSPACE_IS_MISS(BAD_REQUEST, MODEL, "1027"),

    /**
     * Model service provider auth info is invalid. AK_SK auth config is invalid.
     */
    MD_AUTH_INFO_AUTH_INVALID(BAD_REQUEST, MODEL, "1028"),

    /**
     * Model service provider auth info is invalid. API_KEY auth config is invalid
     */
    MD_AUTH_INFO_API_INVALID(BAD_REQUEST, MODEL, "1029"),

    /**
     * Model service provider auth info is invalid. APP_CODE auth config is invalid.
     */
    MD_AUTH_INFO_APP_INVALID(BAD_REQUEST, MODEL, "1030"),

    /**
     * Request param is invalid. stream is not boolean.
     */
    MD_REQUEST_BODY_INVALID_STREAM(BAD_REQUEST, MODEL, "1031"),

    /**
     * Fail get model strategy.
     */
    MD_MODEL_SERVICE_NOT_PUBLISH(BAD_REQUEST, MODEL, "1032"),

    /**
     * request model service timeout.
     */
    MD_MODEL_SERVICE_REQUEST_TIMEOUT(GATEWAY_TIMEOUT, MODEL, "1033"),

    /**
     * request model service internal error
     */
    MD_MODEL_SERVICE_REQUEST_INTERNAL_ERROR(INTERNAL_SERVER_ERROR, MODEL, "1034"),

    /**
     * Invoke third model service fail. Empty http response!
     */
    MD_INVOKE_MODEL_SERVICE_FAIL(BAD_GATEWAY, MODEL, "1035"),

    /**
     * Invoke third model service fail. Model response body paras to object exception.
     */
    MD_INVOKE_MODEL_SERVICE_FAIL_BODY(BAD_REQUEST, MODEL, "1036"),

    /**
     * model service is not available
     */
    MD_MODEL_SERVICE_NOT_AVAILABLE(SERVICE_UNAVAILABLE, MODEL, "1037"),

    /**
     * Model strategy no available model.
     */
    MD_MODEL_STRATEGY_NO_AVAILABLE(BAD_REQUEST, MODEL, "1038"),

    /**
     * The request was blocked by traffic control; please try again later.
     */
    MD_INVOKE_TOO_MANY_REQUEST(TOO_MANY_REQUESTS, MODEL, "1039"),

    /**
     * The model type does not meet the requirements
     */
    MD_MODEL_TYPE_INVALID(BAD_REQUEST, MODEL, "1040"),

    /**
     * User not permission operate this auth metadata.
     */
    MD_AUTH_METADATA_PERMISSION_NOT_EXIST(BAD_REQUEST, MODEL, "1041"),

    /**
     * 供应商存在接入模型服务，无法删除
     */
    PROVIDER_ASSOCIATED_MODEL(BAD_REQUEST, MODEL, "1042"),

    MD_PROVIDER_AUTH_DATA_NOT_EXIST(BAD_REQUEST, MODEL, "1043"),

    MD_MODEL_API_URL_INVALID(BAD_REQUEST, MODEL, "1044"), // 模型URL配置不正确
    MD_PROVIDER_AUTH_DATA_INVALID(UNAUTHORIZED, MODEL, "1045"), // 认证配置不可用
    MD_NO_MODEL_ACCESS_PERMISSION(FORBIDDEN, MODEL, "1046"), // 无模型访问权限
    MD_OUTSTANDING_FEEDS(FORBIDDEN, MODEL, "1047"), // 欠费
    MD_MODEL_SERVICE_NOT_EXIST(FORBIDDEN, MODEL, "1048"), // 模型服务不存在
    MD_THIRD_MODEL_FAIL(FORBIDDEN, MODEL, "1049"), // 调用第三方模型服务失败

    /**
     * workspace is not found.
     */
    MD_WORKSPACE_FIND_ERROR(BAD_REQUEST, MODEL, "1050"),

    /**
     * 免费模型Token额度使用完成
     */
    MD_FREE_MODEL_TOKENS_USED_UP(FORBIDDEN, MODEL, "1051"),

    /**
     * License 控制限制接入模型
     */
    MD_FORBIDDEN_ACCESS_MODEL(FORBIDDEN, MODEL, "1052"),
    MD_MODEL_ROUTER_INVALID(FORBIDDEN, MODEL, "1053"), // 模型路由策略不正确
    MD_THIRD_FREE_QUOTA_USED_UP(UNAUTHORIZED, MODEL, "1054"), // 第三方模型的免费额度已用完
    MD_MSG_CONTAIN_SENSITIVE(UNAUTHORIZED, MODEL, "1055"), // 第三方模型的免费额度已用完

    MD_GET_CUSTOM_MODELS_FAIL(INTERNAL_SERVER_ERROR, MODEL, "1056"), // 查询模型网关失败

    MD_PROVIDER_AUTH_NOT_SUPPORT_DELETE(INTERNAL_SERVER_ERROR, MODEL, "1061"), // 当前模型服务鉴权类型，鉴权配置不允许删除 如 IAM和NO_AUTH

    /**
     * 模型开通错误码
     */
    MD_SUBSCRIBE_NONEXISTENT_SERVICE(BAD_REQUEST, MODEL, "1070"),
    MD_PROVIDER_AUTH_BOUND_QUERY_FAILED_BAD_PARAM(INTERNAL_SERVER_ERROR, MODEL, "1071"),
    MD_PROVIDER_AUTH_BOUND_QUERY_FAILED_MORE_THAN_ONE_RECORD(INTERNAL_SERVER_ERROR, MODEL, "1072"),
    MD_SUBSCRIBE_MAAS_APIKEY_CREATE_LIMIT(BAD_REQUEST, MODEL, "1073"),

    /**
     * 模型url无效{0}
     */
    MD_URL_INVALID(BAD_REQUEST, MODEL, "1057"),

    MD_MODEL_OR_AUTH_NOT_INVALID(BAD_REQUEST, MODEL, "1058"), // 认证配置或者模型不正确

    MD_MODEL_TAGS_LIMIT(BAD_REQUEST, MODEL, "1059"),

    MD_INVALID_THROTTLING_POLICY(BAD_REQUEST, MODEL, "1060"),

    API_KEY_CREATE_ERROR(NOT_ACCEPTABLE, MODEL, "1062"),

    API_KEY_AUTH_ERROR(BAD_REQUEST, MODEL, "1063"),

    API_KEY_NAME_EXIST(BAD_REQUEST, MODEL, "1064"),

    API_KEY_NUM_LIMIT(BAD_REQUEST, MODEL, "1065"),

    API_KEY_UNABLE(BAD_REQUEST, MODEL, "1066"),

    INVOKE_MODEL_BAD_REQUEST(BAD_REQUEST, MODEL, "1067"),

    MD_PROVIDER_URL_IS_NULL(BAD_REQUEST, MODEL, "1068"),   // 同步模型服务url不能为空

    MD_MODEL_FORBID_DELETE_OR_UNPUBLISH(BAD_REQUEST, MODEL, "1069"),


    MD_FREE_MODEL_RATE_LIMIT(BAD_REQUEST, MODEL, "1070"),

    /**
     * 视频生成任务不存在
     */
    MD_VIDEO_GENERATION_TASK_NOT_EXIST(BAD_REQUEST, MODEL, "1071"),

    /**
     * ============================== 组件（插件、MCP） ==============================
     */
    /**
     * 工具信息格式有误
     */
    TOOL_INPUT_INVALID(BAD_REQUEST, COMPONENT, "1001"),

    /**
     * 工具信息中入参格式有误
     */
    TOOL_INPUT_SCHEMA_INVALID(BAD_REQUEST, COMPONENT, "1002"),

    /**
     * 工具信息中出参格式有误
     */
    TOOL_OUTPUT_SCHEMA_INVALID(BAD_REQUEST, COMPONENT, "1003"),

    /**
     * 工具ID已存在
     */
    TOOL_NAME_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1004"),

    /**
     * 工具不存在
     */
    TOOL_NOT_EXIST(NOT_FOUND, COMPONENT, "1005"),

    /**
     * Workflow convert components failed!
     */
    CONVERT_NODE_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1006"),

    /**
     * 工具无修改权限
     */
    NO_PERMISSION_MODIFY_TOOL(FORBIDDEN, COMPONENT, "1007"),

    /**
     * 工具无删除权限
     */
    NO_PERMISSION_DELETE_TOOL(FORBIDDEN, COMPONENT, "1008"),

    /**
     * 插件导入失败
     */
    TOOL_IMPORT_FILE(INTERNAL_SERVER_ERROR, COMPONENT, "1009"),

    /**
     * 插件导出失败
     */
    TOOL_EXPORT_FILE(INTERNAL_SERVER_ERROR, COMPONENT, "1010"),

    /**
     * 依赖包为空
     */
    DEPENDENCY_FILE_EMPTY(BAD_REQUEST, COMPONENT, "1011"),

    /**
     * 依赖包过大
     */
    DEPENDENCY_FILE_TOO_LARGE(BAD_REQUEST, COMPONENT, "1012"),

    /**
     * 依赖包格式错误
     */
    DEPENDENCY_FILE_TYPE_ERROR(BAD_REQUEST, COMPONENT, "1013"),

    /**
     * 依赖包已存在
     */
    DEPENDENCY_EXIST(BAD_REQUEST, COMPONENT, "1014"),

    /**
     * 依赖包不存在
     */
    DEPENDENCY_NOT_EXIST(BAD_REQUEST, COMPONENT, "1015"),


    /**
     * data格式校验错误
     */
    DATA_FORMAT_ERROR(BAD_REQUEST, COMPONENT, "1018"),

    /**
     * 依赖包名称已存在
     */
    DEPENDENCY_NAME_EXIST(BAD_REQUEST, COMPONENT, "1019"),

    /**
     * 无效Scope
     */
    INVALID_SCOPE(BAD_REQUEST, COMPONENT, "1020"),

    /**
     * 请求依赖失败
     */
    REQUEST_DEPEND_FAILED(BAD_REQUEST, COMPONENT, "1021"),

    /**
     * 更新依赖失败
     */
    UPDATE_DEPENDENCY_ERROR(BAD_REQUEST, COMPONENT, "1022"),

    /**
     * 依赖包已被使用，删除失败
     */
    DEPENDENCY_DELETE_FAILED_IS_USED(BAD_REQUEST, COMPONENT, "1023"),

    /**
     * 依赖包删除失败
     */
    DEPENDENCY_DELETE_FAILED(BAD_REQUEST, COMPONENT, "1024"),

    /**
     * function's memory size can not over 2048
     */
    FUNCTION_MEMORY_SIZE_TOO_BIG(BAD_REQUEST, COMPONENT, "1025"),

    /**
     * parse UTF-8 exception
     */
    PARSE_UTF8_FAILED(BAD_REQUEST, COMPONENT, "1026"),

    /**
     * Python is not supported. Please select nodejs.
     */
    FUNCTION_NOT_SUPPORTED(BAD_REQUEST, COMPONENT, "1027"),

    /**
     * get function code failed
     */
    FUNCTION_GET_CODE_FAILED(BAD_REQUEST, COMPONENT, "1028"),

    /**
     * java11 function need codeType and codeFileName are not supported.
     */
    FUNCTION_PARAMETERS_NOT_SUPPORTED(BAD_REQUEST, COMPONENT, "1029"),

    /**
     * the number of function over threshold
     */
    FUNCTION_NUMBER_OVER_THRESHOLD(BAD_REQUEST, COMPONENT, "1031"),

    /**
     * function not found
     */
    FUNCTION_NOT_FOUND(BAD_REQUEST, COMPONENT, "1032"),

    /**
     * function runtime is not support
     */
    FUNCTION_RUNTIME_NOT_SUPPORT(BAD_REQUEST, COMPONENT, "1033"),

    /**
     * update code failed
     */
    FUNCTION_CODE_UPDATE_FAILED(BAD_REQUEST, COMPONENT, "1034"),

    /**
     * 函数名称重复
     */
    FUNCTION_NAME_EXIST(BAD_REQUEST, COMPONENT, "1035"),

    /**
     * Check tool info failed! node name is {0}
     */
    GET_TOOL_INFO_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1036"),

    /**
     * 插件权限错误, ID:{0}
     */
    PLUGIN_PRIVILEGE_ERROR(BAD_REQUEST, COMPONENT, "1037"),

    /**
     * Tool {0} projectId {1} workspaceId {2} does not exist
     */
    TOOL_PROJECT_DONE_NOT_EXIST(BAD_REQUEST, COMPONENT, "1038"),

    /**
     * 文件解析失败
     */
    FILE_RESOLVE_FILE(INTERNAL_SERVER_ERROR, COMPONENT, "1039"),

    /**
     * 文件格式错误
     */
    FILE_FORMAT_INCORRECT(BAD_REQUEST, COMPONENT, "1040"),

    /**
     * 超出最大导出数量限制, 最大导出数量为{0}
     */
    EXPORT_LENGTH_TOO_LARGE(BAD_REQUEST, COMPONENT, "1041"),

    /**
     * version not exist. id: {0}, version:{1}.
     */
    TOOL_VERSION_NOT_EXIST(NOT_FOUND, COMPONENT, "1042"),

    /**
     * 获取obs临时url失败
     */
    GET_OBS_TEMPORARY_URL_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1043"),

    /**
     * Visibility value:{0} is invalid.
     */
    INVALID_VISIBILITY(BAD_REQUEST, COMPONENT, "1044"),

    /**
     * openapi生成失败
     */
    OPEN_API_GEN_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1045"),

    /**
     * 发布一个未经测试的组件
     */
    PUBLISH_UNTESTED(INTERNAL_SERVER_ERROR, COMPONENT, "1046"),

    /**
     * 插件鉴权失败
     */
    TOOL_AUTHENTICATION_FAILED(UNAUTHORIZED, COMPONENT, "1047"),

    /**
     * 插件凭证不存在
     */
    TOOL_CREDENTIAL_NOT_EXIST(UNAUTHORIZED, COMPONENT, "1048"),

    /**
     * 插件已有凭证
     */
    TOOL_CREDENTIAL_ALREADY_EXIST(UNAUTHORIZED, COMPONENT, "1049"),

    /**
     * 工具中文名已存在
     */
    TOOL_CN_NAME_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1050"),

    /**
     * 工具英文名已存在
     */
    TOOL_EN_NAME_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1051"),

    /**
     * MCP服务不存在
     */
    MCP_SERVER_NOT_EXIST(NOT_FOUND, COMPONENT, "1052"),

    /**
     * 更新记忆参数信息失败 Fail to update memory variables.
     */
    UPDATE_MEMORY_VARIABLES_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1053"),

    /**
     * 获取记忆参数信息失败  Fail to retrieve memory variables.
     */
    RETRIEVE_MEMORY_VARIABLES_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1054"),

    /**
     * 获取文件输入流失败  Get inputStream from obs by url failed.
     */
    GET_BY_URL_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1055"),

    /**
     * 解析文件失败  Resolve file failed.
     */
    RESOLVE_FILE_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1056"),

    /**
     * 文件不存在   "File is not exist."
     */
    FILE_NOT_EXIST(INTERNAL_SERVER_ERROR, COMPONENT, "1057"),

    /**
     * open api文件解析失败  "parse openapi file failed."
     */
    OPEN_API_PARSE_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1058"),

    /**
     * 从uri中获取path失败  File path is empty or in incorrect format.
     */
    GET_PATH_FROM_URI_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1059"),

    /**
     * Mcp 服务相关错误  "MCP Request Error"
     */
    MCP_REQUEST_ERROR(INTERNAL_SERVER_ERROR, COMPONENT, "1060"),

    /**
     * 构建文件输入流失败  Build file inputStream failed.
     */
    BUILD_INPUT_STREAM_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1061"),

    /**
     * 图片base64编码失败  Failed to encoding image to base64.
     */
    IMAGE_TO_BASE64_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1062"),

    /**
     * OCR识别失败  Failed to process image with ocr.
     */
    OCR_RECOGNIZE_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1063"),

    /**
     * urls参数校验失败  Urls is null or exceed the max url number.
     */
    VALIDATE_RESOLVE_URLS_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1064"),

    /**
     * Api {0} not found in table!
     */
    MCP_API_NOT_FOUND(NOT_FOUND, COMPONENT, "1065"),

    /**
     * Adapt ir failed, mcp server not exist, id: {0}
     */
    MCP_ADAPT_IR_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1066"),

    /**
     * Adapt ir failed, mcp server tool not exist, ID: {0}, 工具名: {1}
     */
    MCP_SERVER_TOOL_NOT_EXIST(NOT_FOUND, COMPONENT, "1067"),

    /**
     * Mcp server with the same name already exist
     */
    MCP_NAME_DUPLICATE(BAD_REQUEST, COMPONENT, "1068"),

    /**
     * Mcp server with id {0} not exist
     */
    MCP_SERVER_ID_NOT_EXIST(NOT_FOUND, COMPONENT, "1069"),

    /**
     * Mcp config already exist
     */
    MCP_CONFIG_EXIST(BAD_REQUEST, COMPONENT, "1070"),

    /**
     * mcp config not exist
     */
    MCP_CONFIG_NOT_EXIST(INTERNAL_SERVER_ERROR, COMPONENT, "1071"),

    /**
     * Mcp server not exist
     */
    MCP_NOT_EXIST(NOT_FOUND, COMPONENT, "1072"),

    /**
     * MCP server url is empty
     */
    MCP_SERVER_URL_EMPTY(BAD_REQUEST, COMPONENT, "1073"),

    /**
     * update mcp server url is not allowed
     */
    UPDATE_MCP_URL_NOT_ALLOW(FORBIDDEN, COMPONENT, "1074"),

    /**
     * mcp server name is empty
     */
    MCP_NAME_EMPTY(BAD_REQUEST, COMPONENT, "1075"),

    /**
     * mcp server english name is empty
     */
    MCP_ENGLISH_EMPTY(BAD_REQUEST, COMPONENT, "1076"),

    /**
     * mcp server description is empty
     */
    MCP_DESCRIPTION_EMPTY(BAD_REQUEST, COMPONENT, "1077"),

    /**
     * Mcp server visibility is invalid
     */
    MCP_VISIBILITY_INVALID(BAD_REQUEST, COMPONENT, "1078"),

    /**
     * permission denied, server is created by others
     */
    MCP_PERMISSION_DENY(FORBIDDEN, COMPONENT, "1079"),

    /**
     * MCP config error, no auth key provided
     */
    MCP_CONFIG_ERROR(BAD_REQUEST, COMPONENT, "1080"),

    /**
     * can't config custom mcp server
     */
    MCP_CANNOT_CONFIG(BAD_REQUEST, COMPONENT, "1081"),

    /**
     * can't config public mcp server
     */
    MCP_CANNOT_CONFIG_PUBLIC(BAD_REQUEST, COMPONENT, "1082"),

    /**
     * MCP config error, {0} is empty
     */
    MCP_CONFIG_ERROR_EMPTY(BAD_REQUEST, COMPONENT, "1083"),

    /**
     * MCP config error, missing keys: {0}
     */
    MCP_CONFIG_MISS_KEY(BAD_REQUEST, COMPONENT, "1084"),

    /**
     * get mcp tools error with code: {0}
     */
    MCP_TOOL_ERROR(INTERNAL_SERVER_ERROR, COMPONENT, "1085"),

    /**
     * 插件不存在或无权限使用
     */
    TOOLS_NOT_EXIST_OR_NO_PERMISSION(INTERNAL_SERVER_ERROR, COMPONENT, "1086"),

    /**
     * 非法API调用
     */
    ILLEGAL_API_INVOKE(BAD_REQUEST, COMPONENT, "1087"),

    /**
     * 无效参数
     */
    INVALID_PARAMETER_ERROR(BAD_REQUEST, COMPONENT, "1088"),

    /**
     * 远程调用失败
     */
    REMOTE_CALL_ERROR(BAD_REQUEST, COMPONENT, "1089"),

    /**
     * 用户无权访问资源
     */
    USER_HAS_NO_PERMISSION(BAD_REQUEST, COMPONENT, "1090"),

    /**
     * 缺少输入参数
     */
    MISSING_PARAM(BAD_REQUEST, COMPONENT, "1091"),

    /**
     * 正在创建的服务无法删除
     */
    MCP_SERVICE_CREATING_STATUS_NOT_DELETE(BAD_REQUEST, COMPONENT, "1092"),

    /**
     * 正在删除的服务无法删除
     */
    MCP_SERVICE_DELETING_STATUS_NOT_DELETE(BAD_REQUEST, COMPONENT, "1093"),

    /**
     * 从FG删除服务失败
     */
    MCP_SERVICE_DELETE_FAILED_FROM_FG(BAD_REQUEST, COMPONENT, "1094"),

    /**
     * MCP服务不存在
     */
    MCP_SERVICE_NOT_EXIST(BAD_REQUEST, COMPONENT, "1095"),

    /**
     * MCP服务配置不是json格式
     */
    TOOLS_DATA_NOT_JSON_FORMAT(BAD_REQUEST, COMPONENT, "1096"),

    /**
     * 修改对象属性失败
     */
    UPDATE_OBJECT_PROPERTIES_FAILED(BAD_REQUEST, COMPONENT, "1097"),

    /**
     * MCP服务已存在
     */
    MCP_SERVICE_IS_EXIST(BAD_REQUEST, COMPONENT, "1098"),

    /**
     * 从FG创建mcp服务不成功
     */
    MCP_SERVICE_CREATE_FAILED_FROM_FG(BAD_REQUEST, COMPONENT, "1099"),

    /**
     * 等待应用程序更新超时
     */
    APPLICATION_UPDATE_TIMEOUT(BAD_REQUEST, COMPONENT, "1100"),

    /**
     * 查询mcp的工具列表错误
     */
    QUERY_MCP_SERVICE_TOOL_ERROR(BAD_REQUEST, COMPONENT, "1101"),

    /**
     * MCP服务配置格式不正确
     */
    MCP_SERVICE_CONFIG_FORMAT_INCORRECT(BAD_REQUEST, COMPONENT, "1102"),

    /**
     * 调用mcp的工具错误
     */
    INVOKING_MCP_SERVICE_TOOL_ERROR(BAD_REQUEST, COMPONENT, "1103"),

    /**
     * 调用FG服务接口失败
     */
    INVOKING_FG_ERROR(BAD_REQUEST, COMPONENT, "1104"),

    /**
     * 部署的MCP服务总数超过最大限制
     */
    SERVICE_EXCEEDING_LIMIT(BAD_REQUEST, COMPONENT, "1105"),

    /**
     * MCP服务器繁忙，请稍后再试
     */
    MCP_SERVICE_BUSY(BAD_REQUEST, COMPONENT, "1106"),

    /**
     * 无MCP服务权限
     */
    NO_PERMISSION_FOR_MCP(BAD_REQUEST, COMPONENT, "1107"),

    /**
     * 非法镜像格式
     */
    ILLEGAL_IMAGE_FORMAT(BAD_REQUEST, COMPONENT, "1108"),

    /**
     * 镜像大小超过限制
     */
    IMAGE_EXCEEDS_LIMIT(BAD_REQUEST, COMPONENT, "1109"),

    /**
     * 授权失败
     */
    DO_AUTHORIZATION_FROM_FG(BAD_REQUEST, COMPONENT, "1110"),

    /**
     * 取消授权失败
     */
    CANCEL_AUTHORIZATION_FROM_FG(BAD_REQUEST, COMPONENT, "1111"),

    /**
     * 查询授权失败
     */
    QUERY_AUTHORIZATION_FROM_FG(BAD_REQUEST, COMPONENT, "1112"),

    /**
     * iam创建/查询机构失败
     */
    AGENCY_FAIL(BAD_REQUEST, COMPONENT, "1113"),

    /**
     * json转换异常
     */
    MCP_JSON_CONVERSION_ERROR(ACCEPTED, COMPONENT, "1114"),

    /**
     * 插件中文名已存在
     */
    PLUGIN_CN_NAME_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1117"),

    /**
     * 插件英文名已存在
     */
    PLUGIN_EN_NAME_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1118"),

    /**
     * MCP名称不合法
     */
    MCP_SERVICE_NAME_INVALID(BAD_REQUEST, COMPONENT, "1119"),

    /**
     * MCP ServiceConfig不合法
     */
    MCP_SERVICE_CONFIG_INVALID(BAD_REQUEST, COMPONENT, "1120"),

    /**
     * Plugin 认证配置不可用
     */
    PLUGIN_AUTH_DATA_INVALID(BAD_REQUEST, COMPONENT, "1121"),

    /**
     * Plugin 鉴权超时
     */
    PLUGIN_AUTH_REQUEST_TIMEOUT(BAD_REQUEST, COMPONENT, "1122"),

    /**
     * Plugin 鉴权网络错误
     */
    PLUGIN_AUTH_REQUEST_INTERNAL_ERROR(BAD_REQUEST, COMPONENT, "1123"),

    /**
     * 函数与插件绑定关系已存在
     */
    PLUGIN_FUNCTION_MAPPING_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1124"),

    PLUGIN_FUNCTION_NOT_EXIST(BAD_REQUEST, COMPONENT, "1125"),

    FUNCTION_DELETE_FAILED(BAD_REQUEST, COMPONENT, "1126"),

    FUNCTION_DELETE_BIND_FAILED(BAD_REQUEST, COMPONENT, "1127"),

    PLUGIN_CALL_MODE_CANNOT_MODIFFY(BAD_REQUEST, COMPONENT, "1128"),

    GET_FUNCTION_TEMPLATE_FAILED(BAD_REQUEST, COMPONENT, "1129"),

    PLUGIN_ID_ALREADY_EXIST(BAD_REQUEST, COMPONENT, "1130"),

    API_PLUGIN_CAN_NOT_COPY(BAD_REQUEST, COMPONENT, "1131"),

    /**
     * 评分需要在[1,10]
     */
    SCORE_PARAM_INVALID(BAD_REQUEST, COMPONENT, "1132"),

    /**
     * Tool number exceeds the limit
     */
    TOOL_NUM_EXCEEDS_LIMIT(BAD_REQUEST, COMPONENT, "1138"),

    /**
     * 异常执行次数超过限制
     */
    PLUGIN_EXCEPTION_OVER_LIMIT(BAD_REQUEST, COMPONENT, "1139"),

    /**
     * 插件不存在或无权限使用
     */
    PLUGIN_NO_PERMISSION_VIEW(INTERNAL_SERVER_ERROR, COMPONENT, "1140"),

    /**
     * 插件和工具的输入参数名重复,请重新输入!
     */
    DUPLICATE_PARAMETER_NAME_EXCEPTION(INTERNAL_SERVER_ERROR, COMPONENT, "1141"),

    /**
     * MCP安装方式不支持
     */
    MCP_SERVICE_ORG_TYPE_INVALID(BAD_REQUEST, COMPONENT, "1142"),

    /**
     * MCP安装方式为空，请重试
     */
    MCP_SERVICE_ORG_TYPE_EMPTY(BAD_REQUEST, COMPONENT, "1143"),

    /**
     * 第三方MCP仅支持SSE部署方式
     */
    ONLY_SSE_OR_STREAMABLE_HTTP_SERVICE_ALLOWED_THIRD(BAD_REQUEST, COMPONENT, "1144"),

    /**
     * 插件IAM认证url参数配置错误,请检查!
     */
    PLUGIN_IAM_AUTNEHTICATION_URL_CONFIG_ERROR(BAD_REQUEST, COMPONENT, "1145"),

    /**
     * MCP配置数据格式校验失败，请检查JSON结构或必填字段
     */
    MCP_CONFIG_FORMAT_INVALID(BAD_REQUEST, COMPONENT, "1146"),

    /**
     * FunctionGraph资源配额不足，请检查配额限制
     */
    MCP_FG_QUOTA_EXCEEDED(INTERNAL_SERVER_ERROR, COMPONENT, "1147"),

    /**
     * FunctionGraph服务执行异常，请检查FG日志或联系管理员
     */
    MCP_FG_EXECUTION_ERROR(INTERNAL_SERVER_ERROR, COMPONENT, "1148"),

    /**
     * 获取MCP工具列表失败，服务端返回错误信息
     */
    MCP_FETCH_TOOLS_SERVER_ERROR(INTERNAL_SERVER_ERROR, COMPONENT, "1149"),

    /**
     * MCP服务网络连接失败，请检查地址连通性或网络配置
     */
    MCP_NETWORK_CONNECTION_ERROR(INTERNAL_SERVER_ERROR, COMPONENT, "1150"),

    /**
     * MCP服务配置的目标地址受限（如包含内网IP或黑名单域名）
     */
    MCP_ADDRESS_RESTRICTED(BAD_REQUEST, COMPONENT, "1151"),

    /**
     * Failed to parse buildOutputList to ToolInfo
     */
    PARSE_BUILD_OUTPUT_LIST_FAILED(BAD_REQUEST, COMPONENT, "1152"),

    /**
     * Failed to parse String to Object
     */
    PARSE_STRING_TO_OBJECT_FAILED(BAD_REQUEST, COMPONENT, "1153"),

    /**
     * Failed to parse requestInfo to ToolInfo
     */
    PARSE_REQUEST_TO_TOOL_FAILED(BAD_REQUEST, COMPONENT, "1154"),

    /**
     * URL prefix not match
     */
    URL_PREFIX_NOT_MATCH(BAD_REQUEST, COMPONENT, "1155"),

    /**
     * Failed to parse buildIntfType to ToolInfo
     */
    PARSE_BUILD_INT_TYPE_FAILED(BAD_REQUEST, COMPONENT, "1156"),

    /**
     * Failed to parse buildTestStatus to ToolInfo
     */
    BUILD_STATUS_TOOL_FAILED(BAD_REQUEST, COMPONENT, "1157"),

    /**
     * Failed to parse buildOutputSchema to ToolInfo
     */
    PARSE_OUTPUT_SCHEMA_TOOL_FAILED(BAD_REQUEST, COMPONENT, "1158"),

    /**
     * Failed to parse buildInputList to ToolInfo
     */
    PARSE_INPUT_SCHEMA_TOOL_FAILED(BAD_REQUEST, COMPONENT, "1159"),

    /**
     * Failed to parse filterToolInputSchema to ToolInfo
     */
    PARSE_filter_SCHEMA_TOOL_FAILED(BAD_REQUEST, COMPONENT, "1160"),

    /**
     * MCP服务网络连接超时 (30s)
     */
    MCP_NETWORK_TIMEOUT(INTERNAL_SERVER_ERROR, COMPONENT, "1161"),

    /**
     * MCP服务网络连接被拒绝，目标端口可能未开启
     */
    MCP_CONNECTION_REFUSED(INTERNAL_SERVER_ERROR, COMPONENT, "1162"),

    /**
     * MCP服务目标地址路径错误 (404 Not Found)
     */
    MCP_TARGET_NOT_FOUND(INTERNAL_SERVER_ERROR, COMPONENT, "1163"),

    /**
     * MCP服务认证失败 (401/403)
     */
    MCP_AUTHENTICATION_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1164"),

    /*
     * apig 创建失败
     */
    CREATE_MCP_API_FAILED(INTERNAL_SERVER_ERROR, COMPONENT, "1165"),

    /**
     * 调用fg依赖包接口失败
     */
    REQUEST_DEPEND_PACKAGE_FAILED(BAD_REQUEST, COMPONENT, "1166"),

    /**
     * 调用fg依赖包版本接口失败
     */
    REQUEST_DEPEND_PACKAGE_VERSION_FAILED(BAD_REQUEST, COMPONENT, "1167"),

    /**
     * 依赖包版本不存在
     */
    REQUEST_DEPEND_PACKAGE_VERSION_NOT_EXITS(BAD_REQUEST, COMPONENT, "1168"),

    /**
     * OpenApi文件为空
     */
    OPENAPI_FILE_NOT_EXIST(BAD_REQUEST, COMPONENT, "1169"),

    /**
     * Server为空
     */
    SERVER_NOT_EXIST(BAD_REQUEST, COMPONENT, "1170"),

    /**
     * Server中URL为空
     */
    SERVER_URL_NOT_EXIST(BAD_REQUEST, COMPONENT, "1171"),

    /**
     * OpenApi文件解析失败
     */
    OPENAPI_PARSE_FAILED(BAD_REQUEST, COMPONENT, "1172"),

    /**
     * MCP服务域名无法解析 (Unknown Host)
     */
    MCP_UNKNOWN_HOST(INTERNAL_SERVER_ERROR, COMPONENT, "1173"),

    /**
     * MCP 认证配置不可用
     */
    MCP_AUTH_DATA_INVALID(BAD_REQUEST, COMPONENT, "1174"),

    /**
     * show function failed
     */
    SHOW_FUNCTION_CODE_FAILED(BAD_REQUEST, COMPONENT,"1175"),

    /**
     * get function metadata failed
     */
    FUNCTION_METADATA_GET_FAILED(BAD_REQUEST, COMPONENT,"1176"),

    /**
     * OAUTH鉴权信息越界
     */
    OAUTH_INFORMATION_OVER_LENGTH(BAD_REQUEST, COMPONENT,"1177"),

    /**
     * apikey鉴权信息越界
     */
    APIKEY_INFORMATION_OVER_LENGTH(BAD_REQUEST, COMPONENT,"1178"),

    PLUGIN_FREE_TRIAL_USAGE_QUOTA_ERROR(BAD_REQUEST, COMPONENT, "1179"),

    RELEASE_PUBLISH_FAILED(BAD_REQUEST, COMPONENT, "1180"),

    PLUGIN_AUTH_KEY_DOMAIN_NOT_NULL(BAD_REQUEST, COMPONENT, "1181"),

    /**
     * ============================== 提示词工程 ==============================
     */
    /**
     * 系统错误
     */

    /**
     * 系统错误, Add dataset failed, datasetName: {0}
     */
    SYSTEM_ERROR_ADD_DATASET(INTERNAL_SERVER_ERROR, PE, "1002"),

    /**
     * Delete dataset failed, datasetId: {0}
     */
    SYSTEM_ERROR_DELETE_DATASET_FAILED(INTERNAL_SERVER_ERROR, PE, "1003"),

    /**
     * listBuckets get obs buckets error, {0}
     */
    LIST_BUCKETS_GET_OBS_ERROR(INTERNAL_SERVER_ERROR, PE, "1004"),

    /**
     * get obs bucket folders error, bucketName: {0}
     */
    GET_OBS_BUCKET_ERROR(INTERNAL_SERVER_ERROR, PE, "1005"),

    /**
     * Json转换错误
     */
    JSON_ENCODE_ERROR(BAD_REQUEST, PE, "1006"),

    /**
     * write json error
     */
    JSON_WRITE_ERROR(BAD_REQUEST, PE, "1007"),

    /**
     * parse json error. classType={} str={}
     */
    JSON_PARSE_ERROR(BAD_REQUEST, PE, "1008"),

    /**
     * 服务白名单校验错误
     */
    SERVER_WHITELIST_CHECK_ERROR(UNAUTHORIZED, PE, "1009"),

    /**
     * 获取白名单状态响应错误
     */
    GET_WHITELIST_RESPONSE_ERROR(BAD_REQUEST, PE, "1010"),

    /**
     * 请求白名单服务异常
     */
    REQUEST_MANAGER_SERVER_EXCEPTION(BAD_REQUEST, PE, "1011"),

    /**
     * IAM token信息缺失
     */
    AUTH_TOKEN_INFO_MISSING(UNAUTHORIZED, PE, "1012"),

    /**
     * 初始化http client错误
     */
    INIT_HTTP_CLIENT_ERROR(UNAUTHORIZED, PE, "1013"),

    /**
     * IAM服务响应错误
     */
    GET_IAM_SERVER_RESPONSE_ERROR(BAD_REQUEST, PE, "1014"),

    /**
     * 请求IAM服务异常
     */
    IAM_SERVER_EXCEPTION(BAD_REQUEST, PE, "1015"),

    /**
     * 存在空指针
     */
    NULL_POINT_ERROR(BAD_REQUEST, PE, "1016"),

    /**
     * 查询模型列表失败
     */
    QUERY_MODEL_LIST_ERROR(BAD_REQUEST, PE, "1017"),

    /**
     * 模型不存在
     */
    PROMPT_MODEL_NOT_EXIST(BAD_REQUEST, PE, "1018"),

    /**
     * 参数校验错误
     */
    ARGUMENT_VALID_ERROR(BAD_REQUEST, PE, "1019"),

    /**
     * 查询订单信息失败, projectId {0}
     */
    QUERY_ORDER_RESOURCES_FAILED(BAD_REQUEST, PE, "1020"),

    /**
     * call model {0} failed, get no result.
     */
    GET_NO_RESULT_FROM_LLM(BAD_REQUEST, PE, "1021"),

    /**
     * 调取大模型接口{0}失败，响应体为空
     */
    OBTAIN_EMPTY_RESPONSE_FROM_LLM(BAD_REQUEST, PE, "1022"),
    /**
     * 调取大模型接口失败
     */
    CANT_OBTAIN_TEXT_FROM_LLM(BAD_REQUEST, PE, "1023"),

    /**
     * 调用大模型接口超时
     */
    CALL_LLM_TIMEOUT(BAD_REQUEST, PE, "1024"),

    /**
     * 调用大模型异常中断。请检查大模型 Api！
     */
    CALL_LLM_INTERRUPTED(BAD_REQUEST, PE, "1025"),

    /**
     * 调用大模型错误。请检查大模型 Api！
     */
    CALL_LLM_EXECUTION_ERROR(BAD_REQUEST, PE, "1026"),

    /**
     * The bucket is not exist, bucketName: {0}
     */
    OBS_ACCESS_EXCEPTION(BAD_REQUEST, PE, "1027"),

    /**
     * The obs file is not exist, filePath: {0}
     */
    OBS_FILE_NOT_EXIST(BAD_REQUEST, PE, "1028"),

    /**
     * obs权限拒绝
     */
    OBS_ACCESS_FAILED_EXCEPTION(BAD_REQUEST, PE, "1029"),

    /**
     * obs桶不存在
     */
    OBS_BUCKET_DOES_NOT_EXIST(BAD_REQUEST, PE, "1030"),

    /**
     * obs read io exception
     */
    OBS_READ_IO_EXCEPTION(BAD_REQUEST, PE, "1031"),

    /**
     * iam token valid failed: projectId ({0}) in token does not match project ID in URL ({1}) traceId {2}
     */
    IAM_SERVER_TOKEN_INVALID(BAD_REQUEST, PE, "1032"),

    /**
     * read file error, upload image error
     */
    UPLOAD_FILE_ERROR(BAD_REQUEST, PE, "1033"),

    /**
     * upload obs file failed
     */
    UPLOAD_FILE_OBS_FAILED(BAD_REQUEST, PE, "1034"),

    /**
     * Failed to upload file
     */
    UPLOAD_FILE_FAILED(BAD_REQUEST, PE, "1035"),

    /**
     * upload file type is not supported
     */
    UPLOAD_FILE_TYPE_INVALID(BAD_REQUEST, PE, "1036"),

    /**
     * 文件类型{0}未定义
     */
    FILE_TYPE_IS_UNDEFINED(BAD_REQUEST, PE, "1037"),

    /**
     * 文件内容类型{0}与{1}不匹配！
     */
    FILE_CONTENT_TYPE_IS_UNMATCHED(BAD_REQUEST, PE, "1038"),

    /**
     * init obs client failed!
     */
    OBS_RUNTIME_EXCEPTION(BAD_REQUEST, PE, "1039"),

    /**
     * The Obs Service is not stable
     */
    OBS_SERVICE_NOT_STABLE(BAD_REQUEST, PE, "1040"),

    /**
     * excel表头校验失败
     */
    EXCEL_HEADER_ERROR(BAD_REQUEST, PE, "1041"),

    /**
     * download file error
     */
    DOWNLOAD_FILE_ERROR(BAD_REQUEST, PE, "1042"),

    /**
     * The file name is illegal: {0}
     */
    PE_ILLEGAL_FILE_NAME(BAD_REQUEST, PE, "1043"),

    /**
     * 非法图片文件
     */
    ILLEGAL_IMAGE_FILE(BAD_REQUEST, PE, "1044"),

    /**
     * 数据集文件格式不符合要求, 数据集仅支持excel和xlsx格式，请检查obs文件！
     */
    DATASET_FILE_FORMAT_ERROR(BAD_REQUEST, PE, "1045"),

    /**
     * 数据集已存在
     */
    DATASET_NAME_ALREADY_EXIST(BAD_REQUEST, PE, "1046"),

    /**
     * 数据集的数量超过了500的配额！
     */
    DATASET_NUMBER_LIMIT(BAD_REQUEST, PE, "1047"),

    /**
     * 该数据集已被评估任务使用！
     */
    DATASET_IN_USING(BAD_REQUEST, PE, "1048"),

    /**
     * 数据集内容的长度超过了1000的配额！
     */
    DATASET_CONTENT_LENGTH_LIMIT(BAD_REQUEST, PE, "1049"),

    /**
     * read dataset excel failed.
     */
    READ_DATASET_EXCEPTION(BAD_REQUEST, PE, "1050"),

    /**
     * download obs file failed
     */
    OBS_DOWNLOAD_FILE_FAILED(BAD_REQUEST, PE, "1051"),

    /**
     * zip file size is too large
     */
    ZIP_FILE_SIZE_LARGE(BAD_REQUEST, PE, "1052"),

    /**
     * Invalid file path: {0}
     */
    INVALID_FILE_PATH(BAD_REQUEST, PE, "1053"),

    /**
     * file entry size is too large, name:{0} ,size:{1}
     */
    FILE_ENTRY_SIZE_LARGE(BAD_REQUEST, PE, "1054"),

    /**
     * file size is too large, size: {0}
     */
    FILE_SIZE_TOO_LARGE(BAD_REQUEST, PE, "1055"),

    /**
     * obs file check zip bomb failed
     */
    OBS_FILE_CHECK_ZIP_BOMB(BAD_REQUEST, PE, "1056"),

    /**
     * 读取数据集缓存异常
     */
    READ_DATASET_CACHE_EXCEPTION(BAD_REQUEST, PE, "1057"),

    /**
     * 数据集文件不存在
     */
    DATASET_FILE_DOES_NOT_EXIST(BAD_REQUEST, PE, "1058"),

    /**
     * 数据集的行号必须在[10，50]的范围内！
     */
    DATASET_ROW_NUM_LIMIT(BAD_REQUEST, PE, "1059"),

    /**
     * 数据集的头行为空，请检查文件！
     */
    DATASET_HEADER_ROW_IS_NULL_ERROR(BAD_REQUEST, PE, "1060"),

    /**
     * 数据集有空值行，请检查文件！
     */
    DATASET_VALUE_ROW_IS_NULL_ERROR(BAD_REQUEST, PE, "1061"),

    /**
     * 数据集表头个数超过了限制20！
     */
    DATASET_KEY_NUMBER_LIMIT(BAD_REQUEST, PE, "1062"),

    /**
     * 数据集表头有空值，请检查文件！
     */
    DATASET_WITH_NULL_KEY_ERROR(BAD_REQUEST, PE, "1063"),

    /**
     * 数据集有相同的表头
     */
    DATASET_WITH_SAME_KEY(BAD_REQUEST, PE, "1064"),

    /**
     * 下载变量数据集失败
     */
    DOWNLOAD_VARIABLE_DATASET_FAILED(BAD_REQUEST, PE, "1065"),

    /**
     * 下载变量数据集无变量
     */
    DOWNLOAD_VARIABLE_DATASET_EMPTY(BAD_REQUEST, PE, "1066"),

    /**
     * 数据集预期结果为空
     */
    DATASET_RESULT_EMPTY(BAD_REQUEST, PE, "1067"),

    /**
     * The task id {0} is not exists.
     */
    TASK_ID_IS_NOT_EXIST(BAD_REQUEST, PE, "1068"),

    /**
     * Failed to delete the task, taskId: {0}
     */
    FAILED_DELETE_TASK(BAD_REQUEST, PE, "1069"),

    /**
     * 提示词工程名称已经存在！
     */
    TASK_NAME_IS_EXIST(BAD_REQUEST, PE, "1070"),

    /**
     * Failed to create task, task name: {0}
     */
    FAILED_TO_CREATE_TASK(BAD_REQUEST, PE, "1071"),

    /**
     * 删除提示词工程任务失败
     */
    FAILED_TO_DELETE_TASK(BAD_REQUEST, PE, "1072"),

    /**
     * Failed to query task list by {0}
     */
    FAILED_TO_QUERY_TASK(BAD_REQUEST, PE, "1073"),

    /**
     * Failed to update task, taskId: {0}
     */
    FAILED_TO_UPDATE_TASK(BAD_REQUEST, PE, "1074"),

    /**
     * 提示词工程任务数超过了{0}配额！
     */
    TASK_EXCEEDS_QUOTA(BAD_REQUEST, PE, "1075"),

    /**
     * 该任务具有正在运行的评估任务，无法删除该任务！
     */
    TASK_HAVE_HAVE_RUNNING_EVALUATION_TASK(INTERNAL_SERVER_ERROR, PE, "1076"),

    /**
     * 评估任务的状态出错，请重新检查！
     */
    STATUS_ERROR(INTERNAL_SERVER_ERROR, PE, "1077"),

    /**
     * 评估任务已存在
     */
    EVALUATION_TASK_IS_EXIST(BAD_REQUEST, PE, "1078"),

    /**
     * 评估任务选择的评估方法不正确，请重新检查！
     */
    EVALUATION_METHOD_ERROR(BAD_REQUEST, PE, "1079"),

    /**
     * 评估任务不存在，请重新检查！
     */
    EVALUATION_TASK_IS_NOT_EXIST(BAD_REQUEST, PE, "1080"),

    /**
     * 查询评估任务信息时出错，请重新检查！
     */
    FAILED_TO_QUERY_EVALUATION_TASK_INFO(BAD_REQUEST, PE, "1081"),

    /**
     * 评估任务{0}处于挂起、正在运行、暂停或重试状态，无法删除，请创建新的评估任务或创建新任务！
     */
    EVALUATION_TASK_RUNNING(BAD_REQUEST, PE, "1082"),

    /**
     * 评估任务重试失败
     */
    RETRY_EVALUATION_TASK_FAILED(BAD_REQUEST, PE, "1083"),

    /**
     * 评估任务更新失败，请查看错误消息！
     */
    EVALUATION_TASK_UPDATE_FAILED(BAD_REQUEST, PE, "1084"),

    /**
     * 评估任务不成功，无法下载！
     */
    EXPORT_EVALUATION_RESULT_FAILED(BAD_REQUEST, PE, "1085"),

    /**
     * 导出预置提示词模板失败
     */
    EXPORT_PROMPT_TEMPLATE_FAILED(BAD_REQUEST, PE, "1086"),

    /**
     * 查询评估结果异常
     */
    QUERY_EVALUATION_RESULT_EXCEPTION(BAD_REQUEST, PE, "1087"),

    /**
     * 评估任务的数量超过了{0}的配额!
     */
    EVALUATION_EXCEEDS_QUOTA(BAD_REQUEST, PE, "1088"),

    /**
     * 导出文件失败, 文件不能以特殊字符开头！
     */
    EXPORT_EXCEL_VALIDATE_FAILED(BAD_REQUEST, PE, "1089"),

    /**
     * 创建模板异常, 无法创建模板！
     */
    CREATE_TEMPLATE_ERROR(BAD_REQUEST, PE, "1090"),

    /**
     * 更新模板异常
     */
    UPDATE_TEMPLATE_ERROR(BAD_REQUEST, PE, "1091"),

    /**
     * 查询模板失败！
     */
    QUERY_TEMPLATE_ERROR(BAD_REQUEST, PE, "1092"),

    /**
     * 删除模板失败！
     */
    DELETE_TEMPLATE_ERROR(BAD_REQUEST, PE, "1093"),

    /**
     * 无法处理变量！
     */
    HANDLE_VARIABLES_ERROR(BAD_REQUEST, PE, "1094"),

    /**
     * The prompt template list is empty.
     */
    PROMPT_TEMPLATE_EMPTY(BAD_REQUEST, PE, "1095"),

    /**
     * 候选模板的数量超过了{0}的配额！
     */
    CANDIDATE_TEMPLATE_EXCEEDS_QUOTA(BAD_REQUEST, PE, "1096"),

    /**
     * Duplicate variable
     */
    VARIABLE_DUPLICATE(BAD_REQUEST, PE, "1097"),

    /**
     * The prompt is in using by evaluating task
     */
    PROMPT_IN_USE(BAD_REQUEST, PE, "1098"),

    /**
     * 保存历史记录失败！
     */
    SAVE_HISTORY_ERROR(BAD_REQUEST, PE, "1099"),

    /**
     * 全局变量的数量超过了{0}的配额！
     */
    VARIABLES_EXCEEDS_QUOTA(BAD_REQUEST, PE, "1100"),

    /**
     * 数据不存在
     */
    DATA_NOT_EXIST(BAD_REQUEST, PE, "1101"),

    /**
     * 候选模板名称重复，请重新输入！
     */
    DUPLICATE_PROMPT_NAME(BAD_REQUEST, PE, "1102"),

    /**
     * 提示词名称已存在！
     */
    NAME_IS_EXIST(BAD_REQUEST, PE, "1103"),

    /**
     * 模板的数量超过了{0}的配额！
     */
    TEMPLATE_EXCEEDS_QUOTA(BAD_REQUEST, PE, "1104"),

    /**
     * only admin tenant can operate preset template
     */
    AUTH_FAILED(UNAUTHORIZED, PE, "1105"),

    /**
     * 要下载的模板数量超过了{0}的配额！
     */
    DOWNLOAD_TEMPLATE_EXCEEDS_QUOTA(BAD_REQUEST, PE, "1106"),

    /**
     * 模型配置温度需要位于[{0}, {1}]！
     */
    TEMPLATE_MODEL_CONFIG_VALIDATE_TEMPERATURE(BAD_REQUEST, PE, "1107"),

    /**
     * 模型配置top_p需位于({0},{1}]！
     */
    TEMPLATE_MODEL_CONFIG_VALIDATE_TOP_P(BAD_REQUEST, PE, "1108"),

    /**
     * 模型配置presence_penalty需位于({0},{1})！
     */
    TEMPLATE_MODEL_CONFIG_VALIDATE_PRESENCE_PENALTY(BAD_REQUEST, PE, "1109"),

    /**
     * 提示词id不存在！
     */
    PROMPT_ID_IS_NOT_EXISTED(BAD_REQUEST, PE, "1110"),

    /**
     * 无法更新模板, name和manual_score不能同时为空！
     */
    UPDATE_TEMPLATE_ERROR_PARAM(BAD_REQUEST, PE, "1111"),

    /**
     * The prompt generate instruct is empty
     */
    PROMPT_GENERATE_INSTRUCT_IS_EMPTY(BAD_REQUEST, PE, "1112"),

    /**
     * Optimize template failed: {0}
     */
    OPTIMIZE_TEMPLATE_FAILED(BAD_REQUEST, PE, "1113"),

    /**
     * The optimize template delete failed
     */
    OPTIMIZE_TEMPLATE_DELETE_FAILED(BAD_REQUEST, PE, "1114"),

    /**
     * The optimization template service access failed
     */
    OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED(BAD_REQUEST, PE, "1115"),

    /**
     * 优化任务{0}处于正在运行状态，无法删除，请停止任务或等待完成后删除！
     */
    OPTIMIZATION_TASK_RUNNING(BAD_REQUEST, PE, "1116"),

    /**
     * 优化任务已存在
     */
    OPTIMIZATION_TASK_IS_EXIST(BAD_REQUEST, PE, "1117"),

    /**
     * 优化任务ID不存在
     */
    OPTIMIZATION_TASK_ID_IS_NOT_EXIST(BAD_REQUEST, PE, "1118"),

    /**
     * 修改优化任务状态不合法
     */
    OPTIMIZATION_TASK_STATUS_IS_INVALIDATE(BAD_REQUEST, PE, "1119"),

    /**
     * 模板优化任务访问服务接口报错
     */
    OPTIMIZATION_TASK_FROM_JIUWEN_SERVICE_ERROR(BAD_REQUEST, PE, "1120"),

    /**
     * Create optimization task resp is null
     */
    CREATE_OPTIMIZATION_TASK_RESP_NULL(BAD_REQUEST, PE, "1121"),

    /**
     * Delete optimization task from 九问 server error! response:{0}
     */
    DELETE_OPTIMIZATION_TASK(BAD_REQUEST, PE, "1122"),

    /**
     * Get optimization task progress from 九问 server error!
     */
    GET_OPTIMIZATION_TASK(BAD_REQUEST, PE, "1123"),

    /**
     * 优化任务状态码 {0} 不存在！
     */
    OPTIMIZATION_TASK_STATUS_IS_NOT_EXIST(BAD_REQUEST, PE, "1124"),

    /**
     * 优化任务操作失败
     */
    OPTIMIZATION_TASK_OPERATION_FAILED(BAD_REQUEST, PE, "1125"),

    /**
     * 模型类型码 {0} 不存在！
     */
    MODEL_TYPE_IS_NOT_EXIST(BAD_REQUEST, PE, "1126"),

    /**
     * 提示词工程 {0} 下已经存在运行中的优化任务！
     */
    OPTIMIZATION_TASK_RUNNING_IS_EXIST(BAD_REQUEST, PE, "1127"),

    /**
     * 文件不存在
     */
    FILE_DOES_NOT_EXIST(BAD_REQUEST, PE, "1128"),

    /**
     * 文件大小超过限制
     */
    TASK_FILE_SIZE_EXCEED_LIMIT(BAD_REQUEST, PE, "1129"),

    /**
     * Invalid limit or offset.
     */
    LIMIT_OR_OFFSET_INVALID(BAD_REQUEST, PE, "1130"),

    /**
     * 标签名称已存在
     */
    TAG_NAME_IS_EXIST(BAD_REQUEST, PE, "1131"),

    /**
     * Failed to insert tag {0} into database
     */
    FAILED_TO_CREATE_TAG(BAD_REQUEST, PE, "1132"),

    /**
     * 查询标签列表失败！
     */
    FAILED_TO_QUERY_TAG(BAD_REQUEST, PE, "1133"),

    /**
     * Failed to delete tag, id: {0}
     */
    FAILED_TO_DELETE_TAG(BAD_REQUEST, PE, "1134"),

    /**
     * Failed to update tag, id: {0}
     */
    FAILED_TO_UPDATE_TAG(BAD_REQUEST, PE, "1135"),

    /**
     * 行业名称重复
     */
    INDUSTRY_NAME_EXIST(BAD_REQUEST, PE, "1136"),

    /**
     * 行业正在使用中
     */
    INDUSTRY_IN_USE(BAD_REQUEST, PE, "1137"),

    /**
     * Failed to update industry, id: {0}
     */
    UPDATE_INDUSTRY_FAILED(BAD_REQUEST, PE, "1138"),

    /**
     * 查询行业失败
     */
    QUERY_INDUSTRY_FAILED(BAD_REQUEST, PE, "1139"),

    /**
     * Failed to insert industry {0} into database
     */
    CREATE_INDUSTRY_FAILED(BAD_REQUEST, PE, "1140"),

    /**
     * industry id not exist
     */
    INDUSTRY_ID_NOT_EXIST(BAD_REQUEST, PE, "1141"),

    /**
     * call model getUserModels failed for projectId: {0}
     */
    MODEL_MANAGER_SERVICE_EXCEPTION(BAD_REQUEST, PE, "1142"),

    /**
     * failed to get user modelList, projectId: {0}
     */
    FAILED_GET_USER_MODEL_LIST(BAD_REQUEST, PE, "1143"),

    /**
     * failed to get preset modelList, projectId: {0}
     */
    FAILED_GET_PRESET_MODEL_LIST(BAD_REQUEST, PE, "1144"),

    /**
     * 查询列表失败
     */
    QUERY_LIST_FAILED(BAD_REQUEST, PE, "1145"),

    /**
     * 模板ID为空
     */
    TEMPLATE_ID_IS_EMPTY(BAD_REQUEST, PE, "1146"),

    /**
     * 项目ID{0}不存在
     */
    PROJECT_ID_NOT_FOUND(BAD_REQUEST, PE, "1147"),

    /**
     * 工作空间ID{0}不存在
     */
    WORKSPACE_ID_NOT_FOUND(BAD_REQUEST, PE, "1148"),

    /**
     * 请求体不能为空
     */
    REQUEST_BODY_NOT_EMPTY(BAD_REQUEST, PE, "1149"),

    /**
     * 模型状态校验失败
     */
    MODEL_STATUS_ERROR(FORBIDDEN, PE, "1150"),

    /**
     * 复制超出上限
     */
    COPY_LIMIT_EXCEEDED(BAD_REQUEST, PE, "1151"),

    /**
     * 上传数据失败
     */
    UPLOAD_EVAL_DATA_FAILED(BAD_REQUEST, PE, "1152"),

    /**
     * 评估数据不存在
     */
    PROMPT_EVAL_DATA_NOT_FOUND(BAD_REQUEST, PE, "1153"),

    /**
     * 评估数据解析失败
     */
    PROMPT_EVAL_DATA_FILE_ERROR(BAD_REQUEST, PE, "1154"),

    /**
     * 查询优化任务失败！
     */
    QUERY_OPTIMIZATION_TASK_ERROR(BAD_REQUEST, PE, "1158"),

    /**
     * 无该提示词优化任务评估结果！
     */
    OPTIMIZATION_TASK_ITERATION_NOT_EXIST(BAD_REQUEST, PE, "1160"),

    /**
     * 非草稿状态不能修改
     */
    OPTIMIZATION_TASK_STATUS_IS_NOT_DRAFT(BAD_REQUEST, PE, "1161"),

    /**
     * 优化任务正在运行，不能删除
     */
    OPTIMIZATION_TASK_IS_RUNNING(BAD_REQUEST, PE, "1162"),

    /**
     * 测评数据集文件超过大小限制
     */
    PROMPT_DATA_SIZE_ERROR(BAD_REQUEST, PE, "1163"),

    /**
     * 上传的json文件只能有1个
     */
    UPLOAD_EVAL_DATA_NUM(BAD_REQUEST, PE, "1164"),

    /**
     * 模板文件不存在
     */
    TEMPLATE_FILE_NOT_FOUND(BAD_REQUEST, PE, "1165"),

    /**
     * 下载模板失败
     */
    DOWNLOAD_TEMPLATE_FAILED(BAD_REQUEST, PE, "1166"),

    /**
     * 定时任务注册失败
     */
    SCHEDULER_REGISTER_EXCEPTION(BAD_REQUEST, PE, "1167"),

    /**
     * JiuWen优化任务还未创建
     */
    OPTIMIZATION_TASK_NOT_CREATED(BAD_REQUEST, PE, "1168"),

    /**
     * 模板类型错误
     */
    INVALID_PT_TYPE(BAD_REQUEST, PE, "1169"),

    /**
     * 变量类型错误
     */
    INVALID_VARIABLES(BAD_REQUEST, PE, "1170"),

    /**
     * 来源类型错误
     */
    INVALID_SOURCE(BAD_REQUEST, PE, "1171"),

    /**
     * text变量类型里有multi变量
     */
    INVALID_VARIABLE_TYPE_FOR_TEXT_TEMPLATE(BAD_REQUEST, PE, "1172"),

    /**
     * 优化任务执行时间未确定
     */
    PROMPT_TASK_EXEC_TIME_NOT_SET(BAD_REQUEST, PE, "1173"),

    /**
     * 当前状态不能执行该操作
     */
    OPERATOR_ERROR(BAD_REQUEST, PE, "1174"),

    /**
     * 优化任务执行时间未确定
     */
    PROMPT_FEEDBACK_PARAM_ERROR(BAD_REQUEST, PE, "1175"),

    /**
     * 上传图片大小不能超过{0}MB
     */
    PICTURE_SIZE_EXCEED(BAD_REQUEST, PE, "1176"),

    /**
     * 上传数据超过限制
     */
    JSON_CONTENT_LENGTH_EXCEED(BAD_REQUEST, PE, "1177"),

    /**
     * 提示词变量个数不能超过{0}
     */
    VARS_NUM_EXCEED(BAD_REQUEST, PE, "1178"),

    /**
     * 提示词内容长度不能超过{0}个字符
     */
    VARS_CONTENT_LENGTH_EXCEED(BAD_REQUEST, PE, "1179"),

    /**
     * 提示词变量名不能超过{0}个字符
     */
    VARS_NAME_LENGTH_EXCEED(BAD_REQUEST, PE, "1180"),

    /**
     * 任务名称长度超过限制
     */
    TASK_NAME_LENGTH_EXCEED(BAD_REQUEST, PE, "1181"),



    /**
     * 获取提示词优化任务详情失败
     */
    GET_PROMPT_TASK_DETAIL_FAILED(BAD_REQUEST, PE, "1185"),





    /**
     * 提示词变量名{0}重复
     */
    VARS_NAME_DUPLICATE(BAD_REQUEST, PE, "1189"),

    /**
     * AGENT_BUILDER_PROMPT_OUTPUT is not set
     */
    AGENT_BUILDER_PROMPT_OUTPUT_ERROR(BAD_REQUEST, PE, "1190"),

    /**
     * 文件类型错误
     */
    PROMPT_DATA_TYPE_ERROR(BAD_REQUEST, PE, "1191"),

    /**
     * JSON文件格式错误
     */
    PROMPT_EVAL_JSON_FILE_ERROR(BAD_REQUEST, PE, "1192"),

    /**
     * render template failed
     */
    PROMPT_RENDER_TEMPLATE_FAILED(BAD_REQUEST, PE, "1193"),

    /**
     * prompt template should not be empty
     */
    PROMPT_TEMPLATE_SHOULD_NOT_BE_EMPTY(BAD_REQUEST, PE, "1194"),

    /**
     * 变量{}缺失
     */
    VARS_MISSING(BAD_REQUEST, PE, "1195"),

    /**
     * 导入数据为空
     */
    IMPORT_DATA_EMPTY(BAD_REQUEST, PE, "1196"),

    /**
     * ============================== 团队空间 ==============================
     */
    /**
     * 用户无权限执行此操作
     */
    USER_NO_PERMISSION_DO_THIS(FORBIDDEN, Module.WORKSPACE, "1001"),

    /**
     * 工作空间名称重复, workspace name {0} is exist
     */
    WORKSPACE_NAME_REPEAT(BAD_REQUEST, WORKSPACE, "1002"),

    /**
     * The member {0} already existed in current workspace.
     */
    WORKSPACE_MEMBER_ALREADY_EXISTED(BAD_REQUEST, WORKSPACE, "1003"),

    /**
     * The member {0} not exist in current workspace.
     */
    WORKSPACE_MEMBER_NOT_EXIST(BAD_REQUEST, WORKSPACE, "1004"),

    /**
     * The member role is invalid.
     */
    INVALID_ROLE(BAD_REQUEST, WORKSPACE, "1005"),

    /**
     * The workspace type is not team type.
     */
    INVALID_WORKSPACE_TYPE(BAD_REQUEST, WORKSPACE, "1006"),

    /**
     * The member is repeat.
     */
    REPEAT_MEMBER(BAD_REQUEST, WORKSPACE, "1007"),

    /**
     * The workspace is not existed.
     */
    WORKSPACE_NOT_EXISTED(BAD_REQUEST, WORKSPACE, "1008"),

    /**
     * The workspace owner cannot exit the workspace before transferring it.
     */
    WORKSPACE_MEMBER_CAN_NOT_EXIT(BAD_REQUEST, WORKSPACE, "1009"),

    /**
     * 工作空间名称不合法, Workspace name not be null!
     */
    WORKSPACE_NAME_INVALID(BAD_REQUEST, WORKSPACE, "1010"),

    /**
     * 工作空间名称不合法, "Workspace name exceeds limit {0}"
     */
    WORKSPACE_NAME_INVALID_LIMIT(BAD_REQUEST, WORKSPACE, "1011"),

    /**
     * Workspace name must be composed of only Chinese, English, numbers, hyphens, underscores, parentheses, and
     * exclamation marks
     */
    WORKSPACE_NAME_INVALID_COMPOSED(BAD_REQUEST, WORKSPACE, "1012"),

    /**
     * Workspace icon is empty!
     */
    WORKSPACE_ICON_INVALID(BAD_REQUEST, WORKSPACE, "1013"),

    /**
     * Workspace icon file type is invalid!
     */
    WORKSPACE_ICON_FILE_TYPE_INVALID(BAD_REQUEST, WORKSPACE, "1014"),

    /**
     * workspace icon size exceeds limit {0} KB
     */
    WORKSPACE_ICON_EXCEED_INVALID(BAD_REQUEST, WORKSPACE, "1015"),

    /**
     * workspace description size exceeds limit {0}
     */
    WORKSPACE_DESCRIPTION_INVALID(BAD_REQUEST, WORKSPACE, "1016"),

    USER_NOT_IN_TARGET_WORKSPACE(BAD_REQUEST, WORKSPACE, "1017"),

    INVALID_EXTENSION_PARAM(BAD_REQUEST, WORKSPACE, "1018"),

    /**
     * 工作空间已经存在
     */
    WORKSPACE_ALREADY_EXISTED(BAD_REQUEST, WORKSPACE, "1019"),

    /**
     * ==============================知识库==============================
     */
    /**
     * The current environment knowledgeBase is not support to access this interface!Please contact the administrator to
     * configure and try again!
     */
    NO_PERMISSION_ACCESS_INTERFACE(FORBIDDEN, KNOWLEDGE_BASE, "4001"),

    /**
     * 知识库不存在
     */
    KNOWLEDGE_REPO_NOT_EXIST(NOT_FOUND, KNOWLEDGE_BASE, "4002"),

    /**
     * 上传知识库文件失败
     */
    FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4003"),

    /**
     * 知识库来源有误
     */
    INVALID_KNOWLEDGE_REPO_SOURCE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4004"),

    /**
     * lakeSearch服务调用异常, Fail to modify model: {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4005"),

    /**
     * Fail to create LakeSearch knowledge repo: {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4006"),

    /**
     * Fail to upload file to LakeSearch knowledge repo: {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_UPLOAD(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4007"),

    /**
     * Fail to delete file in LakeSearch knowledge repo: {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_DELETE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4008"),

    /**
     * Fail to download file {0} from LakeSearch
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_DOWNLOAD(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4009"),

    /**
     * Fail to update file chunk in LakeSearch file {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4010"),

    /**
     * Fail to list file chunks in LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_CHUNK_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4011"),

    /**
     * Fail to search text from LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEARCH(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4012"),

    /**
     * Fail to create faq in LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4013"),

    /**
     * Fail to delete faq in LakeSearch faqId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_DELETE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4014"),

    /**
     * Fail to batch delete faqs in LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_DELETE_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4015"),

    /**
     * Fail to modify faq in LakeSearch faqId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_FAILED(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4016"),

    /**
     * Fail to retrieve faq from LakeSearch faqId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_FAILED_RETRIEVE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4017"),

    /**
     * Fail to list faqs from LakeSearch repoId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_FAILED_ID(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4018"),

    /**
     * Fail to start knowledge repo in LakeSearch repoId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_FAILED_REPO_ID(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4019"),

    /**
     * Fail to stop knowledge repo in LakeSearch repoId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_REPO_ID(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4020"),

    /**
     * Fail to create segment rule from LakeSearch
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4021"),

    /**
     * Fail to modify segment rule from LakeSearch ruleId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_RULE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4022"),

    /**
     * Fail to delete segment rule in LakeSearch ruleId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_DELETE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4023"),

    /**
     * Fail to add model in LakeSearch, modelName {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_MODEL(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4024"),

    /**
     * Fail to delete model in LakeSearch, modelName {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_MODEL_DELETE_FAILED(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4025"),

    /**
     * Fail to list models from LakeSearch
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_MODEL(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4026"),

    /**
     * Fail to create task in LakeSearch, repoId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_TASK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4027"),

    /**
     * Fail to list tasks from LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_TASK_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4028"),

    /**
     * Fail to delete knowledge tasks in LakeSearch repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_TASK_REPO_DELETE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4029"),

    /**
     * Fail to upload faq file {0} to LakeSearch knowledge repo {1}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_TWO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4030"),

    /**
     * Fail to delete faq file {0} in LakeSearch repo {1}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_DELETE_FAQ(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4031"),

    /**
     * Fail to list faq files from LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_FAQ(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4032"),

    /**
     * Fail to download faq file {0} from LakeSearch
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_DOWNLOAD(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4033"),

    /**
     * Fail to create faq file chunk in LakeSearch fileId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_CHUNK_FAQ(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4034"),

    /**
     * Fail to modify faq file chunk in LakeSearch fileId {0} chunkId {1}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4035"),

    /**
     * Fail to delete faq file chunk in LakeSearch fileId {0} chunkId {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_DELETE_FAQ(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4036"),

    /**
     * Fail to list faq file chunks from LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_SEGMENT_FAQ_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4037"),

    /**
     * Fail to list labels from LakeSearch knowledge repo {0}
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_LIST_LABEL(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4038"),

    /**
     * Fail to invoke lakeSearch service with kerberos.
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_LIST_LABEL_KERBEROS(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4039"),

    /**
     * Fail to modify knowledge repo, projectId: {0}, repoName: {1}.
     */
    LAKE_SEARCH_SERVICE_MODIFY_KNOW_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4040"),

    /**
     * Fail to delete knowledge repo, projectId: {0}, knowledgeRepoId: {1}
     */
    LAKE_SEARCH_SERVICE_DELETE_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4041"),

    /**
     * Fail to retrieve knowledge repo, projectId: {0}, knowledgeRepoId: {1}.
     */
    LAKE_SEARCH_SERVICE_EXCEPTION_KNOW_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4042"),

    /**
     * Fail to delete file from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileId: {2}.
     */
    LAKE_SEARCH_SERVICE_DELETE_REPO_FILE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4043"),

    /**
     * Fail to create LakeSearch knowledge repo, projectId: {0}, repoName: {1}
     */
    LAKE_SEARCH_SERVICE_CREATE_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4044"),

    /**
     * Fail to list file from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileName: {2}.
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4045"),

    /**
     * Fail to download file from knowledge repo, projectId: {0}, fileId: {1}.
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_REPO_DOWNLOAD(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4046"),

    /**
     * Fail to create file chunk from knowledge repo, projectId: {0}, fileId: {1}
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_REPO_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4047"),

    /**
     * Fail to update file chunk from knowledge repo, projectId: {0}, fileId: {1}, chunkId: {2}.
     */
    LAKE_SEARCH_SERVICE_CHUNK_KNOWLEDGE_REPO(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4048"),

    /**
     * Fail to delete file chunk from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileName: {2}.
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_REPO_DELETE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4049"),

    /**
     * Fail to list file chunks from knowledge repo, projectId: {0}, fileId: {1}.
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_REPO_CHUNK_LIST(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4050"),

    /**
     * Fail to search text from LakeSearch
     */
    LAKE_SEARCH_SERVICE_SEARCH_TEXT(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4051"),

    /**
     * Fail to delete faq, repo: {0}.
     */
    LAKE_SEARCH_SERVICE_FAQ_DELETE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4052"),

    /**
     * Fail to update faq: {0}.
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_FAQ_UPDATE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4053"),

    /**
     * Fail to retrieve faq: {0}.
     */
    LAKE_SEARCH_SERVICE_KNOWLEDGE_FAQ_RETRIEVE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4054"),

    /**
     * Fail to list faq, repo: {0}.
     */
    LAKE_SEARCH_SERVICE_FAQ_LIST(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4055"),

    /**
     * Fail to stop knowledge repo, knowledgeRepoId: {0}.
     */
    LAKE_SEARCH_SERVICE_STOP(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4056"),

    /**
     * Fail to create segment rule.
     */
    LAKE_SEARCH_SERVICE_CREATE_SEGMENT(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4057"),

    /**
     * Fail to modify segment rule: {0}.
     */
    LAKE_SEARCH_SERVICE_MODIFY_SEGMENT(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4058"),

    /**
     * Fail to delete segment rule: {0}.
     */
    LAKE_SEARCH_SERVICE_DELETE_SEGMENT(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4059"),

    /**
     * Fail to list knowledge repo labels, knowledgeRepoId: {0}
     */
    LAKE_SEARCH_SERVICE_LIST_LABEL(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4060"),

    /**
     * Fail to upload FAQ file to knowledge repo, projectId: {0}, knowledgeRepoId: {1}.
     */
    LAKE_SEARCH_SERVICE_FAQ_UPLOAD(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4061"),

    /**
     * Fail to delete FAQ file from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileId: {2}.
     */
    LAKE_SEARCH_SERVICE_FAQ_DELETE_FILE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4062"),

    /**
     * Fail to list FAQ file from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileName: {2}.
     */
    LAKE_SEARCH_SERVICE_FAQ_FILE_LIST(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4063"),

    /**
     * Fail to download FAQ file from knowledge repo, projectId: {0}, fileId: {1}.
     */
    LAKE_SEARCH_SERVICE_DOWNLOAD_FAQ_FILE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4064"),

    /**
     * Fail to create FAQ file chunk from knowledge repo, projectId: {0}, fileId: {1}.
     */
    LAKE_SEARCH_SERVICE_CREATE_FAQ_FILE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4065"),

    /**
     * Fail to delete FAQ file chunk from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileId: {2}.
     */
    LAKE_SEARCH_SERVICE_DELETE_FAQ_FILE_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4066"),

    /**
     * Fail to list FAQ file chunks from knowledge repo, projectId: {0}, fileId: {1}.
     */
    LAKE_SEARCH_SERVICE_FAQ_UPDATE_FILE_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4067"),

    /**
     * Fail to update FAQ file chunk from knowledge repo, projectId: {0}, fileId: {1}, chunkId: {2}.
     */
    LAKE_SEARCH_SERVICE_FAQ_FILE_LIST_CHUNK(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4068"),

    /**
     * Fail to batch delete file from knowledge repo, projectId: {0}, knowledgeRepoId: {1}, fileIds: {2}.
     */
    LAKE_SEARCH_SERVICE_BRANCH_DELETE_FILE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4069"),

    /**
     * 知识库请求信息有误, KooSearch endpoint is empty.
     */
    INVALID_KNOWLEDGE_REPO_REQUEST(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4070"),

    /**
     * LakeSearch authorization is empty!
     */
    LAKE_SEARCH_AUTH_INVALID(BAD_REQUEST, KNOWLEDGE_BASE, "4071"),

    /**
     * Fail to decrypt authorization.
     */
    LAKE_SEARCH_DECRYPT_AUTH(BAD_REQUEST, KNOWLEDGE_BASE, "4072"),

    /**
     * 知识库搜索模型未注册
     */
    SEARCH_MODEL_NOT_REGISTER(BAD_REQUEST, KNOWLEDGE_BASE, "4073"),

    /**
     * 知识库搜索模型路径有误
     */
    SEARCH_MODEL_URL_ERROR(BAD_REQUEST, KNOWLEDGE_BASE, "4074"),

    /**
     * 知识库搜索模型类型不支持
     */
    UNSUPPORTED_SEARCH_MODEL_TYPE(BAD_REQUEST, KNOWLEDGE_BASE, "4075"),

    /**
     * Ocr model already exist and must only exist one.
     */
    OCR_MODEL_ALREADY_EXIST(BAD_REQUEST, KNOWLEDGE_BASE, "4076"),

    /**
     * model type and kooSearch model api name does not support modify!
     */
    MODEL_MODIFY_FAILED_EXIST(BAD_REQUEST, KNOWLEDGE_BASE, "4077"),

    /**
     * model does not exist, can not modify it.
     */
    MODEL_NOT_EXITS_MODIFY(NOT_FOUND, KNOWLEDGE_BASE, "4078"),

    /**
     * 外部LakeSearch服务已创建
     */
    EXTERNAL_SERVICE_ALREADY_EXIST(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4079"),

    /**
     * 外部LakeSearch服务连接失败
     */
    FAIL_CONNECT_EXTERNAL_SERVICE(BAD_REQUEST, KNOWLEDGE_BASE, "4080"),

    /**
     * 用户没有权限修改外部LakeSearch服务
     */
    NO_PERMISSION_TO_MODIFY_EXTERNAL_SERVICE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4081"),

    /**
     * 知识库检索错误 Knowledge search error.
     */
    KNOWLEDGE_SEARCH_EXCEPTION(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4082"),

    /**
     * The value of knowledge recall threshold is illegal.
     */
    KNOW_RECALL_THRESHOLD_ILLEGAL(BAD_REQUEST, KNOWLEDGE_BASE, "4083"),

    /**
     * The value of knowledge faq threshold is illegal.
     */
    FAQ_THRESHOLD_ILLEGAL(BAD_REQUEST, KNOWLEDGE_BASE, "4084"),

    /**
     * agent绑定的知识库数量超过上限
     */
    KNOWLEDGE_REPO_TYPE_INCONSISTENT(BAD_REQUEST, KNOWLEDGE_BASE, "4085"),

    INVALID_KNOWLEDGE_BASE_EXPANSION_PARAMETER(BAD_REQUEST, KNOWLEDGE_BASE, "4086"),

    /**
     * 节点中的知识库不存在
     */
    KNOWLEDGE_BASE_NOT_EXIST_IN_NODE(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4087"),

    /**
     * 共享的知识库不存在
     */
    SHARED_KNOWLEDGE_BASE_NOT_EXISTS(BAD_REQUEST, KNOWLEDGE_BASE, "1089"),

    /**
     * 免费版共享知识库数量超过上线
     */
    FREE_KNOWLEDGE_BASE_LIMIT_EXCEEDED(INTERNAL_SERVER_ERROR, KNOWLEDGE_BASE, "4088"),

    /**
     * 获取知识库默认连接信息错误
     */
    FAILED_TO_FIND_DEFAULT_CONNECTION_INFO(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4089"),

    /**
     * KooSearch认证模式配置错误
     */
    KOO_SEARCH_AUTH_MODE_ERROR(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4089"),

    INVALID_KNOWLEDGE_MERGING_STRATEGY(INTERNAL_SERVER_ERROR, Module.KNOWLEDGE_BASE, "4090"),

    THIRD_PARTY_KNOWLEDGE_CONNECTION_NOT_EXISTS(INTERNAL_SERVER_ERROR, Module.KNOWLEDGE_BASE, "4091"),

    RAG_FLOW_CONNECT_ERROR(INTERNAL_SERVER_ERROR, Module.KNOWLEDGE_BASE, "4091"),

    FILE_NOT_EXIST_OR_EXPIRED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4092"),

    IMAGE_NOT_EXIST_OR_EXPIRED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4092"),

    EMPTY_FILE_CONTENT(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4093"),

    KNOWLEDGE_BASE_NOT_EXIST(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4094"),

    THE_FILE_NOT_BELONG_KNOWLEDGE_BASE(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4095"),

    LIST_FILES_FROM_KOO_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4096"),

    QUERY_IMAGE_FROM_KOO_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4097"),

    DOWNLOAD_FILE_FROM_KOO_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4098"),

    LIST_FILES_FROM_LAKE_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4099"),

    QUERY_IMAGE_FROM_LAKE_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4100"),

    DOWNLOAD_FILE_FROM_LAKE_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4101"),

    LIST_FAQ_FILES_FROM_LAKE_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4102"),

    DOWNLOAD_FAQ_FILES_FROM_LAKE_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4103"),

    LIST_FAQ_FILES_FROM_KOO_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4104"),

    DOWNLOAD_FAQ_FILES_FROM_KOO_SEARCH_FAILED(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4105"),

    THIRD_PARTY_KNOWLEDGE_BASE_UNSUPPORT_CURRENT_OPERATION(BAD_REQUEST, Module.KNOWLEDGE_BASE, "4106"),

    /**
     * ==============================环境管理==============================
     */
    ENVIRONMENT_WITH_QUERY_VPC_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1001"),

    /**
     * 查询子网信息失败
     */
    ENVIRONMENT_WITH_QUERY_SUBNET_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1002"),

    /**
     * 查询镜像组织失败
     */
    ENVIRONMENT_WITH_QUERY_SWR_NAMESPACES_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1003"),

    /**
     * 查询elb失败
     */
    ENVIRONMENT_WITH_QUERY_ELB_BALANCERS_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1004"),

    /**
     * 查询安全组失败
     */
    ENVIRONMENT_WITH_QUERY_SECURITY_GROUPS_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1005"),

    /**
     * apig查询失败
     */
    ENVIRONMENT_WITH_QUERY_APIG_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1007"),

    /**
     * 创建环境，参数不合法
     */
    ENVIRONMENT_CREATE_PARAMETER_VERIFICATION_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1008"),

    /**
     * 创建环境，vpc不合法或vpc信息不存在
     */
    ENVIRONMENT_CREATE_WITH_VPC_NOT_EXIST(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1009"),

    /**
     * 创建环境，子网信息不存在
     */
    ENVIRONMENT_CREATE_WITH_SUBNET_NOT_EXIST(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1010"),

    /**
     * 环境名称已经存在
     */
    ENVIRONMENT_NAME_EXIST(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1013"),

    /**
     * 环境创建失败
     */
    CALLING_OPS_CREATE_ENVIRONMENT_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1014"),

    /**
     * 环境删除失败
     */
    CALLING_OPS_DELETE_ENVIRONMENT_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1015"),

    /**
     * 查询环境信息失败
     */
    CALLING_OPS_QUERY_ENVIRONMENT_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1016"),

    /**
     * 环境信息不存在
     */
    ENVIRONMENT_NOT_EXIST(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1017"),

    /**
     * 创建环境超过限额
     */
    ENVIRONMENT_LIMIT_EXCEEDED(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1018"),

    /**
     * 没有创建环境的权限
     */
    ENVIRONMENT_NOT_PERMISSION_CREATE(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1019"),

    /**
     * 当前项目和空间下已经存在环境变量
     */
    ENVIRONMENT_VARIABLE_EXISTS(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1020"),

    /**
     * 环境变量不能为空
     */
    ENVIRONMENT_VARIABLE_NOT_EMPTY(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1021"),

    /**
     * 当前项目和空间下不存在环境变量
     */
    ENVIRONMENT_VARIABLE_NOT_EXISTS(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1022"),

    /**
     * 环境变量创建失败
     */
    ENVIRONMENT_VARIABLE_CREATE_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1023"),

    /**
     * 环境变量创建失败
     */
    ENVIRONMENT_VARIABLE_DELETE_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1024"),

    /**
     * 设置默认环境失败
     */
    ENVIRONMENT_DEFAULT_SET_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1025"),

    /**
     * 更新环境信息失败
     */
    ENVIRONMENT_MODIFY_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1026"),

    /**
     * 环境删除失败
     */
    ENVIRONMENT_DELETE_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1027"),

    /**
     * 环境删除失败
     */
    ENVIRONMENT_CREATE_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1028"),

    /**
     * 设置默认环境失败
     */
    ENVIRONMENT_DEFAULT_NOT_SUPPORT(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1029"),

    /**
     * 工作流中使用的环境变量不合法
     */
    USED_INVALID_ENVIRONMENT_VARIABLE(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1030"),

    /**
     * 导出环境变量失败
     */
    EXPORT_ENVIRONMENT_VARIABLE_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1031"),

    /**
     * 导入环境变量失败
     */
    IMPORT_ENVIRONMENT_VARIABLE_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1032"),

    /**
     * 查询EIP列表失败
     */
    DEPLOY_QUERY_EIP_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1033"),

    /**
     * 查询NAT列表失败
     */
    DEPLOY_QUERY_NAT_FAIL(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1034"),

    /**
     * 创建中、更新中、删除中 状态的环境不支持删除
     */
    ENVIRONMENT_DELETE_NOT_SUPPORT(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1035"),

    /**
     * 环境变量数量阈值
     */
    ENVIRONMENT_VARIABLES_LIMIT_EXCEEDED(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1036"),

    /**
     * 存在重名的环境变量
     */
    ENVIRONMENT_VARIABLES_DUPLICATE_NAMES(INTERNAL_SERVER_ERROR, Module.ENVIRONMENT_MANAGER, "1037"),


    /**
     * ==============================License 管理==============================
     */
    /**
     * license 保存失败
     */
    LICENSE_UNSAVED(INTERNAL_SERVER_ERROR, LICENSE, "1001"),
    /**
     * license 缺失
     */
    LICENSE_MISSING(INTERNAL_SERVER_ERROR, LICENSE, "1002"),
    /**
     * license 无效或超期
     */
    LICENSE_INVALID(INTERNAL_SERVER_ERROR, LICENSE, "1003"),
    /**
     * license 资源使用超过限制
     */
    LICENSE_EXCEED(INTERNAL_SERVER_ERROR, LICENSE, "1004"),
    /**
     * license 获取pod资源失败
     */
    LICENSE_PODS_ERROR(INTERNAL_SERVER_ERROR, LICENSE, "1005"),
    /**
     * license 从itep获取license资源失败
     */
    LICENSE_GET_RESOURCE_ERROR(INTERNAL_SERVER_ERROR, LICENSE, "1006"),

    /**
     * ==============================导入管理==============================
     */

    /**
     * 预置资源不允许导入
     */
    NO_IMPORT_PLATFORM(OK, Module.IMPORT, "1001"),

    FILE_LACKS_SOURCE_DATA(OK, Module.IMPORT, "1002"),

    EXISTS_SAME_MODEL(OK, Module.IMPORT, "1003"),


    /**
     * ==============================共享资源==============================
     */
    SHARE_RESOURCE_RELEASE_VERSION_IS_NOT_EXISTED(BAD_REQUEST, SHARE_RESOURCE, "1001"),

    CURRENT_WORKSPACE_IS_NOT_AUTH(BAD_REQUEST, SHARE_RESOURCE, "1002"),

    CANNOT_SHARE_RESOURCE_TO_SELF_WORKSPACE(BAD_REQUEST, SHARE_RESOURCE, "1003"),

    SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY(BAD_REQUEST, SHARE_RESOURCE, "1004"),

    /**
     * ==============================记忆管理==============================
     */

    /**
     * 主题重复
     */
    PROFILE_TOPIC_DUPLICATE(BAD_REQUEST, MEMORY, "1001"),

    /**
     * 主题下缺少标签
     */
    EMPTY_TOPIC(BAD_REQUEST, MEMORY, "1002"),

    /**
     * 标签重复
     */
    PROFILE_TAG_DUPLICATE(BAD_REQUEST, MEMORY, "1003"),

    /**
     * 记忆库不存在
     */
    MEMORY_REPO_NOT_EXIST(BAD_REQUEST, MEMORY, "1004"),

    /**
     *
     */
    AGENT_TYPE_MEMORY_REPO_NOT_SUPPORT(BAD_REQUEST, MEMORY, "1005"),


    /**
     * 导出异常码
     */
    EXPORT_RESOURCE_NOT_EXISTS(BAD_REQUEST, EXPORT, "1001"),
    EXPORT_RESOURCE_COMMON_ERROR(BAD_REQUEST, EXPORT, "1002"),
    EXPORT_PRESET_RESOURCE_ERROR(BAD_REQUEST, EXPORT, "1003"),

    /**
     * 导出资源时resource_versions和resource_ids不能同时为空
     */
    EXPORT_RESOURCE_PARAMS_EMPTY(BAD_REQUEST, EXPORT, "1004"),

    /**
     * 导出资源类型不支持
     */
    EXPORT_RESOURCE_TYPE_NOT_SUPPORTED(BAD_REQUEST, EXPORT, "1005"),

    /**
     * ==============================资产广场-应用模板==============================
     */
    CALL_ASSET_APP_EXCEED_FREE_TRIAL_TIMES(BAD_REQUEST, ASSET, "1001");




    /**
     * ;
     * <p>
     * /**
     * 错误码对应的http状态码
     */
    private final HttpStatus httpStatus;

    /**
     * 所属模块
     */
    private final Module module;

    /**
     * 错误码对应的code
     */
    private final String code;

    /**
     * code按照AgentBuilder.{module.subCode}{code}拼接，如AgentBuilder.02101001，必须在i18n中定义相应的message
     *
     * @param httpStatus http状态码
     * @param module 模块
     * @param code 0000 ~ 1000：系统型错误码，错误正常上报，计入稳定性监控及告警；1001 ~ 9999：业务型错误码，不计入接口稳定性及告警
     */
    StudioError(HttpStatus httpStatus, Module module, String code) {
        this.httpStatus = httpStatus;
        this.module = module;
        this.code = code;
    }

    public String getFullCode() {
        return "openjiuwen." + getModule().getSubCode() + getCode();
    }

    @Getter
    public enum Module {
        /**
         * 公共、其它
         */
        COMMON("0200"),

        /**
         * 单智能体
         */
        AGENT("0210"),

        /**
         * 工作流
         */
        WORKFLOW("0220"),

        /**
         * 多智能体
         */
        MULTI_AGENT("0230"),

        /**
         * 组件（插件、MCP、提示词）
         */
        COMPONENT("0240"),

        /**
         * 模型接入
         */
        MODEL("0250"),

        /**
         * 配置管理（意图、数据源）
         */
        CONFIG("0260"),

        /**
         * 提示词工程
         */
        PE("0270"),

        /**
         * 资产中心
         */
        ASSET("0280"),

        /**
         * 团队空间
         */
        WORKSPACE("0290"),

        /**
         * 知识库
         */
        KNOWLEDGE_BASE("0300"),

        /**
         * 环境管理
         */
        ENVIRONMENT_MANAGER("0310"),

        /**
         * License
         */
        LICENSE("0320"),

        SHARE_RESOURCE("0330"),

        /**
         * 记忆管理
         */
        MEMORY("0340"),

        /**
         * 导入
         */
        IMPORT("0350"),

        /**
         * 导出管理
         */
        EXPORT("0360"),

        /**
         * 高代码智能体
         */
        CODE_AGENT("0370"),
        ;

        /**
         * 预分配的子模块错误码
         */
        private final String subCode;

        Module(String subCode) {
            this.subCode = subCode;
        }
    }
}

