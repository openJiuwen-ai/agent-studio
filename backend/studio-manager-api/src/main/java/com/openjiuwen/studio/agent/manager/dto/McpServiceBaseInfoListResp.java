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
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceBaseInfoListResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("mcps")
    @Schema(description = "mcps", example = "[]")
    @Valid
    @Size()
    private List<McpServiceBaseInfoDto> mcps = null;

    @JsonProperty("total")
    @Schema(description = "总数", example = "1")
    private Long total = null;

    public List<McpServiceBaseInfoDto> getMcps() {
        return mcps;
    }

    public McpServiceBaseInfoListResp setMcps(List<McpServiceBaseInfoDto> mcps) {
        this.mcps = mcps;
        return this;
    }

    public Long getTotal() {
        return total;
    }

    public McpServiceBaseInfoListResp setTotal(Long total) {
        this.total = total;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceBaseInfoListResp {\n");

        sb.append("    mcps: ").append(toIndentedString(mcps)).append("\n");
        sb.append("    total: ").append(toIndentedString(total)).append("\n");
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
        McpServiceBaseInfoListResp mcpServiceBaseInfoListResp = (McpServiceBaseInfoListResp) o;
        return Objects.equals(this.mcps, mcpServiceBaseInfoListResp.mcps) && Objects.equals(this.total,
            mcpServiceBaseInfoListResp.total);
    }

    @Override
    public int hashCode() {
        return Objects.hash(mcps, total);
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
