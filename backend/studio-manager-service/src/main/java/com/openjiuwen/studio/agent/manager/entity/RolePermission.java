/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;// RolePermission.java

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public class RolePermission {
    @JsonProperty("roleName")
    private String roleName;

    @JsonProperty("roleDescription")
    private String roleDescription;

    @JsonProperty("permissions")
    private List<String> permissions;

    /**
     * 需创建人校验的权限列表(METHOD#URI)。这些 URI 通过角色权限校验后，
     * 仍需在 Service 层校验资源创建人(仅创建者本人或 OWNER/ADMIN 可操作)，
     * 用于 DEVELOPER/OPERATOR 等"只能改自己创建的"场景。OWNER/ADMIN 不配置此项(全权)。
     */
    @JsonProperty("creatorCheckPermissions")
    private List<String> creatorCheckPermissions;

    // Getters and Setters
    public String getRoleName() {
        return roleName;
    }

    public void setRoleName(String roleName) {
        this.roleName = roleName;
    }

    public String getRoleDescription() {
        return roleDescription;
    }

    public void setRoleDescription(String roleDescription) {
        this.roleDescription = roleDescription;
    }

    public List<String> getPermissions() {
        return permissions;
    }

    public void setPermissions(List<String> permissions) {
        this.permissions = permissions;
    }

    public List<String> getCreatorCheckPermissions() {
        return creatorCheckPermissions;
    }

    public void setCreatorCheckPermissions(List<String> creatorCheckPermissions) {
        this.creatorCheckPermissions = creatorCheckPermissions;
    }

    @Override
    public String toString() {
        return "RolePermission{" + "roleName='" + roleName + '\'' + ", roleDescription='" + roleDescription + '\''
            + ", permissions=" + permissions + ", creatorCheckPermissions=" + creatorCheckPermissions + '}';
    }
}
