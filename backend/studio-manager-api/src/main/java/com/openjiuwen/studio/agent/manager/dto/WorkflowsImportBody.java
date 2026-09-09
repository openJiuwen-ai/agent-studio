/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;

import org.springframework.core.io.Resource;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * WorkflowsImportBody
 */

@Validated

public class WorkflowsImportBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file")
    @Schema(description = "文件", example = "file-content", required = true)
    @NotBlank
    private Resource file = null;

    @JsonProperty("import_workflows")
    @Schema(description = "导入", example = "示例字符串")
    private String importWorkflows = null;

    @JsonProperty("import_tools")
    @Schema(description = "导入", example = "示例字符串")
    private String importTools = null;

    public Resource getFile() {
        return file;
    }

    public WorkflowsImportBody setFile(Resource file) {
        this.file = file;
        return this;
    }

    public String getImportWorkflows() {
        return importWorkflows;
    }

    public WorkflowsImportBody setImportWorkflows(String importWorkflows) {
        this.importWorkflows = importWorkflows;
        return this;
    }

    public String getImportTools() {
        return importTools;
    }

    public WorkflowsImportBody setImportTools(String importTools) {
        this.importTools = importTools;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowsImportBody {\n");

        sb.append("    file: ").append(toIndentedString(file)).append("\n");
        sb.append("    importWorkflows: ").append(toIndentedString(importWorkflows)).append("\n");
        sb.append("    importTools: ").append(toIndentedString(importTools)).append("\n");
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
        WorkflowsImportBody workflowsImportBody = (WorkflowsImportBody) o;
        return Objects.equals(this.file, workflowsImportBody.file) && Objects.equals(this.importWorkflows,
            workflowsImportBody.importWorkflows) && Objects.equals(this.importTools, workflowsImportBody.importTools);
    }

    @Override
    public int hashCode() {
        return Objects.hash(file, importWorkflows, importTools);
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
