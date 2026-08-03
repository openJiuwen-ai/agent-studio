/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 平台认证服务不可用异常 — 认证服务超时/5xx 时抛出
 *
 * <p>Filter 异常映射：HTTP 503（不退化为仅凭 cust-userid 继续）
 */
public class PlatformAuthServiceUnavailableException extends PlatformAuthException {

    public PlatformAuthServiceUnavailableException(String message) {
        super(message);
    }

    public PlatformAuthServiceUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
