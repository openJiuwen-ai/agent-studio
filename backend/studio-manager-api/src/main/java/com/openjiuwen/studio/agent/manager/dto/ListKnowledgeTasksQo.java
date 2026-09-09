/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListKnowledgeTasksQo: converted from multi query params
 */
@ApiModel(description = "ListKnowledgeTasksQo: converted from multi query params")

@Validated

public class ListKnowledgeTasksQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

    @JsonProperty("task_type")
    @Schema(description = "任务类型", example = "parse")
    @Length(min = 1, max = 16)
    private String taskType = null;

    @JsonProperty("task_status")
    @Schema(description = "任务状态", example = "success")
    @Length(min = 1, max = 64)
    private String taskStatus = null;

    @JsonProperty("file_name")
    @Schema(description = "文件名称", example = "doc.pdf")
    @Length(min = 1, max = 255)
    private String fileName = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListKnowledgeTasksQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListKnowledgeTasksQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListKnowledgeTasksQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getTaskType() {
        return taskType;
    }

    public ListKnowledgeTasksQo setTaskType(String taskType) {
        this.taskType = taskType;
        return this;
    }

    public String getTaskStatus() {
        return taskStatus;
    }

    public ListKnowledgeTasksQo setTaskStatus(String taskStatus) {
        this.taskStatus = taskStatus;
        return this;
    }

    public String getFileName() {
        return fileName;
    }

    public ListKnowledgeTasksQo setFileName(String fileName) {
        this.fileName = fileName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeTasksQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    taskType: ").append(toIndentedString(taskType)).append("\n");
        sb.append("    taskStatus: ").append(toIndentedString(taskStatus)).append("\n");
        sb.append("    fileName: ").append(toIndentedString(fileName)).append("\n");
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
        ListKnowledgeTasksQo listKnowledgeTasksQo = (ListKnowledgeTasksQo) o;
        return Objects.equals(this.workspaceId, listKnowledgeTasksQo.workspaceId) && Objects.equals(this.offset,
            listKnowledgeTasksQo.offset) && Objects.equals(this.limit, listKnowledgeTasksQo.limit) && Objects.equals(
            this.taskType, listKnowledgeTasksQo.taskType) && Objects.equals(this.taskStatus,
            listKnowledgeTasksQo.taskStatus) && Objects.equals(this.fileName, listKnowledgeTasksQo.fileName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, taskType, taskStatus, fileName);
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
