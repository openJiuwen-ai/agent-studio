/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryEnvironmentInstancesQo: converted from multi query params
 */
@ApiModel(description = "QueryEnvironmentInstancesQo: converted from multi query params")

@Validated

public class QueryEnvironmentInstancesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("pageNo")
    @Schema(description = "页码no", example = "0")
    @Range(min = 1L, max = 1000L)
    private Integer pageNo = 1;

    @JsonProperty("pageSize")
    @Schema(description = "页码大小", example = "0")
    @Range(min = 1L, max = 100L)
    private Integer pageSize = 10;

    public Integer getPageNo() {
        return pageNo;
    }

    public QueryEnvironmentInstancesQo setPageNo(Integer pageNo) {
        this.pageNo = pageNo;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public QueryEnvironmentInstancesQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryEnvironmentInstancesQo {\n");

        sb.append("    pageNo: ").append(toIndentedString(pageNo)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
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
        QueryEnvironmentInstancesQo queryEnvironmentInstancesQo = (QueryEnvironmentInstancesQo) o;
        return Objects.equals(this.pageNo, queryEnvironmentInstancesQo.pageNo) && Objects.equals(this.pageSize,
            queryEnvironmentInstancesQo.pageSize);
    }

    @Override
    public int hashCode() {
        return Objects.hash(pageNo, pageSize);
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
