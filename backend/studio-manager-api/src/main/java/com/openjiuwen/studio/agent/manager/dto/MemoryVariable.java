/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 记忆变量参数。
 */
@ApiModel(description = "记忆变量参数。")

@Validated

public class MemoryVariable implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "记忆变量名称", example = "user_preference", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "记忆变量描述", example = "用户偏好设置")
    private String description = null;

    @JsonProperty("default_value")
    @Schema(description = "记忆变量默认值", example = "dark_mode")
    private String defaultValue = null;

    @JsonProperty("life_cycle")
    @Schema(description = "记忆变量生命周期", example = "session", required = true)
    @NotBlank
    private String lifeCycle = null;

    @JsonProperty("value")
    @Schema(description = "记忆变量当前值", example = "dark_mode")
    private String value = null;

    @JsonProperty("updated_on")
    @Schema(description = "最后更新时间戳", example = "1693526400000")
    private Long updatedOn = null;

    public String getName() {
        return name;
    }

    public MemoryVariable setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public MemoryVariable setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDefaultValue() {
        return defaultValue;
    }

    public MemoryVariable setDefaultValue(String defaultValue) {
        this.defaultValue = defaultValue;
        return this;
    }

    public String getLifeCycle() {
        return lifeCycle;
    }

    public MemoryVariable setLifeCycle(String lifeCycle) {
        this.lifeCycle = lifeCycle;
        return this;
    }

    public String getValue() {
        return value;
    }

    public MemoryVariable setValue(String value) {
        this.value = value;
        return this;
    }

    public Long getUpdatedOn() {
        return updatedOn;
    }

    public MemoryVariable setUpdatedOn(Long updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemoryVariable {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    defaultValue: ").append(toIndentedString(defaultValue)).append("\n");
        sb.append("    lifeCycle: ").append(toIndentedString(lifeCycle)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
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
        MemoryVariable memoryVariable = (MemoryVariable) o;
        return Objects.equals(this.name, memoryVariable.name) && Objects.equals(this.description,
            memoryVariable.description) && Objects.equals(this.defaultValue, memoryVariable.defaultValue)
            && Objects.equals(this.lifeCycle, memoryVariable.lifeCycle) && Objects.equals(this.value,
            memoryVariable.value) && Objects.equals(this.updatedOn, memoryVariable.updatedOn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, defaultValue, lifeCycle, value, updatedOn);
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
