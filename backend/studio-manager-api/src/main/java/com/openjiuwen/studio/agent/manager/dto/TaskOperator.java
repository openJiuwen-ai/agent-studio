/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工具编排
 */
@ApiModel(description = "工具编排")

@Validated

public class TaskOperator implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "操作ID", example = "op-001")
    private String id = null;

    @JsonProperty("type")
    @Schema(description = "操作类型", example = "tool")
    private String type = null;

    @JsonProperty("title")
    @Schema(description = "操作标题", example = "查询操作")
    private String title = null;

    @JsonProperty("description")
    @Schema(description = "操作描述", example = "执行数据查询")
    private String description = null;

    public String getId() {
        return id;
    }

    public TaskOperator setId(String id) {
        this.id = id;
        return this;
    }

    public String getType() {
        return type;
    }

    public TaskOperator setType(String type) {
        this.type = type;
        return this;
    }

    public String getTitle() {
        return title;
    }

    public TaskOperator setTitle(String title) {
        this.title = title;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public TaskOperator setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TaskOperator {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    title: ").append(toIndentedString(title)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        TaskOperator taskOperator = (TaskOperator) o;
        return Objects.equals(this.id, taskOperator.id) && Objects.equals(this.type, taskOperator.type)
            && Objects.equals(this.title, taskOperator.title) && Objects.equals(this.description,
            taskOperator.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, type, title, description);
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
