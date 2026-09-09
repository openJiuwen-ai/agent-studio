/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * WorkflowFieldVOMemory
 */

@Validated

public class WorkflowFieldVOMemory implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "字段名称", example = "userMemory", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("aging_level")
    @Schema(description = "老化级别", example = "short_term")
    private String agingLevel = null;

    @JsonProperty("storage_method")
    @Schema(description = "存储方式", example = "kv")
    private String storageMethod = null;

    @JsonProperty("default_value")
    @Schema(description = "默认值", example = "null")
    @Valid
    private Object defaultValue = null;

    @JsonProperty("description")
    @Schema(description = "字段描述", example = "用户对话记忆字段")
    private String description = null;

    @JsonProperty("value")
    @Schema(description = "字段值", example = "{\"type\":\"literal\",\"content\":\"hello\"}")
    @Valid
    private WorkflowFieldVOValue value = null;

    public String getName() {
        return name;
    }

    public WorkflowFieldVOMemory setName(String name) {
        this.name = name;
        return this;
    }

    public String getAgingLevel() {
        return agingLevel;
    }

    public WorkflowFieldVOMemory setAgingLevel(String agingLevel) {
        this.agingLevel = agingLevel;
        return this;
    }

    public String getStorageMethod() {
        return storageMethod;
    }

    public WorkflowFieldVOMemory setStorageMethod(String storageMethod) {
        this.storageMethod = storageMethod;
        return this;
    }

    public Object getDefaultValue() {
        return defaultValue;
    }

    public WorkflowFieldVOMemory setDefaultValue(Object defaultValue) {
        this.defaultValue = defaultValue;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowFieldVOMemory setDescription(String description) {
        this.description = description;
        return this;
    }

    public WorkflowFieldVOValue getValue() {
        return value;
    }

    public WorkflowFieldVOMemory setValue(WorkflowFieldVOValue value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowFieldVOMemory {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    agingLevel: ").append(toIndentedString(agingLevel)).append("\n");
        sb.append("    storageMethod: ").append(toIndentedString(storageMethod)).append("\n");
        sb.append("    defaultValue: ").append(toIndentedString(defaultValue)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        WorkflowFieldVOMemory workflowFieldVOMemory = (WorkflowFieldVOMemory) o;
        return Objects.equals(this.name, workflowFieldVOMemory.name) && Objects.equals(this.agingLevel,
            workflowFieldVOMemory.agingLevel) && Objects.equals(this.storageMethod, workflowFieldVOMemory.storageMethod)
            && Objects.equals(this.defaultValue, workflowFieldVOMemory.defaultValue) && Objects.equals(this.description,
            workflowFieldVOMemory.description) && Objects.equals(this.value, workflowFieldVOMemory.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, agingLevel, storageMethod, defaultValue, description, value);
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
