/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * WorkflowFrontParam
 */

@Validated

public class WorkflowFrontParam implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "参数名称", example = "input_param")
    @Length(max = 1000)
    private String name = null;

    @JsonProperty("front_name")
    @Schema(description = "前端展示名称", example = "输入参数")
    @Length(max = 1000)
    private String frontName = null;

    @JsonProperty("front_content")
    @Schema(description = "前端内容", example = "请输入参数值")
    @Length(max = 100000)
    private String frontContent = null;

    @JsonProperty("type")
    @Schema(description = "参数类型", example = "string")
    @Length(max = 1000)
    private String type = null;

    @JsonProperty("description")
    @Schema(description = "参数描述", example = "用户输入的参数")
    @Length(max = 100000)
    private String description = null;

    @JsonProperty("required")
    @Schema(description = "是否必填", example = "true")
    private Boolean required = null;

    @JsonProperty("source")
    @Schema(description = "参数来源", example = "user_input")
    @Length(max = 1000)
    private String source = null;

    @JsonProperty("schema")
    @Schema(description = "参数Schema定义", example = "{\"type\":\"string\"}")
    @Valid
    private Object schema = null;

    @JsonProperty("value")
    @Schema(description = "参数值", example = "hello")
    @Valid
    private Object value = null;

    public String getName() {
        return name;
    }

    public WorkflowFrontParam setName(String name) {
        this.name = name;
        return this;
    }

    public String getFrontName() {
        return frontName;
    }

    public WorkflowFrontParam setFrontName(String frontName) {
        this.frontName = frontName;
        return this;
    }

    public String getFrontContent() {
        return frontContent;
    }

    public WorkflowFrontParam setFrontContent(String frontContent) {
        this.frontContent = frontContent;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowFrontParam setType(String type) {
        this.type = type;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowFrontParam setDescription(String description) {
        this.description = description;
        return this;
    }

    public WorkflowFrontParam setRequired(Boolean required) {
        this.required = required;
        return this;
    }

    public Boolean isRequired() {
        return required;
    }

    public String getSource() {
        return source;
    }

    public WorkflowFrontParam setSource(String source) {
        this.source = source;
        return this;
    }

    public Object getSchema() {
        return schema;
    }

    public WorkflowFrontParam setSchema(Object schema) {
        this.schema = schema;
        return this;
    }

    public Object getValue() {
        return value;
    }

    public WorkflowFrontParam setValue(Object value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowFrontParam {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    frontName: ").append(toIndentedString(frontName)).append("\n");
        sb.append("    frontContent: ").append(toIndentedString(frontContent)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    required: ").append(toIndentedString(required)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    schema: ").append(toIndentedString(schema)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
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
        WorkflowFrontParam workflowFrontParam = (WorkflowFrontParam) o;
        return Objects.equals(this.name, workflowFrontParam.name) && Objects.equals(this.frontName,
            workflowFrontParam.frontName) && Objects.equals(this.frontContent, workflowFrontParam.frontContent)
            && Objects.equals(this.type, workflowFrontParam.type) && Objects.equals(this.description,
            workflowFrontParam.description) && Objects.equals(this.required, workflowFrontParam.required)
            && Objects.equals(this.source, workflowFrontParam.source) && Objects.equals(this.schema,
            workflowFrontParam.schema) && Objects.equals(this.value, workflowFrontParam.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, frontName, frontContent, type, description, required, source, schema, value);
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
