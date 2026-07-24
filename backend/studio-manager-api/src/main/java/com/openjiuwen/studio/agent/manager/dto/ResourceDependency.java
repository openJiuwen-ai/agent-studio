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
 * agent依赖资源。
 */
@ApiModel(description = "agent依赖资源。")

@Validated

public class ResourceDependency implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    private String resourceId = null;

    @JsonProperty("resource_name")
    private String resourceName = null;

    @JsonProperty("resource_version")
    private String resourceVersion = null;

    @JsonProperty("resource_type")
    private String resourceType = null;

    @JsonProperty("parent_id")
    private String parentId = null;

    public String getResourceId() {
        return resourceId;
    }

    public ResourceDependency setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public ResourceDependency setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public String getResourceVersion() {
        return resourceVersion;
    }

    public ResourceDependency setResourceVersion(String resourceVersion) {
        this.resourceVersion = resourceVersion;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public ResourceDependency setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public String getParentId() {
        return parentId;
    }

    public ResourceDependency setParentId(String parentId) {
        this.parentId = parentId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ResourceDependency {\n");
        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    resourceVersion: ").append(toIndentedString(resourceVersion)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    parentId: ").append(toIndentedString(parentId)).append("\n");
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
        ResourceDependency resourceDependency = (ResourceDependency) o;
        return Objects.equals(this.resourceId, resourceDependency.resourceId) && Objects.equals(this.resourceName,
            resourceDependency.resourceName) && Objects.equals(this.resourceVersion, resourceDependency.resourceVersion)
            && Objects.equals(this.resourceType, resourceDependency.resourceType) && Objects.equals(this.parentId,
            resourceDependency.parentId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceName, resourceVersion, resourceType, parentId);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
