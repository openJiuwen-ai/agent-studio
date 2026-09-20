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
 * 关联组件对象。
 */
@ApiModel(description = "关联组件对象。")

@Validated

public class WorkflowReference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "wf_001")
    private String workflowId = null;

    @JsonProperty("workflow_name")
    @Schema(description = "工作流名称", example = "审批流程")
    private String workflowName = null;

    @JsonProperty("code")
    @Schema(description = "编码", example = "workflow_001")
    private String code = null;

    @JsonProperty("workflow_icon")
    @Schema(description = "工作流图标", example = "icon.png")
    private String workflowIcon = null;

    @JsonProperty("workflow_parameter")
    @Schema(description = "工作流参数", example = "{}")
    private String workflowParameter = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "这是一个工作流")
    @Length(min = 1, max = 256)
    private String desc = null;

    @JsonProperty("last_version_id")
    @Schema(description = "最新版本ID", example = "v1")
    private String lastVersionId = null;

    @JsonProperty("last_version_name")
    @Schema(description = "最新版本名称", example = "v1.0.0")
    private String lastVersionName = null;

    public String getWorkflowId() {
        return workflowId;
    }

    public WorkflowReference setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowName() {
        return workflowName;
    }

    public WorkflowReference setWorkflowName(String workflowName) {
        this.workflowName = workflowName;
        return this;
    }

    public String getCode() {
        return code;
    }

    public WorkflowReference setCode(String code) {
        this.code = code;
        return this;
    }

    public String getWorkflowIcon() {
        return workflowIcon;
    }

    public WorkflowReference setWorkflowIcon(String workflowIcon) {
        this.workflowIcon = workflowIcon;
        return this;
    }

    public String getWorkflowParameter() {
        return workflowParameter;
    }

    public WorkflowReference setWorkflowParameter(String workflowParameter) {
        this.workflowParameter = workflowParameter;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public WorkflowReference setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getLastVersionId() {
        return lastVersionId;
    }

    public WorkflowReference setLastVersionId(String lastVersionId) {
        this.lastVersionId = lastVersionId;
        return this;
    }

    public String getLastVersionName() {
        return lastVersionName;
    }

    public WorkflowReference setLastVersionName(String lastVersionName) {
        this.lastVersionName = lastVersionName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowReference {\n");

        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    workflowName: ").append(toIndentedString(workflowName)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    workflowIcon: ").append(toIndentedString(workflowIcon)).append("\n");
        sb.append("    workflowParameter: ").append(toIndentedString(workflowParameter)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    lastVersionId: ").append(toIndentedString(lastVersionId)).append("\n");
        sb.append("    lastVersionName: ").append(toIndentedString(lastVersionName)).append("\n");
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
        WorkflowReference workflowReference = (WorkflowReference) o;
        return Objects.equals(this.workflowId, workflowReference.workflowId) && Objects.equals(this.workflowName,
            workflowReference.workflowName) && Objects.equals(this.code, workflowReference.code) && Objects.equals(
            this.workflowIcon, workflowReference.workflowIcon) && Objects.equals(this.workflowParameter,
            workflowReference.workflowParameter) && Objects.equals(this.desc, workflowReference.desc) && Objects.equals(
            this.lastVersionId, workflowReference.lastVersionId) && Objects.equals(this.lastVersionName,
            workflowReference.lastVersionName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workflowId, workflowName, code, workflowIcon, workflowParameter, desc, lastVersionId,
            lastVersionName);
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
