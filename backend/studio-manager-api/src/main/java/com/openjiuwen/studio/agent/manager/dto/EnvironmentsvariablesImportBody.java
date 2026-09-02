/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.core.io.Resource;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * EnvironmentsvariablesImportBody
 */

@Validated

public class EnvironmentsvariablesImportBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("environment_id")
    @Schema(description = "环境ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String environmentId = null;

    @JsonProperty("cover_variables")
    @Schema(description = "变量列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<@Length() String> coverVariables = new ArrayList<String>();

    @JsonProperty("file")
    @Schema(description = "文件", example = "file-content")
    private Resource file = null;

    public String getEnvironmentId() {
        return environmentId;
    }

    public EnvironmentsvariablesImportBody setEnvironmentId(String environmentId) {
        this.environmentId = environmentId;
        return this;
    }

    public List<String> getCoverVariables() {
        return coverVariables;
    }

    public EnvironmentsvariablesImportBody setCoverVariables(List<String> coverVariables) {
        this.coverVariables = coverVariables;
        return this;
    }

    public Resource getFile() {
        return file;
    }

    public EnvironmentsvariablesImportBody setFile(Resource file) {
        this.file = file;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentsvariablesImportBody {\n");

        sb.append("    environmentId: ").append(toIndentedString(environmentId)).append("\n");
        sb.append("    coverVariables: ").append(toIndentedString(coverVariables)).append("\n");
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
        EnvironmentsvariablesImportBody environmentsvariablesImportBody = (EnvironmentsvariablesImportBody) o;
        return Objects.equals(this.environmentId, environmentsvariablesImportBody.environmentId) && Objects.equals(
            this.coverVariables, environmentsvariablesImportBody.coverVariables) && Objects.equals(this.file,
            environmentsvariablesImportBody.file);
    }

    @Override
    public int hashCode() {
        return Objects.hash(environmentId, coverVariables, file);
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
