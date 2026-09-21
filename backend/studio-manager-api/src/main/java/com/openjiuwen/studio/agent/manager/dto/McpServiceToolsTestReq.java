/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceToolsTestReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("serviceId")
    @Schema(description = "服务ID", example = "example-id-123")
    @Length(max = 64)
    private String serviceId = null;

    @JsonProperty("toolName")
    @Schema(description = "工具名称", example = "示例名称")
    private String toolName = null;

    @JsonProperty("params")
    @Schema(description = "参数", example = "示例字符串")
    @Valid
    @Size()
    private Map<String, Object> params = null;

    public String getServiceId() {
        return serviceId;
    }

    public McpServiceToolsTestReq setServiceId(String serviceId) {
        this.serviceId = serviceId;
        return this;
    }

    public String getToolName() {
        return toolName;
    }

    public McpServiceToolsTestReq setToolName(String toolName) {
        this.toolName = toolName;
        return this;
    }

    public Map<String, Object> getParams() {
        return params;
    }

    public McpServiceToolsTestReq setParams(Map<String, Object> params) {
        this.params = params;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceToolsTestReq {\n");

        sb.append("    serviceId: ").append(toIndentedString(serviceId)).append("\n");
        sb.append("    toolName: ").append(toIndentedString(toolName)).append("\n");
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
        McpServiceToolsTestReq mcpServiceToolsTestReq = (McpServiceToolsTestReq) o;
        return Objects.equals(this.serviceId, mcpServiceToolsTestReq.serviceId) && Objects.equals(this.toolName,
            mcpServiceToolsTestReq.toolName) && Objects.equals(this.params, mcpServiceToolsTestReq.params);
    }

    @Override
    public int hashCode() {
        return Objects.hash(serviceId, toolName, params);
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
