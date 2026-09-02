/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * KnowledgeBaseObsConfigExecuteRecordsQo: converted from multi query params
 */
@ApiModel(description = "KnowledgeBaseObsConfigExecuteRecordsQo: converted from multi query params")

@Validated

public class KnowledgeBaseObsConfigExecuteRecordsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @NotBlank
    private String workspaceId = null;

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

    public KnowledgeBaseObsConfigExecuteRecordsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public KnowledgeBaseObsConfigExecuteRecordsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public KnowledgeBaseObsConfigExecuteRecordsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseObsConfigExecuteRecordsQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        KnowledgeBaseObsConfigExecuteRecordsQo knowledgeBaseObsConfigExecuteRecordsQo
            = (KnowledgeBaseObsConfigExecuteRecordsQo) o;
        return Objects.equals(this.workspaceId, knowledgeBaseObsConfigExecuteRecordsQo.workspaceId) && Objects.equals(
            this.offset, knowledgeBaseObsConfigExecuteRecordsQo.offset) && Objects.equals(this.limit,
            knowledgeBaseObsConfigExecuteRecordsQo.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit);
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
