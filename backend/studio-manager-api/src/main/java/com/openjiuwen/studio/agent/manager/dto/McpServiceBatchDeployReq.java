/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量部署MCP服务请求
 */
@ApiModel(description = "批量部署MCP服务请求")

@Validated

public class McpServiceBatchDeployReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("servers")
    @Schema(description = "servers", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 100)
    private List<McpServiceBatchDeployItem> servers = new ArrayList<McpServiceBatchDeployItem>();

    public List<McpServiceBatchDeployItem> getServers() {
        return servers;
    }

    public McpServiceBatchDeployReq setServers(List<McpServiceBatchDeployItem> servers) {
        this.servers = servers;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceBatchDeployReq {\n");

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
        McpServiceBatchDeployReq mcpServiceBatchDeployReq = (McpServiceBatchDeployReq) o;
        return Objects.equals(this.servers, mcpServiceBatchDeployReq.servers);
    }

    @Override
    public int hashCode() {
        return Objects.hash(servers);
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
