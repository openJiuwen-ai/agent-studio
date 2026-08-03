/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 平台认证协议异常 — 响应格式错时抛出
 *
 * <p>Filter 异常映射：HTTP 500（不设 effective）
 */
public class PlatformAuthProtocolException extends PlatformAuthException {

    public PlatformAuthProtocolException(String message) {
        super(message);
    }

    public PlatformAuthProtocolException(String message, Throwable cause) {
        super(message, cause);
    }
}
