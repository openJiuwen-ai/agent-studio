/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import com.openjiuwen.studio.agent.common.dto.WorkflowEnvironment;
import com.openjiuwen.studio.agent.common.dto.run.PluginConfig;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * ServiceWorkflowRunReq
 */

@Validated

public class ServiceWorkflowRunReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("inputs")
    @Schema(description = "输入参数", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> inputs = null;

    @JsonProperty("memory_inputs")
    @Schema(description = "记忆输入参数", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> memoryInputs = null;

    @JsonProperty("globals")
    @Schema(description = "全局变量", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> globals = null;

    @JsonProperty("environment")
    @Schema(description = "运行环境", example = "{}")
    @Valid
    private WorkflowEnvironment environment = null;

    @JsonProperty("messages")
    @Schema(description = "消息列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowMessage> messages = null;

    @JsonProperty("plugin_configs")
    @Schema(description = "插件配置列表", example = "[]")
    @Valid
    @Size()
    private List<PluginConfig> pluginConfigs = null;

    @JsonProperty("version")
    @Schema(description = "版本号", example = "1")
    private Long version = null;

    @JsonProperty("userId")
    @Schema(description = "用户ID", example = "user_001")
    private String userId = null;

    @JsonProperty("conversation")
    @Schema(description = "会话信息", example = "{}")
    @Valid
    private Conversation conversation = null;

    @JsonProperty("enable_history")
    @Schema(description = "是否启用历史记录", example = "true")
    private Boolean enableHistory = true;

    @JsonProperty("long_term_memory")
    @Schema(description = "长期记忆配置", example = "{}")
    @Valid
    private LongTermMemoryRuntime longTermMemory = null;

    public Map<String, Object> getInputs() {
        return inputs;
    }

    public ServiceWorkflowRunReq setInputs(Map<String, Object> inputs) {
        this.inputs = inputs;
        return this;
    }

    public Map<String, Object> getMemoryInputs() {
        return memoryInputs;
    }

    public ServiceWorkflowRunReq setMemoryInputs(Map<String, Object> memoryInputs) {
        this.memoryInputs = memoryInputs;
        return this;
    }

    public Map<String, Object> getGlobals() {
        return globals;
    }

    public ServiceWorkflowRunReq setGlobals(Map<String, Object> globals) {
        this.globals = globals;
        return this;
    }

    public WorkflowEnvironment getEnvironment() {
        return environment;
    }

    public ServiceWorkflowRunReq setEnvironment(WorkflowEnvironment environment) {
        this.environment = environment;
        return this;
    }

    public List<WorkflowMessage> getMessages() {
        return messages;
    }

    public ServiceWorkflowRunReq setMessages(List<WorkflowMessage> messages) {
        this.messages = messages;
        return this;
    }

    public List<PluginConfig> getPluginConfigs() {
        return pluginConfigs;
    }

    public ServiceWorkflowRunReq setPluginConfigs(List<PluginConfig> pluginConfigs) {
        this.pluginConfigs = pluginConfigs;
        return this;
    }

    public Long getVersion() {
        return version;
    }

    public ServiceWorkflowRunReq setVersion(Long version) {
        this.version = version;
        return this;
    }

    public String getUserId() {
        return userId;
    }

    public ServiceWorkflowRunReq setUserId(String userId) {
        this.userId = userId;
        return this;
    }

    public Conversation getConversation() {
        return conversation;
    }

    public ServiceWorkflowRunReq setConversation(Conversation conversation) {
        this.conversation = conversation;
        return this;
    }

    public ServiceWorkflowRunReq setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    public LongTermMemoryRuntime getLongTermMemory() {
        return longTermMemory;
    }

    public ServiceWorkflowRunReq setLongTermMemory(LongTermMemoryRuntime longTermMemory) {
        this.longTermMemory = longTermMemory;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ServiceWorkflowRunReq {\n");

        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    memoryInputs: ").append(toIndentedString(memoryInputs)).append("\n");
        sb.append("    globals: ").append(toIndentedString(globals)).append("\n");
        sb.append("    environment: ").append(toIndentedString(environment)).append("\n");
        sb.append("    messages: ").append(toIndentedString(messages)).append("\n");
        sb.append("    pluginConfigs: ").append(toIndentedString(pluginConfigs)).append("\n");
        sb.append("    version: ").append(toIndentedString(version)).append("\n");
        sb.append("    userId: ").append(toIndentedString(userId)).append("\n");
        sb.append("    conversation: ").append(toIndentedString(conversation)).append("\n");
        sb.append("    enableHistory: ").append(toIndentedString(enableHistory)).append("\n");
        sb.append("    longTermMemory: ").append(toIndentedString(longTermMemory)).append("\n");
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
        ServiceWorkflowRunReq serviceWorkflowRunReq = (ServiceWorkflowRunReq) o;
        return Objects.equals(this.inputs, serviceWorkflowRunReq.inputs) && Objects.equals(this.memoryInputs,
            serviceWorkflowRunReq.memoryInputs) && Objects.equals(this.globals, serviceWorkflowRunReq.globals)
            && Objects.equals(this.environment, serviceWorkflowRunReq.environment) && Objects.equals(this.messages,
            serviceWorkflowRunReq.messages) && Objects.equals(this.pluginConfigs, serviceWorkflowRunReq.pluginConfigs)
            && Objects.equals(this.version, serviceWorkflowRunReq.version) && Objects.equals(this.userId,
            serviceWorkflowRunReq.userId) && Objects.equals(this.conversation, serviceWorkflowRunReq.conversation)
            && Objects.equals(this.enableHistory, serviceWorkflowRunReq.enableHistory) && Objects.equals(
            this.longTermMemory, serviceWorkflowRunReq.longTermMemory);
    }

    @Override
    public int hashCode() {
        return Objects.hash(inputs, memoryInputs, globals, environment, messages, pluginConfigs, version, userId,
            conversation, enableHistory, longTermMemory);
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
