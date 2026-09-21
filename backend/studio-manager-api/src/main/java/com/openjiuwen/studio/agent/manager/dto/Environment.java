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
 * 环境信息
 */
@ApiModel(description = "环境信息")

@Validated

public class Environment implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "环境ID", example = "env-001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "环境名称", example = "生产环境")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "环境描述", example = "生产部署环境")
    private String description = null;

    @JsonProperty("isDefault")
    @Schema(description = "是否为默认环境", example = "true")
    private Boolean isDefault = null;

    @JsonProperty("envVariable")
    @Schema(description = "环境变量", example = "KEY=value")
    private String envVariable = null;

    @JsonProperty("vpcName")
    @Schema(description = "VPC名称", example = "vpc-001")
    private String vpcName = null;

    @JsonProperty("subnetName")
    @Schema(description = "子网名称", example = "subnet-001")
    private String subnetName = null;

    @JsonProperty("vpcCidr")
    @Schema(description = "VPC CIDR", example = "192.168.0.0/16")
    private String vpcCidr = null;

    @JsonProperty("subnetCidr")
    @Schema(description = "子网 CIDR", example = "192.168.1.0/24")
    private String subnetCidr = null;

    @JsonProperty("vpcEp")
    @Schema(description = "VPC终端节点", example = "vpce-001")
    private String vpcEp = null;

    @JsonProperty("statusReason")
    @Schema(description = "状态原因", example = "正常")
    private String statusReason = null;

    @JsonProperty("eip")
    @Schema(description = "弹性公网IP", example = "10.0.0.1")
    private String eip = null;

    @JsonProperty("status")
    @Schema(description = "环境状态", example = "available")
    private String status = null;

    @JsonProperty("createdOn")
    @Schema(description = "创建时间", example = "1700000000000")
    private Long createdOn = null;

    @JsonProperty("updatedOn")
    @Schema(description = "更新时间", example = "1700000000000")
    private Long updatedOn = null;

    public String getId() {
        return id;
    }

    public Environment setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public Environment setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public Environment setDescription(String description) {
        this.description = description;
        return this;
    }

    public Environment setIsDefault(Boolean isDefault) {
        this.isDefault = isDefault;
        return this;
    }

    public Boolean isIsDefault() {
        return isDefault;
    }

    public String getEnvVariable() {
        return envVariable;
    }

    public Environment setEnvVariable(String envVariable) {
        this.envVariable = envVariable;
        return this;
    }

    public String getVpcName() {
        return vpcName;
    }

    public Environment setVpcName(String vpcName) {
        this.vpcName = vpcName;
        return this;
    }

    public String getSubnetName() {
        return subnetName;
    }

    public Environment setSubnetName(String subnetName) {
        this.subnetName = subnetName;
        return this;
    }

    public String getVpcCidr() {
        return vpcCidr;
    }

    public Environment setVpcCidr(String vpcCidr) {
        this.vpcCidr = vpcCidr;
        return this;
    }

    public String getSubnetCidr() {
        return subnetCidr;
    }

    public Environment setSubnetCidr(String subnetCidr) {
        this.subnetCidr = subnetCidr;
        return this;
    }

    public String getVpcEp() {
        return vpcEp;
    }

    public Environment setVpcEp(String vpcEp) {
        this.vpcEp = vpcEp;
        return this;
    }

    public String getStatusReason() {
        return statusReason;
    }

    public Environment setStatusReason(String statusReason) {
        this.statusReason = statusReason;
        return this;
    }

    public String getEip() {
        return eip;
    }

    public Environment setEip(String eip) {
        this.eip = eip;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public Environment setStatus(String status) {
        this.status = status;
        return this;
    }

    public Long getCreatedOn() {
        return createdOn;
    }

    public Environment setCreatedOn(Long createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public Long getUpdatedOn() {
        return updatedOn;
    }

    public Environment setUpdatedOn(Long updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Environment {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    isDefault: ").append(toIndentedString(isDefault)).append("\n");
        sb.append("    envVariable: ").append(toIndentedString(envVariable)).append("\n");
        sb.append("    vpcName: ").append(toIndentedString(vpcName)).append("\n");
        sb.append("    subnetName: ").append(toIndentedString(subnetName)).append("\n");
        sb.append("    vpcCidr: ").append(toIndentedString(vpcCidr)).append("\n");
        sb.append("    subnetCidr: ").append(toIndentedString(subnetCidr)).append("\n");
        sb.append("    vpcEp: ").append(toIndentedString(vpcEp)).append("\n");
        sb.append("    statusReason: ").append(toIndentedString(statusReason)).append("\n");
        sb.append("    eip: ").append(toIndentedString(eip)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
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
        Environment environment = (Environment) o;
        return Objects.equals(this.id, environment.id) && Objects.equals(this.name, environment.name) && Objects.equals(
            this.description, environment.description) && Objects.equals(this.isDefault, environment.isDefault)
            && Objects.equals(this.envVariable, environment.envVariable) && Objects.equals(this.vpcName,
            environment.vpcName) && Objects.equals(this.subnetName, environment.subnetName) && Objects.equals(
            this.vpcCidr, environment.vpcCidr) && Objects.equals(this.subnetCidr, environment.subnetCidr)
            && Objects.equals(this.vpcEp, environment.vpcEp) && Objects.equals(this.statusReason,
            environment.statusReason) && Objects.equals(this.eip, environment.eip) && Objects.equals(this.status,
            environment.status) && Objects.equals(this.createdOn, environment.createdOn) && Objects.equals(
            this.updatedOn, environment.updatedOn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, isDefault, envVariable, vpcName, subnetName, vpcCidr, subnetCidr,
            vpcEp, statusReason, eip, status, createdOn, updatedOn);
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
