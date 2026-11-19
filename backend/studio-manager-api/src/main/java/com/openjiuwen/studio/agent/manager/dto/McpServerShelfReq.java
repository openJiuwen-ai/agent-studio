/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * MCP 服务实例上架到资产广场请求。
 */
@ApiModel(description = "MCP 服务实例上架到资产广场请求")

@Validated

public class McpServerShelfReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("service_id")
    @Schema(description = "MCP服务实例ID（组件库已部署实例）", example = "service-001")
    @NotBlank(message = "service_id is required")
    @Size(max = 64)
    private String serviceId = null;

    @JsonProperty("category")
    @Schema(description = "行业分类ID，关联 t_pe_industry.id", example = "uuid")
    @Size(max = 36)
    private String category = null;

    @JsonProperty("readme")
    @Schema(description = "服务说明（上架时补充的目录展示信息，缺省沿用实例的服务介绍）", example = "提供天气查询服务")
    @Size(max = 4096)
    private String readme = null;

    public String getServiceId() {
        return serviceId;
    }

    public McpServerShelfReq setServiceId(String serviceId) {
        this.serviceId = serviceId;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public McpServerShelfReq setCategory(String category) {
        this.category = category;
        return this;
    }

    public String getReadme() {
        return readme;
    }

    public McpServerShelfReq setReadme(String readme) {
        this.readme = readme;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerShelfReq {\n");
        sb.append("    serviceId: ").append(toIndentedString(serviceId)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    readme: ").append(toIndentedString(readme)).append("\n");
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
        McpServerShelfReq that = (McpServerShelfReq) o;
        return Objects.equals(this.serviceId, that.serviceId) && Objects.equals(this.category, that.category)
            && Objects.equals(this.readme, that.readme);
    }

    @Override
    public int hashCode() {
        return Objects.hash(serviceId, category, readme);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}