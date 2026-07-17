/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 条件表达式对象
 */
@ApiModel(description = "条件表达式对象")

@Validated

public class WorkflowBranchBoolExpression implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("operator")
    private String operator = null;

    @JsonProperty("expressions")
    @Valid
    @Size()
    private List<@Length() String> expressions = null;

    public String getOperator() {
        return operator;
    }

    public WorkflowBranchBoolExpression setOperator(String operator) {
        this.operator = operator;
        return this;
    }

    public List<String> getExpressions() {
        return expressions;
    }

    public WorkflowBranchBoolExpression setExpressions(List<String> expressions) {
        this.expressions = expressions;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowBranchBoolExpression {\n");

        sb.append("    operator: ").append(toIndentedString(operator)).append("\n");
        sb.append("    expressions: ").append(toIndentedString(expressions)).append("\n");
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
        WorkflowBranchBoolExpression workflowBranchBoolExpression = (WorkflowBranchBoolExpression) o;
        return Objects.equals(this.operator, workflowBranchBoolExpression.operator) && Objects.equals(this.expressions,
            workflowBranchBoolExpression.expressions);
    }

    @Override
    public int hashCode() {
        return Objects.hash(operator, expressions);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
