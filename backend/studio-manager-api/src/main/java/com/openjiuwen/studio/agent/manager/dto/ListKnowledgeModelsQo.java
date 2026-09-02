/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListKnowledgeModelsQo: converted from multi query params
 */
@ApiModel(description = "ListKnowledgeModelsQo: converted from multi query params")

@Validated

public class ListKnowledgeModelsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "embedding-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String modelName = null;

    @JsonProperty("repo_id")
    @Schema(description = "知识库ID", example = "repo-001")
    @Length(min = 1, max = 64)
    private String repoId = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "embedding")
    @Length(min = 1, max = 64)
    private String modelType = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListKnowledgeModelsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public ListKnowledgeModelsQo setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getRepoId() {
        return repoId;
    }

    public ListKnowledgeModelsQo setRepoId(String repoId) {
        this.repoId = repoId;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public ListKnowledgeModelsQo setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListKnowledgeModelsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListKnowledgeModelsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeModelsQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    repoId: ").append(toIndentedString(repoId)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
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
        ListKnowledgeModelsQo listKnowledgeModelsQo = (ListKnowledgeModelsQo) o;
        return Objects.equals(this.workspaceId, listKnowledgeModelsQo.workspaceId) && Objects.equals(this.modelName,
            listKnowledgeModelsQo.modelName) && Objects.equals(this.repoId, listKnowledgeModelsQo.repoId)
            && Objects.equals(this.modelType, listKnowledgeModelsQo.modelType) && Objects.equals(this.offset,
            listKnowledgeModelsQo.offset) && Objects.equals(this.limit, listKnowledgeModelsQo.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, modelName, repoId, modelType, offset, limit);
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
