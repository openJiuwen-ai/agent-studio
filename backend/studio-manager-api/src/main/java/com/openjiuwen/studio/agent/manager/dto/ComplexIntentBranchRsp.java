/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 意图包信息分支结果
 */
@ApiModel(description = "意图包信息分支结果")

@Validated

public class ComplexIntentBranchRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("branch_id")
    @Schema(description = "分支ID", example = "branch_001")
    @Length(max = 64)
    private String branchId = null;

    @JsonProperty("intent_id")
    @Schema(description = "意图ID", example = "intent_001")
    @Length(max = 64)
    private String intentId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj_001")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("branch_index")
    @Schema(description = "分支索引", example = "0")
    @Length(max = 64)
    private String branchIndex = null;

    @JsonProperty("name")
    @Schema(description = "分支名称", example = "天气查询")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "分支描述", example = "查询天气信息")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user_001")
    @Length(max = 1024)
    private String creatorId = null;

    @JsonProperty("examples")
    @Schema(description = "示例列表", example = "[\"今天天气怎么样\"]")
    @Valid
    @Size()
    private List<@Length(max = 8096) String> examples = null;

    public String getBranchId() {
        return branchId;
    }

    public ComplexIntentBranchRsp setBranchId(String branchId) {
        this.branchId = branchId;
        return this;
    }

    public String getIntentId() {
        return intentId;
    }

    public ComplexIntentBranchRsp setIntentId(String intentId) {
        this.intentId = intentId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ComplexIntentBranchRsp setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ComplexIntentBranchRsp setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getBranchIndex() {
        return branchIndex;
    }

    public ComplexIntentBranchRsp setBranchIndex(String branchIndex) {
        this.branchIndex = branchIndex;
        return this;
    }

    public String getName() {
        return name;
    }

    public ComplexIntentBranchRsp setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ComplexIntentBranchRsp setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ComplexIntentBranchRsp setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public List<String> getExamples() {
        return examples;
    }

    public ComplexIntentBranchRsp setExamples(List<String> examples) {
        this.examples = examples;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentBranchRsp {\n");

        sb.append("    branchId: ").append(toIndentedString(branchId)).append("\n");
        sb.append("    intentId: ").append(toIndentedString(intentId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    branchIndex: ").append(toIndentedString(branchIndex)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    examples: ").append(toIndentedString(examples)).append("\n");
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
        ComplexIntentBranchRsp complexIntentBranchRsp = (ComplexIntentBranchRsp) o;
        return Objects.equals(this.branchId, complexIntentBranchRsp.branchId) && Objects.equals(this.intentId,
            complexIntentBranchRsp.intentId) && Objects.equals(this.projectId, complexIntentBranchRsp.projectId)
            && Objects.equals(this.workspaceId, complexIntentBranchRsp.workspaceId) && Objects.equals(this.branchIndex,
            complexIntentBranchRsp.branchIndex) && Objects.equals(this.name, complexIntentBranchRsp.name)
            && Objects.equals(this.description, complexIntentBranchRsp.description) && Objects.equals(this.creatorId,
            complexIntentBranchRsp.creatorId) && Objects.equals(this.examples, complexIntentBranchRsp.examples);
    }

    @Override
    public int hashCode() {
        return Objects.hash(branchId, intentId, projectId, workspaceId, branchIndex, name, description, creatorId,
            examples);
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
