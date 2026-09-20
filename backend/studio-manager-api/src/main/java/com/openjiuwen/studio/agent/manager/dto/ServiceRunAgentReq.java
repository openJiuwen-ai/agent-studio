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
import java.util.Map;
import java.util.Objects;

/**
 * 知识型Agent执行请求体。
 */
@ApiModel(description = "知识型Agent执行请求体。")

@Validated

public class ServiceRunAgentReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("query")
    @Schema(description = "查询内容", example = "你好")
    @Length(max = 1000000)
    private String query = null;

    @JsonProperty("inputs")
    @Schema(description = "输入参数", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<String, Object> inputs = null;

    @JsonProperty("tool_switch_dict")
    @Schema(description = "工具开关字典", example = "{\"search\":true}")
    @Valid
    @Size()
    private Map<String, Boolean> toolSwitchDict = null;

    @JsonProperty("model_deployment_id")
    @Schema(description = "模型部署ID", example = "dep_001")
    @Length(max = 100)
    private String modelDeploymentId = null;

    @JsonProperty("enable_history")
    @Schema(description = "是否启用历史记录", example = "true")
    private Boolean enableHistory = true;

    @JsonProperty("long_term_memory")
    @Schema(description = "长期记忆配置", example = "{}")
    @Valid
    private LongTermMemoryRuntime longTermMemory = null;

    @JsonProperty("files")
    @Schema(description = "文件列表", example = "[\"file_001\"]")
    @Valid
    @Size()
    private List<@Length(max = 1000) String> files = null;

    public String getQuery() {
        return query;
    }

    public ServiceRunAgentReq setQuery(String query) {
        this.query = query;
        return this;
    }

    public Map<String, Object> getInputs() {
        return inputs;
    }

    public ServiceRunAgentReq setInputs(Map<String, Object> inputs) {
        this.inputs = inputs;
        return this;
    }

    public Map<String, Boolean> getToolSwitchDict() {
        return toolSwitchDict;
    }

    public ServiceRunAgentReq setToolSwitchDict(Map<String, Boolean> toolSwitchDict) {
        this.toolSwitchDict = toolSwitchDict;
        return this;
    }

    public String getModelDeploymentId() {
        return modelDeploymentId;
    }

    public ServiceRunAgentReq setModelDeploymentId(String modelDeploymentId) {
        this.modelDeploymentId = modelDeploymentId;
        return this;
    }

    public ServiceRunAgentReq setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    public LongTermMemoryRuntime getLongTermMemory() {
        return longTermMemory;
    }

    public ServiceRunAgentReq setLongTermMemory(LongTermMemoryRuntime longTermMemory) {
        this.longTermMemory = longTermMemory;
        return this;
    }

    public List<String> getFiles() {
        return files;
    }

    public ServiceRunAgentReq setFiles(List<String> files) {
        this.files = files;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ServiceRunAgentReq {\n");

        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    toolSwitchDict: ").append(toIndentedString(toolSwitchDict)).append("\n");
        sb.append("    modelDeploymentId: ").append(toIndentedString(modelDeploymentId)).append("\n");
        sb.append("    enableHistory: ").append(toIndentedString(enableHistory)).append("\n");
        sb.append("    longTermMemory: ").append(toIndentedString(longTermMemory)).append("\n");
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
        ServiceRunAgentReq serviceRunAgentReq = (ServiceRunAgentReq) o;
        return Objects.equals(this.query, serviceRunAgentReq.query) && Objects.equals(this.inputs,
            serviceRunAgentReq.inputs) && Objects.equals(this.toolSwitchDict, serviceRunAgentReq.toolSwitchDict)
            && Objects.equals(this.modelDeploymentId, serviceRunAgentReq.modelDeploymentId) && Objects.equals(
            this.enableHistory, serviceRunAgentReq.enableHistory) && Objects.equals(this.longTermMemory,
            serviceRunAgentReq.longTermMemory) && Objects.equals(this.files, serviceRunAgentReq.files);
    }

    @Override
    public int hashCode() {
        return Objects.hash(query, inputs, toolSwitchDict, modelDeploymentId, enableHistory, longTermMemory, files);
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
