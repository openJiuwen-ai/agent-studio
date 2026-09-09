/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * Datapoints
 */

@Validated

public class Datapoints implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("unit")
    @Schema(description = "单位", example = "ms")
    private String unit = null;

    @JsonProperty("average")
    @Schema(description = "平均值", example = "12.5")
    private Double average = null;

    @JsonProperty("max")
    @Schema(description = "最大值", example = "100.0")
    private Double max = null;

    @JsonProperty("min")
    @Schema(description = "最小值", example = "0.0")
    private Double min = null;

    @JsonProperty("sum")
    @Schema(description = "总和", example = "250.0")
    private Double sum = null;

    @JsonProperty("variance")
    @Schema(description = "方差", example = "3.2")
    private Double variance = null;

    @JsonProperty("timestamp")
    @Schema(description = "时间戳", example = "1714521600000")
    private Long timestamp = null;

    public String getUnit() {
        return unit;
    }

    public Datapoints setUnit(String unit) {
        this.unit = unit;
        return this;
    }

    public Double getAverage() {
        return average;
    }

    public Datapoints setAverage(Double average) {
        this.average = average;
        return this;
    }

    public Double getMax() {
        return max;
    }

    public Datapoints setMax(Double max) {
        this.max = max;
        return this;
    }

    public Double getMin() {
        return min;
    }

    public Datapoints setMin(Double min) {
        this.min = min;
        return this;
    }

    public Double getSum() {
        return sum;
    }

    public Datapoints setSum(Double sum) {
        this.sum = sum;
        return this;
    }

    public Double getVariance() {
        return variance;
    }

    public Datapoints setVariance(Double variance) {
        this.variance = variance;
        return this;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public Datapoints setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Datapoints {\n");

        sb.append("    unit: ").append(toIndentedString(unit)).append("\n");
        sb.append("    average: ").append(toIndentedString(average)).append("\n");
        sb.append("    max: ").append(toIndentedString(max)).append("\n");
        sb.append("    min: ").append(toIndentedString(min)).append("\n");
        sb.append("    sum: ").append(toIndentedString(sum)).append("\n");
        sb.append("    variance: ").append(toIndentedString(variance)).append("\n");
        sb.append("    timestamp: ").append(toIndentedString(timestamp)).append("\n");
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
        Datapoints datapoints = (Datapoints) o;
        return Objects.equals(this.unit, datapoints.unit) && Objects.equals(this.average, datapoints.average)
            && Objects.equals(this.max, datapoints.max) && Objects.equals(this.min, datapoints.min) && Objects.equals(
            this.sum, datapoints.sum) && Objects.equals(this.variance, datapoints.variance) && Objects.equals(
            this.timestamp, datapoints.timestamp);
    }

    @Override
    public int hashCode() {
        return Objects.hash(unit, average, max, min, sum, variance, timestamp);
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
