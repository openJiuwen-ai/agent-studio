/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;
import lombok.experimental.Accessors;

import java.io.Serializable;

@Data
@Accessors(chain = true)
public class DatasourceEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    private String id;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("type")
    private String type;

    @JsonProperty("desc")
    private String desc;

    @JsonProperty("connection_info")
    private String connectionInfo;

    @JsonProperty("status")
    private String status;

    @JsonProperty("last_error_message")
    private String lastErrorMessage;

    @JsonProperty("created_by")
    private String createdBy;

    @JsonProperty("created_on")
    private String createdOn;

    @JsonProperty("updated_by")
    private String updatedBy;

    @JsonProperty("updated_on")
    private String updatedOn;
}
