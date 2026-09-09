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
 * 团队空间成员角色响应列表。
 */
@ApiModel(description = "团队空间成员角色响应列表。")

@Validated

public class GetWorkspaceMemberRoleRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("roleList")
    @Schema(description = "角色列表", example = "[]")
    @Valid
    @Size()
    private List<RoleInfo> roleList = null;

    public List<RoleInfo> getRoleList() {
        return roleList;
    }

    public GetWorkspaceMemberRoleRsp setRoleList(List<RoleInfo> roleList) {
        this.roleList = roleList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class GetWorkspaceMemberRoleRsp {\n");

        sb.append("    roleList: ").append(toIndentedString(roleList)).append("\n");
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
        GetWorkspaceMemberRoleRsp getWorkspaceMemberRoleRsp = (GetWorkspaceMemberRoleRsp) o;
        return Objects.equals(this.roleList, getWorkspaceMemberRoleRsp.roleList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(roleList);
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
