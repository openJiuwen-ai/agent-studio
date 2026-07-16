/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.List;

@Data
public class ExportResult {

    @JsonProperty("resource_id")
    private String resourceId;

    @JsonProperty("resource_version")
    private String resourceVersion;

    @JsonProperty("resource_type")
    private String resourceType;


    @JsonProperty("resource_name")
    private String resourceName;

    @JsonProperty("resource_desc")
    private String resourceDesc;

    private ImportExportStatusEnum status;

    private String reason;

    private String suggestion;

    @JsonProperty("level2_resources")
    private List<String> level2Resources;

    @JsonProperty("resource_level")
    private Integer resourceLevel;

    @JsonProperty("child_results")
    private List<ExportResult> childResults;
}
