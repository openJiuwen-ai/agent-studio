/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * UpdateOrDeletePromptCheckDto
 */

@Validated
public class UpdateOrDeletePromptCheckDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String taskId = null;

    @JsonProperty("prompt_id")
    @Schema(description = "提示词ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String promptId = null;

    public String getTaskId() {
        return taskId;
    }

    public UpdateOrDeletePromptCheckDto setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getPromptId() {
        return promptId;
    }

    public UpdateOrDeletePromptCheckDto setPromptId(String promptId) {
        this.promptId = promptId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UpdateOrDeletePromptCheckDto {\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    promptId: ").append(toIndentedString(promptId)).append("\n");
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
        UpdateOrDeletePromptCheckDto updateOrDeletePromptCheckDto = (UpdateOrDeletePromptCheckDto) o;
        return Objects.equals(this.taskId, updateOrDeletePromptCheckDto.taskId) && Objects.equals(this.promptId,
            updateOrDeletePromptCheckDto.promptId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskId, promptId);
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
