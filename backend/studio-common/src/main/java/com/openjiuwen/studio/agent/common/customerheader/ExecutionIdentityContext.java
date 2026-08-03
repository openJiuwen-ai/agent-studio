/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 执行身份上下文 — 携带平台 principal 和 effective userId
 *
 * <p>设计原则：
 * <ul>
 *   <li>CURRENT_USER 存平台 principal（非 effective 视图），防非执行模块漂移</li>
 *   <li>effectiveUserId = cust-userid（simple 模式 + Profile 启用 + cust-userid 非空时）</li>
 *   <li>effectiveUserId 缺失时回退 platformPrincipal.userId</li>
 *   <li>平台 token/agentSid 认证链路不因 cust-userid 被绕过</li>
 * </ul>
 *
 * @param platformPrincipal 平台身份（认证后的，不可变）
 * @param effectiveUserId   执行用 userId（cust-userid 或回退平台 userId）
 */
public record ExecutionIdentityContext(
    PlatformPrincipal platformPrincipal,
    String effectiveUserId
) {
}
