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
 * 环境信息
 */
@ApiModel(description = "环境信息")

@Validated

public class EnvironmentInstance implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("agentName")
    @Schema(description = "Agent名称", example = "my-agent")
    private String agentName = null;

    @JsonProperty("deployName")
    @Schema(description = "部署名称", example = "deploy-001")
    private String deployName = null;

    @JsonProperty("status")
    @Schema(description = "运行状态", example = "running")
    private String status = null;

    @JsonProperty("agentType")
    @Schema(description = "Agent类型", example = "chat")
    private String agentType = null;

    @JsonProperty("version")
    @Schema(description = "版本号", example = "1.0.0")
    private String version = null;

    @JsonProperty("workspaceName")
    @Schema(description = "工作空间名称", example = "my-workspace")
    private String workspaceName = null;

    public String getAgentName() {
        return agentName;
    }

    public EnvironmentInstance setAgentName(String agentName) {
        this.agentName = agentName;
        return this;
    }

    public String getDeployName() {
        return deployName;
    }

    public EnvironmentInstance setDeployName(String deployName) {
        this.deployName = deployName;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public EnvironmentInstance setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getAgentType() {
        return agentType;
    }

    public EnvironmentInstance setAgentType(String agentType) {
        this.agentType = agentType;
        return this;
    }

    public String getVersion() {
        return version;
    }

    public EnvironmentInstance setVersion(String version) {
        this.version = version;
        return this;
    }

    public String getWorkspaceName() {
        return workspaceName;
    }

    public EnvironmentInstance setWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentInstance {\n");

        sb.append("    agentName: ").append(toIndentedString(agentName)).append("\n");
        sb.append("    deployName: ").append(toIndentedString(deployName)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    agentType: ").append(toIndentedString(agentType)).append("\n");
        sb.append("    version: ").append(toIndentedString(version)).append("\n");
        sb.append("    workspaceName: ").append(toIndentedString(workspaceName)).append("\n");
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
        EnvironmentInstance environmentInstance = (EnvironmentInstance) o;
        return Objects.equals(this.agentName, environmentInstance.agentName) && Objects.equals(this.deployName,
            environmentInstance.deployName) && Objects.equals(this.status, environmentInstance.status)
            && Objects.equals(this.agentType, environmentInstance.agentType) && Objects.equals(this.version,
            environmentInstance.version) && Objects.equals(this.workspaceName, environmentInstance.workspaceName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(agentName, deployName, status, agentType, version, workspaceName);
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
