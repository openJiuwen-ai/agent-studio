/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * WorkflowValidationVO
 */

@Validated

public class WorkflowValidationVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("success")
    @Schema(description = "是否成功", example = "true")
    private Boolean success = null;

    @JsonProperty("errors")
    @Schema(description = "错误列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowValidationVOErrors> errors = null;

    public WorkflowValidationVO setSuccess(Boolean success) {
        this.success = success;
        return this;
    }

    public Boolean isSuccess() {
        return success;
    }

    public List<WorkflowValidationVOErrors> getErrors() {
        return errors;
    }

    public WorkflowValidationVO setErrors(List<WorkflowValidationVOErrors> errors) {
        this.errors = errors;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowValidationVO {\n");

        sb.append("    success: ").append(toIndentedString(success)).append("\n");
        sb.append("    errors: ").append(toIndentedString(errors)).append("\n");
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
        WorkflowValidationVO workflowValidationVO = (WorkflowValidationVO) o;
        return Objects.equals(this.success, workflowValidationVO.success) && Objects.equals(this.errors,
            workflowValidationVO.errors);
    }

    @Override
    public int hashCode() {
        return Objects.hash(success, errors);
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
