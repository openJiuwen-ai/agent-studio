/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 子网列表
 */
@ApiModel(description = "子网列表")

@Validated

public class ListSubnets implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("subnet")
    @Schema(description = "子网", example = "[]")
    @Valid
    @Size()
    private List<SubnetInfo> subnet = null;

    public List<SubnetInfo> getSubnet() {
        return subnet;
    }

    public ListSubnets setSubnet(List<SubnetInfo> subnet) {
        this.subnet = subnet;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListSubnets {\n");

        sb.append("    subnet: ").append(toIndentedString(subnet)).append("\n");
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
        ListSubnets listSubnets = (ListSubnets) o;
        return Objects.equals(this.subnet, listSubnets.subnet);
    }

    @Override
    public int hashCode() {
        return Objects.hash(subnet);
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
