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
 * mcp 服务列表
 */
@ApiModel(description = "mcp 服务列表")

@Validated

public class McpServerInfoList implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    private Long count = null;

    @JsonProperty("servers")
    @Schema(description = "servers", example = "[]")
    @Valid
    @Size()
    private List<McpServerInfo> servers = null;

    public Long getCount() {
        return count;
    }

    public McpServerInfoList setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<McpServerInfo> getServers() {
        return servers;
    }

    public McpServerInfoList setServers(List<McpServerInfo> servers) {
        this.servers = servers;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerInfoList {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    servers: ").append(toIndentedString(servers)).append("\n");
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
        McpServerInfoList mcpServerInfoList = (McpServerInfoList) o;
        return Objects.equals(this.count, mcpServerInfoList.count) && Objects.equals(this.servers,
            mcpServerInfoList.servers);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, servers);
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
