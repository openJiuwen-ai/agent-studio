/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 导出相关参数。
 */
@ApiModel(description = "导出相关参数。")

@Validated

public class ExportResourceVersion implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    @NotBlank
    private String resourceId = null;

    @JsonProperty("resource_version")
    private String resourceVersion = null;

    @JsonProperty("child_nodes")
    @Valid
    private List<ExportChildResource> childNodes = null;

    public String getResourceId() {
        return resourceId;
    }

    public ExportResourceVersion setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceVersion() {
        return resourceVersion;
    }

    public ExportResourceVersion setResourceVersion(String resourceVersion) {
        this.resourceVersion = resourceVersion;
        return this;
    }

    public List<ExportChildResource> getChildNodes() {
        return childNodes;
    }

    public ExportResourceVersion setChildNodes(List<ExportChildResource> childNodes) {
        this.childNodes = childNodes;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportResourceVersion {\n");

        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceVersion: ").append(toIndentedString(resourceVersion)).append("\n");
        sb.append("    childNodes: ").append(toIndentedString(childNodes)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        ExportResourceVersion exportResourceVersion = (ExportResourceVersion) o;
        return Objects.equals(this.resourceId, exportResourceVersion.resourceId)
            && Objects.equals(this.resourceVersion, exportResourceVersion.resourceVersion)
            && Objects.equals(this.childNodes, exportResourceVersion.childNodes);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceVersion, childNodes);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
