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
 * 工具详情。
 */
@ApiModel(description = "工具详情。")

@Validated

public class AgentToolDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_id")
    @Schema(description = "工具ID", example = "tool_001")
    private String toolId = null;

    @JsonProperty("tool_version")
    @Schema(description = "工具版本", example = "v1.0.0")
    private String toolVersion = null;

    @JsonProperty("tool_param")
    @Schema(description = "工具参数", example = "{\"key\":\"value\"}")
    private String toolParam = null;

    public String getToolId() {
        return toolId;
    }

    public AgentToolDetail setToolId(String toolId) {
        this.toolId = toolId;
        return this;
    }

    public String getToolVersion() {
        return toolVersion;
    }

    public AgentToolDetail setToolVersion(String toolVersion) {
        this.toolVersion = toolVersion;
        return this;
    }

    public String getToolParam() {
        return toolParam;
    }

    public AgentToolDetail setToolParam(String toolParam) {
        this.toolParam = toolParam;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentToolDetail {\n");

        sb.append("    toolId: ").append(toIndentedString(toolId)).append("\n");
        sb.append("    toolVersion: ").append(toIndentedString(toolVersion)).append("\n");
        sb.append("    toolParam: ").append(toIndentedString(toolParam)).append("\n");
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
        AgentToolDetail agentToolDetail = (AgentToolDetail) o;
        return Objects.equals(this.toolId, agentToolDetail.toolId) && Objects.equals(this.toolVersion,
            agentToolDetail.toolVersion) && Objects.equals(this.toolParam, agentToolDetail.toolParam);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolId, toolVersion, toolParam);
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
