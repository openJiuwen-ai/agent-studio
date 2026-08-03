/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 平台认证异常基类 — Resolver 失败时抛出，带类型区分失败原因
 *
 * <p>异常映射：
 * <ul>
 *   <li>{@link InvalidPlatformTokenException} → 401（Token 无效/过期/撤权）</li>
 *   <li>{@link PlatformAuthServiceUnavailableException} → 503（认证服务超时/5xx）</li>
 *   <li>{@link PlatformAuthProtocolException} → 500（响应格式错）</li>
 * </ul>
 */
public abstract class PlatformAuthException extends RuntimeException {
    protected PlatformAuthException(String message) {
        super(message);
    }

    protected PlatformAuthException(String message, Throwable cause) {
        super(message, cause);
    }
}
