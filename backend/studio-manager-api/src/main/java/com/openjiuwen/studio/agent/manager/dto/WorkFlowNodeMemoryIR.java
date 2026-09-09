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
 * IR文件中工作流节点的记忆配置。
 */
@ApiModel(description = "IR文件中工作流节点的记忆配置。")

@Validated

public class WorkFlowNodeMemoryIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("userProfile")
    @Schema(description = "用户profile", example = "{}")
    @Valid
    private WorkFlowNodeUserProfileIR userProfile = null;

    public WorkFlowNodeUserProfileIR getUserProfile() {
        return userProfile;
    }

    public WorkFlowNodeMemoryIR setUserProfile(WorkFlowNodeUserProfileIR userProfile) {
        this.userProfile = userProfile;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkFlowNodeMemoryIR {\n");

        sb.append("    userProfile: ").append(toIndentedString(userProfile)).append("\n");
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
        WorkFlowNodeMemoryIR workFlowNodeMemoryIR = (WorkFlowNodeMemoryIR) o;
        return Objects.equals(this.userProfile, workFlowNodeMemoryIR.userProfile);
    }

    @Override
    public int hashCode() {
        return Objects.hash(userProfile);
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
