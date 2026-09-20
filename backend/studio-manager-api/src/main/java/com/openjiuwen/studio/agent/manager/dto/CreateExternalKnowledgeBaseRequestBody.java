/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 接入的第三方知识库
 */
@ApiModel(description = "接入的第三方知识库")

@Validated

public class CreateExternalKnowledgeBaseRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_connection_id")
    @Schema(description = "知识库", example = "example-id-123", required = true)
    @NotBlank
    @Length(max = 100)
    private String knowledgeBaseConnectionId = null;

    @JsonProperty("knowledge_base_external_ids")
    @Schema(description = "知识库", example = "[]")
    @Valid
    @Size(min = 1, max = 100)
    private List<@Length(min = 1, max = 100) String> knowledgeBaseExternalIds = null;

    public String getKnowledgeBaseConnectionId() {
        return knowledgeBaseConnectionId;
    }

    public CreateExternalKnowledgeBaseRequestBody setKnowledgeBaseConnectionId(String knowledgeBaseConnectionId) {
        this.knowledgeBaseConnectionId = knowledgeBaseConnectionId;
        return this;
    }

    public List<String> getKnowledgeBaseExternalIds() {
        return knowledgeBaseExternalIds;
    }

    public CreateExternalKnowledgeBaseRequestBody setKnowledgeBaseExternalIds(List<String> knowledgeBaseExternalIds) {
        this.knowledgeBaseExternalIds = knowledgeBaseExternalIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateExternalKnowledgeBaseRequestBody {\n");

        sb.append("    knowledgeBaseConnectionId: ").append(toIndentedString(knowledgeBaseConnectionId)).append("\n");
        sb.append("    knowledgeBaseExternalIds: ").append(toIndentedString(knowledgeBaseExternalIds)).append("\n");
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
        CreateExternalKnowledgeBaseRequestBody createExternalKnowledgeBaseRequestBody
            = (CreateExternalKnowledgeBaseRequestBody) o;
        return Objects.equals(this.knowledgeBaseConnectionId,
            createExternalKnowledgeBaseRequestBody.knowledgeBaseConnectionId) && Objects.equals(
            this.knowledgeBaseExternalIds, createExternalKnowledgeBaseRequestBody.knowledgeBaseExternalIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeBaseConnectionId, knowledgeBaseExternalIds);
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
