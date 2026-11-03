/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.bo;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.experimental.Accessors;

@Data
@Accessors(chain = true)
public class SkillDetails {
    @JsonProperty("skill_id")
    private String skillId;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("icon")
    private String icon;

    @JsonProperty("status")
    private String status;

    @JsonProperty("source")
    private String source;

    @JsonProperty("description")
    private String description;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("creator_name")
    private String creatorName;

    @JsonProperty("latest_version")
    private String latestVersion;

    @JsonProperty("used_version")
    private String usedVersion;

    @JsonProperty("version_name")
    private String versionName;

    @JsonProperty("created_at")
    private Long createdAt;

    @JsonProperty("updated_at")
    private Long updatedAt;

    @JsonProperty("obs_path")
    private String obsPath;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("published_asset")
    private Integer publishedAsset;
}
