/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 平台身份解析器接口 — 从平台 Token 解析 PlatformPrincipal
 *
 * <p>Filter 和异步恢复（TaskRuntime）共注入同一 bean，复用同一组类型异常（/）。
 * 现状 {@code SimpleUserContextFilter.getUserByToken} 是 private，TaskRuntime 无法复用；
 * 抽 public bean 后 Filter 注册改 bean 注入。
 *
 * <p>异常映射：
 * <ul>
 *   <li>Token 无效/过期/撤权 → {@link InvalidPlatformTokenException}（401）</li>
 *   <li>认证服务超时/5xx → {@link PlatformAuthServiceUnavailableException}（503）</li>
 *   <li>响应格式错 → {@link PlatformAuthProtocolException}（500）</li>
 * </ul>
 *
 * <p>任何 Resolver 失败不得仅凭 cust-userid 建 ExecutionIdentityContext。
 */
public interface PlatformPrincipalResolver {

    /**
     * 解析平台 Token，返回认证后的 PlatformPrincipal
     *
     * @param platformToken 平台 Token（从 agentSid / X-Auth-Token 提取）
     * @return 认证后的 PlatformPrincipal
     * @throws InvalidPlatformTokenException           Token 无效/过期/撤权
     * @throws PlatformAuthServiceUnavailableException 认证服务超时/5xx
     * @throws PlatformAuthProtocolException           响应格式错
     */
    PlatformPrincipal resolveOrThrow(String platformToken);
}
