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
import java.util.Date;
import java.util.Objects;

/**
 * 意图包信息概要结果
 */
@ApiModel(description = "意图包信息概要结果")

@Validated

public class ComplexIntentRsp implements Serializable {
    private static final long serialVersionUID = 1L;

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

    @JsonProperty("name")
    @Schema(description = "名称", example = "我的意图")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "意图描述")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("branches_cnt")
    @Schema(description = "分支数量", example = "3")
    private Integer branchesCnt = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user_001")
    @Length(max = 1024)
    private String creatorId = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000+00:00")
    private Date createTime = null;

    public String getIntentId() {
        return intentId;
    }

    public ComplexIntentRsp setIntentId(String intentId) {
        this.intentId = intentId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ComplexIntentRsp setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ComplexIntentRsp setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ComplexIntentRsp setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ComplexIntentRsp setDescription(String description) {
        this.description = description;
        return this;
    }

    public Integer getBranchesCnt() {
        return branchesCnt;
    }

    public ComplexIntentRsp setBranchesCnt(Integer branchesCnt) {
        this.branchesCnt = branchesCnt;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ComplexIntentRsp setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public ComplexIntentRsp setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentRsp {\n");

        sb.append("    intentId: ").append(toIndentedString(intentId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    branchesCnt: ").append(toIndentedString(branchesCnt)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
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
        ComplexIntentRsp complexIntentRsp = (ComplexIntentRsp) o;
        return Objects.equals(this.intentId, complexIntentRsp.intentId) && Objects.equals(this.projectId,
            complexIntentRsp.projectId) && Objects.equals(this.workspaceId, complexIntentRsp.workspaceId)
            && Objects.equals(this.name, complexIntentRsp.name) && Objects.equals(this.description,
            complexIntentRsp.description) && Objects.equals(this.branchesCnt, complexIntentRsp.branchesCnt)
            && Objects.equals(this.creatorId, complexIntentRsp.creatorId) && Objects.equals(this.createTime,
            complexIntentRsp.createTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(intentId, projectId, workspaceId, name, description, branchesCnt, creatorId, createTime);
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
