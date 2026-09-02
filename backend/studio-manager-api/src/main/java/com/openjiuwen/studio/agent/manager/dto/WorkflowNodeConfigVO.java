/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流节点config对象。
 */
@ApiModel(description = "工作流节点config对象。")

@Validated

public class WorkflowNodeConfigVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "节点ID", example = "node_001")
    private String id = null;

    @JsonProperty("intent")
    @Schema(description = "意图配置", example = "{}")
    @Valid
    private WorkflowNodeConfigVOIntent intent = null;

    @JsonProperty("name")
    @Schema(description = "节点名称", example = "意图识别")
    private String name = null;

    @JsonProperty("code")
    @Schema(description = "节点编码", example = "intent_node")
    private String code = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1.0.0")
    private String versionId = null;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "1.0.0")
    private String versionName = null;

    @JsonProperty("description")
    @Schema(description = "节点描述", example = "意图识别节点")
    private String description = null;

    @JsonProperty("original_info")
    @Schema(description = "原始信息", example = "{}")
    @Valid
    private WorkflowNodeConfigVOOriginalInfo originalInfo = null;

    public String getId() {
        return id;
    }

    public WorkflowNodeConfigVO setId(String id) {
        this.id = id;
        return this;
    }

    public WorkflowNodeConfigVOIntent getIntent() {
        return intent;
    }

    public WorkflowNodeConfigVO setIntent(WorkflowNodeConfigVOIntent intent) {
        this.intent = intent;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkflowNodeConfigVO setName(String name) {
        this.name = name;
        return this;
    }

    public String getCode() {
        return code;
    }

    public WorkflowNodeConfigVO setCode(String code) {
        this.code = code;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public WorkflowNodeConfigVO setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getVersionName() {
        return versionName;
    }

    public WorkflowNodeConfigVO setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowNodeConfigVO setDescription(String description) {
        this.description = description;
        return this;
    }

    public WorkflowNodeConfigVOOriginalInfo getOriginalInfo() {
        return originalInfo;
    }

    public WorkflowNodeConfigVO setOriginalInfo(WorkflowNodeConfigVOOriginalInfo originalInfo) {
        this.originalInfo = originalInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowNodeConfigVO {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    intent: ").append(toIndentedString(intent)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    originalInfo: ").append(toIndentedString(originalInfo)).append("\n");
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
        WorkflowNodeConfigVO workflowNodeConfigVO = (WorkflowNodeConfigVO) o;
        return Objects.equals(this.id, workflowNodeConfigVO.id) && Objects.equals(this.intent,
            workflowNodeConfigVO.intent) && Objects.equals(this.name, workflowNodeConfigVO.name) && Objects.equals(
            this.code, workflowNodeConfigVO.code) && Objects.equals(this.versionId, workflowNodeConfigVO.versionId)
            && Objects.equals(this.versionName, workflowNodeConfigVO.versionName) && Objects.equals(this.description,
            workflowNodeConfigVO.description) && Objects.equals(this.originalInfo, workflowNodeConfigVO.originalInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, intent, name, code, versionId, versionName, description, originalInfo);
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
