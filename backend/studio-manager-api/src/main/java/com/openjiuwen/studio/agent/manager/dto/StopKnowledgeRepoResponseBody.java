/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 停用知识库响应体
 */
@ApiModel(description = "停用知识库响应体")

@Validated

public class StopKnowledgeRepoResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String id = null;

    public String getId() {
        return id;
    }

    public StopKnowledgeRepoResponseBody setId(String id) {
        this.id = id;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class StopKnowledgeRepoResponseBody {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
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
        StopKnowledgeRepoResponseBody stopKnowledgeRepoResponseBody = (StopKnowledgeRepoResponseBody) o;
        return Objects.equals(this.id, stopKnowledgeRepoResponseBody.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
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
