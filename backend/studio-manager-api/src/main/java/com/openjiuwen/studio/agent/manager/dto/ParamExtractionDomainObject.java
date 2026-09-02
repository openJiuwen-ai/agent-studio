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
 * ParamExtractionDomainObject
 */

@Validated

public class ParamExtractionDomainObject implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    @JsonProperty("processing_workflows")
    @Schema(description = "工作流列表", example = "[]")
    @Valid
    @Size()
    private List<ParamExtractionWorkflow> processingWorkflows = null;

    public String getName() {
        return name;
    }

    public ParamExtractionDomainObject setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ParamExtractionDomainObject setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<ParamExtractionWorkflow> getProcessingWorkflows() {
        return processingWorkflows;
    }

    public ParamExtractionDomainObject setProcessingWorkflows(List<ParamExtractionWorkflow> processingWorkflows) {
        this.processingWorkflows = processingWorkflows;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ParamExtractionDomainObject {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    processingWorkflows: ").append(toIndentedString(processingWorkflows)).append("\n");
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
        ParamExtractionDomainObject paramExtractionDomainObject = (ParamExtractionDomainObject) o;
        return Objects.equals(this.name, paramExtractionDomainObject.name) && Objects.equals(this.description,
            paramExtractionDomainObject.description) && Objects.equals(this.processingWorkflows,
            paramExtractionDomainObject.processingWorkflows);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, processingWorkflows);
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
