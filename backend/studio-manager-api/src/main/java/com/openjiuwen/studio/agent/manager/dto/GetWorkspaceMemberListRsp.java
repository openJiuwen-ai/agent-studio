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
 * 团队空间成员响应列表。
 */
@ApiModel(description = "团队空间成员响应列表。")

@Validated

public class GetWorkspaceMemberListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    @JsonProperty("workspaceList")
    @Schema(description = "工作空间列表", example = "[]")
    @Valid
    @Size()
    private List<WorkspaceMemberInfo> workspaceList = null;

    public Integer getCount() {
        return count;
    }

    public GetWorkspaceMemberListRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<WorkspaceMemberInfo> getWorkspaceList() {
        return workspaceList;
    }

    public GetWorkspaceMemberListRsp setWorkspaceList(List<WorkspaceMemberInfo> workspaceList) {
        this.workspaceList = workspaceList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class GetWorkspaceMemberListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    workspaceList: ").append(toIndentedString(workspaceList)).append("\n");
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
        GetWorkspaceMemberListRsp getWorkspaceMemberListRsp = (GetWorkspaceMemberListRsp) o;
        return Objects.equals(this.count, getWorkspaceMemberListRsp.count) && Objects.equals(this.workspaceList,
            getWorkspaceMemberListRsp.workspaceList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, workspaceList);
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
