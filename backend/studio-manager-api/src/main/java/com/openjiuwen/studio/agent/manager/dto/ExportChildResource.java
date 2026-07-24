/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 导出子资源信息。
 */
@ApiModel(description = "导出子资源信息。")

@Validated

public class ExportChildResource implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    private String resourceId = null;

    @JsonProperty("resource_type")
    private String resourceType = null;

    public String getResourceId() {
        return resourceId;
    }

    public ExportChildResource setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public ExportChildResource setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportChildResource {\n");
        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
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
        ExportChildResource exportChildResource = (ExportChildResource) o;
        return Objects.equals(this.resourceId, exportChildResource.resourceId) && Objects.equals(this.resourceType,
            exportChildResource.resourceType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceType);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
