/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 分支节点config对象。
 */
@ApiModel(description = "分支节点config对象。")

@Validated

public class WorkflowBranchConfigVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("logic")
    @Schema(description = "logic", example = "STRING", required = true)
    @NotNull
    private LogicEnum logic = null;

    @JsonProperty("conditions")
    @Schema(description = "conditions", example = "[]")
    @Valid
    @Size()
    private List<WorkflowBranchConfigVOConditions> conditions = null;

    public LogicEnum getLogic() {
        return logic;
    }

    public WorkflowBranchConfigVO setLogic(LogicEnum logic) {
        this.logic = logic;
        return this;
    }

    public List<WorkflowBranchConfigVOConditions> getConditions() {
        return conditions;
    }

    public WorkflowBranchConfigVO setConditions(List<WorkflowBranchConfigVOConditions> conditions) {
        this.conditions = conditions;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowBranchConfigVO {\n");

        sb.append("    logic: ").append(toIndentedString(logic)).append("\n");
        sb.append("    conditions: ").append(toIndentedString(conditions)).append("\n");
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
        WorkflowBranchConfigVO workflowBranchConfigVO = (WorkflowBranchConfigVO) o;
        return Objects.equals(this.logic, workflowBranchConfigVO.logic) && Objects.equals(this.conditions,
            workflowBranchConfigVO.conditions);
    }

    @Override
    public int hashCode() {
        return Objects.hash(logic, conditions);
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

    /**
     * 逻辑操作符。
     */
    public enum LogicEnum {
        AND("and"),

        OR("or");

        private String value;

        LogicEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static LogicEnum fromValue(String text) {
            for (LogicEnum b : LogicEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
