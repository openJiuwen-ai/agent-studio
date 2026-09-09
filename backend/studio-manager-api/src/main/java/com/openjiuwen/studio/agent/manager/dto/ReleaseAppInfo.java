/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 发布应用信息。
 */
@ApiModel(description = "发布应用信息。")

@Validated

public class ReleaseAppInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1.0.0", required = true)
    @NotBlank
    private String versionId = null;

    @JsonProperty("app_id")
    @Schema(description = "应用ID", example = "app-123456", required = true)
    @NotBlank
    private String appId = null;

    @JsonProperty("app_type")
    @Schema(description = "应用类型", example = "agent")
    private String appType = null;

    @JsonProperty("sub_type")
    @Schema(description = "应用子类型", example = "chat")
    @Length(max = 100)
    private String subType = null;

    @JsonProperty("name")
    @Schema(description = "应用名称", example = "智能助手")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "应用描述", example = "这是一个智能助手应用")
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "应用图标URL", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("prologue")
    @Schema(description = "开场白", example = "您好，有什么可以帮您？")
    private String prologue = null;

    @JsonProperty("suggest_queries")
    @Schema(description = "推荐问题列表", example = "[\"如何使用\",\"功能介绍\"]")
    @Valid
    @Size()
    private List<@Length() String> suggestQueries = null;

    @JsonProperty("workflow_type")
    @Schema(description = "工作流类型", example = "standard")
    private String workflowType = null;

    @JsonProperty("nodes")
    @Schema(description = "工作流节点列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowNodeVO> nodes = null;

    @JsonProperty("voice_interaction")
    @Schema(description = "语音交互配置", example = "{}")
    @Valid
    private VoiceInteraction voiceInteraction = null;

    @JsonProperty("memory_repo_id")
    @Schema(description = "记忆库ID", example = "repo-123456")
    private String memoryRepoId = null;

    public String getVersionId() {
        return versionId;
    }

    public ReleaseAppInfo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getAppId() {
        return appId;
    }

    public ReleaseAppInfo setAppId(String appId) {
        this.appId = appId;
        return this;
    }

    public String getAppType() {
        return appType;
    }

    public ReleaseAppInfo setAppType(String appType) {
        this.appType = appType;
        return this;
    }

    public String getSubType() {
        return subType;
    }

    public ReleaseAppInfo setSubType(String subType) {
        this.subType = subType;
        return this;
    }

    public String getName() {
        return name;
    }

    public ReleaseAppInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ReleaseAppInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ReleaseAppInfo setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getPrologue() {
        return prologue;
    }

    public ReleaseAppInfo setPrologue(String prologue) {
        this.prologue = prologue;
        return this;
    }

    public List<String> getSuggestQueries() {
        return suggestQueries;
    }

    public ReleaseAppInfo setSuggestQueries(List<String> suggestQueries) {
        this.suggestQueries = suggestQueries;
        return this;
    }

    public String getWorkflowType() {
        return workflowType;
    }

    public ReleaseAppInfo setWorkflowType(String workflowType) {
        this.workflowType = workflowType;
        return this;
    }

    public List<WorkflowNodeVO> getNodes() {
        return nodes;
    }

    public ReleaseAppInfo setNodes(List<WorkflowNodeVO> nodes) {
        this.nodes = nodes;
        return this;
    }

    public VoiceInteraction getVoiceInteraction() {
        return voiceInteraction;
    }

    public ReleaseAppInfo setVoiceInteraction(VoiceInteraction voiceInteraction) {
        this.voiceInteraction = voiceInteraction;
        return this;
    }

    public String getMemoryRepoId() {
        return memoryRepoId;
    }

    public ReleaseAppInfo setMemoryRepoId(String memoryRepoId) {
        this.memoryRepoId = memoryRepoId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ReleaseAppInfo {\n");

        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    appId: ").append(toIndentedString(appId)).append("\n");
        sb.append("    appType: ").append(toIndentedString(appType)).append("\n");
        sb.append("    subType: ").append(toIndentedString(subType)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    prologue: ").append(toIndentedString(prologue)).append("\n");
        sb.append("    suggestQueries: ").append(toIndentedString(suggestQueries)).append("\n");
        sb.append("    workflowType: ").append(toIndentedString(workflowType)).append("\n");
        sb.append("    nodes: ").append(toIndentedString(nodes)).append("\n");
        sb.append("    voiceInteraction: ").append(toIndentedString(voiceInteraction)).append("\n");
        sb.append("    memoryRepoId: ").append(toIndentedString(memoryRepoId)).append("\n");
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
        ReleaseAppInfo releaseAppInfo = (ReleaseAppInfo) o;
        return Objects.equals(this.versionId, releaseAppInfo.versionId) && Objects.equals(this.appId,
            releaseAppInfo.appId) && Objects.equals(this.appType, releaseAppInfo.appType) && Objects.equals(
            this.subType, releaseAppInfo.subType) && Objects.equals(this.name, releaseAppInfo.name) && Objects.equals(
            this.description, releaseAppInfo.description) && Objects.equals(this.icon, releaseAppInfo.icon)
            && Objects.equals(this.prologue, releaseAppInfo.prologue) && Objects.equals(this.suggestQueries,
            releaseAppInfo.suggestQueries) && Objects.equals(this.workflowType, releaseAppInfo.workflowType)
            && Objects.equals(this.nodes, releaseAppInfo.nodes) && Objects.equals(this.voiceInteraction,
            releaseAppInfo.voiceInteraction) && Objects.equals(this.memoryRepoId, releaseAppInfo.memoryRepoId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionId, appId, appType, subType, name, description, icon, prologue, suggestQueries,
            workflowType, nodes, voiceInteraction, memoryRepoId);
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
