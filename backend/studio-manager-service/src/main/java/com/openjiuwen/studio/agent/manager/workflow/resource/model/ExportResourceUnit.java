/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;

import lombok.Data;

import java.util.List;

@Data
public class ExportResourceUnit {

    @JsonProperty("resource_id")
    private String resourceId;

    @JsonProperty("resource_name")
    private String resourceName;

    @JsonProperty("resource_type")
    private String resourceType;

    @JsonProperty("resource_version")
    private String resourceVersion;

    @JsonProperty("parent_resource_id")
    private String parentResourceId;

    @JsonProperty("resource_level")
    private Integer resourceLevel;

    @JsonProperty("level2_resources")
    private List<String> level2Resources;

    @JsonProperty("app_id")
    private String appId;

    @JsonProperty("app_type")
    private String appType;

    @JsonProperty("l1_mappings")
    private List<MappingEntity> l1Mappings;
}
