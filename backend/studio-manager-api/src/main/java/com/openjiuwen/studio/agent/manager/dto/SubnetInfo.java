/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 子网信息
 */
@ApiModel(description = "子网信息")

@Validated

public class SubnetInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "子网ID", example = "subnet-001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "子网名称", example = "subnet-name")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "子网描述")
    private String description = null;

    @JsonProperty("cidr")
    @Schema(description = "CIDR网段", example = "192.168.0.0/24")
    private String cidr = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "ACTIVE")
    private String status = null;

    public String getId() {
        return id;
    }

    public SubnetInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public SubnetInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public SubnetInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getCidr() {
        return cidr;
    }

    public SubnetInfo setCidr(String cidr) {
        this.cidr = cidr;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public SubnetInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SubnetInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    cidr: ").append(toIndentedString(cidr)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        SubnetInfo subnetInfo = (SubnetInfo) o;
        return Objects.equals(this.id, subnetInfo.id) && Objects.equals(this.name, subnetInfo.name) && Objects.equals(
            this.description, subnetInfo.description) && Objects.equals(this.cidr, subnetInfo.cidr) && Objects.equals(
            this.status, subnetInfo.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, cidr, status);
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
