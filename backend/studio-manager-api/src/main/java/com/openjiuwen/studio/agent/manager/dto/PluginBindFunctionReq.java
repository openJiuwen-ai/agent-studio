/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 修改工具请求体
 */
@ApiModel(description = "修改工具请求体")

@Validated

public class PluginBindFunctionReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("function_id")
    @Schema(description = "函数ID", example = "func_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String functionId = null;

    @JsonProperty("tool_id")
    @Schema(description = "工具ID", example = "tool_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String toolId = null;

    @JsonProperty("function_input")
    @Schema(description = "函数输入", example = "{\"key\":\"value\"}")
    @Valid
    private Object functionInput = null;

    @JsonProperty("function_output")
    @Schema(description = "函数输出", example = "{\"result\":\"success\"}")
    @Valid
    private Object functionOutput = null;

    public String getFunctionId() {
        return functionId;
    }

    public PluginBindFunctionReq setFunctionId(String functionId) {
        this.functionId = functionId;
        return this;
    }

    public String getToolId() {
        return toolId;
    }

    public PluginBindFunctionReq setToolId(String toolId) {
        this.toolId = toolId;
        return this;
    }

    public Object getFunctionInput() {
        return functionInput;
    }

    public PluginBindFunctionReq setFunctionInput(Object functionInput) {
        this.functionInput = functionInput;
        return this;
    }

    public Object getFunctionOutput() {
        return functionOutput;
    }

    public PluginBindFunctionReq setFunctionOutput(Object functionOutput) {
        this.functionOutput = functionOutput;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PluginBindFunctionReq {\n");

        sb.append("    functionId: ").append(toIndentedString(functionId)).append("\n");
        sb.append("    toolId: ").append(toIndentedString(toolId)).append("\n");
        sb.append("    functionInput: ").append(toIndentedString(functionInput)).append("\n");
        sb.append("    functionOutput: ").append(toIndentedString(functionOutput)).append("\n");
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
        PluginBindFunctionReq pluginBindFunctionReq = (PluginBindFunctionReq) o;
        return Objects.equals(this.functionId, pluginBindFunctionReq.functionId) && Objects.equals(this.toolId,
            pluginBindFunctionReq.toolId) && Objects.equals(this.functionInput, pluginBindFunctionReq.functionInput)
            && Objects.equals(this.functionOutput, pluginBindFunctionReq.functionOutput);
    }

    @Override
    public int hashCode() {
        return Objects.hash(functionId, toolId, functionInput, functionOutput);
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
