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
 * ControllerNodeConfigVOWorkflows
 */

@Validated

public class ControllerNodeConfigVOWorkflows implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    private String nodeId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "workflow-node")
    private String name = null;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "wf-001")
    private String id = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "workflow")
    private String type = null;

    @JsonProperty("action")
    @Schema(description = "动作", example = "start")
    private String action = null;

    public String getNodeId() {
        return nodeId;
    }

    public ControllerNodeConfigVOWorkflows setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerNodeConfigVOWorkflows setName(String name) {
        this.name = name;
        return this;
    }

    public String getId() {
        return id;
    }

    public ControllerNodeConfigVOWorkflows setId(String id) {
        this.id = id;
        return this;
    }

    public String getType() {
        return type;
    }

    public ControllerNodeConfigVOWorkflows setType(String type) {
        this.type = type;
        return this;
    }

    public String getAction() {
        return action;
    }

    public ControllerNodeConfigVOWorkflows setAction(String action) {
        this.action = action;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerNodeConfigVOWorkflows {\n");

        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    action: ").append(toIndentedString(action)).append("\n");
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
        ControllerNodeConfigVOWorkflows controllerNodeConfigVOWorkflows = (ControllerNodeConfigVOWorkflows) o;
        return Objects.equals(this.nodeId, controllerNodeConfigVOWorkflows.nodeId) && Objects.equals(this.name,
            controllerNodeConfigVOWorkflows.name) && Objects.equals(this.id, controllerNodeConfigVOWorkflows.id)
            && Objects.equals(this.type, controllerNodeConfigVOWorkflows.type) && Objects.equals(this.action,
            controllerNodeConfigVOWorkflows.action);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nodeId, name, id, type, action);
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
