/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * McpServiceStatisticResp
 */

@Validated

public class McpServiceStatisticResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("serviceId")
    @Schema(description = "服务ID", example = "service-001")
    @Length(max = 64)
    private String serviceId = null;

    @JsonProperty("totalInvokingTimes")
    @Schema(description = "总调用次数", example = "100.0")
    private Double totalInvokingTimes = null;

    @JsonProperty("totalInvokingTimesPerMonth")
    @Schema(description = "月调用次数", example = "50.0")
    private Double totalInvokingTimesPerMonth = null;

    @JsonProperty("totalInvokingTimesCurrentDay")
    @Schema(description = "当日调用次数", example = "10.0")
    private Double totalInvokingTimesCurrentDay = null;

    @JsonProperty("totalInvokingTimesCurrentWeek")
    @Schema(description = "当周调用次数", example = "30.0")
    private Double totalInvokingTimesCurrentWeek = null;

    public String getServiceId() {
        return serviceId;
    }

    public McpServiceStatisticResp setServiceId(String serviceId) {
        this.serviceId = serviceId;
        return this;
    }

    public Double getTotalInvokingTimes() {
        return totalInvokingTimes;
    }

    public McpServiceStatisticResp setTotalInvokingTimes(Double totalInvokingTimes) {
        this.totalInvokingTimes = totalInvokingTimes;
        return this;
    }

    public Double getTotalInvokingTimesPerMonth() {
        return totalInvokingTimesPerMonth;
    }

    public McpServiceStatisticResp setTotalInvokingTimesPerMonth(Double totalInvokingTimesPerMonth) {
        this.totalInvokingTimesPerMonth = totalInvokingTimesPerMonth;
        return this;
    }

    public Double getTotalInvokingTimesCurrentDay() {
        return totalInvokingTimesCurrentDay;
    }

    public McpServiceStatisticResp setTotalInvokingTimesCurrentDay(Double totalInvokingTimesCurrentDay) {
        this.totalInvokingTimesCurrentDay = totalInvokingTimesCurrentDay;
        return this;
    }

    public Double getTotalInvokingTimesCurrentWeek() {
        return totalInvokingTimesCurrentWeek;
    }

    public McpServiceStatisticResp setTotalInvokingTimesCurrentWeek(Double totalInvokingTimesCurrentWeek) {
        this.totalInvokingTimesCurrentWeek = totalInvokingTimesCurrentWeek;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceStatisticResp {\n");

        sb.append("    serviceId: ").append(toIndentedString(serviceId)).append("\n");
        sb.append("    totalInvokingTimes: ").append(toIndentedString(totalInvokingTimes)).append("\n");
        sb.append("    totalInvokingTimesPerMonth: ").append(toIndentedString(totalInvokingTimesPerMonth)).append("\n");
        sb.append("    totalInvokingTimesCurrentDay: ")
            .append(toIndentedString(totalInvokingTimesCurrentDay))
            .append("\n");
        sb.append("    totalInvokingTimesCurrentWeek: ")
            .append(toIndentedString(totalInvokingTimesCurrentWeek))
            .append("\n");
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
        McpServiceStatisticResp mcpServiceStatisticResp = (McpServiceStatisticResp) o;
        return Objects.equals(this.serviceId, mcpServiceStatisticResp.serviceId) && Objects.equals(
            this.totalInvokingTimes, mcpServiceStatisticResp.totalInvokingTimes) && Objects.equals(
            this.totalInvokingTimesPerMonth, mcpServiceStatisticResp.totalInvokingTimesPerMonth) && Objects.equals(
            this.totalInvokingTimesCurrentDay, mcpServiceStatisticResp.totalInvokingTimesCurrentDay) && Objects.equals(
            this.totalInvokingTimesCurrentWeek, mcpServiceStatisticResp.totalInvokingTimesCurrentWeek);
    }

    @Override
    public int hashCode() {
        return Objects.hash(serviceId, totalInvokingTimes, totalInvokingTimesPerMonth, totalInvokingTimesCurrentDay,
            totalInvokingTimesCurrentWeek);
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
