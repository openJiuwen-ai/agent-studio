/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * KnowledgeTaskInfo
 */

@Validated

public class KnowledgeTaskInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "知识任务ID", example = "task_001")
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "知识任务名称", example = "知识库构建任务")
    @Length(min = 1, max = 255)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "任务类型", example = "knowledge")
    @Length(max = 64)
    private String type = null;

    @JsonProperty("status")
    @Schema(description = "任务状态", example = "running")
    @Length(max = 64)
    private String status = null;

    @JsonProperty("process")
    @Schema(description = "处理进度", example = "50.0")
    @Range(min = 0L, max = 64L)
    private Float process = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1717200000000")
    @Range(min = 0L, max = 253402214400000L)
    private Long createTime = null;

    @JsonProperty("task_desc")
    @Schema(description = "任务描述", example = "构建知识库")
    @Length(min = 1, max = 255)
    private String taskDesc = null;

    public String getId() {
        return id;
    }

    public KnowledgeTaskInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public KnowledgeTaskInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public KnowledgeTaskInfo setType(String type) {
        this.type = type;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public KnowledgeTaskInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    public Float getProcess() {
        return process;
    }

    public KnowledgeTaskInfo setProcess(Float process) {
        this.process = process;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public KnowledgeTaskInfo setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getTaskDesc() {
        return taskDesc;
    }

    public KnowledgeTaskInfo setTaskDesc(String taskDesc) {
        this.taskDesc = taskDesc;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeTaskInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    process: ").append(toIndentedString(process)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    taskDesc: ").append(toIndentedString(taskDesc)).append("\n");
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
        KnowledgeTaskInfo knowledgeTaskInfo = (KnowledgeTaskInfo) o;
        return Objects.equals(this.id, knowledgeTaskInfo.id) && Objects.equals(this.name, knowledgeTaskInfo.name)
            && Objects.equals(this.type, knowledgeTaskInfo.type) && Objects.equals(this.status,
            knowledgeTaskInfo.status) && Objects.equals(this.process, knowledgeTaskInfo.process) && Objects.equals(
            this.createTime, knowledgeTaskInfo.createTime) && Objects.equals(this.taskDesc, knowledgeTaskInfo.taskDesc);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type, status, process, createTime, taskDesc);
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
