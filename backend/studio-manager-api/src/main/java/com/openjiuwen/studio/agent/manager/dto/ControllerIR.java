/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * controller ir 对象。
 */
@ApiModel(description = "controller ir 对象。")

@Validated

public class ControllerIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("schemaVersion")
    @Schema(description = "Schema版本", example = "1.0")
    private String schemaVersion = null;

    @JsonProperty("agentId")
    @Schema(description = "Agent ID", example = "agent_001")
    private String agentId = null;

    @JsonProperty("agentVersion")
    @Schema(description = "Agent版本", example = "1.0.0")
    private String agentVersion = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "这是一个Agent")
    private String description = null;

    @JsonProperty("agentName")
    @Schema(description = "Agent名称", example = "my_agent")
    private String agentName = null;

    @JsonProperty("inputs")
    @Schema(description = "输入参数列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerParamIR> inputs = null;

    @JsonProperty("configs")
    @Schema(description = "配置", example = "{}")
    @Valid
    private ControllerConfigIR configs = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> metadata = null;

    public String getSchemaVersion() {
        return schemaVersion;
    }

    public ControllerIR setSchemaVersion(String schemaVersion) {
        this.schemaVersion = schemaVersion;
        return this;
    }

    public String getAgentId() {
        return agentId;
    }

    public ControllerIR setAgentId(String agentId) {
        this.agentId = agentId;
        return this;
    }

    public String getAgentVersion() {
        return agentVersion;
    }

    public ControllerIR setAgentVersion(String agentVersion) {
        this.agentVersion = agentVersion;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerIR setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getAgentName() {
        return agentName;
    }

    public ControllerIR setAgentName(String agentName) {
        this.agentName = agentName;
        return this;
    }

    public List<ControllerParamIR> getInputs() {
        return inputs;
    }

    public ControllerIR setInputs(List<ControllerParamIR> inputs) {
        this.inputs = inputs;
        return this;
    }

    public ControllerConfigIR getConfigs() {
        return configs;
    }

    public ControllerIR setConfigs(ControllerConfigIR configs) {
        this.configs = configs;
        return this;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public ControllerIR setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerIR {\n");

        sb.append("    schemaVersion: ").append(toIndentedString(schemaVersion)).append("\n");
        sb.append("    agentId: ").append(toIndentedString(agentId)).append("\n");
        sb.append("    agentVersion: ").append(toIndentedString(agentVersion)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    agentName: ").append(toIndentedString(agentName)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    configs: ").append(toIndentedString(configs)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
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
        ControllerIR controllerIR = (ControllerIR) o;
        return Objects.equals(this.schemaVersion, controllerIR.schemaVersion) && Objects.equals(this.agentId,
            controllerIR.agentId) && Objects.equals(this.agentVersion, controllerIR.agentVersion) && Objects.equals(
            this.description, controllerIR.description) && Objects.equals(this.agentName, controllerIR.agentName)
            && Objects.equals(this.inputs, controllerIR.inputs) && Objects.equals(this.configs, controllerIR.configs)
            && Objects.equals(this.metadata, controllerIR.metadata);
    }

    @Override
    public int hashCode() {
        return Objects.hash(schemaVersion, agentId, agentVersion, description, agentName, inputs, configs, metadata);
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
