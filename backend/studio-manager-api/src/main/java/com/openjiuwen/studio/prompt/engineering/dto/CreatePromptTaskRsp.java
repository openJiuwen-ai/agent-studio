/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建提示词优化工程响应
 */
@ApiModel(description = "创建提示词优化工程响应")

@Validated
public class CreatePromptTaskRsp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String taskId = null;

    public String getTaskId() {
        return taskId;
    }

    public CreatePromptTaskRsp setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreatePromptTaskRsp {\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
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
        CreatePromptTaskRsp createPromptTaskRsp = (CreatePromptTaskRsp) o;
        return Objects.equals(this.taskId, createPromptTaskRsp.taskId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskId);
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
