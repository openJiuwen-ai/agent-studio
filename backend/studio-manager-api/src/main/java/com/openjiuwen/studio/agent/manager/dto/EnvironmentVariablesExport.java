/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 环境变量导出参数
 */
@ApiModel(description = "环境变量导出参数")

@Validated

public class EnvironmentVariablesExport implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("environment_id")
    @Schema(description = "环境ID", example = "[]")
    @Valid
    @Size(max = 50)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(max = 100) String> environmentId = null;

    public List<String> getEnvironmentId() {
        return environmentId;
    }

    public EnvironmentVariablesExport setEnvironmentId(List<String> environmentId) {
        this.environmentId = environmentId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentVariablesExport {\n");

        sb.append("    environmentId: ").append(toIndentedString(environmentId)).append("\n");
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
        EnvironmentVariablesExport environmentVariablesExport = (EnvironmentVariablesExport) o;
        return Objects.equals(this.environmentId, environmentVariablesExport.environmentId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(environmentId);
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
