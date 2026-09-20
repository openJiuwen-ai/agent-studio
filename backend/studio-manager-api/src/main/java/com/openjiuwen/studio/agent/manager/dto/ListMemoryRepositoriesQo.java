/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ListMemoryRepositoriesQo: converted from multi query params
 */
@ApiModel(description = "ListMemoryRepositoriesQo: converted from multi query params")

@Validated

public class ListMemoryRepositoriesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws001", required = true)
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

    @JsonProperty("name")
    @Schema(description = "记忆仓库名称", example = "conversation_history")
    @Length(min = 1, max = 50)
    private String name = null;

    @JsonProperty("ids")
    @Schema(description = "ID列表", example = "[\"mem001\",\"mem002\"]")
    @Valid
    @Size()
    private List<@Length() String> ids = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListMemoryRepositoriesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListMemoryRepositoriesQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListMemoryRepositoriesQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListMemoryRepositoriesQo setName(String name) {
        this.name = name;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public ListMemoryRepositoriesQo setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListMemoryRepositoriesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
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
        ListMemoryRepositoriesQo listMemoryRepositoriesQo = (ListMemoryRepositoriesQo) o;
        return Objects.equals(this.workspaceId, listMemoryRepositoriesQo.workspaceId) && Objects.equals(this.offset,
            listMemoryRepositoriesQo.offset) && Objects.equals(this.limit, listMemoryRepositoriesQo.limit)
            && Objects.equals(this.name, listMemoryRepositoriesQo.name) && Objects.equals(this.ids,
            listMemoryRepositoriesQo.ids);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, name, ids);
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
