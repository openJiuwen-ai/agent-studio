/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 知识库通用基本信息
 *
 * @since 2025-08-15
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeBaseEntity {

    /**
     * 主键ID
     */
    private String id;

    /**
     * 知识库名称
     */
    private String name;

    /**
     * 知识库类型
     */
    private String type;

    /**
     * 状态：启用，停用
     */
    private String status;

    /**
     * 知识库图标
     */
    private String icon;

    /**
     * 来源知识库连接ID(包含第三方和自带）
     */
    private String knowledgeBaseConnectionId;

    private String knowledgeBaseTenantType;

    /**
     * 知识库类型
     */
    private String connectorId;

    /**
     * 第三方知识库的外部ID
     */
    private String externalId;

    /**
     * 知识库描述
     */
    private String description;

    /**
     * 记录创建时间
     */
    private Long createTime;

    /**
     * 记录最后更新时间
     */
    private Long updateTime;

    /**
     * 项目ID
     */
    private String projectId;

    /**
     * 租户id
     */
    private String domainId;

    /**
     * 租户名
     */
    private String domainName;

    /**
     * 工作空间ID
     */
    private String workspaceId;

    /**
     * 创建人（用户ID）
     */
    private String createdUserId;

    /**
     * 创建人（用户名）
     */
    private String createdUserName;

    /**
     * 更新人（用户id）
     */
    private String lastUpdateUserId;

    /**
     * 更新人（用户名）
     */
    private String lastUpdateUserName;

    /**
     * 复制来源的知识库ID，知识库是从其他空间复制而来时有效
     */
    private String copySourceId;

    private String shareScope;

    private String repoType;

    /**
     * Embedding模型服务ID（model_service_id，用于openjiuwen知识库）
     */
    private String embeddingModelServiceId;

    /**
     * Rerank模型服务ID（model_service_id，用于openjiuwen知识库）
     */
    private String rerankModelServiceId;

}
