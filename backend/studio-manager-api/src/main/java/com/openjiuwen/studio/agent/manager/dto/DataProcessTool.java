/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 数据处理 工具信息
 */
@ApiModel(description = "数据处理 工具信息")

@Validated

public class DataProcessTool implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "工具名称", example = "text_splitter")
    private String name = null;

    @JsonProperty("title")
    @Schema(description = "工具标题", example = "文本分割器")
    private String title = null;

    @JsonProperty("description")
    @Schema(description = "工具描述", example = "将长文本按规则切分为小块")
    private String description = null;

    @JsonProperty("task_operators")
    @Schema(description = "任务操作符", example = "{\"operator\":\"split\"}")
    @Valid
    private DataProcessToolTaskOperators taskOperators = null;

    @JsonProperty("inputSchema")
    @Schema(description = "输入Schema", example = "{\"type\":\"object\"}")
    @Valid
    private Object inputSchema = null;

    @JsonProperty("outputSchema")
    @Schema(description = "输出Schema", example = "{\"type\":\"array\"}")
    @Valid
    private Object outputSchema = null;

    public String getName() {
        return name;
    }

    public DataProcessTool setName(String name) {
        this.name = name;
        return this;
    }

    public String getTitle() {
        return title;
    }

    public DataProcessTool setTitle(String title) {
        this.title = title;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public DataProcessTool setDescription(String description) {
        this.description = description;
        return this;
    }

    public DataProcessToolTaskOperators getTaskOperators() {
        return taskOperators;
    }

    public DataProcessTool setTaskOperators(DataProcessToolTaskOperators taskOperators) {
        this.taskOperators = taskOperators;
        return this;
    }

    public Object getInputSchema() {
        return inputSchema;
    }

    public DataProcessTool setInputSchema(Object inputSchema) {
        this.inputSchema = inputSchema;
        return this;
    }

    public Object getOutputSchema() {
        return outputSchema;
    }

    public DataProcessTool setOutputSchema(Object outputSchema) {
        this.outputSchema = outputSchema;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DataProcessTool {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    title: ").append(toIndentedString(title)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    taskOperators: ").append(toIndentedString(taskOperators)).append("\n");
        sb.append("    inputSchema: ").append(toIndentedString(inputSchema)).append("\n");
        sb.append("    outputSchema: ").append(toIndentedString(outputSchema)).append("\n");
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
        DataProcessTool dataProcessTool = (DataProcessTool) o;
        return Objects.equals(this.name, dataProcessTool.name) && Objects.equals(this.title, dataProcessTool.title)
            && Objects.equals(this.description, dataProcessTool.description) && Objects.equals(this.taskOperators,
            dataProcessTool.taskOperators) && Objects.equals(this.inputSchema, dataProcessTool.inputSchema)
            && Objects.equals(this.outputSchema, dataProcessTool.outputSchema);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, title, description, taskOperators, inputSchema, outputSchema);
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
