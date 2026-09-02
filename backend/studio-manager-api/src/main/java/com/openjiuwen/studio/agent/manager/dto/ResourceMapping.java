/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 绑定关系。
 */
@ApiModel(description = "绑定关系。")

@Validated

public class ResourceMapping implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "example-id-123")
    private String resourceId = null;

    @JsonProperty("resource_name")
    @Schema(description = "资源名称", example = "示例名称")
    private String resourceName = null;

    @JsonProperty("reference_number")
    @Schema(description = "引用编号", example = "1")
    private Long referenceNumber = null;

    public String getResourceId() {
        return resourceId;
    }

    public ResourceMapping setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public ResourceMapping setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public Long getReferenceNumber() {
        return referenceNumber;
    }

    public ResourceMapping setReferenceNumber(Long referenceNumber) {
        this.referenceNumber = referenceNumber;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ResourceMapping {\n");

        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    referenceNumber: ").append(toIndentedString(referenceNumber)).append("\n");
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
        ResourceMapping resourceMapping = (ResourceMapping) o;
        return Objects.equals(this.resourceId, resourceMapping.resourceId) && Objects.equals(this.resourceName,
            resourceMapping.resourceName) && Objects.equals(this.referenceNumber, resourceMapping.referenceNumber);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceName, referenceNumber);
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
