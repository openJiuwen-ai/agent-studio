/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;

/**
 * 不可变平台身份记录 — 从平台 Token 认证结果中提取的身份信息
 *
 * <p>使用 record 保证不可变（SimpleUser 是 @Data 可变，无法防止 setUserId 漂移）。
 * 仅在 {@link ExecutionIdentityContext} 内使用，非执行模块通过防御性副本获取 SimpleUser 视图。
 *
 * @param userId     平台用户 ID
 * @param token      平台 Token（认证后的，非请求未验 header）
 * @param userName   平台用户名
 * @param projectId  平台项目 ID
 * @param domainId   平台域 ID
 * @param domainName 平台域名
 */
public record PlatformPrincipal(
    String userId,
    String token,
    String userName,
    String projectId,
    String domainId,
    String domainName
) {
    /**
     * 转换为 SimpleUser 防御性副本 — 供 {@code RequestContextUtils.getRequestUser()} 兼容返回
     *
     * @return 不可变 SimpleUser 副本（字段值来自本 record）
     */
    public SimpleUser toSimpleUserCopy() {
        return SimpleUser.builder()
            .userId(userId)
            .token(token)
            .userName(userName)
            .projectId(projectId)
            .domainId(domainId != null ? domainId : "0")
            .domainName(domainName != null ? domainName : "0")
            .build();
    }

    /**
     * 从 SimpleUser 构造 PlatformPrincipal
     *
     * @param simpleUser 平台认证后的用户信息
     * @return PlatformPrincipal
     */
    public static PlatformPrincipal from(SimpleUser simpleUser) {
        return new PlatformPrincipal(
            simpleUser.getUserId(),
            simpleUser.getToken(),
            simpleUser.getUserName(),
            simpleUser.getProjectId(),
            simpleUser.getDomainId(),
            simpleUser.getDomainName()
        );
    }
}
