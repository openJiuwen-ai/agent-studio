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
 * Mcp详情。
 */
@ApiModel(description = "Mcp详情。")

@Validated

public class AgentMcpDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("mcp_id")
    @Schema(description = "MCP服务ID", example = "mcp_001")
    private String mcpId = null;

    @JsonProperty("mcp_param")
    @Schema(description = "MCP参数", example = "{\"key\":\"value\"}")
    private String mcpParam = null;

    public String getMcpId() {
        return mcpId;
    }

    public AgentMcpDetail setMcpId(String mcpId) {
        this.mcpId = mcpId;
        return this;
    }

    public String getMcpParam() {
        return mcpParam;
    }

    public AgentMcpDetail setMcpParam(String mcpParam) {
        this.mcpParam = mcpParam;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentMcpDetail {\n");

        sb.append("    mcpId: ").append(toIndentedString(mcpId)).append("\n");
        sb.append("    mcpParam: ").append(toIndentedString(mcpParam)).append("\n");
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
        AgentMcpDetail agentMcpDetail = (AgentMcpDetail) o;
        return Objects.equals(this.mcpId, agentMcpDetail.mcpId) && Objects.equals(this.mcpParam,
            agentMcpDetail.mcpParam);
    }

    @Override
    public int hashCode() {
        return Objects.hash(mcpId, mcpParam);
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
