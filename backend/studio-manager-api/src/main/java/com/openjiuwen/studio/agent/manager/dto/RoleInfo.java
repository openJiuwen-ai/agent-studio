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
 * 角色。
 */
@ApiModel(description = "角色。")

@Validated

public class RoleInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("roleId")
    @Schema(description = "角色ID", example = "example-id-123")
    private String roleId = null;

    @JsonProperty("roleNameCn")
    @Schema(description = "角色名称cn", example = "示例名称")
    private String roleNameCn = null;

    @JsonProperty("roleNameEn")
    @Schema(description = "角色名称en", example = "{}")
    @Valid
    private Object roleNameEn = null;

    public String getRoleId() {
        return roleId;
    }

    public RoleInfo setRoleId(String roleId) {
        this.roleId = roleId;
        return this;
    }

    public String getRoleNameCn() {
        return roleNameCn;
    }

    public RoleInfo setRoleNameCn(String roleNameCn) {
        this.roleNameCn = roleNameCn;
        return this;
    }

    public Object getRoleNameEn() {
        return roleNameEn;
    }

    public RoleInfo setRoleNameEn(Object roleNameEn) {
        this.roleNameEn = roleNameEn;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RoleInfo {\n");

        sb.append("    roleId: ").append(toIndentedString(roleId)).append("\n");
        sb.append("    roleNameCn: ").append(toIndentedString(roleNameCn)).append("\n");
        sb.append("    roleNameEn: ").append(toIndentedString(roleNameEn)).append("\n");
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
        RoleInfo roleInfo = (RoleInfo) o;
        return Objects.equals(this.roleId, roleInfo.roleId) && Objects.equals(this.roleNameCn, roleInfo.roleNameCn)
            && Objects.equals(this.roleNameEn, roleInfo.roleNameEn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(roleId, roleNameCn, roleNameEn);
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
