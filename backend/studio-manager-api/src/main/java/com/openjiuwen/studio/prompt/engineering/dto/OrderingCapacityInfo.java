/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 订购功能项信息
 */
@ApiModel(description = "订购功能项信息")

@Validated
public class OrderingCapacityInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_spec_code")
    @Schema(description = "resourceSpec编码", example = "示例文本")
    private String resourceSpecCode = null;

    @JsonProperty("capacities")
    @Schema(description = "capacities", example = "")
    @Valid
    private List<@Length() String> capacities = null;

    public String getResourceSpecCode() {
        return resourceSpecCode;
    }

    public OrderingCapacityInfo setResourceSpecCode(String resourceSpecCode) {
        this.resourceSpecCode = resourceSpecCode;
        return this;
    }

    public List<String> getCapacities() {
        return capacities;
    }

    public OrderingCapacityInfo setCapacities(List<String> capacities) {
        this.capacities = capacities;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class OrderingCapacityInfo {\n");
        sb.append("    resourceSpecCode: ").append(toIndentedString(resourceSpecCode)).append("\n");
        sb.append("    capacities: ").append(toIndentedString(capacities)).append("\n");
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
        OrderingCapacityInfo orderingCapacityInfo = (OrderingCapacityInfo) o;
        return Objects.equals(this.resourceSpecCode, orderingCapacityInfo.resourceSpecCode) && Objects.equals(
            this.capacities, orderingCapacityInfo.capacities);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceSpecCode, capacities);
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
