/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.constant;

/**
 * 功能描述 通用常量
 *
 */
public final class CommonConstant {
    /**
     * excel文件后缀 xls
     */
    public static final String EXCEL_SUFFIX_XLS = ".xls";

    /**
     * excel文件后缀 xlsx
     */
    public static final String EXCEL_SUFFIX_XLSX = ".xlsx";

    /**
     * 数字-1
     */
    public static final int NUM_MINUS_ONE = -1;

    /**
     * 数字0
     */
    public static final int NUM_ZERO = 0;

    /**
     * 数字1
     */
    public static final int NUM_ONE = 1;

    /**
     * 数字2
     */
    public static final int NUM_TWO = 2;

    /**
     * 数字3
     */
    public static final int NUM_THREE = 3;

    /**
     * 数字50
     */
    public static final int NUM_FIFTY = 50;

    /**
     * 数字50
     */
    public static final int NUM_FIVE_HUNDRED = 500;

    /**
     * 文件夹分隔符
     */
    public static final String FOLDER_SEPARATOR = "/";

    /**
     * 乌兰三
     */
    public static final String WLCB_ENV = "wlcb";

    /**
     * HCS环境变量
     */
    public static final String HCS_ENV = "HCS";

    /**
     * HC环境
     */
    public static final String HC_ENV = "HC";

    /**
     * trace id
     */
    public static final String CONTEXT_TRACE_ID = "TraceId";

    /**
     * 请求头TOKEN
     */
    public static final String X_AUTH_TOKEN = "X-Auth-Token";

    /**
     * 工作空间id
     */
    public static final String X_WORKSPACE_ID = "x-workspace-id";

    /**
     * 请求头语言
     */
    public static final String X_LANGUAGE = "X-Language";

    /**
     * 语言-中文
     */
    public static final String LANGUAGE_ZH = "zh";

    /**
     * 国家-中国
     */
    public static final String COUNTRY_CN = "cn";

    /**
     * 中文
     */
    public static final String CN_LANGUAGE = "zh-cn";

    /**
     * 语言-英文
     */
    public static final String LANGUAGE_EN = "en";

    /**
     * 国家-美国
     */
    public static final String COUNTRY_US = "us";

    /**
     * 英文
     */
    public static final String EN_LANGUAGE = "en-us";

    public static final String LOCAL_NAME_EVALUATION_TASK = "excel.export.evaluation.task";

    public static final String LOCAL_NAME_EXPORT_RESULT = "excel.export.export.result";

    public static final String LOCAL_NAME_EXPORT_MATCHING = "excel.export.evaluation.result.matching";

    public static final String LOCAL_NAME_EXPORT_SIMILARITY = "excel.export.evaluation.result.similarity";

    public static final String LOCAL_NAME_EXPORT_TIME_CONSUMED = "excel.export.evaluation.result.time.consumed";

    public static final String LOCAL_NAME_TEMPLATE_NAME = "excel.prompt.template.name";

    public static final String LOCAL_NAME_TEMPLATE_CONTENT = "excel.prompt.template.content";

    public static final String LOCAL_NAME_TEMPLATE_DESCP = "excel.prompt.template.descp";

    public static final String LOCAL_NAME_TEMPLATE_VAR = "excel.prompt.template.var";

    public static final String LOCAL_NAME_TEMPLATE_LABEL = "excel.prompt.template.label";

    public static final String LOCAL_NAME_TEMPLATE_INDUSTRY = "excel.prompt.template.industry";

    public static final String LOCAL_NAME_TEMPLATE_CREATOR = "excel.prompt.template.creator";

    public static final String LOCAL_NAME_TEMPLATE_CREATED_ON = "excel.prompt.template.created.on";

    public static final String LOCAL_NAME_TEMPLATE_MODIFIED_ON = "excel.prompt.template.modified.on";

    public static final String LOCAL_NAME_TEMPLATE_CONST_EXPECT_RESULT = "excel.prompt.template.const.expect.result";

    public static final String LOCAL_NAME_TEMPLATE_CONST_REAL_RESULT = "excel.prompt.template.const.real.result";

    public static final String RETRY = "请稍后重试！";

    public static final String CONTACT = "或联系系统管理员";

    public static final String FAILED = "failed";

    public static final String SUCCESS = "success";

    public static final String OPERATE = "operate";

    public static final String INSERT = "insert";

    public static final String DELETE = "delete";

    public static final String UPDATE = "update";

    public static final String SELECT = "select";

    public static final String APPLICATION_MS_EXCEL = ".xlsx";

    public static final String APPLICATION_EXCEL = ".xls";

    /**
     * 导入行数超过上限的完整提示信息
     */
    public static final String ROWS_EXCEED_LIMIT = "excel.prompt.row.limit";

    /**
     * 提示信息：导入中重复的模板名称
     */
    public static final String PROMPT_NAME_DUPLICATE = "excel.prompt.duplicate.name";

    /**
     * 提示信息：模板名称不合法
     */
    public static final String PROMPT_NAME_INVALID = "excel.prompt.name.invalid";

    /**
     * 提示信息：模板名称在平台中已存在
     */
    public static final String PROMPT_NAME_EXISTS = "excel.prompt.name.exists";

    /**
     * 提示信息：内容长度超过限制
     */
    public static final String CONTENT_LENGTH_EXCEED = "excel.content.length.exceed";

    /**
     * 提示信息：行业名称不存在
     */
    public static final String INDUSTRY_NOT_FOUND = "excel.industry.not.found";

    /**
     * 提示信息：标签名称不存在
     */
    public static final String TAG_NOT_FOUND = "excel.tag.not.found";

    /**
     * 提示信息：必填项为空
     */
    public static final String REQUIRED_FIELD_MISSING = "excel.prompt.required.field.missing";

    /**
     * 查询订单信息URL
     */
    public static final String RESOURCES_ORDERS_URL = "%s/v1/%s/agentBuilder/operation/resources/orders";

    /**
     * 模型适用范围
     */
    public static final String USE_RANGE_AVAILABLE = "available";

    public static final String USE_RANGE_SELFTRAINING = "selfTraining";

    /**
     * 盘古模型类型
     */
    public static final String AGENT_BUILDER_MODEL_TYPE = "ei_agentBuilder";

    /**
     * 三方模型类型
     */
    public static final String THIRD_MODEL_TYPE = "ei_3rd";

    /**
     * 千问模型类型
     */
    public static final String QWEN_MODEL_TYPE = "qwen";

    /**
     * 模型发布类型
     */
    public static final String MODEL_PUBLISH_TYPE = "online";

    /**
     * 模型状态
     */
    public static final String MODEL_STATUS = "success";

    /**
     * 提示词期望输出
     */
    public static final String AGENT_BUILDER_PROMPT_OUTPUT = "AGENT_BUILDER_PROMPT_OUTPUT";

    /**
     * 提示词期望输出-中文
     */
    public static final String AGENT_BUILDER_PROMPT_OUTPUT_CN = "期望输出";

    /**
     * 提示词期望输出-英文
     */
    public static final String AGENT_BUILDER_PROMPT_OUTPUT_EN = "expected_output";


}
