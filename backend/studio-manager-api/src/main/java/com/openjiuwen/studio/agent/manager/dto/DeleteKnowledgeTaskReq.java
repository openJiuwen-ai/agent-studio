/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * DeleteKnowledgeTaskReq
 */

@Validated

public class DeleteKnowledgeTaskReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("task_ids")
    @Schema(description = "任务", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<@Length(max = 100) String> taskIds = new ArrayList<String>();

    public List<String> getTaskIds() {
        return taskIds;
    }

    public DeleteKnowledgeTaskReq setTaskIds(List<String> taskIds) {
        this.taskIds = taskIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DeleteKnowledgeTaskReq {\n");

        sb.append("    taskIds: ").append(toIndentedString(taskIds)).append("\n");
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
        DeleteKnowledgeTaskReq deleteKnowledgeTaskReq = (DeleteKnowledgeTaskReq) o;
        return Objects.equals(this.taskIds, deleteKnowledgeTaskReq.taskIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskIds);
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
