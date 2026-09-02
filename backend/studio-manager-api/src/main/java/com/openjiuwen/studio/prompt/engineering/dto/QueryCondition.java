/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryCondition
 */

@Validated
public class QueryCondition implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String taskId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Length(max = 255)
    private String name = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容")
    @Length(max = 10000)
    private String content = null;

    @JsonProperty("is_good_rating")
    @Schema(description = "isGoodRating", example = "true")
    private Boolean isGoodRating = false;

    @JsonProperty("type")
    @Schema(description = "类型", example = "1")
    private Integer type = null;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String fileId = null;

    public String getTaskId() {
        return taskId;
    }

    public QueryCondition setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getName() {
        return name;
    }

    public QueryCondition setName(String name) {
        this.name = name;
        return this;
    }

    public String getContent() {
        return content;
    }

    public QueryCondition setContent(String content) {
        this.content = content;
        return this;
    }

    public QueryCondition setIsGoodRating(Boolean isGoodRating) {
        this.isGoodRating = isGoodRating;
        return this;
    }

    public Boolean isIsGoodRating() {
        return isGoodRating;
    }

    public Integer getType() {
        return type;
    }

    public QueryCondition setType(Integer type) {
        this.type = type;
        return this;
    }

    public String getFileId() {
        return fileId;
    }

    public QueryCondition setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryCondition {\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    isGoodRating: ").append(toIndentedString(isGoodRating)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    fileId: ").append(toIndentedString(fileId)).append("\n");
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
        QueryCondition queryCondition = (QueryCondition) o;
        return Objects.equals(this.taskId, queryCondition.taskId) && Objects.equals(this.name, queryCondition.name)
            && Objects.equals(this.content, queryCondition.content) && Objects.equals(this.isGoodRating,
            queryCondition.isGoodRating) && Objects.equals(this.type, queryCondition.type) && Objects.equals(
            this.fileId, queryCondition.fileId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskId, name, content, isGoodRating, type, fileId);
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
