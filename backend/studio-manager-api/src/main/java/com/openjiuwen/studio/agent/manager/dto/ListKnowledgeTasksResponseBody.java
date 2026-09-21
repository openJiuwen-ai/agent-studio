/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ListKnowledgeTasksResponseBody
 */

@Validated

public class ListKnowledgeTasksResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "任务总数", example = "100")
    @Range(min = 0L, max = 65535L)
    private Integer total = null;

    @JsonProperty("fail_count")
    @Schema(description = "失败数量", example = "5")
    @Range(min = 0L, max = 65535L)
    private Integer failCount = null;

    @JsonProperty("success_count")
    @Schema(description = "成功数量", example = "90")
    @Range(min = 0L, max = 65535L)
    private Integer successCount = null;

    @JsonProperty("running_count")
    @Schema(description = "运行中数量", example = "3")
    @Range(min = 0L, max = 65535L)
    private Integer runningCount = null;

    @JsonProperty("pending_count")
    @Schema(description = "等待中数量", example = "2")
    @Range(min = 0L, max = 65535L)
    private Integer pendingCount = null;

    @JsonProperty("tasks")
    @Schema(description = "任务列表", example = "[{\"id\":\"task-001\"}]")
    @Valid
    @Size(max = 65535)
    private List<KnowledgeTaskInfo> tasks = null;

    public Integer getTotal() {
        return total;
    }

    public ListKnowledgeTasksResponseBody setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public Integer getFailCount() {
        return failCount;
    }

    public ListKnowledgeTasksResponseBody setFailCount(Integer failCount) {
        this.failCount = failCount;
        return this;
    }

    public Integer getSuccessCount() {
        return successCount;
    }

    public ListKnowledgeTasksResponseBody setSuccessCount(Integer successCount) {
        this.successCount = successCount;
        return this;
    }

    public Integer getRunningCount() {
        return runningCount;
    }

    public ListKnowledgeTasksResponseBody setRunningCount(Integer runningCount) {
        this.runningCount = runningCount;
        return this;
    }

    public Integer getPendingCount() {
        return pendingCount;
    }

    public ListKnowledgeTasksResponseBody setPendingCount(Integer pendingCount) {
        this.pendingCount = pendingCount;
        return this;
    }

    public List<KnowledgeTaskInfo> getTasks() {
        return tasks;
    }

    public ListKnowledgeTasksResponseBody setTasks(List<KnowledgeTaskInfo> tasks) {
        this.tasks = tasks;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeTasksResponseBody {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    failCount: ").append(toIndentedString(failCount)).append("\n");
        sb.append("    successCount: ").append(toIndentedString(successCount)).append("\n");
        sb.append("    runningCount: ").append(toIndentedString(runningCount)).append("\n");
        sb.append("    pendingCount: ").append(toIndentedString(pendingCount)).append("\n");
        sb.append("    tasks: ").append(toIndentedString(tasks)).append("\n");
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
        ListKnowledgeTasksResponseBody listKnowledgeTasksResponseBody = (ListKnowledgeTasksResponseBody) o;
        return Objects.equals(this.total, listKnowledgeTasksResponseBody.total) && Objects.equals(this.failCount,
            listKnowledgeTasksResponseBody.failCount) && Objects.equals(this.successCount,
            listKnowledgeTasksResponseBody.successCount) && Objects.equals(this.runningCount,
            listKnowledgeTasksResponseBody.runningCount) && Objects.equals(this.pendingCount,
            listKnowledgeTasksResponseBody.pendingCount) && Objects.equals(this.tasks,
            listKnowledgeTasksResponseBody.tasks);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, failCount, successCount, runningCount, pendingCount, tasks);
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
