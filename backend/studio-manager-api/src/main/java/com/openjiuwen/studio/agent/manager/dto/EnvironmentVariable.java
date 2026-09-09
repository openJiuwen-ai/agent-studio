/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 环境变量
 */
@ApiModel(description = "环境变量")

@Validated

public class EnvironmentVariable implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[a-zA-Z_$][a-zA-Z0-9_$]{0,63}$")
    private String name = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "{}")
    @Valid
    private EnvironmentVariableValue value = null;

    public String getName() {
        return name;
    }

    public EnvironmentVariable setName(String name) {
        this.name = name;
        return this;
    }

    public EnvironmentVariableValue getValue() {
        return value;
    }

    public EnvironmentVariable setValue(EnvironmentVariableValue value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder builder = new StringBuilder();
        builder.append("class EnvironmentVariable {\n");

        builder.append("    name: ").append(toIndentedString(name)).append("\n");
        builder.append("    value: ").append(toIndentedString(value)).append("\n");
        builder.append("}");
        return builder.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        EnvironmentVariable environmentVariable = (EnvironmentVariable) obj;
        return Objects.equals(this.name, environmentVariable.name) && Objects.equals(this.value,
            environmentVariable.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, value);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}
