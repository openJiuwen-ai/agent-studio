/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 对话信息表。
 */
@ApiModel(description = "对话信息表。")

@Validated

public class ExecutionQueries implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10", required = true)
    @NotNull
    private Integer count = null;

    @JsonProperty("execution_infos")
    @Schema(description = "执行信息列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<ExecutionInfo> executionInfos = new ArrayList<ExecutionInfo>();

    public Integer getCount() {
        return count;
    }

    public ExecutionQueries setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<ExecutionInfo> getExecutionInfos() {
        return executionInfos;
    }

    public ExecutionQueries setExecutionInfos(List<ExecutionInfo> executionInfos) {
        this.executionInfos = executionInfos;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExecutionQueries {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    executionInfos: ").append(toIndentedString(executionInfos)).append("\n");
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
        ExecutionQueries executionQueries = (ExecutionQueries) o;
        return Objects.equals(this.count, executionQueries.count) && Objects.equals(this.executionInfos,
            executionQueries.executionInfos);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, executionInfos);
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
