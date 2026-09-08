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
 * mcp 服务工具
 */
@ApiModel(description = "mcp 服务工具")

@Validated

public class McpServerTool implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "工具名称", example = "search-tool")
    private String name = null;

    @JsonProperty("desc")
    @Schema(description = "工具描述", example = "搜索工具")
    private String desc = null;

    @JsonProperty("input")
    @Schema(description = "输入参数", example = "{}")
    private String input = null;

    @JsonProperty("output")
    @Schema(description = "输出参数", example = "{}")
    private String output = null;

    @JsonProperty("params_count")
    @Schema(description = "参数数量", example = "3")
    private Integer paramsCount = 0;

    public String getName() {
        return name;
    }

    public McpServerTool setName(String name) {
        this.name = name;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public McpServerTool setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getInput() {
        return input;
    }

    public McpServerTool setInput(String input) {
        this.input = input;
        return this;
    }

    public String getOutput() {
        return output;
    }

    public McpServerTool setOutput(String output) {
        this.output = output;
        return this;
    }

    public Integer getParamsCount() {
        return paramsCount;
    }

    public McpServerTool setParamsCount(Integer paramsCount) {
        this.paramsCount = paramsCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerTool {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    input: ").append(toIndentedString(input)).append("\n");
        sb.append("    output: ").append(toIndentedString(output)).append("\n");
        sb.append("    paramsCount: ").append(toIndentedString(paramsCount)).append("\n");
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
        McpServerTool mcpServerTool = (McpServerTool) o;
        return Objects.equals(this.name, mcpServerTool.name) && Objects.equals(this.desc, mcpServerTool.desc)
            && Objects.equals(this.input, mcpServerTool.input) && Objects.equals(this.output, mcpServerTool.output)
            && Objects.equals(this.paramsCount, mcpServerTool.paramsCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, desc, input, output, paramsCount);
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
