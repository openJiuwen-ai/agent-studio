/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.Date;

/**
 * 功能描述
 *
 * @since 2024-11-12
 */
@Data
public class KnowledgeRepoEntity {
    @JsonProperty("knowledge_repo_id")
    private String knowledgeRepoId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("display_name")
    private String displayName;

    private String desc;

    private String type;

    private String source;

    private String icon;

    @JsonProperty("icon_name")
    private String iconName;

    private Long size;

    @JsonProperty("file_num")
    private Integer fileNum;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("tenant_type")
    private String tenantType;

    @JsonProperty("domain_name")
    private String domainName;

    private String creator;

    @JsonProperty("creator_id")
    private String creatorId;

    private String status;

    private String metadata;

    @JsonProperty("created_on")
    private Date createdOn;

    @JsonProperty("updated_on")
    private Date updatedOn;

    @JsonProperty("workspace_id")
    private String workspaceId;
}
