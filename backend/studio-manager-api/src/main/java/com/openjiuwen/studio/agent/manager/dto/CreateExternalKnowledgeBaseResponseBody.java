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
 * 接入第三方知识库的响应消息
 */
@ApiModel(description = "接入第三方知识库的响应消息")

@Validated

public class CreateExternalKnowledgeBaseResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_results")
    @Schema(description = "知识库", example = "[]")
    @Valid
    @Size(max = 100)
    private List<CreateExternalKnowledgeResult> knowledgeBaseResults = null;

    public List<CreateExternalKnowledgeResult> getKnowledgeBaseResults() {
        return knowledgeBaseResults;
    }

    public CreateExternalKnowledgeBaseResponseBody setKnowledgeBaseResults(
        List<CreateExternalKnowledgeResult> knowledgeBaseResults) {
        this.knowledgeBaseResults = knowledgeBaseResults;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateExternalKnowledgeBaseResponseBody {\n");

        sb.append("    knowledgeBaseResults: ").append(toIndentedString(knowledgeBaseResults)).append("\n");
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
        CreateExternalKnowledgeBaseResponseBody createExternalKnowledgeBaseResponseBody
            = (CreateExternalKnowledgeBaseResponseBody) o;
        return Objects.equals(this.knowledgeBaseResults, createExternalKnowledgeBaseResponseBody.knowledgeBaseResults);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeBaseResults);
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
