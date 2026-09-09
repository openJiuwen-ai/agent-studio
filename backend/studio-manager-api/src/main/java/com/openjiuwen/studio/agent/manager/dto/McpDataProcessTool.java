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
import java.math.BigDecimal;
import java.util.List;
import java.util.Objects;

/**
 * 数据处理 工具信息
 */
@ApiModel(description = "数据处理 工具信息")

@Validated

public class McpDataProcessTool implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1.0")
    private BigDecimal count = null;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "[]")
    @Valid
    @Size()
    private List<DataProcessTool> tools = null;

    public BigDecimal getCount() {
        return count;
    }

    public McpDataProcessTool setCount(BigDecimal count) {
        this.count = count;
        return this;
    }

    public List<DataProcessTool> getTools() {
        return tools;
    }

    public McpDataProcessTool setTools(List<DataProcessTool> tools) {
        this.tools = tools;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpDataProcessTool {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
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
        McpDataProcessTool mcpDataProcessTool = (McpDataProcessTool) o;
        return Objects.equals(this.count, mcpDataProcessTool.count) && Objects.equals(this.tools,
            mcpDataProcessTool.tools);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, tools);
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
