/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 优化用例记录信息（分页）
 */
@ApiModel(description = "优化用例记录信息（分页）")

@Validated
public class OptimizationTaskListVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("data")
    @Schema(description = "数据列表", example = "")
    @Valid
    @Size(max = 500)
    private List<PeOptimizationTaskVo> data = null;

    @JsonProperty("total_page")
    @Schema(description = "总页数", example = "10", required = true)
    @NotNull
    private Integer totalPage = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "100", required = true)
    @NotNull
    private Long count = null;

    @JsonProperty("failed_count")
    @Schema(description = "失败数量", example = "2")
    private Long failedCount = null;

    @JsonProperty("finished_count")
    @Schema(description = "完成数量", example = "8")
    private Long finishedCount = null;

    @JsonProperty("optimizing_count")
    @Schema(description = "优化中数量", example = "0")
    private Long optimizingCount = null;

    @JsonProperty("has_next_page")
    @Schema(description = "是否有下一页", example = "false", required = true)
    @NotNull
    private Boolean hasNextPage = false;

    public List<PeOptimizationTaskVo> getData() {
        return data;
    }

    public OptimizationTaskListVo setData(List<PeOptimizationTaskVo> data) {
        this.data = data;
        return this;
    }

    public Integer getTotalPage() {
        return totalPage;
    }

    public OptimizationTaskListVo setTotalPage(Integer totalPage) {
        this.totalPage = totalPage;
        return this;
    }

    public Long getCount() {
        return count;
    }

    public OptimizationTaskListVo setCount(Long count) {
        this.count = count;
        return this;
    }

    public Long getFailedCount() {
        return failedCount;
    }

    public OptimizationTaskListVo setFailedCount(Long failedCount) {
        this.failedCount = failedCount;
        return this;
    }

    public Long getFinishedCount() {
        return finishedCount;
    }

    public OptimizationTaskListVo setFinishedCount(Long finishedCount) {
        this.finishedCount = finishedCount;
        return this;
    }

    public Long getOptimizingCount() {
        return optimizingCount;
    }

    public OptimizationTaskListVo setOptimizingCount(Long optimizingCount) {
        this.optimizingCount = optimizingCount;
        return this;
    }

    public OptimizationTaskListVo setHasNextPage(Boolean hasNextPage) {
        this.hasNextPage = hasNextPage;
        return this;
    }

    public Boolean isHasNextPage() {
        return hasNextPage;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class OptimizationTaskListVo {\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    totalPage: ").append(toIndentedString(totalPage)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    failedCount: ").append(toIndentedString(failedCount)).append("\n");
        sb.append("    finishedCount: ").append(toIndentedString(finishedCount)).append("\n");
        sb.append("    optimizingCount: ").append(toIndentedString(optimizingCount)).append("\n");
        sb.append("    hasNextPage: ").append(toIndentedString(hasNextPage)).append("\n");
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
        OptimizationTaskListVo optimizationTaskListVo = (OptimizationTaskListVo) o;
        return Objects.equals(this.data, optimizationTaskListVo.data) && Objects.equals(this.totalPage,
            optimizationTaskListVo.totalPage) && Objects.equals(this.count, optimizationTaskListVo.count)
            && Objects.equals(this.failedCount, optimizationTaskListVo.failedCount) && Objects.equals(
            this.finishedCount, optimizationTaskListVo.finishedCount) && Objects.equals(this.optimizingCount,
            optimizationTaskListVo.optimizingCount) && Objects.equals(this.hasNextPage,
            optimizationTaskListVo.hasNextPage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(data, totalPage, count, failedCount, finishedCount, optimizingCount, hasNextPage);
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
