/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryWorkspaceMemberListQo: converted from multi query params
 */
@ApiModel(description = "QueryWorkspaceMemberListQo: converted from multi query params")

@Validated

public class QueryWorkspaceMemberListQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("member_name")
    @Schema(description = "成员名称", example = "user001")
    private String memberName = null;

    @JsonProperty("role")
    @Schema(description = "角色", example = "admin")
    private String role = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    private Integer pageNum = 1;

    @JsonProperty("page_size")
    @Schema(description = "每页数量", example = "10")
    private Integer pageSize = 10;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public QueryWorkspaceMemberListQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getMemberName() {
        return memberName;
    }

    public QueryWorkspaceMemberListQo setMemberName(String memberName) {
        this.memberName = memberName;
        return this;
    }

    public String getRole() {
        return role;
    }

    public QueryWorkspaceMemberListQo setRole(String role) {
        this.role = role;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public QueryWorkspaceMemberListQo setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public QueryWorkspaceMemberListQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryWorkspaceMemberListQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    memberName: ").append(toIndentedString(memberName)).append("\n");
        sb.append("    role: ").append(toIndentedString(role)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
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
        QueryWorkspaceMemberListQo queryWorkspaceMemberListQo = (QueryWorkspaceMemberListQo) o;
        return Objects.equals(this.workspaceId, queryWorkspaceMemberListQo.workspaceId) && Objects.equals(
            this.memberName, queryWorkspaceMemberListQo.memberName) && Objects.equals(this.role,
            queryWorkspaceMemberListQo.role) && Objects.equals(this.pageNum, queryWorkspaceMemberListQo.pageNum)
            && Objects.equals(this.pageSize, queryWorkspaceMemberListQo.pageSize);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, memberName, role, pageNum, pageSize);
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
