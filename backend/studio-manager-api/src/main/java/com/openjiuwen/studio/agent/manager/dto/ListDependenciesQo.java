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
 * ListDependenciesQo: converted from multi query params
 */
@ApiModel(description = "ListDependenciesQo: converted from multi query params")

@Validated

public class ListDependenciesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

    @JsonProperty("keyword")
    @Schema(description = "搜索关键词", example = "requests")
    private String keyword = null;

    @JsonProperty("runtime")
    @Schema(description = "运行时环境", example = "python3")
    private String runtime = null;

    @JsonProperty("scope")
    @Schema(description = "查询范围", example = "all")
    private String scope = "all";

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListDependenciesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListDependenciesQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListDependenciesQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getKeyword() {
        return keyword;
    }

    public ListDependenciesQo setKeyword(String keyword) {
        this.keyword = keyword;
        return this;
    }

    public String getRuntime() {
        return runtime;
    }

    public ListDependenciesQo setRuntime(String runtime) {
        this.runtime = runtime;
        return this;
    }

    public String getScope() {
        return scope;
    }

    public ListDependenciesQo setScope(String scope) {
        this.scope = scope;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListDependenciesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    keyword: ").append(toIndentedString(keyword)).append("\n");
        sb.append("    runtime: ").append(toIndentedString(runtime)).append("\n");
        sb.append("    scope: ").append(toIndentedString(scope)).append("\n");
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
        ListDependenciesQo listDependenciesQo = (ListDependenciesQo) o;
        return Objects.equals(this.workspaceId, listDependenciesQo.workspaceId) && Objects.equals(this.offset,
            listDependenciesQo.offset) && Objects.equals(this.limit, listDependenciesQo.limit) && Objects.equals(
            this.keyword, listDependenciesQo.keyword) && Objects.equals(this.runtime, listDependenciesQo.runtime)
            && Objects.equals(this.scope, listDependenciesQo.scope);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, keyword, runtime, scope);
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
