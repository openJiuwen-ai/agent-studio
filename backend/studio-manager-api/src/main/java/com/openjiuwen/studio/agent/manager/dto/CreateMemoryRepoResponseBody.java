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
 * 创建记忆库响应体
 */
@ApiModel(description = "创建记忆库响应体")

@Validated

public class CreateMemoryRepoResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("memory_repo_id")
    @Schema(description = "记忆仓ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String memoryRepoId = null;

    public String getMemoryRepoId() {
        return memoryRepoId;
    }

    public CreateMemoryRepoResponseBody setMemoryRepoId(String memoryRepoId) {
        this.memoryRepoId = memoryRepoId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateMemoryRepoResponseBody {\n");

        sb.append("    memoryRepoId: ").append(toIndentedString(memoryRepoId)).append("\n");
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
        CreateMemoryRepoResponseBody createMemoryRepoResponseBody = (CreateMemoryRepoResponseBody) o;
        return Objects.equals(this.memoryRepoId, createMemoryRepoResponseBody.memoryRepoId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memoryRepoId);
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
