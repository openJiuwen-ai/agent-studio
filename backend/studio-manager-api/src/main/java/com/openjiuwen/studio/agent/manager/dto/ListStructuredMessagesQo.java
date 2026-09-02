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
 * ListStructuredMessagesQo: converted from multi query params
 */
@ApiModel(description = "ListStructuredMessagesQo: converted from multi query params")

@Validated

public class ListStructuredMessagesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 100000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "1000")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 1000;

    @JsonProperty("sort")
    @Schema(description = "排序方式", example = "desc")
    @Length(max = 5)
    private String sort = "desc";

    @JsonProperty("name")
    @Schema(description = "名称", example = "测试消息")
    @Pattern(regexp = "^.{0,64}$")
    @Length(max = 192)
    private String name = null;

    @JsonProperty("category")
    @Schema(description = "分类", example = "general")
    @Length(max = 16)
    private String category = null;

    @JsonProperty("import_method")
    @Schema(description = "导入方式", example = "manual")
    @Length(max = 16)
    private String importMethod = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "active")
    @Length(max = 32)
    private String status = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user001")
    @Length(max = 32)
    private String creator = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "user002")
    @Length(max = 32)
    private String updater = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListStructuredMessagesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListStructuredMessagesQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListStructuredMessagesQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getSort() {
        return sort;
    }

    public ListStructuredMessagesQo setSort(String sort) {
        this.sort = sort;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListStructuredMessagesQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public ListStructuredMessagesQo setCategory(String category) {
        this.category = category;
        return this;
    }

    public String getImportMethod() {
        return importMethod;
    }

    public ListStructuredMessagesQo setImportMethod(String importMethod) {
        this.importMethod = importMethod;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ListStructuredMessagesQo setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public ListStructuredMessagesQo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public ListStructuredMessagesQo setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListStructuredMessagesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    sort: ").append(toIndentedString(sort)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    importMethod: ").append(toIndentedString(importMethod)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
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
        ListStructuredMessagesQo listStructuredMessagesQo = (ListStructuredMessagesQo) o;
        return Objects.equals(this.workspaceId, listStructuredMessagesQo.workspaceId) && Objects.equals(this.offset,
            listStructuredMessagesQo.offset) && Objects.equals(this.limit, listStructuredMessagesQo.limit)
            && Objects.equals(this.sort, listStructuredMessagesQo.sort) && Objects.equals(this.name,
            listStructuredMessagesQo.name) && Objects.equals(this.category, listStructuredMessagesQo.category)
            && Objects.equals(this.importMethod, listStructuredMessagesQo.importMethod) && Objects.equals(this.status,
            listStructuredMessagesQo.status) && Objects.equals(this.creator, listStructuredMessagesQo.creator)
            && Objects.equals(this.updater, listStructuredMessagesQo.updater);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, sort, name, category, importMethod, status, creator, updater);
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
