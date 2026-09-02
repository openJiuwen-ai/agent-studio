/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 第三方知识库基本信息
 */
@ApiModel(description = "第三方知识库基本信息")

@Validated

public class ExternalKnowledgeItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_id")
    @Schema(description = "知识库ID", example = "kb-001")
    @Length(max = 100)
    private String knowledgeBaseId = null;

    @JsonProperty("knowledge_base_name")
    @Schema(description = "知识库名称", example = "外部知识库")
    @Length(max = 1000)
    private String knowledgeBaseName = null;

    @JsonProperty("description")
    @Schema(description = "知识库描述", example = "外部知识库描述")
    @Length(max = 1000)
    private String description = null;

    @JsonProperty("present")
    @Schema(description = "是否存在", example = "true")
    private Boolean present = null;

    public String getKnowledgeBaseId() {
        return knowledgeBaseId;
    }

    public ExternalKnowledgeItem setKnowledgeBaseId(String knowledgeBaseId) {
        this.knowledgeBaseId = knowledgeBaseId;
        return this;
    }

    public String getKnowledgeBaseName() {
        return knowledgeBaseName;
    }

    public ExternalKnowledgeItem setKnowledgeBaseName(String knowledgeBaseName) {
        this.knowledgeBaseName = knowledgeBaseName;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ExternalKnowledgeItem setDescription(String description) {
        this.description = description;
        return this;
    }

    public ExternalKnowledgeItem setPresent(Boolean present) {
        this.present = present;
        return this;
    }

    public Boolean isPresent() {
        return present;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExternalKnowledgeItem {\n");

        sb.append("    knowledgeBaseId: ").append(toIndentedString(knowledgeBaseId)).append("\n");
        sb.append("    knowledgeBaseName: ").append(toIndentedString(knowledgeBaseName)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    present: ").append(toIndentedString(present)).append("\n");
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
        ExternalKnowledgeItem externalKnowledgeItem = (ExternalKnowledgeItem) o;
        return Objects.equals(this.knowledgeBaseId, externalKnowledgeItem.knowledgeBaseId) && Objects.equals(
            this.knowledgeBaseName, externalKnowledgeItem.knowledgeBaseName) && Objects.equals(this.description,
            externalKnowledgeItem.description) && Objects.equals(this.present, externalKnowledgeItem.present);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeBaseId, knowledgeBaseName, description, present);
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
