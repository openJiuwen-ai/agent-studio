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
 * workflow最新版本列表响应体。
 */
@ApiModel(description = "workflow最新版本列表响应体。")

@Validated

public class WorkflowVersionListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    private Long count = null;

    @JsonProperty("workflow_version_list")
    @Schema(description = "工作流版本列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowVersionListItem> workflowVersionList = null;

    public Long getCount() {
        return count;
    }

    public WorkflowVersionListRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<WorkflowVersionListItem> getWorkflowVersionList() {
        return workflowVersionList;
    }

    public WorkflowVersionListRsp setWorkflowVersionList(List<WorkflowVersionListItem> workflowVersionList) {
        this.workflowVersionList = workflowVersionList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowVersionListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    workflowVersionList: ").append(toIndentedString(workflowVersionList)).append("\n");
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
        WorkflowVersionListRsp workflowVersionListRsp = (WorkflowVersionListRsp) o;
        return Objects.equals(this.count, workflowVersionListRsp.count) && Objects.equals(this.workflowVersionList,
            workflowVersionListRsp.workflowVersionList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, workflowVersionList);
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
