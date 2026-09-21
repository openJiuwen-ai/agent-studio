/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryMdInterfaceProtocolQo: converted from multi query params
 */
@ApiModel(description = "QueryMdInterfaceProtocolQo: converted from multi query params")

@Validated

public class QueryMdInterfaceProtocolQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "example-type")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    private String modelType = null;

    @JsonProperty("visible")
    @Schema(description = "可见", example = "示例字符串")
    private String visible = "true";

    public String getWorkspaceId() {
        return workspaceId;
    }

    public QueryMdInterfaceProtocolQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public QueryMdInterfaceProtocolQo setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getVisible() {
        return visible;
    }

    public QueryMdInterfaceProtocolQo setVisible(String visible) {
        this.visible = visible;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryMdInterfaceProtocolQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    visible: ").append(toIndentedString(visible)).append("\n");
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
        QueryMdInterfaceProtocolQo queryMdInterfaceProtocolQo = (QueryMdInterfaceProtocolQo) o;
        return Objects.equals(this.workspaceId, queryMdInterfaceProtocolQo.workspaceId) && Objects.equals(
            this.modelType, queryMdInterfaceProtocolQo.modelType) && Objects.equals(this.visible,
            queryMdInterfaceProtocolQo.visible);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, modelType, visible);
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
