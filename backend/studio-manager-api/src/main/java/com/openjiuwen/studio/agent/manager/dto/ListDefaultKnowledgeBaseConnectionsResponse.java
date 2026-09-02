/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ListDefaultKnowledgeBaseConnectionsResponse
 */

@Validated

public class ListDefaultKnowledgeBaseConnectionsResponse implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "1")
    @Range(min = 0L, max = 10000L)
    private Long total = null;

    @JsonProperty("items")
    @Schema(description = "items", example = "[]")
    @Valid
    @Size(max = 200)
    private List<DefaultKnowledgeBaseConnectionListItem> items = null;

    public Long getTotal() {
        return total;
    }

    public ListDefaultKnowledgeBaseConnectionsResponse setTotal(Long total) {
        this.total = total;
        return this;
    }

    public List<DefaultKnowledgeBaseConnectionListItem> getItems() {
        return items;
    }

    public ListDefaultKnowledgeBaseConnectionsResponse setItems(List<DefaultKnowledgeBaseConnectionListItem> items) {
        this.items = items;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListDefaultKnowledgeBaseConnectionsResponse {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    items: ").append(toIndentedString(items)).append("\n");
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
        ListDefaultKnowledgeBaseConnectionsResponse listDefaultKnowledgeBaseConnectionsResponse
            = (ListDefaultKnowledgeBaseConnectionsResponse) o;
        return Objects.equals(this.total, listDefaultKnowledgeBaseConnectionsResponse.total) && Objects.equals(
            this.items, listDefaultKnowledgeBaseConnectionsResponse.items);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, items);
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
