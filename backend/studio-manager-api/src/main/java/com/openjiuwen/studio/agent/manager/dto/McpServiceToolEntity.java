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
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceToolEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "工具名称", example = "search-tool")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "工具描述", example = "搜索工具")
    private String description = null;

    @JsonProperty("input")
    @Schema(description = "输入参数", example = "{}")
    private String input = null;

    @JsonProperty("output")
    @Schema(description = "输出参数", example = "{}")
    private String output = null;

    @JsonProperty("config")
    @Schema(description = "配置信息", example = "{}")
    private String config = null;

    public String getName() {
        return name;
    }

    public McpServiceToolEntity setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServiceToolEntity setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getInput() {
        return input;
    }

    public McpServiceToolEntity setInput(String input) {
        this.input = input;
        return this;
    }

    public String getOutput() {
        return output;
    }

    public McpServiceToolEntity setOutput(String output) {
        this.output = output;
        return this;
    }

    public String getConfig() {
        return config;
    }

    public McpServiceToolEntity setConfig(String config) {
        this.config = config;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceToolEntity {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    input: ").append(toIndentedString(input)).append("\n");
        sb.append("    output: ").append(toIndentedString(output)).append("\n");
        sb.append("    config: ").append(toIndentedString(config)).append("\n");
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
        McpServiceToolEntity mcpServiceToolEntity = (McpServiceToolEntity) o;
        return Objects.equals(this.name, mcpServiceToolEntity.name) && Objects.equals(this.description,
            mcpServiceToolEntity.description) && Objects.equals(this.input, mcpServiceToolEntity.input)
            && Objects.equals(this.output, mcpServiceToolEntity.output) && Objects.equals(this.config,
            mcpServiceToolEntity.config);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, input, output, config);
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
