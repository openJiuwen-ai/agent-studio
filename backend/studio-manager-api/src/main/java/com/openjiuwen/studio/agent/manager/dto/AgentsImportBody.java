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
 * AgentsImportBody
 */

@Validated

public class AgentsImportBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file")
    @Schema(description = "导入文件", example = "agents.zip", required = true)
    @NotBlank
    private Resource file = null;

    @JsonProperty("import_agents")
    @Schema(description = "导入Agent标识", example = "true")
    private String importAgents = null;

    @JsonProperty("import_tools")
    @Schema(description = "导入工具标识", example = "true")
    private String importTools = null;

    @JsonProperty("import_workflows")
    @Schema(description = "导入工作流标识", example = "true")
    private String importWorkflows = null;

    public Resource getFile() {
        return file;
    }

    public AgentsImportBody setFile(Resource file) {
        this.file = file;
        return this;
    }

    public String getImportAgents() {
        return importAgents;
    }

    public AgentsImportBody setImportAgents(String importAgents) {
        this.importAgents = importAgents;
        return this;
    }

    public String getImportTools() {
        return importTools;
    }

    public AgentsImportBody setImportTools(String importTools) {
        this.importTools = importTools;
        return this;
    }

    public String getImportWorkflows() {
        return importWorkflows;
    }

    public AgentsImportBody setImportWorkflows(String importWorkflows) {
        this.importWorkflows = importWorkflows;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentsImportBody {\n");

        sb.append("    file: ").append(toIndentedString(file)).append("\n");
        sb.append("    importAgents: ").append(toIndentedString(importAgents)).append("\n");
        sb.append("    importTools: ").append(toIndentedString(importTools)).append("\n");
        sb.append("    importWorkflows: ").append(toIndentedString(importWorkflows)).append("\n");
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
        AgentsImportBody agentsImportBody = (AgentsImportBody) o;
        return Objects.equals(this.file, agentsImportBody.file) && Objects.equals(this.importAgents,
            agentsImportBody.importAgents) && Objects.equals(this.importTools, agentsImportBody.importTools)
            && Objects.equals(this.importWorkflows, agentsImportBody.importWorkflows);
    }

    @Override
    public int hashCode() {
        return Objects.hash(file, importAgents, importTools, importWorkflows);
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
