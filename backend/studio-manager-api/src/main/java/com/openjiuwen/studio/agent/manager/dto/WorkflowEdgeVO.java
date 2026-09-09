/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流连线。
 */
@ApiModel(description = "工作流连线。")

@Validated

public class WorkflowEdgeVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "连线ID", example = "edge_001")
    private String id = null;

    @JsonProperty("source")
    @Schema(description = "源节点ID", example = "node_001", required = true)
    @NotBlank
    private String source = null;

    @JsonProperty("exception_branch")
    @Schema(description = "是否为异常分支", example = "false")
    private Boolean exceptionBranch = false;

    @JsonProperty("target")
    @Schema(description = "目标节点ID", example = "node_002", required = true)
    @NotBlank
    private String target = null;

    @JsonProperty("branch")
    @Schema(description = "分支标识", example = "branch_1")
    private String branch = null;

    @JsonProperty("sourceBranchId")
    @Schema(description = "源分支ID", example = "source_branch_1")
    private String sourceBranchId = null;

    @JsonProperty("targetBranchId")
    @Schema(description = "目标分支ID", example = "target_branch_1")
    private String targetBranchId = null;

    public String getId() {
        return id;
    }

    public WorkflowEdgeVO setId(String id) {
        this.id = id;
        return this;
    }

    public String getSource() {
        return source;
    }

    public WorkflowEdgeVO setSource(String source) {
        this.source = source;
        return this;
    }

    public WorkflowEdgeVO setExceptionBranch(Boolean exceptionBranch) {
        this.exceptionBranch = exceptionBranch;
        return this;
    }

    public Boolean isExceptionBranch() {
        return exceptionBranch;
    }

    public String getTarget() {
        return target;
    }

    public WorkflowEdgeVO setTarget(String target) {
        this.target = target;
        return this;
    }

    public String getBranch() {
        return branch;
    }

    public WorkflowEdgeVO setBranch(String branch) {
        this.branch = branch;
        return this;
    }

    public String getSourceBranchId() {
        return sourceBranchId;
    }

    public WorkflowEdgeVO setSourceBranchId(String sourceBranchId) {
        this.sourceBranchId = sourceBranchId;
        return this;
    }

    public String getTargetBranchId() {
        return targetBranchId;
    }

    public WorkflowEdgeVO setTargetBranchId(String targetBranchId) {
        this.targetBranchId = targetBranchId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowEdgeVO {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    exceptionBranch: ").append(toIndentedString(exceptionBranch)).append("\n");
        sb.append("    target: ").append(toIndentedString(target)).append("\n");
        sb.append("    branch: ").append(toIndentedString(branch)).append("\n");
        sb.append("    sourceBranchId: ").append(toIndentedString(sourceBranchId)).append("\n");
        sb.append("    targetBranchId: ").append(toIndentedString(targetBranchId)).append("\n");
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
        WorkflowEdgeVO workflowEdgeVO = (WorkflowEdgeVO) o;
        return Objects.equals(this.id, workflowEdgeVO.id) && Objects.equals(this.source, workflowEdgeVO.source)
            && Objects.equals(this.exceptionBranch, workflowEdgeVO.exceptionBranch) && Objects.equals(this.target,
            workflowEdgeVO.target) && Objects.equals(this.branch, workflowEdgeVO.branch) && Objects.equals(
            this.sourceBranchId, workflowEdgeVO.sourceBranchId) && Objects.equals(this.targetBranchId,
            workflowEdgeVO.targetBranchId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, source, exceptionBranch, target, branch, sourceBranchId, targetBranchId);
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
