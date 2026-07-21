/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 知识型Agent执行请求体
 */
@ApiModel(description = "知识型Agent执行请求体")

@Validated

public class AgentRunReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("query")
    @Length(max = 1000000)
    @NotBlank
    private String query = null;

    @JsonProperty("inputs")
    @Valid
    @Size()
    private Map<String, Object> inputs = null;

    @JsonProperty("long_term_memory")
    @Valid
    private LongTermMemoryRuntime longTermMemory = null;

    @JsonProperty("tool_switch_dict")
    @Valid
    @Size()
    private Map<String, Boolean> toolSwitchDict = null;

    @JsonProperty("model_deployment_id")
    private String modelDeploymentId = null;

    @JsonProperty("enable_history")
    private Boolean enableHistory = true;

    @JsonProperty("histories")
    @Valid
    @Size()
    private List<com.openjiuwen.studio.agent.common.dto.agent.Message> histories = null;

    @JsonProperty("files")
    @Valid
    @Size(max = 100)
    private List<@Length(max = 1000) String> files = null;

    public String getQuery() {
        return query;
    }

    public AgentRunReq setQuery(String query) {
        this.query = query;
        return this;
    }

    public Map<String, Object> getInputs() {
        return inputs;
    }

    public AgentRunReq setInputs(Map<String, Object> inputs) {
        this.inputs = inputs;
        return this;
    }

    public LongTermMemoryRuntime getLongTermMemory() {
        return longTermMemory;
    }

    public AgentRunReq setLongTermMemory(LongTermMemoryRuntime longTermMemory) {
        this.longTermMemory = longTermMemory;
        return this;
    }

    public Map<String, Boolean> getToolSwitchDict() {
        return toolSwitchDict;
    }

    public AgentRunReq setToolSwitchDict(Map<String, Boolean> toolSwitchDict) {
        this.toolSwitchDict = toolSwitchDict;
        return this;
    }

    public String getModelDeploymentId() {
        return modelDeploymentId;
    }

    public AgentRunReq setModelDeploymentId(String modelDeploymentId) {
        this.modelDeploymentId = modelDeploymentId;
        return this;
    }

    public AgentRunReq setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    public List<com.openjiuwen.studio.agent.common.dto.agent.Message> getHistories() {
        return histories;
    }

    public AgentRunReq setHistories(List<com.openjiuwen.studio.agent.common.dto.agent.Message> histories) {
        this.histories = histories;
        return this;
    }

    public List<String> getFiles() {
        return files;
    }

    public AgentRunReq setFiles(List<String> files) {
        this.files = files;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentRunReq {\n");

        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    longTermMemory: ").append(toIndentedString(longTermMemory)).append("\n");
        sb.append("    toolSwitchDict: ").append(toIndentedString(toolSwitchDict)).append("\n");
        sb.append("    modelDeploymentId: ").append(toIndentedString(modelDeploymentId)).append("\n");
        sb.append("    enableHistory: ").append(toIndentedString(enableHistory)).append("\n");
        sb.append("    histories: ").append(toIndentedString(histories)).append("\n");
        sb.append("    files: ").append(toIndentedString(files)).append("\n");
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
        AgentRunReq agentRunReq = (AgentRunReq) o;
        return Objects.equals(this.query, agentRunReq.query) && Objects.equals(this.inputs, agentRunReq.inputs)
            && Objects.equals(this.longTermMemory, agentRunReq.longTermMemory) && Objects.equals(this.toolSwitchDict,
            agentRunReq.toolSwitchDict) && Objects.equals(this.modelDeploymentId, agentRunReq.modelDeploymentId)
            && Objects.equals(this.enableHistory, agentRunReq.enableHistory) && Objects.equals(this.histories,
            agentRunReq.histories) && Objects.equals(this.files, agentRunReq.files);
    }

    @Override
    public int hashCode() {
        return Objects.hash(query, inputs, longTermMemory, toolSwitchDict, modelDeploymentId, enableHistory, histories,
            files);
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
