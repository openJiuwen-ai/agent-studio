/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * WorkflowInfo
 */

@Validated

public class WorkflowInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "workflow-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String workflowId = null;

    @JsonProperty("trace_id")
    @Schema(description = "链路追踪ID", example = "trace-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String traceId = null;

    @JsonProperty("name")
    @Schema(description = "工作流名称", example = "我的工作流")
    @Length(min = 2, max = 64)
    private String name = null;

    @JsonProperty("code")
    @Schema(description = "工作流编码", example = "workflow-code-01")
    @Length(min = 2, max = 64)
    private String code = null;

    @JsonProperty("description")
    @Schema(description = "工作流描述", example = "用于自动回复的工作流")
    @Length(min = 1, max = 1024)
    private String description = null;

    @JsonProperty("avatar")
    @Schema(description = "工作流头像", example = "data:image/png;base64,iVBORw0KGgo=")
    @Length(max = 1024)
    private String avatar = null;

    @JsonProperty("status")
    @Schema(description = "工作流状态", example = "1")
    @Range(min = -10L, max = 10L)
    private Integer status = null;

    @JsonProperty("trigger_list")
    @Schema(description = "触发器列表", example = "[]")
    @Valid
    @Size(max = 100)
    private List<TriggerConfig> triggerList = null;

    @JsonProperty("workflow_details")
    @Schema(description = "工作流详情", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> workflowDetails = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间（毫秒时间戳）", example = "1714521600000")
    @Range(max = 9999999999999L)
    private Long createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间（毫秒时间戳）", example = "1714608000000")
    @Range(max = 9999999999999L)
    private Long updateTime = null;

    @JsonProperty("publish_time")
    @Schema(description = "发布时间（毫秒时间戳）", example = "1714694400000")
    @Range(max = 9999999999999L)
    private Long publishTime = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user001")
    @Length(max = 64)
    private String creator = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "user002")
    @Length(max = 64)
    private String updater = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("domain_id")
    @Schema(description = "领域ID", example = "domain-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String domainId = null;

    @JsonProperty("dsl_path")
    @Schema(description = "DSL文件路径", example = "/workflows/example.dsl")
    @Length(max = 256)
    private String dslPath = null;

    @JsonProperty("is_drag")
    @Schema(description = "是否为拖拽创建", example = "false")
    private Boolean isDrag = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "creator-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String creatorId = null;

    @JsonProperty("type")
    @Schema(description = "工作流类型", example = "chat")
    @Length(max = 32)
    private String type = null;

    @JsonProperty("ref_workflows")
    @Schema(description = "引用的工作流列表", example = "[]")
    @Valid
    @Size(max = 1000)
    private List<WorkflowInfoRefWorkflows> refWorkflows = null;

    @JsonProperty("test_status")
    @Schema(description = "测试状态", example = "1")
    @Range(max = 9L)
    private Integer testStatus = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否包含自定义节点", example = "false")
    private Boolean customizeNode = null;

    public String getWorkflowId() {
        return workflowId;
    }

    public WorkflowInfo setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getTraceId() {
        return traceId;
    }

    public WorkflowInfo setTraceId(String traceId) {
        this.traceId = traceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkflowInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getCode() {
        return code;
    }

    public WorkflowInfo setCode(String code) {
        this.code = code;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getAvatar() {
        return avatar;
    }

    public WorkflowInfo setAvatar(String avatar) {
        this.avatar = avatar;
        return this;
    }

    public Integer getStatus() {
        return status;
    }

    public WorkflowInfo setStatus(Integer status) {
        this.status = status;
        return this;
    }

    public List<TriggerConfig> getTriggerList() {
        return triggerList;
    }

    public WorkflowInfo setTriggerList(List<TriggerConfig> triggerList) {
        this.triggerList = triggerList;
        return this;
    }

    public Map<String, Object> getWorkflowDetails() {
        return workflowDetails;
    }

    public WorkflowInfo setWorkflowDetails(Map<String, Object> workflowDetails) {
        this.workflowDetails = workflowDetails;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public WorkflowInfo setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public WorkflowInfo setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public Long getPublishTime() {
        return publishTime;
    }

    public WorkflowInfo setPublishTime(Long publishTime) {
        this.publishTime = publishTime;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public WorkflowInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public WorkflowInfo setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public WorkflowInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public WorkflowInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDomainId() {
        return domainId;
    }

    public WorkflowInfo setDomainId(String domainId) {
        this.domainId = domainId;
        return this;
    }

    public String getDslPath() {
        return dslPath;
    }

    public WorkflowInfo setDslPath(String dslPath) {
        this.dslPath = dslPath;
        return this;
    }

    public WorkflowInfo setIsDrag(Boolean isDrag) {
        this.isDrag = isDrag;
        return this;
    }

    public Boolean isIsDrag() {
        return isDrag;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public WorkflowInfo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowInfo setType(String type) {
        this.type = type;
        return this;
    }

    public List<WorkflowInfoRefWorkflows> getRefWorkflows() {
        return refWorkflows;
    }

    public WorkflowInfo setRefWorkflows(List<WorkflowInfoRefWorkflows> refWorkflows) {
        this.refWorkflows = refWorkflows;
        return this;
    }

    public Integer getTestStatus() {
        return testStatus;
    }

    public WorkflowInfo setTestStatus(Integer testStatus) {
        this.testStatus = testStatus;
        return this;
    }

    public WorkflowInfo setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowInfo {\n");

        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    traceId: ").append(toIndentedString(traceId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    avatar: ").append(toIndentedString(avatar)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    triggerList: ").append(toIndentedString(triggerList)).append("\n");
        sb.append("    workflowDetails: ").append(toIndentedString(workflowDetails)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    publishTime: ").append(toIndentedString(publishTime)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    domainId: ").append(toIndentedString(domainId)).append("\n");
        sb.append("    dslPath: ").append(toIndentedString(dslPath)).append("\n");
        sb.append("    isDrag: ").append(toIndentedString(isDrag)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    refWorkflows: ").append(toIndentedString(refWorkflows)).append("\n");
        sb.append("    testStatus: ").append(toIndentedString(testStatus)).append("\n");
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
        WorkflowInfo workflowInfo = (WorkflowInfo) o;
        return Objects.equals(this.workflowId, workflowInfo.workflowId) && Objects.equals(this.traceId,
            workflowInfo.traceId) && Objects.equals(this.name, workflowInfo.name) && Objects.equals(this.code,
            workflowInfo.code) && Objects.equals(this.description, workflowInfo.description) && Objects.equals(
            this.avatar, workflowInfo.avatar) && Objects.equals(this.status, workflowInfo.status) && Objects.equals(
            this.triggerList, workflowInfo.triggerList) && Objects.equals(this.workflowDetails,
            workflowInfo.workflowDetails) && Objects.equals(this.createTime, workflowInfo.createTime) && Objects.equals(
            this.updateTime, workflowInfo.updateTime) && Objects.equals(this.publishTime, workflowInfo.publishTime)
            && Objects.equals(this.creator, workflowInfo.creator) && Objects.equals(this.updater, workflowInfo.updater)
            && Objects.equals(this.projectId, workflowInfo.projectId) && Objects.equals(this.workspaceId,
            workflowInfo.workspaceId) && Objects.equals(this.domainId, workflowInfo.domainId) && Objects.equals(
            this.dslPath, workflowInfo.dslPath) && Objects.equals(this.isDrag, workflowInfo.isDrag) && Objects.equals(
            this.creatorId, workflowInfo.creatorId) && Objects.equals(this.type, workflowInfo.type) && Objects.equals(
            this.refWorkflows, workflowInfo.refWorkflows) && Objects.equals(this.testStatus, workflowInfo.testStatus)
            && Objects.equals(this.customizeNode, workflowInfo.customizeNode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workflowId, traceId, name, code, description, avatar, status, triggerList, workflowDetails,
            createTime, updateTime, publishTime, creator, updater, projectId, workspaceId, domainId, dslPath, isDrag,
            creatorId, type, refWorkflows, testStatus, customizeNode);
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
