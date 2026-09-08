/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListMcpServersQo: converted from multi query params
 */
@ApiModel(description = "ListMcpServersQo: converted from multi query params")

@Validated

public class ListMcpServersQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 0L, max = 100L)
    private Integer limit = 10;

    @JsonProperty("name")
    @Schema(description = "MCP服务名称", example = "mcp-server")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "stdio")
    @Length(max = 32)
    private String type = null;

    @JsonProperty("active_status")
    @Schema(description = "激活状态", example = "active")
    @Length(max = 32)
    private String activeStatus = null;

    public Integer getOffset() {
        return offset;
    }

    public ListMcpServersQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListMcpServersQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListMcpServersQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListMcpServersQo setType(String type) {
        this.type = type;
        return this;
    }

    public String getActiveStatus() {
        return activeStatus;
    }

    public ListMcpServersQo setActiveStatus(String activeStatus) {
        this.activeStatus = activeStatus;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListMcpServersQo {\n");

        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    activeStatus: ").append(toIndentedString(activeStatus)).append("\n");
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
        ListMcpServersQo listMcpServersQo = (ListMcpServersQo) o;
        return Objects.equals(this.offset, listMcpServersQo.offset) && Objects.equals(this.limit,
            listMcpServersQo.limit) && Objects.equals(this.name, listMcpServersQo.name) && Objects.equals(this.type,
            listMcpServersQo.type) && Objects.equals(this.activeStatus, listMcpServersQo.activeStatus);
    }

    @Override
    public int hashCode() {
        return Objects.hash(offset, limit, name, type, activeStatus);
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
