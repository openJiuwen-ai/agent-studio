/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 修改默认知识库连接的请求体
 */
@ApiModel(description = "修改默认知识库连接的请求体")

@Validated

public class UpdateDefaultKnowledgeBaseConnectionRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("changed")
    @Schema(description = "changed", example = "true")
    private Boolean changed = false;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "example-id-123")
    private String connectorId = null;

    @JsonProperty("params")
    @Schema(description = "参数", example = "[]")
    @Valid
    @Size()
    private List<ConnectionParamInfo> params = null;

    public UpdateDefaultKnowledgeBaseConnectionRequestBody setChanged(Boolean changed) {
        this.changed = changed;
        return this;
    }

    public Boolean isChanged() {
        return changed;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public UpdateDefaultKnowledgeBaseConnectionRequestBody setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public List<ConnectionParamInfo> getParams() {
        return params;
    }

    public UpdateDefaultKnowledgeBaseConnectionRequestBody setParams(List<ConnectionParamInfo> params) {
        this.params = params;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UpdateDefaultKnowledgeBaseConnectionRequestBody {\n");

        sb.append("    changed: ").append(toIndentedString(changed)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    params: ").append(toIndentedString(params)).append("\n");
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
        UpdateDefaultKnowledgeBaseConnectionRequestBody updateDefaultKnowledgeBaseConnectionRequestBody
            = (UpdateDefaultKnowledgeBaseConnectionRequestBody) o;
        return Objects.equals(this.changed, updateDefaultKnowledgeBaseConnectionRequestBody.changed) && Objects.equals(
            this.connectorId, updateDefaultKnowledgeBaseConnectionRequestBody.connectorId) && Objects.equals(
            this.params, updateDefaultKnowledgeBaseConnectionRequestBody.params);
    }

    @Override
    public int hashCode() {
        return Objects.hash(changed, connectorId, params);
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
