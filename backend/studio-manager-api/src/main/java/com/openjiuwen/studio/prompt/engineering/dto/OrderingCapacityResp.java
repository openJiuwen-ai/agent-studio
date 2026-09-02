/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 查询订购功能项信息响应体
 */
@ApiModel(description = "查询订购功能项信息响应体")

@Validated
public class OrderingCapacityResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("ordering_capacities")
    @Schema(description = "排序Capacities", example = "")
    @Valid
    private List<OrderingCapacityInfo> orderingCapacities = null;

    public List<OrderingCapacityInfo> getOrderingCapacities() {
        return orderingCapacities;
    }

    public OrderingCapacityResp setOrderingCapacities(List<OrderingCapacityInfo> orderingCapacities) {
        this.orderingCapacities = orderingCapacities;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class OrderingCapacityResp {\n");
        sb.append("    orderingCapacities: ").append(toIndentedString(orderingCapacities)).append("\n");
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
        OrderingCapacityResp orderingCapacityResp = (OrderingCapacityResp) o;
        return Objects.equals(this.orderingCapacities, orderingCapacityResp.orderingCapacities);
    }

    @Override
    public int hashCode() {
        return Objects.hash(orderingCapacities);
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
