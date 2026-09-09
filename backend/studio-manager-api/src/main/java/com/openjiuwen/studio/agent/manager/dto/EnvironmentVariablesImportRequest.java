/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 环境变量导入参数
 */
@ApiModel(description = "环境变量导入参数")

@Validated

public class EnvironmentVariablesImportRequest implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("environment_id")
    @Schema(description = "环境ID", example = "example-id-123")
    @Length(max = 100)
    private String environmentId = null;

    @JsonProperty("is_cover")
    @Schema(description = "iscover", example = "[]")
    @Valid
    @Size()
    private List<@Length(max = 100) String> isCover = null;

    public String getEnvironmentId() {
        return environmentId;
    }

    public EnvironmentVariablesImportRequest setEnvironmentId(String environmentId) {
        this.environmentId = environmentId;
        return this;
    }

    public List<String> getIsCover() {
        return isCover;
    }

    public EnvironmentVariablesImportRequest setIsCover(List<String> isCover) {
        this.isCover = isCover;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentVariablesImportRequest {\n");

        sb.append("    environmentId: ").append(toIndentedString(environmentId)).append("\n");
        sb.append("    isCover: ").append(toIndentedString(isCover)).append("\n");
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
        EnvironmentVariablesImportRequest environmentVariablesImportRequest = (EnvironmentVariablesImportRequest) o;
        return Objects.equals(this.environmentId, environmentVariablesImportRequest.environmentId) && Objects.equals(
            this.isCover, environmentVariablesImportRequest.isCover);
    }

    @Override
    public int hashCode() {
        return Objects.hash(environmentId, isCover);
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
