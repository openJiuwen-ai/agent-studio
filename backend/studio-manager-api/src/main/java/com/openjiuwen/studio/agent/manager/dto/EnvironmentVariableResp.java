/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 环境变量
 */
@ApiModel(description = "环境变量")

@Validated

public class EnvironmentVariableResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "环境变量ID", example = "env-001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "环境变量名称", example = "env-config")
    private String name = null;

    @JsonProperty("envDescription")
    @Schema(description = "环境描述", example = "环境变量配置")
    private String envDescription = null;

    @JsonProperty("variables")
    @Schema(description = "环境变量列表", example = "[]")
    @Valid
    @Size()
    private List<EnvironmentVariable> variables = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "5")
    private Integer count = null;

    public String getId() {
        return id;
    }

    public EnvironmentVariableResp setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public EnvironmentVariableResp setName(String name) {
        this.name = name;
        return this;
    }

    public String getEnvDescription() {
        return envDescription;
    }

    public EnvironmentVariableResp setEnvDescription(String envDescription) {
        this.envDescription = envDescription;
        return this;
    }

    public List<EnvironmentVariable> getVariables() {
        return variables;
    }

    public EnvironmentVariableResp setVariables(List<EnvironmentVariable> variables) {
        this.variables = variables;
        return this;
    }

    public Integer getCount() {
        return count;
    }

    public EnvironmentVariableResp setCount(Integer count) {
        this.count = count;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentVariableResp {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    envDescription: ").append(toIndentedString(envDescription)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
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
        EnvironmentVariableResp environmentVariableResp = (EnvironmentVariableResp) o;
        return Objects.equals(this.id, environmentVariableResp.id) && Objects.equals(this.name,
            environmentVariableResp.name) && Objects.equals(this.envDescription, environmentVariableResp.envDescription)
            && Objects.equals(this.variables, environmentVariableResp.variables) && Objects.equals(this.count,
            environmentVariableResp.count);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, envDescription, variables, count);
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
