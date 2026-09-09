/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * McpServiceBatchDeployResp
 */

@Validated

public class McpServiceBatchDeployResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("totalCount")
    @Schema(description = "总数量", example = "10")
    private Integer totalCount = null;

    @JsonProperty("successCount")
    @Schema(description = "成功数量", example = "8")
    private Integer successCount = null;

    @JsonProperty("failedCount")
    @Schema(description = "失败数量", example = "2")
    private Integer failedCount = null;

    @JsonProperty("results")
    @Schema(description = "部署结果列表", example = "[]")
    @Valid
    @Size()
    private List<McpDeployResult> results = null;

    public Integer getTotalCount() {
        return totalCount;
    }

    public McpServiceBatchDeployResp setTotalCount(Integer totalCount) {
        this.totalCount = totalCount;
        return this;
    }

    public Integer getSuccessCount() {
        return successCount;
    }

    public McpServiceBatchDeployResp setSuccessCount(Integer successCount) {
        this.successCount = successCount;
        return this;
    }

    public Integer getFailedCount() {
        return failedCount;
    }

    public McpServiceBatchDeployResp setFailedCount(Integer failedCount) {
        this.failedCount = failedCount;
        return this;
    }

    public List<McpDeployResult> getResults() {
        return results;
    }

    public McpServiceBatchDeployResp setResults(List<McpDeployResult> results) {
        this.results = results;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceBatchDeployResp {\n");

        sb.append("    totalCount: ").append(toIndentedString(totalCount)).append("\n");
        sb.append("    successCount: ").append(toIndentedString(successCount)).append("\n");
        sb.append("    failedCount: ").append(toIndentedString(failedCount)).append("\n");
        sb.append("    results: ").append(toIndentedString(results)).append("\n");
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
        McpServiceBatchDeployResp mcpServiceBatchDeployResp = (McpServiceBatchDeployResp) o;
        return Objects.equals(this.totalCount, mcpServiceBatchDeployResp.totalCount) && Objects.equals(
            this.successCount, mcpServiceBatchDeployResp.successCount) && Objects.equals(this.failedCount,
            mcpServiceBatchDeployResp.failedCount) && Objects.equals(this.results, mcpServiceBatchDeployResp.results);
    }

    @Override
    public int hashCode() {
        return Objects.hash(totalCount, successCount, failedCount, results);
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
