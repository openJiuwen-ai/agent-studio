/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListKnowledgeFilesQo: converted from multi query params
 */
@ApiModel(description = "ListKnowledgeFilesQo: converted from multi query params")

@Validated

public class ListKnowledgeFilesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 65534L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

    @JsonProperty("name")
    @Schema(description = "文件名称", example = "knowledge.pdf")
    @Length(max = 1024)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "文件类型", example = "pdf,docx")
    @Pattern(regexp = "^[a-zA-Z,]*$")
    @Length(max = 128)
    private String type = null;

    @JsonProperty("status")
    @Schema(description = "文件状态", example = "ready")
    @Length(max = 128)
    private String status = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListKnowledgeFilesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListKnowledgeFilesQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListKnowledgeFilesQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListKnowledgeFilesQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListKnowledgeFilesQo setType(String type) {
        this.type = type;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ListKnowledgeFilesQo setStatus(String status) {
        this.status = status;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeFilesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        ListKnowledgeFilesQo listKnowledgeFilesQo = (ListKnowledgeFilesQo) o;
        return Objects.equals(this.workspaceId, listKnowledgeFilesQo.workspaceId) && Objects.equals(this.offset,
            listKnowledgeFilesQo.offset) && Objects.equals(this.limit, listKnowledgeFilesQo.limit) && Objects.equals(
            this.name, listKnowledgeFilesQo.name) && Objects.equals(this.type, listKnowledgeFilesQo.type)
            && Objects.equals(this.status, listKnowledgeFilesQo.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, name, type, status);
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
