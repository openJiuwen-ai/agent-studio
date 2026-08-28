/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.md;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

/**
 * 供应商鉴权数据（API Key 等）。
 *
 * <p>MASKED 模式：导出时 {@code authInfo} 被置为空格占位，导入后用户在目标环境重新配置密钥，
 * 导入端遇空白 authInfo 不插入 {@code t_provider_auth_info} 行（等价于新建供应商的"未配置鉴权"初始态）。
 */
@Getter
@Setter
@Accessors(chain = true)
@NoArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
@JsonIgnoreProperties(ignoreUnknown = true)
public class ProviderAuthData {
    private String id;

    private String providerId;

    private String authMetadataId;

    private String authType;

    private String authInfo;

    private String createdByUser;

    private long createdDate;

    private long lastUpdatedDate;

    private String domainId;

    private String projectId;

    private String workspaceId;

    private String identityId;
}
