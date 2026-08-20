/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;

import java.util.Date;

/**
 * DependencyEntity
 */

@Data
@NoArgsConstructor
@AllArgsConstructor
@Accessors(chain = true)
@Entity
@Table(name = "t_dependency")
public class DependencyEntityRepo {
    @JsonProperty("id")
    @Id
    private String id;

    @JsonProperty("version_id")
    private String versionId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("description")
    private String description;

    @JsonProperty("runtime")
    private String runtime;

    @JsonProperty("scope")
    private String scope;

    @JsonProperty("link")
    private String link;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("created_on")
    private Date createdOn;

    @JsonProperty("updater_id")
    private String updaterId;

    @JsonProperty("updated_on")
    private Date updatedOn;

    @JsonProperty("version")
    private int version;

    @JsonProperty("deleted")
    private Boolean deleted = false;
}
