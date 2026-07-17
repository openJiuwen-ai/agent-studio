/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * WorkflowBranch
 */

@Validated

public class WorkflowBranch implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("boolExpression")
    @Valid
    private WorkflowBranchBoolExpression boolExpression = null;

    public String getId() {
        return id;
    }

    public WorkflowBranch setId(String id) {
        this.id = id;
        return this;
    }

    public WorkflowBranchBoolExpression getBoolExpression() {
        return boolExpression;
    }

    public WorkflowBranch setBoolExpression(WorkflowBranchBoolExpression boolExpression) {
        this.boolExpression = boolExpression;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowBranch {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    boolExpression: ").append(toIndentedString(boolExpression)).append("\n");
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
        WorkflowBranch workflowBranch = (WorkflowBranch) o;
        return Objects.equals(this.id, workflowBranch.id) && Objects.equals(this.boolExpression,
            workflowBranch.boolExpression);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, boolExpression);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
