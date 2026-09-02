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
 * ControllerNodeConfigVOAgents
 */

@Validated

public class ControllerNodeConfigVOAgents implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    private String nodeId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "控制器节点")
    private String name = null;

    @JsonProperty("id")
    @Schema(description = "ID", example = "agent-001")
    private String id = null;

    @JsonProperty("mode")
    @Schema(description = "模式", example = "auto")
    private String mode = null;

    public String getNodeId() {
        return nodeId;
    }

    public ControllerNodeConfigVOAgents setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerNodeConfigVOAgents setName(String name) {
        this.name = name;
        return this;
    }

    public String getId() {
        return id;
    }

    public ControllerNodeConfigVOAgents setId(String id) {
        this.id = id;
        return this;
    }

    public String getMode() {
        return mode;
    }

    public ControllerNodeConfigVOAgents setMode(String mode) {
        this.mode = mode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerNodeConfigVOAgents {\n");

        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    mode: ").append(toIndentedString(mode)).append("\n");
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
        ControllerNodeConfigVOAgents controllerNodeConfigVOAgents = (ControllerNodeConfigVOAgents) o;
        return Objects.equals(this.nodeId, controllerNodeConfigVOAgents.nodeId) && Objects.equals(this.name,
            controllerNodeConfigVOAgents.name) && Objects.equals(this.id, controllerNodeConfigVOAgents.id)
            && Objects.equals(this.mode, controllerNodeConfigVOAgents.mode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nodeId, name, id, mode);
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
