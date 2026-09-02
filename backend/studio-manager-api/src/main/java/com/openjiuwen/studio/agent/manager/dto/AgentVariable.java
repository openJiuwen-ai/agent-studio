/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 智能体中的变量定义。
 */
@ApiModel(description = "智能体中的变量定义。")

@Validated

public class AgentVariable implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("variable_key")
    @Schema(description = "变量键名", example = "user_name")
    @Pattern(regexp = "^[^\\^]*$")
    @Length(max = 100)
    private String variableKey = null;

    @JsonProperty("description")
    @Schema(description = "变量描述", example = "用户名称")
    @Length(max = 200)
    private String description = null;

    @JsonProperty("default_value")
    @Schema(description = "变量默认值", example = "张三")
    @Length(max = 100)
    private String defaultValue = null;

    public String getVariableKey() {
        return variableKey;
    }

    public AgentVariable setVariableKey(String variableKey) {
        this.variableKey = variableKey;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public AgentVariable setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDefaultValue() {
        return defaultValue;
    }

    public AgentVariable setDefaultValue(String defaultValue) {
        this.defaultValue = defaultValue;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentVariable {\n");

        sb.append("    variableKey: ").append(toIndentedString(variableKey)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    defaultValue: ").append(toIndentedString(defaultValue)).append("\n");
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
        AgentVariable agentVariable = (AgentVariable) o;
        return Objects.equals(this.variableKey, agentVariable.variableKey) && Objects.equals(this.description,
            agentVariable.description) && Objects.equals(this.defaultValue, agentVariable.defaultValue);
    }

    @Override
    public int hashCode() {
        return Objects.hash(variableKey, description, defaultValue);
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
