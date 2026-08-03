/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 异步身份快照— 平台 Token + effective userId
 *
 * <p>与客户 header 快照（{@link AsyncExecutionSnapshot}）分离存储，provenance 在 Redis 往返不丢：
 * <ul>
 *   <li>{@code platformToken}：创建任务时实际通过认证的平台 Token（来自
 *       {@code ExecutionIdentityContext.platformPrincipal.token}，非请求未验 header）；
 *       恢复时经 {@code PlatformPrincipalResolver.resolveOrThrow} 重新解析，
 *       <b>不拼 {@code taskEntity.userId|projectId}</b>。</li>
 *   <li>{@code effectiveUserId}：cust-userid（缺失回退平台 userId）；Agent/Workflow 业务执行用户。</li>
 * </ul>
 *
 * @param platformToken  平台 Token（认证后的）
 * @param effectiveUserId effective userId（cust-userid 或平台回退）
 */
public record AsyncIdentitySnapshot(String platformToken, String effectiveUserId) {
}
