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
 * RouterStrategyListResponse
 */

@Validated

public class RouterStrategyListResponse implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "100")
    private Integer total = null;

    @JsonProperty("data")
    @Schema(description = "数据", example = "[]")
    @Valid
    @Size()
    private List<RouterStrategyBaseInfo> data = null;

    public Integer getTotal() {
        return total;
    }

    public RouterStrategyListResponse setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public List<RouterStrategyBaseInfo> getData() {
        return data;
    }

    public RouterStrategyListResponse setData(List<RouterStrategyBaseInfo> data) {
        this.data = data;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RouterStrategyListResponse {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
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
        RouterStrategyListResponse routerStrategyListResponse = (RouterStrategyListResponse) o;
        return Objects.equals(this.total, routerStrategyListResponse.total) && Objects.equals(this.data,
            routerStrategyListResponse.data);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, data);
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
