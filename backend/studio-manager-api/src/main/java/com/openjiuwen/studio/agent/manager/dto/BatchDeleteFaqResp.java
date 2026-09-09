/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 批量删除FAQ问答对响应体
 */
@ApiModel(description = "批量删除FAQ问答对响应体")

@Validated

public class BatchDeleteFaqResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total_count")
    @Schema(description = "总数", example = "10", required = true)
    @NotNull
    @Range(min = 0L, max = 65535L)
    private Integer totalCount = null;

    @JsonProperty("deleted_count")
    @Schema(description = "是否删除", example = "10", required = true)
    @NotNull
    @Range(min = 0L, max = 65535L)
    private Integer deletedCount = null;

    public Integer getTotalCount() {
        return totalCount;
    }

    public BatchDeleteFaqResp setTotalCount(Integer totalCount) {
        this.totalCount = totalCount;
        return this;
    }

    public Integer getDeletedCount() {
        return deletedCount;
    }

    public BatchDeleteFaqResp setDeletedCount(Integer deletedCount) {
        this.deletedCount = deletedCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchDeleteFaqResp {\n");

        sb.append("    totalCount: ").append(toIndentedString(totalCount)).append("\n");
        sb.append("    deletedCount: ").append(toIndentedString(deletedCount)).append("\n");
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
        BatchDeleteFaqResp batchDeleteFaqResp = (BatchDeleteFaqResp) o;
        return Objects.equals(this.totalCount, batchDeleteFaqResp.totalCount) && Objects.equals(this.deletedCount,
            batchDeleteFaqResp.deletedCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(totalCount, deletedCount);
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
