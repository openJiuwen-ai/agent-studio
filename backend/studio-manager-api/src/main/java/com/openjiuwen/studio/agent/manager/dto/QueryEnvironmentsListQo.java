/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryEnvironmentsListQo: converted from multi query params
 */
@ApiModel(description = "QueryEnvironmentsListQo: converted from multi query params")

@Validated

public class QueryEnvironmentsListQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[a-zA-Z][a-zA-Z0-9_.-]{0,47}$")
    private String name = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 1000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 100L)
    private Integer limit = 10;

    public String getName() {
        return name;
    }

    public QueryEnvironmentsListQo setName(String name) {
        this.name = name;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public QueryEnvironmentsListQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public QueryEnvironmentsListQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryEnvironmentsListQo {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
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
        QueryEnvironmentsListQo queryEnvironmentsListQo = (QueryEnvironmentsListQo) o;
        return Objects.equals(this.name, queryEnvironmentsListQo.name) && Objects.equals(this.offset,
            queryEnvironmentsListQo.offset) && Objects.equals(this.limit, queryEnvironmentsListQo.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, offset, limit);
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
