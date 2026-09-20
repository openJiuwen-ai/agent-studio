/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListExternalKnowledgeBasesQo: converted from multi query params
 */
@ApiModel(description = "ListExternalKnowledgeBasesQo: converted from multi query params")

@Validated

public class ListExternalKnowledgeBasesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws001", required = true)
    @NotBlank
    @Length(max = 100)
    private String workspaceId = null;

    @JsonProperty("knowledge_base_name")
    @Schema(description = "知识库名称", example = "产品知识库")
    @Length(max = 100)
    private String knowledgeBaseName = null;

    @JsonProperty("knowledge_base_connection_id")
    @Schema(description = "知识库连接ID", example = "conn001", required = true)
    @NotBlank
    @Length(max = 100)
    private String knowledgeBaseConnectionId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 65535L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 200L)
    private Integer limit = 10;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListExternalKnowledgeBasesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getKnowledgeBaseName() {
        return knowledgeBaseName;
    }

    public ListExternalKnowledgeBasesQo setKnowledgeBaseName(String knowledgeBaseName) {
        this.knowledgeBaseName = knowledgeBaseName;
        return this;
    }

    public String getKnowledgeBaseConnectionId() {
        return knowledgeBaseConnectionId;
    }

    public ListExternalKnowledgeBasesQo setKnowledgeBaseConnectionId(String knowledgeBaseConnectionId) {
        this.knowledgeBaseConnectionId = knowledgeBaseConnectionId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListExternalKnowledgeBasesQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListExternalKnowledgeBasesQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListExternalKnowledgeBasesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    knowledgeBaseName: ").append(toIndentedString(knowledgeBaseName)).append("\n");
        sb.append("    knowledgeBaseConnectionId: ").append(toIndentedString(knowledgeBaseConnectionId)).append("\n");
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
        ListExternalKnowledgeBasesQo listExternalKnowledgeBasesQo = (ListExternalKnowledgeBasesQo) o;
        return Objects.equals(this.workspaceId, listExternalKnowledgeBasesQo.workspaceId) && Objects.equals(
            this.knowledgeBaseName, listExternalKnowledgeBasesQo.knowledgeBaseName) && Objects.equals(
            this.knowledgeBaseConnectionId, listExternalKnowledgeBasesQo.knowledgeBaseConnectionId) && Objects.equals(
            this.offset, listExternalKnowledgeBasesQo.offset) && Objects.equals(this.limit,
            listExternalKnowledgeBasesQo.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, knowledgeBaseName, knowledgeBaseConnectionId, offset, limit);
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
