/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.core.io.Resource;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * EnvironmentsvariablesImportvalidationBody
 */

@Validated

public class EnvironmentsvariablesImportvalidationBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("environment_id")
    @Schema(description = "环境ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String environmentId = null;

    @JsonProperty("file")
    @Schema(description = "文件", example = "file-content")
    private Resource file = null;

    public String getEnvironmentId() {
        return environmentId;
    }

    public EnvironmentsvariablesImportvalidationBody setEnvironmentId(String environmentId) {
        this.environmentId = environmentId;
        return this;
    }

    public Resource getFile() {
        return file;
    }

    public EnvironmentsvariablesImportvalidationBody setFile(Resource file) {
        this.file = file;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentsvariablesImportvalidationBody {\n");

        sb.append("    environmentId: ").append(toIndentedString(environmentId)).append("\n");
        sb.append("    file: ").append(toIndentedString(file)).append("\n");
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
        EnvironmentsvariablesImportvalidationBody environmentsvariablesImportvalidationBody
            = (EnvironmentsvariablesImportvalidationBody) o;
        return Objects.equals(this.environmentId, environmentsvariablesImportvalidationBody.environmentId)
            && Objects.equals(this.file, environmentsvariablesImportvalidationBody.file);
    }

    @Override
    public int hashCode() {
        return Objects.hash(environmentId, file);
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
