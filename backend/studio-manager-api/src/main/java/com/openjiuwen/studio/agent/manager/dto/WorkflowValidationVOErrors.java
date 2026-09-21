/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * WorkflowValidationVOErrors
 */

@Validated

public class WorkflowValidationVOErrors implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    private String id = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "example-type")
    private String type = null;

    @JsonProperty("reason")
    @Schema(description = "原因", example = "原因示例")
    private String reason = null;

    public String getId() {
        return id;
    }

    public WorkflowValidationVOErrors setId(String id) {
        this.id = id;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowValidationVOErrors setType(String type) {
        this.type = type;
        return this;
    }

    public String getReason() {
        return reason;
    }

    public WorkflowValidationVOErrors setReason(String reason) {
        this.reason = reason;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowValidationVOErrors {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    reason: ").append(toIndentedString(reason)).append("\n");
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
        WorkflowValidationVOErrors workflowValidationVOErrors = (WorkflowValidationVOErrors) o;
        return Objects.equals(this.id, workflowValidationVOErrors.id) && Objects.equals(this.type,
            workflowValidationVOErrors.type) && Objects.equals(this.reason, workflowValidationVOErrors.reason);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, type, reason);
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
