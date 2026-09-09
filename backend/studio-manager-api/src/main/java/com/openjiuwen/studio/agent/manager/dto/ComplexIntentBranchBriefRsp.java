/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 意图包信息分支概要结果
 */
@ApiModel(description = "意图包信息分支概要结果")

@Validated

public class ComplexIntentBranchBriefRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("branch_id")
    @Schema(description = "分支ID", example = "example-id-123")
    @Length(max = 64)
    private String branchId = null;

    public String getBranchId() {
        return branchId;
    }

    public ComplexIntentBranchBriefRsp setBranchId(String branchId) {
        this.branchId = branchId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentBranchBriefRsp {\n");

        sb.append("    branchId: ").append(toIndentedString(branchId)).append("\n");
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
        ComplexIntentBranchBriefRsp complexIntentBranchBriefRsp = (ComplexIntentBranchBriefRsp) o;
        return Objects.equals(this.branchId, complexIntentBranchBriefRsp.branchId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(branchId);
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
