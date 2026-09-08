/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListTagsQo: converted from multi query params
 */
@ApiModel(description = "ListTagsQo: converted from multi query params")

@Validated
public class ListTagsQo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "50", required = true)
    @NotNull
    @Range(min = 1L, max = 1000L)
    private Integer limit = 50;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0", required = true)
    @NotNull
    @Range(min = 0L, max = 100000L)
    private Integer offset = 0;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @NotBlank
    private String workspaceId = null;

    public Integer getLimit() {
        return limit;
    }

    public ListTagsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListTagsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListTagsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListTagsQo {\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        ListTagsQo listTagsQo = (ListTagsQo) o;
        return Objects.equals(this.limit, listTagsQo.limit) && Objects.equals(this.offset, listTagsQo.offset)
            && Objects.equals(this.workspaceId, listTagsQo.workspaceId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(limit, offset, workspaceId);
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
