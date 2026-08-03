/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 平台 Token 无效异常 — Token 无效/过期/撤权时抛出
 *
 * <p>Filter 异常映射：HTTP 401
 */
public class InvalidPlatformTokenException extends PlatformAuthException {

    public InvalidPlatformTokenException(String message) {
        super(message);
    }

    public InvalidPlatformTokenException(String message, Throwable cause) {
        super(message, cause);
    }
}
