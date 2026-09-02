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
 * CesMetricDataResp
 */

@Validated

public class CesMetricDataResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("metric_name")
    @Schema(description = "指标名称", example = "cpu_usage")
    private String metricName = null;

    @JsonProperty("max")
    @Schema(description = "最大值", example = "95.5")
    private Double max = null;

    @JsonProperty("min")
    @Schema(description = "最小值", example = "10.2")
    private Double min = null;

    @JsonProperty("datapoints")
    @Schema(description = "数据点列表", example = "[]")
    @Valid
    @Size()
    private List<Datapoints> datapoints = null;

    public String getMetricName() {
        return metricName;
    }

    public CesMetricDataResp setMetricName(String metricName) {
        this.metricName = metricName;
        return this;
    }

    public Double getMax() {
        return max;
    }

    public CesMetricDataResp setMax(Double max) {
        this.max = max;
        return this;
    }

    public Double getMin() {
        return min;
    }

    public CesMetricDataResp setMin(Double min) {
        this.min = min;
        return this;
    }

    public List<Datapoints> getDatapoints() {
        return datapoints;
    }

    public CesMetricDataResp setDatapoints(List<Datapoints> datapoints) {
        this.datapoints = datapoints;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CesMetricDataResp {\n");

        sb.append("    metricName: ").append(toIndentedString(metricName)).append("\n");
        sb.append("    max: ").append(toIndentedString(max)).append("\n");
        sb.append("    min: ").append(toIndentedString(min)).append("\n");
        sb.append("    datapoints: ").append(toIndentedString(datapoints)).append("\n");
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
        CesMetricDataResp cesMetricDataResp = (CesMetricDataResp) o;
        return Objects.equals(this.metricName, cesMetricDataResp.metricName) && Objects.equals(this.max,
            cesMetricDataResp.max) && Objects.equals(this.min, cesMetricDataResp.min) && Objects.equals(this.datapoints,
            cesMetricDataResp.datapoints);
    }

    @Override
    public int hashCode() {
        return Objects.hash(metricName, max, min, datapoints);
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
