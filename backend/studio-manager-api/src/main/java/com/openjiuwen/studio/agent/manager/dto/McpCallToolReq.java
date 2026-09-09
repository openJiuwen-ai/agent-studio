/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/**
 * mcp 运行态请求体
 */
@ApiModel(description = "mcp 运行态请求体")

@Validated

public class McpCallToolReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("params")
    @Schema(description = "参数", example = "示例字符串", required = true)
    @Valid
    @NotNull
    @Size()
    private Map<String, Object> params = new HashMap<String, Object>();

    public String getName() {
        return name;
    }

    public McpCallToolReq setName(String name) {
        this.name = name;
        return this;
    }

    public Map<String, Object> getParams() {
        return params;
    }

    public McpCallToolReq setParams(Map<String, Object> params) {
        this.params = params;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpCallToolReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    params: ").append(toIndentedString(params)).append("\n");
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
        McpCallToolReq mcpCallToolReq = (McpCallToolReq) o;
        return Objects.equals(this.name, mcpCallToolReq.name) && Objects.equals(this.params, mcpCallToolReq.params);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, params);
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
