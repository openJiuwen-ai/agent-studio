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
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 创建记忆库请求体
 */
@ApiModel(description = "创建记忆库请求体")

@Validated

public class CreateMemoryRepoRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "记忆库名称", example = "我的记忆库", required = true)
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!](?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!])?$")
    @NotBlank
    @Length(min = 1, max = 50)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "记忆库描述", example = "用于存储用户对话记忆")
    @Length(max = 1000)
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "记忆库图标", example = "memory-icon")
    private String icon = null;

    @JsonProperty("long_term_memory_strategies")
    @Schema(description = "长期记忆策略列表", example = "[{\"type\":\"summary\"}]")
    @Valid
    @NotNull
    @Size(min = 1, max = 200)
    private List<LongTermMemoryStrategy> longTermMemoryStrategies = null;

    @JsonProperty("conversation_round")
    @Schema(description = "对话轮次", example = "10")
    private Integer conversationRound = null;

    @JsonProperty("time_span")
    @Schema(description = "时间跨度（秒）", example = "3600")
    private Integer timeSpan = null;

    @JsonProperty("memory_backend_type")
    @Schema(description = "记忆后端类型：BUILTIN（内置）/EXTERNAL（外部），默认BUILTIN", example = "BUILTIN")
    private String memoryBackendType = null;

    @JsonProperty("memory_service_instance_id")
    @Schema(description = "外部记忆服务实例ID（EXTERNAL时必填）", example = "instance-001")
    private String memoryServiceInstanceId = null;

    @JsonProperty("scope_model_config")
    @Schema(description = "scope级模型配置JSON（LLM/Embedding + enable_*），由manager推送到实例，不进IR")
    private String scopeModelConfig = null;

    public String getName() {
        return name;
    }

    public CreateMemoryRepoRequestBody setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public CreateMemoryRepoRequestBody setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public CreateMemoryRepoRequestBody setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public List<LongTermMemoryStrategy> getLongTermMemoryStrategies() {
        return longTermMemoryStrategies;
    }

    public CreateMemoryRepoRequestBody setLongTermMemoryStrategies(
        List<LongTermMemoryStrategy> longTermMemoryStrategies) {
        this.longTermMemoryStrategies = longTermMemoryStrategies;
        return this;
    }

    public Integer getConversationRound() {
        return conversationRound;
    }

    public CreateMemoryRepoRequestBody setConversationRound(Integer conversationRound) {
        this.conversationRound = conversationRound;
        return this;
    }

    public Integer getTimeSpan() {
        return timeSpan;
    }

    public CreateMemoryRepoRequestBody setTimeSpan(Integer timeSpan) {
        this.timeSpan = timeSpan;
        return this;
    }

    public String getMemoryBackendType() {
        return memoryBackendType;
    }

    public CreateMemoryRepoRequestBody setMemoryBackendType(String memoryBackendType) {
        this.memoryBackendType = memoryBackendType;
        return this;
    }

    public String getMemoryServiceInstanceId() {
        return memoryServiceInstanceId;
    }

    public CreateMemoryRepoRequestBody setMemoryServiceInstanceId(String memoryServiceInstanceId) {
        this.memoryServiceInstanceId = memoryServiceInstanceId;
        return this;
    }

    public String getScopeModelConfig() {
        return scopeModelConfig;
    }

    public CreateMemoryRepoRequestBody setScopeModelConfig(String scopeModelConfig) {
        this.scopeModelConfig = scopeModelConfig;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateMemoryRepoRequestBody {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    longTermMemoryStrategies: ").append(toIndentedString(longTermMemoryStrategies)).append("\n");
        sb.append("    conversationRound: ").append(toIndentedString(conversationRound)).append("\n");
        sb.append("    timeSpan: ").append(toIndentedString(timeSpan)).append("\n");
        sb.append("    memoryBackendType: ").append(toIndentedString(memoryBackendType)).append("\n");
        sb.append("    memoryServiceInstanceId: ").append(toIndentedString(memoryServiceInstanceId)).append("\n");
        sb.append("    scopeModelConfig: ").append(toIndentedString(scopeModelConfig)).append("\n");
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
        CreateMemoryRepoRequestBody createMemoryRepoRequestBody = (CreateMemoryRepoRequestBody) o;
        return Objects.equals(this.name, createMemoryRepoRequestBody.name) && Objects.equals(this.description,
            createMemoryRepoRequestBody.description) && Objects.equals(this.icon, createMemoryRepoRequestBody.icon)
            && Objects.equals(this.longTermMemoryStrategies, createMemoryRepoRequestBody.longTermMemoryStrategies)
            && Objects.equals(this.conversationRound, createMemoryRepoRequestBody.conversationRound)
            && Objects.equals(this.timeSpan, createMemoryRepoRequestBody.timeSpan)
            && Objects.equals(this.memoryBackendType, createMemoryRepoRequestBody.memoryBackendType)
            && Objects.equals(this.memoryServiceInstanceId, createMemoryRepoRequestBody.memoryServiceInstanceId)
            && Objects.equals(this.scopeModelConfig, createMemoryRepoRequestBody.scopeModelConfig);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, icon, longTermMemoryStrategies, conversationRound, timeSpan,
            memoryBackendType, memoryServiceInstanceId, scopeModelConfig);
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
