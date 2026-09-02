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
 * ListComplexIntentQo: converted from multi query params
 */
@ApiModel(description = "ListComplexIntentQo: converted from multi query params")

@Validated

public class ListComplexIntentQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "分页偏移量", example = "0")
    @Range(min = 0L, max = 100000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "1000")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 1000;

    @JsonProperty("name")
    @Schema(description = "意图名称", example = "用户咨询意图")
    @Pattern(regexp = "^.{0,64}$")
    @Length(max = 192)
    private String name = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListComplexIntentQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListComplexIntentQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListComplexIntentQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListComplexIntentQo setName(String name) {
        this.name = name;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListComplexIntentQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
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
        ListComplexIntentQo listComplexIntentQo = (ListComplexIntentQo) o;
        return Objects.equals(this.workspaceId, listComplexIntentQo.workspaceId) && Objects.equals(this.offset,
            listComplexIntentQo.offset) && Objects.equals(this.limit, listComplexIntentQo.limit) && Objects.equals(
            this.name, listComplexIntentQo.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, name);
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
