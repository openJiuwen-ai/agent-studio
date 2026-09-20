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
 * 评估用例记录信息（分页）
 */
@ApiModel(description = "评估用例记录信息（分页）")

@Validated
public class EvaluationTaskListVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("data")
    @Schema(description = "数据列表", example = "")
    @Valid
    @Size(max = 500)
    private List<PeEvaluationTaskVo> data = null;

    @JsonProperty("total_page")
    @Schema(description = "总页数", example = "10", required = true)
    @NotNull
    private Integer totalPage = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "100", required = true)
    @NotNull
    private Long count = null;

    @JsonProperty("has_next_page")
    @Schema(description = "是否有下一页", example = "false", required = true)
    @NotNull
    private Boolean hasNextPage = false;

    public List<PeEvaluationTaskVo> getData() {
        return data;
    }

    public EvaluationTaskListVo setData(List<PeEvaluationTaskVo> data) {
        this.data = data;
        return this;
    }

    public Integer getTotalPage() {
        return totalPage;
    }

    public EvaluationTaskListVo setTotalPage(Integer totalPage) {
        this.totalPage = totalPage;
        return this;
    }

    public Long getCount() {
        return count;
    }

    public EvaluationTaskListVo setCount(Long count) {
        this.count = count;
        return this;
    }

    public EvaluationTaskListVo setHasNextPage(Boolean hasNextPage) {
        this.hasNextPage = hasNextPage;
        return this;
    }

    public Boolean isHasNextPage() {
        return hasNextPage;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EvaluationTaskListVo {\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    totalPage: ").append(toIndentedString(totalPage)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
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
        EvaluationTaskListVo evaluationTaskListVo = (EvaluationTaskListVo) o;
        return Objects.equals(this.data, evaluationTaskListVo.data) && Objects.equals(this.totalPage,
            evaluationTaskListVo.totalPage) && Objects.equals(this.count, evaluationTaskListVo.count) && Objects.equals(
            this.hasNextPage, evaluationTaskListVo.hasNextPage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(data, totalPage, count, hasNextPage);
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
