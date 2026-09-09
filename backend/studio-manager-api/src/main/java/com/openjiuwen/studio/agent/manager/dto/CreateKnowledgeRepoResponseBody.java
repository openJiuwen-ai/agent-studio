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
 * 创建知识库响应体
 */
@ApiModel(description = "创建知识库响应体")

@Validated

public class CreateKnowledgeRepoResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_repo_id")
    @Schema(description = "知识仓ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String knowledgeRepoId = null;

    public String getKnowledgeRepoId() {
        return knowledgeRepoId;
    }

    public CreateKnowledgeRepoResponseBody setKnowledgeRepoId(String knowledgeRepoId) {
        this.knowledgeRepoId = knowledgeRepoId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateKnowledgeRepoResponseBody {\n");

        sb.append("    knowledgeRepoId: ").append(toIndentedString(knowledgeRepoId)).append("\n");
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
        CreateKnowledgeRepoResponseBody createKnowledgeRepoResponseBody = (CreateKnowledgeRepoResponseBody) o;
        return Objects.equals(this.knowledgeRepoId, createKnowledgeRepoResponseBody.knowledgeRepoId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeRepoId);
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
