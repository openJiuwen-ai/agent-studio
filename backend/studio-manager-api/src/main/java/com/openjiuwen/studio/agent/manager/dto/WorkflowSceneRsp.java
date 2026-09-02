/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 场景化应用详细信息。
 */
@ApiModel(description = "场景化应用详细信息。")

@Validated

public class WorkflowSceneRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "智能客服", required = true)
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "智能客服场景应用", required = true)
    @NotBlank
    @Length(max = 128)
    private String desc = null;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "wf_001", required = true)
    @NotBlank
    private String workflowId = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> tags = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "scene")
    private String type = null;

    @JsonProperty("inputs")
    @Schema(description = "输入参数列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<WorkflowFrontParam> inputs = new ArrayList<WorkflowFrontParam>();

    @JsonProperty("outputs")
    @Schema(description = "输出参数列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<WorkflowFrontParam> outputs = new ArrayList<WorkflowFrontParam>();

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user_001")
    private String creator = null;

    @JsonProperty("publish_time")
    @Schema(description = "发布时间", example = "2026-01-01T00:00:00Z", required = true)
    @NotNull
    private Date publishTime = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1.0.0", required = true)
    @NotBlank
    private String versionId = null;

    @JsonProperty("prologue")
    @Schema(description = "开场白", example = "你好，请问有什么可以帮助您？")
    private String prologue = null;

    @JsonProperty("suggest_queries")
    @Schema(description = "建议查询列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> suggestQueries = null;

    @JsonProperty("free_trial_quota")
    @Schema(description = "免费试用额度")
    @Valid
    private FreeTrialQuota freeTrialQuota = null;

    public String getName() {
        return name;
    }

    public WorkflowSceneRsp setName(String name) {
        this.name = name;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public WorkflowSceneRsp setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getWorkflowId() {
        return workflowId;
    }

    public WorkflowSceneRsp setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public WorkflowSceneRsp setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public List<String> getTags() {
        return tags;
    }

    public WorkflowSceneRsp setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowSceneRsp setType(String type) {
        this.type = type;
        return this;
    }

    public List<WorkflowFrontParam> getInputs() {
        return inputs;
    }

    public WorkflowSceneRsp setInputs(List<WorkflowFrontParam> inputs) {
        this.inputs = inputs;
        return this;
    }

    public List<WorkflowFrontParam> getOutputs() {
        return outputs;
    }

    public WorkflowSceneRsp setOutputs(List<WorkflowFrontParam> outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public WorkflowSceneRsp setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public Date getPublishTime() {
        return publishTime;
    }

    public WorkflowSceneRsp setPublishTime(Date publishTime) {
        this.publishTime = publishTime;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public WorkflowSceneRsp setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getPrologue() {
        return prologue;
    }

    public WorkflowSceneRsp setPrologue(String prologue) {
        this.prologue = prologue;
        return this;
    }

    public List<String> getSuggestQueries() {
        return suggestQueries;
    }

    public WorkflowSceneRsp setSuggestQueries(List<String> suggestQueries) {
        this.suggestQueries = suggestQueries;
        return this;
    }

    public FreeTrialQuota getFreeTrialQuota() {
        return freeTrialQuota;
    }

    public WorkflowSceneRsp setFreeTrialQuota(FreeTrialQuota freeTrialQuota) {
        this.freeTrialQuota = freeTrialQuota;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowSceneRsp {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    publishTime: ").append(toIndentedString(publishTime)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    prologue: ").append(toIndentedString(prologue)).append("\n");
        sb.append("    suggestQueries: ").append(toIndentedString(suggestQueries)).append("\n");
        sb.append("    freeTrialQuota: ").append(toIndentedString(freeTrialQuota)).append("\n");
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
        WorkflowSceneRsp workflowSceneRsp = (WorkflowSceneRsp) o;
        return Objects.equals(this.name, workflowSceneRsp.name) && Objects.equals(this.desc, workflowSceneRsp.desc)
            && Objects.equals(this.workflowId, workflowSceneRsp.workflowId) && Objects.equals(this.icon,
            workflowSceneRsp.icon) && Objects.equals(this.tags, workflowSceneRsp.tags) && Objects.equals(this.type,
            workflowSceneRsp.type) && Objects.equals(this.inputs, workflowSceneRsp.inputs) && Objects.equals(
            this.outputs, workflowSceneRsp.outputs) && Objects.equals(this.creator, workflowSceneRsp.creator)
            && Objects.equals(this.publishTime, workflowSceneRsp.publishTime) && Objects.equals(this.versionId,
            workflowSceneRsp.versionId) && Objects.equals(this.prologue, workflowSceneRsp.prologue) && Objects.equals(
            this.suggestQueries, workflowSceneRsp.suggestQueries) && Objects.equals(this.freeTrialQuota,
            workflowSceneRsp.freeTrialQuota);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, desc, workflowId, icon, tags, type, inputs, outputs, creator, publishTime, versionId,
            prologue, suggestQueries, freeTrialQuota);
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
