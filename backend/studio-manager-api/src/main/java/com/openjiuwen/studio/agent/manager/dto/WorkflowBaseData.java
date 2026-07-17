/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流基础信息
 */
@ApiModel(description = "工作流基础信息")

@Validated

public class WorkflowBaseData implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("flow_id")
    @Length(max = 64)
    private String flowId = null;

    @JsonProperty("flow_name")
    @Length(max = 1000)
    private String flowName = null;

    public String getFlowId() {
        return flowId;
    }

    public WorkflowBaseData setFlowId(String flowId) {
        this.flowId = flowId;
        return this;
    }

    public String getFlowName() {
        return flowName;
    }

    public WorkflowBaseData setFlowName(String flowName) {
        this.flowName = flowName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowBaseData {\n");

        sb.append("    flowId: ").append(toIndentedString(flowId)).append("\n");
        sb.append("    flowName: ").append(toIndentedString(flowName)).append("\n");
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
        WorkflowBaseData workflowBaseData = (WorkflowBaseData) o;
        return Objects.equals(this.flowId, workflowBaseData.flowId) && Objects.equals(this.flowName,
            workflowBaseData.flowName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(flowId, flowName);
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
