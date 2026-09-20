/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ExportAgent
 */

@Validated

public class ExportAgent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("agent_id")
    @Schema(description = "Agent ID", example = "example-id-123")
    private String agentId = null;

    @JsonProperty("agent_version")
    @Schema(description = "Agent版本", example = "1.0.0")
    private String agentVersion = null;

    public String getAgentId() {
        return agentId;
    }

    public ExportAgent setAgentId(String agentId) {
        this.agentId = agentId;
        return this;
    }

    public String getAgentVersion() {
        return agentVersion;
    }

    public ExportAgent setAgentVersion(String agentVersion) {
        this.agentVersion = agentVersion;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportAgent {\n");

        sb.append("    agentId: ").append(toIndentedString(agentId)).append("\n");
        sb.append("    agentVersion: ").append(toIndentedString(agentVersion)).append("\n");
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
        ExportAgent exportAgent = (ExportAgent) o;
        return Objects.equals(this.agentId, exportAgent.agentId) && Objects.equals(this.agentVersion,
            exportAgent.agentVersion);
    }

    @Override
    public int hashCode() {
        return Objects.hash(agentId, agentVersion);
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
