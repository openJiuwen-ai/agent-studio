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
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * McpServicesCesLineChartQo: converted from multi query params
 */
@ApiModel(description = "McpServicesCesLineChartQo: converted from multi query params")

@Validated

public class McpServicesCesLineChartQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("from")
    @Schema(description = "查询起始时间", example = "2026-01-01T00:00:00Z")
    private String from = null;

    @JsonProperty("to")
    @Schema(description = "查询结束时间", example = "2026-01-02T00:00:00Z")
    private String to = null;

    @JsonProperty("period")
    @Schema(description = "查询时间粒度", example = "60")
    private Integer period = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public McpServicesCesLineChartQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getFrom() {
        return from;
    }

    public McpServicesCesLineChartQo setFrom(String from) {
        this.from = from;
        return this;
    }

    public String getTo() {
        return to;
    }

    public McpServicesCesLineChartQo setTo(String to) {
        this.to = to;
        return this;
    }

    public Integer getPeriod() {
        return period;
    }

    public McpServicesCesLineChartQo setPeriod(Integer period) {
        this.period = period;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServicesCesLineChartQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    from: ").append(toIndentedString(from)).append("\n");
        sb.append("    to: ").append(toIndentedString(to)).append("\n");
        sb.append("    period: ").append(toIndentedString(period)).append("\n");
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
        McpServicesCesLineChartQo mcpServicesCesLineChartQo = (McpServicesCesLineChartQo) o;
        return Objects.equals(this.workspaceId, mcpServicesCesLineChartQo.workspaceId) && Objects.equals(this.from,
            mcpServicesCesLineChartQo.from) && Objects.equals(this.to, mcpServicesCesLineChartQo.to) && Objects.equals(
            this.period, mcpServicesCesLineChartQo.period);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, from, to, period);
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
