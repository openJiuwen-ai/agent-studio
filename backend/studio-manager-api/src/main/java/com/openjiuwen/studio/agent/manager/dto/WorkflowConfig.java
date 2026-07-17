/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流参数格式信息
 */
@ApiModel(description = "工作流参数格式信息")

@Validated

public class WorkflowConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @NotBlank
    @Length(max = 64)
    private String type = null;

    @JsonProperty("name")
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Length(max = 64)
    private String description = null;

    @JsonProperty("value")
    @Valid
    private Object value = null;

    @JsonProperty("required")
    private Boolean required = null;

    @JsonProperty("front")
    @Length(max = 64)
    private String front = null;

    @JsonProperty("hint")
    @Length(max = 64)
    private String hint = null;

    public String getType() {
        return type;
    }

    public WorkflowConfig setType(String type) {
        this.type = type;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkflowConfig setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowConfig setDescription(String description) {
        this.description = description;
        return this;
    }

    public Object getValue() {
        return value;
    }

    public WorkflowConfig setValue(Object value) {
        this.value = value;
        return this;
    }

    public WorkflowConfig setRequired(Boolean required) {
        this.required = required;
        return this;
    }

    public Boolean isRequired() {
        return required;
    }

    public String getFront() {
        return front;
    }

    public WorkflowConfig setFront(String front) {
        this.front = front;
        return this;
    }

    public String getHint() {
        return hint;
    }

    public WorkflowConfig setHint(String hint) {
        this.hint = hint;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowConfig {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
        sb.append("    required: ").append(toIndentedString(required)).append("\n");
        sb.append("    front: ").append(toIndentedString(front)).append("\n");
        sb.append("    hint: ").append(toIndentedString(hint)).append("\n");
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
        WorkflowConfig workflowConfig = (WorkflowConfig) o;
        return Objects.equals(this.type, workflowConfig.type) && Objects.equals(this.name, workflowConfig.name)
            && Objects.equals(this.description, workflowConfig.description) && Objects.equals(this.value,
            workflowConfig.value) && Objects.equals(this.required, workflowConfig.required) && Objects.equals(
            this.front, workflowConfig.front) && Objects.equals(this.hint, workflowConfig.hint);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, name, description, value, required, front, hint);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
