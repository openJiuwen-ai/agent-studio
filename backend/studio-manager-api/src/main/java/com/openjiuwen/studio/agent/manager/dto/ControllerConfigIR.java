/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * Controller Config 字段 IR结构。
 */
@ApiModel(description = "Controller Config 字段 IR结构。")

@Validated

public class ControllerConfigIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("intent_identification")
    @Schema(description = "意图识别配置", example = "{}")
    @Valid
    private ControllerConfigIRIntentIdentification intentIdentification = null;

    @JsonProperty("mode")
    @Schema(description = "控制器模式", example = "single")
    private String mode = null;

    @JsonProperty("specify_workflow_order")
    @Schema(description = "是否指定工作流顺序", example = "true")
    private Boolean specifyWorkflowOrder = null;

    @JsonProperty("modelConfig")
    @Schema(description = "模型配置", example = "{}")
    @Valid
    private ControllerConfigIRModelConfig modelConfig = null;

    @JsonProperty("workflows")
    @Schema(description = "工作流列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerWorkflowIR> workflows = null;

    @JsonProperty("agents")
    @Schema(description = "智能体列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerAgentIR> agents = null;

    @JsonProperty("maxIteration")
    @Schema(description = "最大迭代次数", example = "10")
    private Integer maxIteration = null;

    @JsonProperty("global_intents")
    @Schema(description = "全局意图列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerConfigIRGlobalIntents> globalIntents = null;

    @JsonProperty("global_variables")
    @Schema(description = "全局变量列表", example = "[]")
    @Valid
    @Size()
    private List<ControllerConfigIRGlobalVariables> globalVariables = null;

    @JsonProperty("sysPromptTemplate")
    @Schema(description = "系统提示词模板", example = "你是一个智能助手")
    private String sysPromptTemplate = null;

    @JsonProperty("plugins")
    @Schema(description = "插件列表", example = "[\"plugin1\"]")
    @Valid
    @Size()
    private List<@Length() String> plugins = null;

    @JsonProperty("chatHistoryMaxTurn")
    @Schema(description = "聊天历史最大轮次", example = "20")
    private Integer chatHistoryMaxTurn = null;

    @JsonProperty("memory")
    @Schema(description = "记忆配置", example = "{}")
    @Valid
    private MemoryConfigIR memory = null;

    public ControllerConfigIRIntentIdentification getIntentIdentification() {
        return intentIdentification;
    }

    public ControllerConfigIR setIntentIdentification(ControllerConfigIRIntentIdentification intentIdentification) {
        this.intentIdentification = intentIdentification;
        return this;
    }

    public String getMode() {
        return mode;
    }

    public ControllerConfigIR setMode(String mode) {
        this.mode = mode;
        return this;
    }

    public ControllerConfigIR setSpecifyWorkflowOrder(Boolean specifyWorkflowOrder) {
        this.specifyWorkflowOrder = specifyWorkflowOrder;
        return this;
    }

    public Boolean isSpecifyWorkflowOrder() {
        return specifyWorkflowOrder;
    }

    public ControllerConfigIRModelConfig getModelConfig() {
        return modelConfig;
    }

    public ControllerConfigIR setModelConfig(ControllerConfigIRModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    public List<ControllerWorkflowIR> getWorkflows() {
        return workflows;
    }

    public ControllerConfigIR setWorkflows(List<ControllerWorkflowIR> workflows) {
        this.workflows = workflows;
        return this;
    }

    public List<ControllerAgentIR> getAgents() {
        return agents;
    }

    public ControllerConfigIR setAgents(List<ControllerAgentIR> agents) {
        this.agents = agents;
        return this;
    }

    public Integer getMaxIteration() {
        return maxIteration;
    }

    public ControllerConfigIR setMaxIteration(Integer maxIteration) {
        this.maxIteration = maxIteration;
        return this;
    }

    public List<ControllerConfigIRGlobalIntents> getGlobalIntents() {
        return globalIntents;
    }

    public ControllerConfigIR setGlobalIntents(List<ControllerConfigIRGlobalIntents> globalIntents) {
        this.globalIntents = globalIntents;
        return this;
    }

    public List<ControllerConfigIRGlobalVariables> getGlobalVariables() {
        return globalVariables;
    }

    public ControllerConfigIR setGlobalVariables(List<ControllerConfigIRGlobalVariables> globalVariables) {
        this.globalVariables = globalVariables;
        return this;
    }

    public String getSysPromptTemplate() {
        return sysPromptTemplate;
    }

    public ControllerConfigIR setSysPromptTemplate(String sysPromptTemplate) {
        this.sysPromptTemplate = sysPromptTemplate;
        return this;
    }

    public List<String> getPlugins() {
        return plugins;
    }

    public ControllerConfigIR setPlugins(List<String> plugins) {
        this.plugins = plugins;
        return this;
    }

    public Integer getChatHistoryMaxTurn() {
        return chatHistoryMaxTurn;
    }

    public ControllerConfigIR setChatHistoryMaxTurn(Integer chatHistoryMaxTurn) {
        this.chatHistoryMaxTurn = chatHistoryMaxTurn;
        return this;
    }

    public MemoryConfigIR getMemory() {
        return memory;
    }

    public ControllerConfigIR setMemory(MemoryConfigIR memory) {
        this.memory = memory;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerConfigIR {\n");

        sb.append("    intentIdentification: ").append(toIndentedString(intentIdentification)).append("\n");
        sb.append("    mode: ").append(toIndentedString(mode)).append("\n");
        sb.append("    specifyWorkflowOrder: ").append(toIndentedString(specifyWorkflowOrder)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
        sb.append("    workflows: ").append(toIndentedString(workflows)).append("\n");
        sb.append("    agents: ").append(toIndentedString(agents)).append("\n");
        sb.append("    maxIteration: ").append(toIndentedString(maxIteration)).append("\n");
        sb.append("    globalIntents: ").append(toIndentedString(globalIntents)).append("\n");
        sb.append("    globalVariables: ").append(toIndentedString(globalVariables)).append("\n");
        sb.append("    sysPromptTemplate: ").append(toIndentedString(sysPromptTemplate)).append("\n");
        sb.append("    plugins: ").append(toIndentedString(plugins)).append("\n");
        sb.append("    chatHistoryMaxTurn: ").append(toIndentedString(chatHistoryMaxTurn)).append("\n");
        sb.append("    memory: ").append(toIndentedString(memory)).append("\n");
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
        ControllerConfigIR controllerConfigIR = (ControllerConfigIR) o;
        return Objects.equals(this.intentIdentification, controllerConfigIR.intentIdentification) && Objects.equals(
            this.mode, controllerConfigIR.mode) && Objects.equals(this.specifyWorkflowOrder,
            controllerConfigIR.specifyWorkflowOrder) && Objects.equals(this.modelConfig, controllerConfigIR.modelConfig)
            && Objects.equals(this.workflows, controllerConfigIR.workflows) && Objects.equals(this.agents,
            controllerConfigIR.agents) && Objects.equals(this.maxIteration, controllerConfigIR.maxIteration)
            && Objects.equals(this.globalIntents, controllerConfigIR.globalIntents) && Objects.equals(
            this.globalVariables, controllerConfigIR.globalVariables) && Objects.equals(this.sysPromptTemplate,
            controllerConfigIR.sysPromptTemplate) && Objects.equals(this.plugins, controllerConfigIR.plugins)
            && Objects.equals(this.chatHistoryMaxTurn, controllerConfigIR.chatHistoryMaxTurn) && Objects.equals(
            this.memory, controllerConfigIR.memory);
    }

    @Override
    public int hashCode() {
        return Objects.hash(intentIdentification, mode, specifyWorkflowOrder, modelConfig, workflows, agents,
            maxIteration, globalIntents, globalVariables, sysPromptTemplate, plugins, chatHistoryMaxTurn, memory);
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
