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
 * SubControllerNodeConfigVOAgents
 */

@Validated

public class SubControllerNodeConfigVOAgents implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    private String nodeId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "agent-node")
    private String name = null;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "agent-001")
    private String id = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "agent")
    private String type = null;

    @JsonProperty("mode")
    @Schema(description = "模式", example = "auto")
    private String mode = null;

    public String getNodeId() {
        return nodeId;
    }

    public SubControllerNodeConfigVOAgents setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getName() {
        return name;
    }

    public SubControllerNodeConfigVOAgents setName(String name) {
        this.name = name;
        return this;
    }

    public String getId() {
        return id;
    }

    public SubControllerNodeConfigVOAgents setId(String id) {
        this.id = id;
        return this;
    }

    public String getType() {
        return type;
    }

    public SubControllerNodeConfigVOAgents setType(String type) {
        this.type = type;
        return this;
    }

    public String getMode() {
        return mode;
    }

    public SubControllerNodeConfigVOAgents setMode(String mode) {
        this.mode = mode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SubControllerNodeConfigVOAgents {\n");

        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        SubControllerNodeConfigVOAgents subControllerNodeConfigVOAgents = (SubControllerNodeConfigVOAgents) o;
        return Objects.equals(this.nodeId, subControllerNodeConfigVOAgents.nodeId) && Objects.equals(this.name,
            subControllerNodeConfigVOAgents.name) && Objects.equals(this.id, subControllerNodeConfigVOAgents.id)
            && Objects.equals(this.type, subControllerNodeConfigVOAgents.type) && Objects.equals(this.mode,
            subControllerNodeConfigVOAgents.mode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nodeId, name, id, type, mode);
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
