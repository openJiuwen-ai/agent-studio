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
 * ControllerNodeConfigVO
 */

@Validated

public class ControllerNodeConfigVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识ID", example = "node-001")
    private String id = null;

    @JsonProperty("intent")
    @Schema(description = "意图配置", example = "{}")
    @Valid
    private WorkflowNodeConfigVOIntent intent = null;

    @JsonProperty("name")
    @Schema(description = "节点名称", example = "控制器节点")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "节点描述", example = "控制器节点描述")
    private String description = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1")
    private String versionId = null;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "1.0.0")
    private String versionName = null;

    @JsonProperty("model")
    @Schema(description = "模型配置", example = "{}")
    @Valid
    private ModelConfigVO model = null;

    @JsonProperty("top_p")
    @Schema(description = "Top P采样参数", example = "0.9")
    private Float topP = null;

    @JsonProperty("temperature")
    @Schema(description = "温度参数", example = "0.7")
    private Float temperature = null;

    @JsonProperty("enable_history")
    @Schema(description = "是否启用历史记录", example = "true")
    private Boolean enableHistory = null;

    @JsonProperty("max_iteration")
    @Schema(description = "最大迭代次数", example = "10")
    private Integer maxIteration = null;

    @JsonProperty("workflows")
    @Schema(description = "工作流列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerNodeConfigVOWorkflows> workflows = null;

    @JsonProperty("agents")
    @Schema(description = "智能体列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerNodeConfigVOAgents> agents = null;

    @JsonProperty("specify_workflow_order")
    @Schema(description = "是否指定工作流顺序", example = "false")
    private Boolean specifyWorkflowOrder = null;

    @JsonProperty("global_intents")
    @Schema(description = "全局意图列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerNodeConfigVOGlobalIntents> globalIntents = null;

    @JsonProperty("prompt")
    @Schema(description = "提示词", example = "请根据用户输入生成回复")
    private String prompt = null;

    @JsonProperty("chat_history_max_turn")
    @Schema(description = "聊天历史最大轮次", example = "5")
    private Integer chatHistoryMaxTurn = null;

    @JsonProperty("mode")
    @Schema(description = "运行模式", example = "standard")
    private String mode = null;

    public String getId() {
        return id;
    }

    public ControllerNodeConfigVO setId(String id) {
        this.id = id;
        return this;
    }

    public WorkflowNodeConfigVOIntent getIntent() {
        return intent;
    }

    public ControllerNodeConfigVO setIntent(WorkflowNodeConfigVOIntent intent) {
        this.intent = intent;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerNodeConfigVO setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerNodeConfigVO setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public ControllerNodeConfigVO setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getVersionName() {
        return versionName;
    }

    public ControllerNodeConfigVO setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public ModelConfigVO getModel() {
        return model;
    }

    public ControllerNodeConfigVO setModel(ModelConfigVO model) {
        this.model = model;
        return this;
    }

    public Float getTopP() {
        return topP;
    }

    public ControllerNodeConfigVO setTopP(Float topP) {
        this.topP = topP;
        return this;
    }

    public Float getTemperature() {
        return temperature;
    }

    public ControllerNodeConfigVO setTemperature(Float temperature) {
        this.temperature = temperature;
        return this;
    }

    public ControllerNodeConfigVO setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    public Integer getMaxIteration() {
        return maxIteration;
    }

    public ControllerNodeConfigVO setMaxIteration(Integer maxIteration) {
        this.maxIteration = maxIteration;
        return this;
    }

    public List<ControllerNodeConfigVOWorkflows> getWorkflows() {
        return workflows;
    }

    public ControllerNodeConfigVO setWorkflows(List<ControllerNodeConfigVOWorkflows> workflows) {
        this.workflows = workflows;
        return this;
    }

    public List<ControllerNodeConfigVOAgents> getAgents() {
        return agents;
    }

    public ControllerNodeConfigVO setAgents(List<ControllerNodeConfigVOAgents> agents) {
        this.agents = agents;
        return this;
    }

    public ControllerNodeConfigVO setSpecifyWorkflowOrder(Boolean specifyWorkflowOrder) {
        this.specifyWorkflowOrder = specifyWorkflowOrder;
        return this;
    }

    public Boolean isSpecifyWorkflowOrder() {
        return specifyWorkflowOrder;
    }

    public List<ControllerNodeConfigVOGlobalIntents> getGlobalIntents() {
        return globalIntents;
    }

    public ControllerNodeConfigVO setGlobalIntents(List<ControllerNodeConfigVOGlobalIntents> globalIntents) {
        this.globalIntents = globalIntents;
        return this;
    }

    public String getPrompt() {
        return prompt;
    }

    public ControllerNodeConfigVO setPrompt(String prompt) {
        this.prompt = prompt;
        return this;
    }

    public Integer getChatHistoryMaxTurn() {
        return chatHistoryMaxTurn;
    }

    public ControllerNodeConfigVO setChatHistoryMaxTurn(Integer chatHistoryMaxTurn) {
        this.chatHistoryMaxTurn = chatHistoryMaxTurn;
        return this;
    }

    public String getMode() {
        return mode;
    }

    public ControllerNodeConfigVO setMode(String mode) {
        this.mode = mode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerNodeConfigVO {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    intent: ").append(toIndentedString(intent)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    topP: ").append(toIndentedString(topP)).append("\n");
        sb.append("    temperature: ").append(toIndentedString(temperature)).append("\n");
        sb.append("    enableHistory: ").append(toIndentedString(enableHistory)).append("\n");
        sb.append("    maxIteration: ").append(toIndentedString(maxIteration)).append("\n");
        sb.append("    workflows: ").append(toIndentedString(workflows)).append("\n");
        sb.append("    agents: ").append(toIndentedString(agents)).append("\n");
        sb.append("    specifyWorkflowOrder: ").append(toIndentedString(specifyWorkflowOrder)).append("\n");
        sb.append("    globalIntents: ").append(toIndentedString(globalIntents)).append("\n");
        sb.append("    prompt: ").append(toIndentedString(prompt)).append("\n");
        sb.append("    chatHistoryMaxTurn: ").append(toIndentedString(chatHistoryMaxTurn)).append("\n");
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
        ControllerNodeConfigVO controllerNodeConfigVO = (ControllerNodeConfigVO) o;
        return Objects.equals(this.id, controllerNodeConfigVO.id) && Objects.equals(this.intent,
            controllerNodeConfigVO.intent) && Objects.equals(this.name, controllerNodeConfigVO.name) && Objects.equals(
            this.description, controllerNodeConfigVO.description) && Objects.equals(this.versionId,
            controllerNodeConfigVO.versionId) && Objects.equals(this.versionName, controllerNodeConfigVO.versionName)
            && Objects.equals(this.model, controllerNodeConfigVO.model) && Objects.equals(this.topP,
            controllerNodeConfigVO.topP) && Objects.equals(this.temperature, controllerNodeConfigVO.temperature)
            && Objects.equals(this.enableHistory, controllerNodeConfigVO.enableHistory) && Objects.equals(
            this.maxIteration, controllerNodeConfigVO.maxIteration) && Objects.equals(this.workflows,
            controllerNodeConfigVO.workflows) && Objects.equals(this.agents, controllerNodeConfigVO.agents)
            && Objects.equals(this.specifyWorkflowOrder, controllerNodeConfigVO.specifyWorkflowOrder) && Objects.equals(
            this.globalIntents, controllerNodeConfigVO.globalIntents) && Objects.equals(this.prompt,
            controllerNodeConfigVO.prompt) && Objects.equals(this.chatHistoryMaxTurn,
            controllerNodeConfigVO.chatHistoryMaxTurn) && Objects.equals(this.mode, controllerNodeConfigVO.mode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, intent, name, description, versionId, versionName, model, topP, temperature,
            enableHistory, maxIteration, workflows, agents, specifyWorkflowOrder, globalIntents, prompt,
            chatHistoryMaxTurn, mode);
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
