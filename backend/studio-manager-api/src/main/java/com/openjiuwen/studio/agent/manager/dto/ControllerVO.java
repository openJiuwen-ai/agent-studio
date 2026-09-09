/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 控制器和前端交互对象定义。
 */
@ApiModel(description = "控制器和前端交互对象定义。")

@Validated

public class ControllerVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "控制器ID", example = "ctrl_001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "控制器名称", example = "客服控制器", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "控制器描述", example = "处理客服交互的控制器")
    private String description = null;

    @JsonProperty("nodes")
    @Schema(description = "节点列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<ControllerNodeVO> nodes = new ArrayList<ControllerNodeVO>();

    @JsonProperty("edges")
    @Schema(description = "边列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowEdgeVO> edges = null;

    @JsonProperty("layouts")
    @Schema(description = "布局配置", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> layouts = null;

    @JsonProperty("inputs")
    @Schema(description = "输入字段列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFieldVO> inputs = null;

    @JsonProperty("memory_config")
    @Schema(description = "记忆配置", example = "{}")
    @Valid
    private AgentMemoryConfig memoryConfig = null;

    @JsonProperty("global_variables")
    @Schema(description = "全局变量列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFieldVO> globalVariables = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj_001")
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    private String workspaceId = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2026-09-01T12:00:00Z")
    private String updateTime = null;

    @JsonProperty("environment")
    @Schema(description = "环境标识", example = "production")
    private String environment = null;

    public String getId() {
        return id;
    }

    public ControllerVO setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerVO setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerVO setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<ControllerNodeVO> getNodes() {
        return nodes;
    }

    public ControllerVO setNodes(List<ControllerNodeVO> nodes) {
        this.nodes = nodes;
        return this;
    }

    public List<WorkflowEdgeVO> getEdges() {
        return edges;
    }

    public ControllerVO setEdges(List<WorkflowEdgeVO> edges) {
        this.edges = edges;
        return this;
    }

    public Map<String, Object> getLayouts() {
        return layouts;
    }

    public ControllerVO setLayouts(Map<String, Object> layouts) {
        this.layouts = layouts;
        return this;
    }

    public List<WorkflowFieldVO> getInputs() {
        return inputs;
    }

    public ControllerVO setInputs(List<WorkflowFieldVO> inputs) {
        this.inputs = inputs;
        return this;
    }

    public AgentMemoryConfig getMemoryConfig() {
        return memoryConfig;
    }

    public ControllerVO setMemoryConfig(AgentMemoryConfig memoryConfig) {
        this.memoryConfig = memoryConfig;
        return this;
    }

    public List<WorkflowFieldVO> getGlobalVariables() {
        return globalVariables;
    }

    public ControllerVO setGlobalVariables(List<WorkflowFieldVO> globalVariables) {
        this.globalVariables = globalVariables;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ControllerVO setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ControllerVO setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getUpdateTime() {
        return updateTime;
    }

    public ControllerVO setUpdateTime(String updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public String getEnvironment() {
        return environment;
    }

    public ControllerVO setEnvironment(String environment) {
        this.environment = environment;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerVO {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    nodes: ").append(toIndentedString(nodes)).append("\n");
        sb.append("    edges: ").append(toIndentedString(edges)).append("\n");
        sb.append("    layouts: ").append(toIndentedString(layouts)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    memoryConfig: ").append(toIndentedString(memoryConfig)).append("\n");
        sb.append("    globalVariables: ").append(toIndentedString(globalVariables)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    environment: ").append(toIndentedString(environment)).append("\n");
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
        ControllerVO controllerVO = (ControllerVO) o;
        return Objects.equals(this.id, controllerVO.id) && Objects.equals(this.name, controllerVO.name)
            && Objects.equals(this.description, controllerVO.description) && Objects.equals(this.nodes,
            controllerVO.nodes) && Objects.equals(this.edges, controllerVO.edges) && Objects.equals(this.layouts,
            controllerVO.layouts) && Objects.equals(this.inputs, controllerVO.inputs) && Objects.equals(
            this.memoryConfig, controllerVO.memoryConfig) && Objects.equals(this.globalVariables,
            controllerVO.globalVariables) && Objects.equals(this.projectId, controllerVO.projectId) && Objects.equals(
            this.workspaceId, controllerVO.workspaceId) && Objects.equals(this.updateTime, controllerVO.updateTime)
            && Objects.equals(this.environment, controllerVO.environment);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, nodes, edges, layouts, inputs, memoryConfig, globalVariables,
            projectId, workspaceId, updateTime, environment);
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
