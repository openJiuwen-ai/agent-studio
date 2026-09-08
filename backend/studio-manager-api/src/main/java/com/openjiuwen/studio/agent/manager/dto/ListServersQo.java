/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListServersQo: converted from multi query params
 */
@ApiModel(description = "ListServersQo: converted from multi query params")

@Validated

public class ListServersQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("language")
    @Schema(description = "编程语言", example = "python")
    private String language = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "my-server")
    @Length(max = 255)
    private String name = null;

    @JsonProperty("category")
    @Schema(description = "服务分类", example = "mcp")
    private String category = null;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10", required = true)
    @NotNull
    private Integer limit = 0;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0", required = true)
    @NotNull
    private Integer offset = 0;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListServersQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getLanguage() {
        return language;
    }

    public ListServersQo setLanguage(String language) {
        this.language = language;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListServersQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public ListServersQo setCategory(String category) {
        this.category = category;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListServersQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListServersQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListServersQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    language: ").append(toIndentedString(language)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
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
        ListServersQo listServersQo = (ListServersQo) o;
        return Objects.equals(this.workspaceId, listServersQo.workspaceId) && Objects.equals(this.language,
            listServersQo.language) && Objects.equals(this.name, listServersQo.name) && Objects.equals(this.category,
            listServersQo.category) && Objects.equals(this.limit, listServersQo.limit) && Objects.equals(this.offset,
            listServersQo.offset);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, language, name, category, limit, offset);
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
