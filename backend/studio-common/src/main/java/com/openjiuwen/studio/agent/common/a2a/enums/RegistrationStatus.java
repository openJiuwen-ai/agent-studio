/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.a2a.enums;

/**
 * A2A 注册状态枚举
 *
 * <p>FEAT-131: 注册失败不阻断发布，挂"注册异常"角标 + 重试入口</p>
 */
public enum RegistrationStatus {

    /**
     * 已注册（正常）
     */
    REGISTERED("已注册"),

    /**
     * 注册异常（可重试）
     */
    REGISTRATION_FAILED("注册异常"),

    /**
     * 不支持 A2A 暴露（UNKNOWN 类型）
     */
    NOT_SUPPORTED("不支持 A2A 暴露"),

    /**
     * 注销中
     */
    DEREGISTERING("注销中"),

    /**
     * 注销失败（可重试）
     */
    DEREGISTRATION_FAILED("注销异常");

    private final String description;

    RegistrationStatus(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
