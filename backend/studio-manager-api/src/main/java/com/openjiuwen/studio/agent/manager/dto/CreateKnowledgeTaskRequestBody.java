/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 创建知识库任务请求体
 */
@ApiModel(description = "创建知识库任务请求体")

@Validated

public class CreateKnowledgeTaskRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("task_type")
    @Schema(description = "任务类型", example = "STRING", required = true)
    @NotNull
    private TaskTypeEnum taskType = null;

    @JsonProperty("file_ids")
    @Schema(description = "文件", example = "[]")
    @Valid
    @Size(min = 1, max = 1000)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(min = 1, max = 64) String> fileIds = null;

    public TaskTypeEnum getTaskType() {
        return taskType;
    }

    public CreateKnowledgeTaskRequestBody setTaskType(TaskTypeEnum taskType) {
        this.taskType = taskType;
        return this;
    }

    public List<@Size(min = 1, max = 1000) String> getFileIds() {
        return fileIds;
    }

    public CreateKnowledgeTaskRequestBody setFileIds(List<@Size(min = 1, max = 1000) String> fileIds) {
        this.fileIds = fileIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateKnowledgeTaskRequestBody {\n");

        sb.append("    taskType: ").append(toIndentedString(taskType)).append("\n");
        sb.append("    fileIds: ").append(toIndentedString(fileIds)).append("\n");
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
        CreateKnowledgeTaskRequestBody createKnowledgeTaskRequestBody = (CreateKnowledgeTaskRequestBody) o;
        return Objects.equals(this.taskType, createKnowledgeTaskRequestBody.taskType) && Objects.equals(this.fileIds,
            createKnowledgeTaskRequestBody.fileIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskType, fileIds);
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

    /**
     * 任务类型，可取值：RETRY_FILES（部分文件重试）、QA（QA生成）
     */
    public enum TaskTypeEnum {
        RETRY_FILES("RETRY_FILES"),

        QA("QA");

        private String value;

        TaskTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static TaskTypeEnum fromValue(String text) {
            for (TaskTypeEnum b : TaskTypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
