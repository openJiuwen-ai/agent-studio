/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * NotifyReq
 */

@Validated

public class NotifyReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("domain_id")
    @Schema(description = "域名", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @Length(min = 2, max = 64)
    private String domainId = null;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @Length(max = 64)
    private String taskId = null;

    public String getDomainId() {
        return domainId;
    }

    public NotifyReq setDomainId(String domainId) {
        this.domainId = domainId;
        return this;
    }

    public String getTaskId() {
        return taskId;
    }

    public NotifyReq setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class NotifyReq {\n");

        sb.append("    domainId: ").append(toIndentedString(domainId)).append("\n");
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
        NotifyReq notifyReq = (NotifyReq) o;
        return Objects.equals(this.domainId, notifyReq.domainId) && Objects.equals(this.taskId, notifyReq.taskId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(domainId, taskId);
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
