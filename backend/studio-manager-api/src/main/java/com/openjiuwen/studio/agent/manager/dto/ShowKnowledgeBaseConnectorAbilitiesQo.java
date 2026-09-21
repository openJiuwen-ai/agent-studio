/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ShowKnowledgeBaseConnectorAbilitiesQo: converted from multi query params
 */
@ApiModel(description = "ShowKnowledgeBaseConnectorAbilitiesQo: converted from multi query params")

@Validated

public class ShowKnowledgeBaseConnectorAbilitiesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("connector_type")
    @Schema(description = "连接器类型", example = "example-type")
    @Length(max = 64)
    private String connectorType = null;

    @JsonProperty("connection_id")
    @Schema(description = "连接ID", example = "example-id-123")
    @Length(max = 64)
    private String connectionId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ShowKnowledgeBaseConnectorAbilitiesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getConnectorType() {
        return connectorType;
    }

    public ShowKnowledgeBaseConnectorAbilitiesQo setConnectorType(String connectorType) {
        this.connectorType = connectorType;
        return this;
    }

    public String getConnectionId() {
        return connectionId;
    }

    public ShowKnowledgeBaseConnectorAbilitiesQo setConnectionId(String connectionId) {
        this.connectionId = connectionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShowKnowledgeBaseConnectorAbilitiesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    connectorType: ").append(toIndentedString(connectorType)).append("\n");
        sb.append("    connectionId: ").append(toIndentedString(connectionId)).append("\n");
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
        ShowKnowledgeBaseConnectorAbilitiesQo showKnowledgeBaseConnectorAbilitiesQo
            = (ShowKnowledgeBaseConnectorAbilitiesQo) o;
        return Objects.equals(this.workspaceId, showKnowledgeBaseConnectorAbilitiesQo.workspaceId) && Objects.equals(
            this.connectorType, showKnowledgeBaseConnectorAbilitiesQo.connectorType) && Objects.equals(
            this.connectionId, showKnowledgeBaseConnectorAbilitiesQo.connectionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, connectorType, connectionId);
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
