/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 安全组信息
 */
@ApiModel(description = "安全组信息")

@Validated

public class EnvironmentInfoRequest implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "安全组名称", example = "my-security-group")
    @Pattern(regexp = "^[a-zA-Z][a-zA-Z0-9-]{3,47}$")
    private String name = null;

    @JsonProperty("id")
    @Schema(description = "安全组ID", example = "sg-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("description")
    @Schema(description = "安全组描述", example = "用于Agent运行的安全组")
    @Pattern(regexp = "^(?:[\\u4e00-\\u9fa5a-zA-Z0-9][\\u4e00-\\u9fa5_a-zA-Z0-9\\-()]{0,127})?$")
    @Length(max = 128)
    private String description = null;

    @JsonProperty("vpcId")
    @Schema(description = "VPC ID", example = "vpc-001")
    @Length(min = 1, max = 64)
    private String vpcId = null;

    @JsonProperty("subnetId")
    @Schema(description = "子网ID", example = "subnet-001")
    @Length(min = 1, max = 64)
    private String subnetId = null;

    @JsonProperty("isDefault")
    @Schema(description = "是否为默认安全组", example = "false")
    private Boolean isDefault = false;

    public String getName() {
        return name;
    }

    public EnvironmentInfoRequest setName(String name) {
        this.name = name;
        return this;
    }

    public String getId() {
        return id;
    }

    public EnvironmentInfoRequest setId(String id) {
        this.id = id;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public EnvironmentInfoRequest setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getVpcId() {
        return vpcId;
    }

    public EnvironmentInfoRequest setVpcId(String vpcId) {
        this.vpcId = vpcId;
        return this;
    }

    public String getSubnetId() {
        return subnetId;
    }

    public EnvironmentInfoRequest setSubnetId(String subnetId) {
        this.subnetId = subnetId;
        return this;
    }

    public EnvironmentInfoRequest setIsDefault(Boolean isDefault) {
        this.isDefault = isDefault;
        return this;
    }

    public Boolean isIsDefault() {
        return isDefault;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentInfoRequest {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    vpcId: ").append(toIndentedString(vpcId)).append("\n");
        sb.append("    subnetId: ").append(toIndentedString(subnetId)).append("\n");
        sb.append("    isDefault: ").append(toIndentedString(isDefault)).append("\n");
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
        EnvironmentInfoRequest environmentInfoRequest = (EnvironmentInfoRequest) o;
        return Objects.equals(this.name, environmentInfoRequest.name) && Objects.equals(this.id,
            environmentInfoRequest.id) && Objects.equals(this.description, environmentInfoRequest.description)
            && Objects.equals(this.vpcId, environmentInfoRequest.vpcId) && Objects.equals(this.subnetId,
            environmentInfoRequest.subnetId) && Objects.equals(this.isDefault, environmentInfoRequest.isDefault);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, id, description, vpcId, subnetId, isDefault);
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
