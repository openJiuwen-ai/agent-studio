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
 * CreateToolOpenAPIResponseBody
 */

@Validated

public class CreateToolOpenAPIResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_id")
    @Schema(description = "工具ID", example = "example-id-123")
    private String toolId = null;

    public String getToolId() {
        return toolId;
    }

    public CreateToolOpenAPIResponseBody setToolId(String toolId) {
        this.toolId = toolId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateToolOpenAPIResponseBody {\n");

        sb.append("    toolId: ").append(toIndentedString(toolId)).append("\n");
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
        CreateToolOpenAPIResponseBody createToolOpenAPIResponseBody = (CreateToolOpenAPIResponseBody) o;
        return Objects.equals(this.toolId, createToolOpenAPIResponseBody.toolId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolId);
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
