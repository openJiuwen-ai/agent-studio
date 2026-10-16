/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 记忆服务实例列表响应体
 */
@ApiModel(description = "记忆服务实例列表响应体")
public class ListMemoryServiceInstancesResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("items")
    @Schema(description = "实例列表")
    private List<MemoryServiceInstanceListItem> items = null;

    @JsonProperty("total")
    @Schema(description = "总数", example = "10")
    private Long total = null;

    public List<MemoryServiceInstanceListItem> getItems() {
        return items;
    }

    public ListMemoryServiceInstancesResponseBody setItems(List<MemoryServiceInstanceListItem> items) {
        this.items = items;
        return this;
    }

    public Long getTotal() {
        return total;
    }

    public ListMemoryServiceInstancesResponseBody setTotal(Long total) {
        this.total = total;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        ListMemoryServiceInstancesResponseBody that = (ListMemoryServiceInstancesResponseBody) o;
        return Objects.equals(this.items, that.items) && Objects.equals(this.total, that.total);
    }

    @Override
    public int hashCode() {
        return Objects.hash(items, total);
    }
}
