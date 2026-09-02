/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * MCP 工具调试返回。
 */
@ApiModel(description = "MCP 工具调试返回。")

@Validated

public class McpServiceDataResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("data")
    @Schema(description = "数据", example = "{}")
    @Valid
    private Object data = null;

    public Object getData() {
        return data;
    }

    public McpServiceDataResp setData(Object data) {
        this.data = data;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceDataResp {\n");

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
        McpServiceDataResp mcpServiceDataResp = (McpServiceDataResp) o;
        return Objects.equals(this.data, mcpServiceDataResp.data);
    }

    @Override
    public int hashCode() {
        return Objects.hash(data);
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
