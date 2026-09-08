/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * workflowVersionListRsp搜索返回item。
 */
@ApiModel(description = "workflowVersionListRsp搜索返回item。")

@Validated

public class WorkflowVersionListItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "wf_001")
    private String workflowId = null;

    @JsonProperty("name")
    @Schema(description = "工作流名称", example = "我的工作流")
    private String name = null;

    @JsonProperty("avatar")
    @Schema(description = "头像", example = "https://example.com/avatar.png")
    private String avatar = null;

    @JsonProperty("code")
    @Schema(description = "工作流编码", example = "WF001")
    private String code = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "这是一个工作流")
    private String description = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "workflow")
    private String type = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "ver_001")
    private String versionId = null;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "v1.0.0")
    private String versionName = null;

    @JsonProperty("reference_workflows")
    @Schema(description = "引用工作流", example = "[]")
    private String referenceWorkflows = null;

    @JsonProperty("reference_agents")
    @Schema(description = "引用智能体", example = "[]")
    private String referenceAgents = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    public String getWorkflowId() {
        return workflowId;
    }

    public WorkflowVersionListItem setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkflowVersionListItem setName(String name) {
        this.name = name;
        return this;
    }

    public String getAvatar() {
        return avatar;
    }

    public WorkflowVersionListItem setAvatar(String avatar) {
        this.avatar = avatar;
        return this;
    }

    public String getCode() {
        return code;
    }

    public WorkflowVersionListItem setCode(String code) {
        this.code = code;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowVersionListItem setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public WorkflowVersionListItem setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowVersionListItem setType(String type) {
        this.type = type;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public WorkflowVersionListItem setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getVersionName() {
        return versionName;
    }

    public WorkflowVersionListItem setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public String getReferenceWorkflows() {
        return referenceWorkflows;
    }

    public WorkflowVersionListItem setReferenceWorkflows(String referenceWorkflows) {
        this.referenceWorkflows = referenceWorkflows;
        return this;
    }

    public String getReferenceAgents() {
        return referenceAgents;
    }

    public WorkflowVersionListItem setReferenceAgents(String referenceAgents) {
        this.referenceAgents = referenceAgents;
        return this;
    }

    public WorkflowVersionListItem setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowVersionListItem {\n");

        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    avatar: ").append(toIndentedString(avatar)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    referenceWorkflows: ").append(toIndentedString(referenceWorkflows)).append("\n");
        sb.append("    referenceAgents: ").append(toIndentedString(referenceAgents)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
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
        WorkflowVersionListItem workflowVersionListItem = (WorkflowVersionListItem) o;
        return Objects.equals(this.workflowId, workflowVersionListItem.workflowId) && Objects.equals(this.name,
            workflowVersionListItem.name) && Objects.equals(this.avatar, workflowVersionListItem.avatar)
            && Objects.equals(this.code, workflowVersionListItem.code) && Objects.equals(this.description,
            workflowVersionListItem.description) && Objects.equals(this.creator, workflowVersionListItem.creator)
            && Objects.equals(this.type, workflowVersionListItem.type) && Objects.equals(this.versionId,
            workflowVersionListItem.versionId) && Objects.equals(this.versionName, workflowVersionListItem.versionName)
            && Objects.equals(this.referenceWorkflows, workflowVersionListItem.referenceWorkflows) && Objects.equals(
            this.referenceAgents, workflowVersionListItem.referenceAgents) && Objects.equals(this.customizeNode,
            workflowVersionListItem.customizeNode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workflowId, name, avatar, code, description, creator, type, versionId, versionName,
            referenceWorkflows, referenceAgents, customizeNode);
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
