/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * PromptBaseInfo
 */

@Validated
public class PromptBaseInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String taskId = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "示例文本")
    private String message = null;

    public String getTaskId() {
        return taskId;
    }

    public PromptBaseInfo setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public PromptBaseInfo setMessage(String message) {
        this.message = message;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptBaseInfo {\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
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
        PromptBaseInfo promptBaseInfo = (PromptBaseInfo) o;
        return Objects.equals(this.taskId, promptBaseInfo.taskId) && Objects.equals(this.message,
            promptBaseInfo.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskId, message);
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
