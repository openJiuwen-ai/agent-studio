/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareInfo;

import lombok.Data;

import java.util.List;

@Data
public class ExportInfo {

    @JsonProperty("resource_id")
    private String resourceId;

    @JsonProperty("resource_type")
    private String resourceType;

    @JsonProperty("resource_name")
    private String resourceName;

    @JsonProperty("resource_level")
    private Integer resourceLevel;

    @JsonProperty("dsl")
    private Object dsl;

    @JsonProperty("metadata")
    private Object metadata;

    @JsonProperty("release_version")
    private ReleaseVersion releaseVersion;

    @JsonProperty("share_info")
    private ShareInfo shareInfo;

    @JsonProperty("level2_resources")
    private List<String> level2Resources;

    @JsonProperty("parents")
    private List<String> parents;

    @JsonProperty("schema_version")
    private String schemaVersion = "V2.0";

    @JsonProperty("l1_mappings")
    private List<MappingEntity> l1Mappings;

}
