/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * DeleteWorkspaceMemberReq
 */

@Validated

public class DeleteWorkspaceMemberReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("user_ids")
    @Schema(description = "用户", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 1000)
    private List<@Length() String> userIds = new ArrayList<String>();

    public List<String> getUserIds() {
        return userIds;
    }

    public DeleteWorkspaceMemberReq setUserIds(List<String> userIds) {
        this.userIds = userIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DeleteWorkspaceMemberReq {\n");

        sb.append("    userIds: ").append(toIndentedString(userIds)).append("\n");
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
        DeleteWorkspaceMemberReq deleteWorkspaceMemberReq = (DeleteWorkspaceMemberReq) o;
        return Objects.equals(this.userIds, deleteWorkspaceMemberReq.userIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(userIds);
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
