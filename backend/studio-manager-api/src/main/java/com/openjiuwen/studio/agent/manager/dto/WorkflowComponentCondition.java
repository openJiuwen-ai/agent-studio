/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * WorkflowComponentCondition
 */

@Validated

public class WorkflowComponentCondition implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("branches")
    @Valid
    @Size()
    private List<WorkflowBranch> branches = null;

    public List<WorkflowBranch> getBranches() {
        return branches;
    }

    public WorkflowComponentCondition setBranches(List<WorkflowBranch> branches) {
        this.branches = branches;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowComponentCondition {\n");

        sb.append("    branches: ").append(toIndentedString(branches)).append("\n");
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
        WorkflowComponentCondition workflowComponentCondition = (WorkflowComponentCondition) o;
        return Objects.equals(this.branches, workflowComponentCondition.branches);
    }

    @Override
    public int hashCode() {
        return Objects.hash(branches);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
