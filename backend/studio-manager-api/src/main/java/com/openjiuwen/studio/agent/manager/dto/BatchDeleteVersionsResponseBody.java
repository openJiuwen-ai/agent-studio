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
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量删除版本响应体
 */
@ApiModel(description = "批量删除版本响应体")

@Validated

public class BatchDeleteVersionsResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total_count")
    @Schema(description = "提交删除的版本总数", example = "3", required = true)
    @NotNull
    @Range(min = 0L, max = 65535L)
    private Integer totalCount = null;

    @JsonProperty("deleted_count")
    @Schema(description = "删除成功的版本数", example = "2", required = true)
    @NotNull
    @Range(min = 0L, max = 65535L)
    private Integer deletedCount = null;

    @JsonProperty("success")
    @Schema(description = "删除成功的版本ID列表", example = "[]")
    private List<String> success = new ArrayList<>();

    @JsonProperty("failed")
    @Schema(description = "删除失败的版本详情列表", example = "[]")
    private List<BatchDeleteVersionFailedInfo> failed = new ArrayList<>();

    public Integer getTotalCount() {
        return totalCount;
    }

    public BatchDeleteVersionsResponseBody setTotalCount(Integer totalCount) {
        this.totalCount = totalCount;
        return this;
    }

    public Integer getDeletedCount() {
        return deletedCount;
    }

    public BatchDeleteVersionsResponseBody setDeletedCount(Integer deletedCount) {
        this.deletedCount = deletedCount;
        return this;
    }

    public List<String> getSuccess() {
        return success;
    }

    public BatchDeleteVersionsResponseBody setSuccess(List<String> success) {
        this.success = success;
        return this;
    }

    public List<BatchDeleteVersionFailedInfo> getFailed() {
        return failed;
    }

    public BatchDeleteVersionsResponseBody setFailed(List<BatchDeleteVersionFailedInfo> failed) {
        this.failed = failed;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchDeleteVersionsResponseBody {\n");

        sb.append("    totalCount: ").append(toIndentedString(totalCount)).append("\n");
        sb.append("    deletedCount: ").append(toIndentedString(deletedCount)).append("\n");
        sb.append("    success: ").append(toIndentedString(success)).append("\n");
        sb.append("    failed: ").append(toIndentedString(failed)).append("\n");
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
        BatchDeleteVersionsResponseBody batchDeleteVersionsResponseBody = (BatchDeleteVersionsResponseBody) o;
        return Objects.equals(this.totalCount, batchDeleteVersionsResponseBody.totalCount) && Objects.equals(
            this.deletedCount, batchDeleteVersionsResponseBody.deletedCount) && Objects.equals(this.success,
            batchDeleteVersionsResponseBody.success) && Objects.equals(this.failed,
            batchDeleteVersionsResponseBody.failed);
    }

    @Override
    public int hashCode() {
        return Objects.hash(totalCount, deletedCount, success, failed);
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
