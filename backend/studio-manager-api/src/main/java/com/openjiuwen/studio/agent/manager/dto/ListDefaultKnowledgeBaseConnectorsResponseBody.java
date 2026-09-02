/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 查询默认知识库连接器响应体
 */
@ApiModel(description = "查询默认知识库连接器响应体")

@Validated

public class ListDefaultKnowledgeBaseConnectorsResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "1")
    @Range(min = 0L, max = 10000L)
    private Long total = null;

    @JsonProperty("connectors")
    @Schema(description = "连接器列表", example = "[]")
    @Valid
    @Size(max = 200)
    private List<KnowledgeBaseConnectorDetail> connectors = null;

    public Long getTotal() {
        return total;
    }

    public ListDefaultKnowledgeBaseConnectorsResponseBody setTotal(Long total) {
        this.total = total;
        return this;
    }

    public List<KnowledgeBaseConnectorDetail> getConnectors() {
        return connectors;
    }

    public ListDefaultKnowledgeBaseConnectorsResponseBody setConnectors(List<KnowledgeBaseConnectorDetail> connectors) {
        this.connectors = connectors;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListDefaultKnowledgeBaseConnectorsResponseBody {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    connectors: ").append(toIndentedString(connectors)).append("\n");
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
        ListDefaultKnowledgeBaseConnectorsResponseBody listDefaultKnowledgeBaseConnectorsResponseBody
            = (ListDefaultKnowledgeBaseConnectorsResponseBody) o;
        return Objects.equals(this.total, listDefaultKnowledgeBaseConnectorsResponseBody.total) && Objects.equals(
            this.connectors, listDefaultKnowledgeBaseConnectorsResponseBody.connectors);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, connectors);
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
